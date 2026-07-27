//! A standalone node: the consensus-complete `NodeState` + crash-safe persistence + a real TCP
//! block-sync. NOT money.
//!
//! This is the transport that turns the validator into a runnable node. The sync is deliberately
//! minimal (the full gossip/mempool/DoS transport lives, tested, in the Python `netnode`): a client
//! sends its current height; the server replies with every main-chain block above it, framed; the
//! client validates each into its own `NodeState` and persists it. Two nodes end in sync — over
//! real TCP, with every block re-validated by the native consensus.

use std::io::{self, Read, Write};
use std::net::{TcpStream, ToSocketAddrs};
use std::path::Path;

use crate::reorg::NodeState;
use crate::rules::Rules;
use crate::store::BlockStore;
use crate::wire::{frame, read_message};

pub struct Node {
    pub state: NodeState,
    store: BlockStore,
    magic: [u8; 4],
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
        Ok(Node { state, store, magic })
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

    /// Serve a peer: read its height, send every main-chain block above it.
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
        stream.flush()
    }

    /// Sync from a peer at `addr`: send our height, then validate + persist the blocks it sends.
    pub fn sync_from<A: ToSocketAddrs>(&mut self, addr: A) -> io::Result<()> {
        let mut s = TcpStream::connect(addr)?;
        s.write_all(&(self.height() as i32).to_le_bytes())?;
        s.flush()?;
        while let Some((command, payload)) = read_message(&mut s, &self.magic)? {
            if command == "block" {
                self.state.add_block(&payload);
                self.state.activate_best();
                self.store.append(&payload)?;
            }
        }
        Ok(())
    }
}
