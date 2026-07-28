//! A standalone node: the consensus-complete `NodeState` + crash-safe persistence + a real TCP
//! block-sync. NOT money.
//!
//! This is the transport that turns the validator into a runnable node. The sync is deliberately
//! minimal (the full gossip/mempool/DoS transport lives, tested, in the Python `netnode`): a client
//! sends its current height; the server replies with every main-chain block above it, framed; the
//! client validates each into its own `NodeState` and persists it. Two nodes end in sync — over
//! real TCP, with every block re-validated by the native consensus.

use std::collections::HashSet;
use std::io::{self, Read, Write};
use std::net::{TcpStream, ToSocketAddrs};
use std::path::Path;

use crate::mempool::Mempool;
use crate::reorg::NodeState;
use crate::rules::Rules;
use crate::store::BlockStore;
use crate::wallet::Wallet;
use crate::wire::{frame, read_message};
use crate::{block_hash, dsha256, validate_context_free};

type Peer = (String, u16);

const BAN_THRESHOLD: i32 = 20; // drop a peer once its misbehavior score reaches this
const MAX_MESSAGES: u64 = 5_000_000; // bound messages per session (flood cap)

// ---- bounds-safe structural check (never panics on adversarial bytes) ----------
fn read_compact_safe(d: &[u8], i: usize) -> Option<(u64, usize)> {
    let b = *d.get(i)?;
    match b {
        0xff if i + 9 <= d.len() => Some((u64::from_le_bytes(d[i + 1..i + 9].try_into().unwrap()), i + 9)),
        0xfe if i + 5 <= d.len() => Some((u32::from_le_bytes(d[i + 1..i + 5].try_into().unwrap()) as u64, i + 5)),
        0xfd if i + 3 <= d.len() => Some((u16::from_le_bytes(d[i + 1..i + 3].try_into().unwrap()) as u64, i + 3)),
        b if b < 0xfd => Some((b as u64, i + 1)),
        _ => None,
    }
}

fn tx_len_safe(d: &[u8], off: usize) -> Option<usize> {
    let mut i = off.checked_add(4)?;
    if i > d.len() {
        return None;
    }
    let (nin, ni) = read_compact_safe(d, i)?;
    i = ni;
    for _ in 0..nin {
        i = i.checked_add(36)?;
        if i > d.len() {
            return None;
        }
        let (slen, si) = read_compact_safe(d, i)?;
        i = si.checked_add(slen as usize)?.checked_add(4)?;
        if i > d.len() {
            return None;
        }
    }
    let (nout, no) = read_compact_safe(d, i)?;
    i = no;
    for _ in 0..nout {
        i = i.checked_add(8)?;
        if i > d.len() {
            return None;
        }
        let (slen, si) = read_compact_safe(d, i)?;
        i = si.checked_add(slen as usize)?;
        if i > d.len() {
            return None;
        }
    }
    i = i.checked_add(4)?;
    if i > d.len() {
        return None;
    }
    Some(i - off)
}

/// True iff `raw` is a structurally well-formed block (bounds-checked) — a **panic-safe** gate for
/// untrusted network bytes before any further parsing.
fn well_formed_block(raw: &[u8]) -> bool {
    if raw.len() < 81 {
        return false;
    }
    let body = &raw[80..];
    let (ntx, mut i) = match read_compact_safe(body, 0) {
        Some(x) => x,
        None => return false,
    };
    if ntx == 0 {
        return false;
    }
    for _ in 0..ntx {
        match tx_len_safe(body, i) {
            Some(l) => i += l,
            None => return false,
        }
    }
    i == body.len()
}

/// True iff `raw` is a structurally well-formed transaction that consumes exactly its bytes — the
/// **panic-safe** gate for an untrusted `tx` message before the (indexing, `with_capacity`) `parse_tx`.
fn well_formed_tx(raw: &[u8]) -> bool {
    matches!(tx_len_safe(raw, 0), Some(l) if l == raw.len())
}

fn encode_addrs(addrs: &[Peer]) -> Vec<u8> {
    let mut o = (addrs.len() as u16).to_le_bytes().to_vec();
    for (host, port) in addrs {
        let hb = host.as_bytes();
        let n = hb.len().min(255);
        o.push(n as u8);
        o.extend_from_slice(&hb[..n]);
        o.extend_from_slice(&port.to_le_bytes());
    }
    o
}

fn decode_addrs(p: &[u8]) -> Vec<Peer> {
    let mut out = Vec::new();
    if p.len() < 2 {
        return out;
    }
    let n = u16::from_le_bytes(p[0..2].try_into().unwrap()) as usize;
    let mut i = 2;
    for _ in 0..n.min(1000) {
        if i >= p.len() {
            break;
        }
        let ln = p[i] as usize;
        i += 1;
        if i + ln + 2 > p.len() {
            break;
        }
        let host = String::from_utf8_lossy(&p[i..i + ln]).to_string();
        i += ln;
        let port = u16::from_le_bytes(p[i..i + 2].try_into().unwrap());
        i += 2;
        if !host.is_empty() && port != 0 {
            out.push((host, port));
        }
    }
    out
}

fn inv_payload(hashes: &[[u8; 32]]) -> Vec<u8> {
    let mut o = (hashes.len() as u32).to_le_bytes().to_vec();
    for h in hashes {
        o.extend_from_slice(h);
    }
    o
}

fn parse_inv(p: &[u8]) -> Vec<[u8; 32]> {
    let mut out = Vec::new();
    if p.len() < 4 {
        return out;
    }
    let n = u32::from_le_bytes(p[0..4].try_into().unwrap()) as usize;
    let mut i = 4;
    for _ in 0..n {
        if i + 32 > p.len() {
            break;
        }
        let mut h = [0u8; 32];
        h.copy_from_slice(&p[i..i + 32]);
        out.push(h);
        i += 32;
    }
    out
}

pub struct Node {
    pub state: NodeState,
    pub mempool: Mempool,
    store: BlockStore,
    magic: [u8; 4],
    maturity: i64,
    advertise: Option<Peer>,
    known: HashSet<Peer>,
    wallet: Option<Wallet>,
}

impl Node {
    /// Open (or create) a node at `dir`. If the store is empty it is seeded with `genesis`;
    /// otherwise the chain is reloaded from disk. Either way the validated chain is activated.
    pub fn open(
        dir: &Path,
        rules: Rules,
        maturity: i64,
        min_bits: Option<u32>,
        magic: [u8; 4],
        genesis: &[u8],
    ) -> io::Result<Self> {
        let mut store = BlockStore::open(dir)?;
        let mut state = NodeState::new(rules, maturity, min_bits);
        let existing = store.read_all()?;
        if existing.is_empty() {
            state.add_block(genesis);
            store.append(genesis)?;
        } else {
            for raw in &existing {
                state.add_block(raw);
            }
        }
        state.activate_best();
        Ok(Node {
            state,
            mempool: Mempool::new(maturity),
            store,
            magic,
            maturity,
            advertise: None,
            known: HashSet::new(),
            wallet: None,
        })
    }

    // -- wallet (present only when enabled) ------------------------------------
    pub fn enable_wallet(&mut self, seed: [u8; 32]) {
        self.wallet = Some(Wallet::new(seed));
    }

    /// The receive scriptPubKey (bare P2PK) — e.g. for a miner to pay the coinbase to.
    pub fn wallet_receive_spk(&self) -> Option<Vec<u8>> {
        Some(self.wallet.as_ref()?.receive_spk())
    }

    pub fn wallet_new_address(&mut self) -> Option<Vec<u8>> {
        Some(self.wallet.as_mut()?.new_address())
    }

    pub fn wallet_balance(&self) -> Option<i64> {
        let w = self.wallet.as_ref()?;
        Some(w.balance(self.state.utxo(), self.state.height(), self.maturity))
    }

    /// Build + sign a payment from the wallet, submit it to the mempool, and return the txid.
    pub fn wallet_send(&mut self, to: &[u8], amount: i64, fee: i64) -> Result<[u8; 32], &'static str> {
        let raw = {
            let w = self.wallet.as_ref().ok_or("no wallet")?;
            w.create_payment(self.state.utxo(), self.state.height(), self.maturity, to, amount, fee)?
        };
        let txid = dsha256(&raw);
        self.submit_tx(&raw)?;
        Ok(txid)
    }

    /// Set this node's own reachable address, gossiped so peers can dial it back.
    pub fn set_advertise(&mut self, host: &str, port: u16) {
        self.advertise = Some((host.to_string(), port));
    }

    /// Learn a peer address (as `--connect` / bootstrap would).
    pub fn add_peer(&mut self, host: &str, port: u16) {
        self.known.insert((host.to_string(), port));
    }

    /// The peers this node knows (learned via `addr` gossip or seeded).
    pub fn known_peers(&self) -> Vec<Peer> {
        let mut v: Vec<Peer> = self.known.iter().cloned().collect();
        v.sort();
        v
    }

    pub fn height(&self) -> i64 {
        self.state.height()
    }

    pub fn tip(&self) -> Option<[u8; 32]> {
        self.state.tip()
    }

    pub fn balance(&self) -> i64 {
        self.state.balance()
    }

    /// Add a block we produced/received: validate into the chain and persist it.
    pub fn submit_block(&mut self, raw: &[u8]) -> io::Result<()> {
        self.state.add_block(raw);
        self.state.activate_best();
        self.mempool.reconcile(self.state.utxo(), self.state.height());
        self.store.append(raw)
    }

    /// Validate a transaction into our mempool. Returns the fee, or the reason it was rejected.
    pub fn submit_tx(&mut self, raw: &[u8]) -> Result<i64, &'static str> {
        let h = self.state.height();
        self.mempool.accept(raw, self.state.utxo(), h)
    }

    /// Serve a peer: read its height, send every main-chain block above it, announce our mempool
    /// (`inv`), then answer its `getdata` with the requested transactions.
    pub fn serve(&self, stream: &mut TcpStream) -> io::Result<()> {
        let mut h = [0u8; 4];
        stream.read_exact(&mut h)?;
        let from = i32::from_le_bytes(h) as i64;
        for hh in self.state.index.main_chain() {
            let e = self.state.index.get(&hh).unwrap();
            if e.height > from {
                stream.write_all(&frame("block", &e.raw, &self.magic))?;
            }
        }
        stream.write_all(&frame("inv", &inv_payload(&self.mempool.txids()), &self.magic))?;
        let mut sample: Vec<Peer> = Vec::new();
        if let Some(a) = &self.advertise {
            sample.push(a.clone()); // our own reachable address
        }
        sample.extend(self.known.iter().cloned()); // + the peers we know
        stream.write_all(&frame("addr", &encode_addrs(&sample), &self.magic))?;
        stream.flush()?;
        if let Some((command, payload)) = read_message(stream, &self.magic)? {
            if command == "getdata" {
                for want in parse_inv(&payload) {
                    if let Some(raw) = self.mempool.get(&want) {
                        stream.write_all(&frame("tx", raw, &self.magic))?;
                    }
                }
            }
        }
        stream.flush()
    }

    /// Sync from a peer at `addr`: send our height, validate + persist the blocks it sends, then
    /// request the mempool transactions we're missing (`getdata`) and pool the ones it returns.
    pub fn sync_from<A: ToSocketAddrs>(&mut self, addr: A) -> io::Result<()> {
        let mut s = TcpStream::connect(addr)?;
        s.write_all(&(self.height() as i32).to_le_bytes())?;
        s.flush()?;
        let mut misbehavior: i32 = 0;
        let mut messages: u64 = 0;
        while let Some((command, payload)) = read_message(&mut s, &self.magic)? {
            messages += 1;
            if messages > MAX_MESSAGES {
                return Err(io::Error::new(io::ErrorKind::InvalidData, "peer flooded (too many messages)"));
            }
            match command.as_str() {
                "block" => {
                    // panic-safe gate: reject a malformed block from a hostile peer, and score it
                    if !well_formed_block(&payload) || validate_context_free(&payload).is_err() {
                        misbehavior += 5;
                    } else {
                        let bh = block_hash(&payload);
                        self.state.add_block(&payload);
                        self.state.activate_best();
                        if self.state.is_invalid(&bh) {
                            misbehavior += 5; // structurally fine but consensus-invalid
                        } else {
                            self.mempool.reconcile(self.state.utxo(), self.state.height());
                            self.store.append(&payload)?;
                        }
                    }
                }
                "inv" => {
                    let want: Vec<[u8; 32]> =
                        parse_inv(&payload).into_iter().filter(|h| !self.mempool.has(h)).collect();
                    s.write_all(&frame("getdata", &inv_payload(&want), &self.magic))?;
                    s.flush()?;
                }
                "tx" => {
                    // panic-safe gate: never hand a malformed tx to the indexing parser (with_capacity /
                    // slice unwraps would panic); a hostile peer that floods them is scored and dropped.
                    if !well_formed_tx(&payload) {
                        misbehavior += 5;
                    } else {
                        let h = self.state.height();
                        if self.mempool.accept(&payload, self.state.utxo(), h).is_err() {
                            misbehavior += 1;
                        }
                    }
                }
                "addr" => {
                    for peer in decode_addrs(&payload) {
                        self.known.insert(peer); // learn peers via gossip (discovery)
                    }
                }
                _ => misbehavior += 1, // unknown command
            }
            if misbehavior >= BAN_THRESHOLD {
                return Err(io::Error::new(io::ErrorKind::InvalidData, "peer banned (misbehavior)"));
            }
        }
        Ok(())
    }
}
