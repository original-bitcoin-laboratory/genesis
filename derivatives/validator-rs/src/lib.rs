//! A dependency-free Rust port of the X-chain **context-free block validator**. NOT money.
//!
//! This mirrors the Python `netnode/fullnode.py::validate_block` context-free checks — the part
//! that needs only the block bytes (structure, coinbase placement, and the merkle commitment) plus
//! the proof-of-work check — as a first, self-contained step of a native node. The value/UTXO rules
//! (double-spends, script/ECDSA, no-inflation, coinbase value, difficulty retarget) are *stateful*
//! and live in the Python `ChainState`; they are out of scope here.
//!
//! SHA-256 is implemented in-crate (FIPS 180-4), so the *context-free* validator has **zero
//! dependencies**. The **stateful** layer (`sighash`, `script`, `chainstate` modules) adds real
//! ECDSA via the pure-Rust `k256` crate. `cargo test` verifies everything against golden vectors
//! produced by the verified Python node. Provenance: NEW-EXP; the byte formats are the lab's.

pub mod chainstate;
pub mod script;
pub mod sighash;

// ---- SHA-256 (FIPS 180-4) + double SHA-256 ---------------------------------------

const K: [u32; 64] = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
];

/// SHA-256 of `data`.
pub fn sha256(data: &[u8]) -> [u8; 32] {
    let mut h: [u32; 8] = [
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
    ];
    let bit_len = (data.len() as u64).wrapping_mul(8);
    let mut msg = data.to_vec();
    msg.push(0x80);
    while msg.len() % 64 != 56 {
        msg.push(0);
    }
    msg.extend_from_slice(&bit_len.to_be_bytes());

    for chunk in msg.chunks_exact(64) {
        let mut w = [0u32; 64];
        for i in 0..16 {
            w[i] = u32::from_be_bytes([chunk[i * 4], chunk[i * 4 + 1], chunk[i * 4 + 2], chunk[i * 4 + 3]]);
        }
        for i in 16..64 {
            let s0 = w[i - 15].rotate_right(7) ^ w[i - 15].rotate_right(18) ^ (w[i - 15] >> 3);
            let s1 = w[i - 2].rotate_right(17) ^ w[i - 2].rotate_right(19) ^ (w[i - 2] >> 10);
            w[i] = w[i - 16]
                .wrapping_add(s0)
                .wrapping_add(w[i - 7])
                .wrapping_add(s1);
        }
        let (mut a, mut b, mut c, mut d, mut e, mut f, mut g, mut hh) =
            (h[0], h[1], h[2], h[3], h[4], h[5], h[6], h[7]);
        for i in 0..64 {
            let s1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
            let ch = (e & f) ^ ((!e) & g);
            let t1 = hh.wrapping_add(s1).wrapping_add(ch).wrapping_add(K[i]).wrapping_add(w[i]);
            let s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let maj = (a & b) ^ (a & c) ^ (b & c);
            let t2 = s0.wrapping_add(maj);
            hh = g;
            g = f;
            f = e;
            e = d.wrapping_add(t1);
            d = c;
            c = b;
            b = a;
            a = t1.wrapping_add(t2);
        }
        h[0] = h[0].wrapping_add(a);
        h[1] = h[1].wrapping_add(b);
        h[2] = h[2].wrapping_add(c);
        h[3] = h[3].wrapping_add(d);
        h[4] = h[4].wrapping_add(e);
        h[5] = h[5].wrapping_add(f);
        h[6] = h[6].wrapping_add(g);
        h[7] = h[7].wrapping_add(hh);
    }
    let mut out = [0u8; 32];
    for i in 0..8 {
        out[i * 4..i * 4 + 4].copy_from_slice(&h[i].to_be_bytes());
    }
    out
}

/// Bitcoin's double SHA-256.
pub fn dsha256(data: &[u8]) -> [u8; 32] {
    sha256(&sha256(data))
}

// ---- byte parsing (CompactSize + tx traversal) -----------------------------------

fn read_compact(data: &[u8], off: usize) -> (u64, usize) {
    match data[off] {
        0xff => (u64::from_le_bytes(data[off + 1..off + 9].try_into().unwrap()), off + 9),
        0xfe => (u32::from_le_bytes(data[off + 1..off + 5].try_into().unwrap()) as u64, off + 5),
        0xfd => (u16::from_le_bytes(data[off + 1..off + 3].try_into().unwrap()) as u64, off + 3),
        n => (n as u64, off + 1),
    }
}

/// Byte length of the transaction starting at `off` (inverse of the lab's `serialize`).
fn tx_len(data: &[u8], off: usize) -> usize {
    let mut i = off + 4; // version
    let (nin, ni) = read_compact(data, i);
    i = ni;
    for _ in 0..nin {
        i += 36; // prevhash(32) + index(4)
        let (slen, ni) = read_compact(data, i);
        i = ni + slen as usize + 4; // script + sequence(4)
    }
    let (nout, no) = read_compact(data, i);
    i = no;
    for _ in 0..nout {
        i += 8; // value(8, signed)
        let (slen, ni) = read_compact(data, i);
        i = ni + slen as usize; // script
    }
    i + 4 - off // locktime(4)
}

fn is_coinbase_at(data: &[u8], off: usize) -> bool {
    let mut i = off + 4;
    let (nin, ni) = read_compact(data, i);
    i = ni;
    nin == 1
        && data[i..i + 32].iter().all(|&b| b == 0)
        && u32::from_le_bytes(data[i + 32..i + 36].try_into().unwrap()) == 0xffff_ffff
}

// ---- block-level primitives ------------------------------------------------------

/// The block hash: double SHA-256 of the 80-byte header (internal byte order, as the node stores it).
pub fn block_hash(raw: &[u8]) -> [u8; 32] {
    dsha256(&raw[0..80])
}

/// The merkle root recomputed from the transactions (the tree the header commits to).
pub fn merkle_root(raw: &[u8]) -> [u8; 32] {
    let body = &raw[80..];
    let (ntx, mut i) = read_compact(body, 0);
    let mut layer: Vec<[u8; 32]> = Vec::new();
    for _ in 0..ntx {
        let len = tx_len(body, i);
        layer.push(dsha256(&body[i..i + len]));
        i += len;
    }
    if layer.is_empty() {
        return [0u8; 32];
    }
    while layer.len() > 1 {
        if layer.len() % 2 == 1 {
            let last = *layer.last().unwrap();
            layer.push(last); // duplicate the final hash (Satoshi's merkle)
        }
        let mut next = Vec::with_capacity(layer.len() / 2);
        for pair in layer.chunks(2) {
            let mut cat = [0u8; 64];
            cat[..32].copy_from_slice(&pair[0]);
            cat[32..].copy_from_slice(&pair[1]);
            next.push(dsha256(&cat));
        }
        layer = next;
    }
    layer[0]
}

/// The 256-bit PoW target encoded by a compact `nbits`, as big-endian bytes.
pub fn target_from_bits(nbits: u32) -> [u8; 32] {
    let exp = (nbits >> 24) as i32;
    let mant = nbits & 0x007f_ffff; // drop the sign bit
    let mant_bytes = [(mant >> 16) as u8, (mant >> 8) as u8, mant as u8];
    let mut t = [0u8; 32];
    if exp >= 3 {
        let shift = exp - 3; // bytes of left shift
        for (k, &b) in mant_bytes.iter().enumerate() {
            let pos = 31 - shift - 2 + k as i32; // place mant so its LSB is `shift` bytes from the end
            if (0..32).contains(&pos) {
                t[pos as usize] = b;
            }
        }
    } else {
        let v = mant >> (8 * (3 - exp)) as u32;
        t[29] = (v >> 16) as u8;
        t[30] = (v >> 8) as u8;
        t[31] = v as u8;
    }
    t
}

/// PoW check: the header hash, read as a little-endian integer, is <= the target.
pub fn pow_ok(raw: &[u8], nbits: u32) -> bool {
    let mut hbe = block_hash(raw); // little-endian integer per the node…
    hbe.reverse(); // …compare as big-endian bytes == integer comparison
    hbe <= target_from_bits(nbits)
}

// ---- the context-free validator --------------------------------------------------

/// What a context-free validation yields (all the block-local facts).
pub struct Summary {
    pub block_hash: [u8; 32],
    pub merkle_root: [u8; 32],
    pub ntx: u64,
    pub pow_ok: bool,
}

/// Validate the checks that need only the block itself: at least one transaction, the first is a
/// coinbase and no other is, and the header's merkle root matches the transactions. Returns a
/// `Summary` (including the PoW result) or the first failing reason.
pub fn validate_context_free(raw: &[u8]) -> Result<Summary, &'static str> {
    if raw.len() < 81 {
        return Err("too short");
    }
    let body = &raw[80..];
    let (ntx, mut i) = read_compact(body, 0);
    if ntx < 1 {
        return Err("no transactions");
    }
    let mut offsets = Vec::with_capacity(ntx as usize);
    for _ in 0..ntx {
        offsets.push(i);
        i += tx_len(body, i);
    }
    if !is_coinbase_at(body, offsets[0]) {
        return Err("first tx is not a coinbase");
    }
    for &o in &offsets[1..] {
        if is_coinbase_at(body, o) {
            return Err("more than one coinbase");
        }
    }
    let mr = merkle_root(raw);
    if mr[..] != raw[36..68] {
        return Err("merkle root mismatch");
    }
    let nbits = u32::from_le_bytes(raw[72..76].try_into().unwrap());
    Ok(Summary {
        block_hash: block_hash(raw),
        merkle_root: mr,
        ntx,
        pow_ok: pow_ok(raw, nbits),
    })
}

// ---- structured transactions + value-rule primitives -----------------------------
//
// The next slice toward a native node: parse transactions into structured form (inputs, outputs,
// scripts) and provide the *value* rules that the stateful validator applies. Script / ECDSA
// verification and the UTXO set are deliberately NOT here — those need a real secp256k1 backend and
// a script interpreter (a separate effort); this ports the parts that are pure byte/integer logic
// and are fully checkable against the Python node's golden vectors.

/// A transaction input (outpoint + scriptSig + sequence).
pub struct TxIn {
    pub prevhash: [u8; 32],
    pub n: u32,
    pub script: Vec<u8>,
    pub seq: u32,
}

/// A transaction output (value is a **signed** int64, as in v0.1) + scriptPubKey.
pub struct TxOut {
    pub value: i64,
    pub script: Vec<u8>,
}

/// A deserialized transaction.
pub struct Tx {
    pub version: u32,
    pub vin: Vec<TxIn>,
    pub vout: Vec<TxOut>,
    pub locktime: u32,
}

/// Deserialize one transaction at `off`; returns it and the offset just past it.
pub fn parse_tx(data: &[u8], off: usize) -> (Tx, usize) {
    let mut i = off;
    let version = u32::from_le_bytes(data[i..i + 4].try_into().unwrap());
    i += 4;
    let (nin, ni) = read_compact(data, i);
    i = ni;
    let mut vin = Vec::with_capacity(nin as usize);
    for _ in 0..nin {
        let mut prevhash = [0u8; 32];
        prevhash.copy_from_slice(&data[i..i + 32]);
        i += 32;
        let n = u32::from_le_bytes(data[i..i + 4].try_into().unwrap());
        i += 4;
        let (slen, si) = read_compact(data, i);
        i = si;
        let script = data[i..i + slen as usize].to_vec();
        i += slen as usize;
        let seq = u32::from_le_bytes(data[i..i + 4].try_into().unwrap());
        i += 4;
        vin.push(TxIn { prevhash, n, script, seq });
    }
    let (nout, no) = read_compact(data, i);
    i = no;
    let mut vout = Vec::with_capacity(nout as usize);
    for _ in 0..nout {
        let value = i64::from_le_bytes(data[i..i + 8].try_into().unwrap()); // signed int64
        i += 8;
        let (slen, si) = read_compact(data, i);
        i = si;
        let script = data[i..i + slen as usize].to_vec();
        i += slen as usize;
        vout.push(TxOut { value, script });
    }
    let locktime = u32::from_le_bytes(data[i..i + 4].try_into().unwrap());
    i += 4;
    (Tx { version, vin, vout, locktime }, i)
}

/// Every transaction in the block, each paired with its txid (double-SHA-256 of its bytes).
pub fn parse_block_txs(raw: &[u8]) -> Vec<(Tx, [u8; 32])> {
    let body = &raw[80..];
    let (ntx, mut i) = read_compact(body, 0);
    let mut out = Vec::with_capacity(ntx as usize);
    for _ in 0..ntx {
        let start = i;
        let (tx, ni) = parse_tx(body, i);
        out.push((tx, dsha256(&body[start..ni])));
        i = ni;
    }
    out
}

/// A coinbase: exactly one input, spending the null outpoint.
pub fn is_coinbase(tx: &Tx) -> bool {
    tx.vin.len() == 1 && tx.vin[0].prevhash == [0u8; 32] && tx.vin[0].n == 0xffff_ffff
}

/// Sum of a transaction's output values.
pub fn sum_outputs(tx: &Tx) -> i64 {
    tx.vout.iter().map(|o| o.value).sum()
}

/// The chain's coinbase‑value rule: NOV08 requires `claimed == subsidy + fees`; JAN09 allows
/// `claimed <= subsidy + fees`. (Mirrors `consensus.Rules.coinbase_ok`.)
pub fn check_coinbase_value(claimed: i64, subsidy: i64, fees: i64, strict: bool) -> bool {
    let allowed = subsidy + fees;
    if strict {
        claimed == allowed
    } else {
        claimed <= allowed
    }
}
