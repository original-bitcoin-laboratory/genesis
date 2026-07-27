//! A minimal block index (the PoW tree) — enough to drive reorg + difficulty. NOT money.
//!
//! Mirrors what `chainsync.Chain` provides the Python `ChainState`: block hash -> (raw, prev,
//! height, nBits), and the height‑selected best chain (v0.1 selects by **height**).

use std::collections::HashMap;

use crate::block_hash;

pub struct IdxEntry {
    pub raw: Vec<u8>,
    pub prev: [u8; 32],
    pub height: i64,
    pub nbits: u32,
}

pub struct BlockIndex {
    pub by_hash: HashMap<[u8; 32], IdxEntry>,
    pub genesis: Option<[u8; 32]>,
    order: Vec<[u8; 32]>, // insertion order, for deterministic tie-breaking
}

impl Default for BlockIndex {
    fn default() -> Self {
        Self::new()
    }
}

impl BlockIndex {
    pub fn new() -> Self {
        BlockIndex { by_hash: HashMap::new(), genesis: None, order: Vec::new() }
    }

    pub fn get(&self, h: &[u8; 32]) -> Option<&IdxEntry> {
        self.by_hash.get(h)
    }

    /// Add a block; the first added is the genesis (height 0). Returns its hash.
    pub fn add(&mut self, raw: &[u8]) -> [u8; 32] {
        let h = block_hash(raw);
        if self.by_hash.contains_key(&h) {
            return h;
        }
        let prev: [u8; 32] = raw[4..36].try_into().unwrap();
        let nbits = u32::from_le_bytes(raw[72..76].try_into().unwrap());
        let height = if self.genesis.is_none() {
            self.genesis = Some(h);
            0
        } else {
            self.by_hash.get(&prev).map(|p| p.height + 1).unwrap_or(0)
        };
        self.by_hash.insert(h, IdxEntry { raw: raw.to_vec(), prev, height, nbits });
        self.order.push(h);
        h
    }

    /// The best chain by **height** (first‑seen on ties), genesis .. tip.
    pub fn main_chain(&self) -> Vec<[u8; 32]> {
        let mut tip: Option<[u8; 32]> = None;
        let mut best = -1i64;
        for h in &self.order {
            let ht = self.by_hash[h].height;
            if ht > best {
                best = ht;
                tip = Some(*h);
            }
        }
        let mut out = Vec::new();
        let mut cur = tip;
        while let Some(h) = cur {
            out.push(h);
            let e = &self.by_hash[&h];
            cur = if Some(h) == self.genesis { None } else { Some(e.prev) };
        }
        out.reverse();
        out
    }
}
