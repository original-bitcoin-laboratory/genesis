//! Block assembly + mining for the standalone node — so a Rust node can produce blocks (incl.
//! mempool transactions), not only validate them. NOT money.

use crate::sighash::compact_size;
use crate::{block_hash, dsha256, serialize_tx, target_from_bits, target_lzb, Tx, TxIn, TxOut};

/// A coinbase paying `value` to `spk`, with `height` + `tag` in the scriptSig for uniqueness.
pub fn coinbase(height: i64, value: i64, spk: &[u8], tag: u32) -> Tx {
    let s = vec![
        (height & 0xff) as u8,
        ((height >> 8) & 0xff) as u8,
        (tag & 0xff) as u8,
        ((tag >> 8) & 0xff) as u8,
    ];
    Tx {
        version: 1,
        vin: vec![TxIn { prevhash: [0u8; 32], n: 0xffff_ffff, script: s, seq: 0xffff_ffff }],
        vout: vec![TxOut { value, script: spk.to_vec() }],
        locktime: 0,
    }
}

fn merkle_of(tx_raws: &[Vec<u8>]) -> [u8; 32] {
    let mut layer: Vec<[u8; 32]> = tx_raws.iter().map(|r| dsha256(r)).collect();
    if layer.is_empty() {
        return [0u8; 32];
    }
    while layer.len() > 1 {
        if layer.len() % 2 == 1 {
            let last = *layer.last().unwrap();
            layer.push(last);
        }
        let mut next = Vec::with_capacity(layer.len() / 2);
        for pair in layer.chunks(2) {
            let mut c = [0u8; 64];
            c[..32].copy_from_slice(&pair[0]);
            c[32..].copy_from_slice(&pair[1]);
            next.push(dsha256(&c));
        }
        layer = next;
    }
    layer[0]
}

fn build_block(prev: &[u8; 32], merkle: &[u8; 32], time: u32, nbits: u32, nonce: u32, tx_raws: &[Vec<u8>]) -> Vec<u8> {
    let mut o = Vec::new();
    o.extend_from_slice(&1u32.to_le_bytes()); // version
    o.extend_from_slice(prev);
    o.extend_from_slice(merkle);
    o.extend_from_slice(&time.to_le_bytes());
    o.extend_from_slice(&nbits.to_le_bytes());
    o.extend_from_slice(&nonce.to_le_bytes());
    o.extend_from_slice(&compact_size(tx_raws.len() as u64));
    for r in tx_raws {
        o.extend_from_slice(r);
    }
    o
}

/// Mine a block on `prev`: a coinbase claiming `coinbase_value` to `coinbase_spk`, followed by
/// `extra` transactions, brute-forcing a nonce until the header hash meets `nbits`.
pub fn mine(
    prev: &[u8; 32],
    height: i64,
    nbits: u32,
    time: u32,
    coinbase_value: i64,
    coinbase_spk: &[u8],
    extra: &[Tx],
    tag: u32,
) -> Vec<u8> {
    let cb = coinbase(height, coinbase_value, coinbase_spk, tag);
    let mut raws = vec![serialize_tx(&cb)];
    raws.extend(extra.iter().map(serialize_tx));
    let merkle = merkle_of(&raws);
    let target = target_from_bits(nbits); // big-endian
    for nonce in 0..u32::MAX {
        let raw = build_block(prev, &merkle, time, nbits, nonce, &raws);
        let mut h = block_hash(&raw); // little-endian integer
        h.reverse(); // -> big-endian bytes for comparison
        if h <= target {
            return raw;
        }
    }
    panic!("no nonce found");
}

/// Mine under NOV08 **leading-zero-bits** PoW: identical block assembly to `mine`, but grind a
/// nonce until the header hash has at least `nbits` leading zero bits (`target_lzb`). NOT money.
pub fn mine_lzb(
    prev: &[u8; 32],
    height: i64,
    nbits: u32,
    time: u32,
    coinbase_value: i64,
    coinbase_spk: &[u8],
    extra: &[Tx],
    tag: u32,
) -> Vec<u8> {
    let cb = coinbase(height, coinbase_value, coinbase_spk, tag);
    let mut raws = vec![serialize_tx(&cb)];
    raws.extend(extra.iter().map(serialize_tx));
    let merkle = merkle_of(&raws);
    let target = target_lzb(nbits); // big-endian
    for nonce in 0..u32::MAX {
        let raw = build_block(prev, &merkle, time, nbits, nonce, &raws);
        let mut h = block_hash(&raw);
        h.reverse();
        if h <= target {
            return raw;
        }
    }
    panic!("no nonce found");
}
