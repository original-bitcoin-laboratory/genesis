//! The v0.1 signature hash (`SignatureHash`), ported to match the Python `tx_sighash.py`
//! byte-for-byte — including its simplified `OP_CODESEPARATOR` find-and-delete (strip all 0xab
//! bytes from the scriptCode). NOT money.

use crate::{dsha256, Tx};

pub const SIGHASH_ALL: u8 = 1;
pub const SIGHASH_NONE: u8 = 2;
pub const SIGHASH_SINGLE: u8 = 3;
pub const SIGHASH_ANYONECANPAY: u8 = 0x80;
const OP_CODESEPARATOR: u8 = 0xab;

/// CompactSize (Bitcoin varint) encoding.
pub fn compact_size(n: u64) -> Vec<u8> {
    if n < 0xfd {
        vec![n as u8]
    } else if n <= 0xffff {
        let mut v = vec![0xfd];
        v.extend_from_slice(&(n as u16).to_le_bytes());
        v
    } else if n <= 0xffff_ffff {
        let mut v = vec![0xfe];
        v.extend_from_slice(&(n as u32).to_le_bytes());
        v
    } else {
        let mut v = vec![0xff];
        v.extend_from_slice(&n.to_le_bytes());
        v
    }
}

fn push(b: &[u8]) -> Vec<u8> {
    let mut v = compact_size(b.len() as u64);
    v.extend_from_slice(b);
    v
}

fn one() -> [u8; 32] {
    let mut o = [0u8; 32];
    o[0] = 1; // the sentinel hash `1` (little-endian), as v0.1 returns for degenerate cases
    o
}

/// The digest a signature commits to, for input `n_in` under `hash_type`, given the `script_code`
/// (the scriptPubKey being spent). Mirrors `tx_sighash.signature_hash`.
pub fn signature_hash(script_code: &[u8], tx: &Tx, n_in: usize, hash_type: u8) -> [u8; 32] {
    if n_in >= tx.vin.len() {
        return one();
    }
    let sc: Vec<u8> = script_code.iter().copied().filter(|&b| b != OP_CODESEPARATOR).collect();
    let ht = hash_type & 0x1f;
    let anyone = hash_type & SIGHASH_ANYONECANPAY != 0;

    let mut s: Vec<u8> = Vec::new();
    s.extend_from_slice(&tx.version.to_le_bytes());

    let inputs: Vec<usize> = if anyone { vec![n_in] } else { (0..tx.vin.len()).collect() };
    s.extend_from_slice(&compact_size(inputs.len() as u64));
    for &k in &inputs {
        let vin = &tx.vin[k];
        s.extend_from_slice(&vin.prevhash);
        s.extend_from_slice(&vin.n.to_le_bytes());
        let script: &[u8] = if k == n_in { &sc } else { &[] };
        s.extend_from_slice(&push(script));
        let seq = if (ht == SIGHASH_NONE || ht == SIGHASH_SINGLE) && k != n_in { 0u32 } else { vin.seq };
        s.extend_from_slice(&seq.to_le_bytes());
    }

    if ht == SIGHASH_NONE {
        s.extend_from_slice(&compact_size(0));
    } else if ht == SIGHASH_SINGLE {
        if n_in >= tx.vout.len() {
            return one();
        }
        s.extend_from_slice(&compact_size((n_in + 1) as u64));
        for k in 0..=n_in {
            if k < n_in {
                s.extend_from_slice(&(-1i64).to_le_bytes()); // set_null: value -1, empty script
                s.extend_from_slice(&push(&[]));
            } else {
                s.extend_from_slice(&tx.vout[k].value.to_le_bytes());
                s.extend_from_slice(&push(&tx.vout[k].script));
            }
        }
    } else {
        // SIGHASH_ALL (and default): all outputs unchanged
        s.extend_from_slice(&compact_size(tx.vout.len() as u64));
        for o in &tx.vout {
            s.extend_from_slice(&o.value.to_le_bytes());
            s.extend_from_slice(&push(&o.script));
        }
    }

    s.extend_from_slice(&tx.locktime.to_le_bytes());
    s.extend_from_slice(&(hash_type as u32).to_le_bytes());
    dsha256(&s)
}
