//! The reorg-capable, difficulty-validating chainstate — the last native-node slice. NOT money.
//!
//! Mirrors the Python `chainstate.ChainState`: a block index (`index`), the active validated chain
//! with per-block undo, and `activate_best`, which moves the validated chain toward the index's
//! best (height-selected) chain — **gating every step on full validity** (value/script rules via
//! `apply_txs`, plus the difficulty retarget) and **rolling back** (restoring the prior chain) if a
//! branch fails to validate.

use std::collections::{HashMap, HashSet};

use crate::chainstate::{apply_txs, Coin, Outpoint, Undo};
use crate::difficulty::expected_bits;
use crate::index::BlockIndex;
use crate::rules::Rules;

pub struct NodeState {
    pub index: BlockIndex,
    utxo: HashMap<Outpoint, Coin>,
    active: Vec<[u8; 32]>,
    undo: HashMap<[u8; 32], Undo>,
    invalid: HashSet<[u8; 32]>,
    rules: Rules,
    maturity: i64,
    min_bits: Option<u32>,
}

impl NodeState {
    pub fn new(rules: Rules, maturity: i64, min_bits: Option<u32>) -> Self {
        NodeState {
            index: BlockIndex::new(),
            utxo: HashMap::new(),
            active: Vec::new(),
            undo: HashMap::new(),
            invalid: HashSet::new(),
            rules,
            maturity,
            min_bits,
        }
    }

    /// Add a block to the index (does not validate — call `activate_best`).
    pub fn add_block(&mut self, raw: &[u8]) -> [u8; 32] {
        self.index.add(raw)
    }

    pub fn tip(&self) -> Option<[u8; 32]> {
        self.active.last().copied()
    }

    pub fn height(&self) -> i64 {
        self.active.last().map(|h| self.index.by_hash[h].height).unwrap_or(-1)
    }

    pub fn utxo_count(&self) -> usize {
        self.utxo.len()
    }

    pub fn balance(&self) -> i64 {
        self.utxo.values().map(|c| c.value).sum()
    }

    /// The current validated UTXO set (for a mempool to validate against).
    pub fn utxo(&self) -> &HashMap<Outpoint, Coin> {
        &self.utxo
    }

    pub fn is_invalid(&self, h: &[u8; 32]) -> bool {
        self.invalid.contains(h)
    }

    fn connect(&mut self, h: [u8; 32]) -> Result<(), &'static str> {
        let (raw, prev, height, nbits) = {
            let e = self.index.get(&h).unwrap();
            (e.raw.clone(), e.prev, e.height, e.nbits)
        };
        let is_genesis = Some(h) == self.index.genesis;
        if !is_genesis {
            if nbits != expected_bits(&self.index, &prev, &self.rules, self.min_bits) {
                return Err("wrong difficulty");
            }
        }
        let subsidy = self.rules.subsidy(height - 1);
        let undo = apply_txs(
            &mut self.utxo,
            &raw,
            height,
            subsidy,
            self.rules.strict,
            self.maturity,
            is_genesis,
        )?;
        self.undo.insert(h, undo);
        self.active.push(h);
        Ok(())
    }

    fn disconnect(&mut self) {
        let h = self.active.pop().unwrap();
        let (spent_prior, created) = self.undo.remove(&h).unwrap();
        for k in &created {
            self.utxo.remove(k);
        }
        for (k, c) in spent_prior {
            self.utxo.insert(k, c);
        }
    }

    /// Move the validated chain to the index's best valid chain (reorg-safe, gated on validity).
    pub fn activate_best(&mut self) {
        let target = self.index.main_chain();
        if !self.active.is_empty() && self.active.last() == target.last() {
            return;
        }
        let old_active = self.active.clone();
        let old_height = self.height();

        let mut fork = 0;
        while fork < old_active.len() && fork < target.len() && old_active[fork] == target[fork] {
            fork += 1;
        }
        while self.active.len() > fork {
            self.disconnect();
        }
        for &h in &target[fork..] {
            if self.invalid.contains(&h) {
                break;
            }
            if self.connect(h).is_err() {
                self.invalid.insert(h);
                break;
            }
        }
        // if the reorg didn't improve height, restore the previously-valid chain
        if self.height() <= old_height && self.active != old_active {
            while self.active.len() > fork {
                self.disconnect();
            }
            for &h in &old_active[fork..] {
                let _ = self.connect(h); // previously valid -> reconnects
            }
        }
    }
}
