//! A validating transaction mempool for the standalone node — mirrors `netnode/mempool.py`. NOT money.
//!
//! Validates a candidate transaction against the confirmed UTXO **and** pooled parents (chained
//! unconfirmed spends) — every input exists and is unspent, no in-pool double-spend, coinbase
//! maturity, the input script is satisfied (the full v0.1 interpreter), and no inflation — records
//! the fee, and `select`s a topologically-ordered batch for a miner. Policy, not consensus: the
//! block still re-validates on connect.

use std::collections::{HashMap, HashSet};

use crate::chainstate::{Coin, Outpoint};
use crate::script::verify_spend;
use crate::{dsha256, is_coinbase, parse_tx, Tx};

pub struct Entry {
    pub tx: Tx,
    pub raw: Vec<u8>,
    pub txid: [u8; 32],
    pub fee: i64,
}

pub struct Mempool {
    txs: Vec<Entry>,
    spent: HashMap<Outpoint, [u8; 32]>,
    maturity: i64,
}

impl Mempool {
    pub fn new(maturity: i64) -> Self {
        Mempool { txs: Vec::new(), spent: HashMap::new(), maturity }
    }

    pub fn len(&self) -> usize {
        self.txs.len()
    }

    pub fn is_empty(&self) -> bool {
        self.txs.is_empty()
    }

    pub fn has(&self, txid: &[u8; 32]) -> bool {
        self.txs.iter().any(|e| &e.txid == txid)
    }

    pub fn get(&self, txid: &[u8; 32]) -> Option<&[u8]> {
        self.txs.iter().find(|e| &e.txid == txid).map(|e| e.raw.as_slice())
    }

    pub fn txids(&self) -> Vec<[u8; 32]> {
        self.txs.iter().map(|e| e.txid).collect()
    }

    fn pooled_output(&self, key: &Outpoint) -> Option<Coin> {
        let (ptxid, n) = *key;
        for e in &self.txs {
            if e.txid == ptxid && (n as usize) < e.tx.vout.len() {
                let o = &e.tx.vout[n as usize];
                return Some(Coin { value: o.value, spk: o.script.clone(), height: -1, coinbase: false });
            }
        }
        None
    }

    /// Validate `raw` against `utxo` (+ pooled parents) at `height`; returns the fee, or the reason.
    pub fn accept(&mut self, raw: &[u8], utxo: &HashMap<Outpoint, Coin>, height: i64) -> Result<i64, &'static str> {
        let (tx, off) = parse_tx(raw, 0);
        if off != raw.len() {
            return Err("trailing bytes");
        }
        let txid = dsha256(raw);
        if self.txs.iter().any(|e| e.txid == txid) {
            return Err("already pooled");
        }
        if is_coinbase(&tx) {
            return Err("coinbase is not a standalone transaction");
        }
        if tx.vin.is_empty() || tx.vout.is_empty() {
            return Err("no inputs or outputs");
        }
        let mut value_in: i64 = 0;
        let mut seen = HashSet::new();
        for (i, vin) in tx.vin.iter().enumerate() {
            let key = (vin.prevhash, vin.n);
            if !seen.insert(key) {
                return Err("duplicate input");
            }
            if self.spent.contains_key(&key) {
                return Err("conflicts with a pooled transaction");
            }
            let coin = match utxo.get(&key) {
                Some(c) => c.clone(),
                None => match self.pooled_output(&key) {
                    Some(c) => c,
                    None => return Err("input missing or already spent"),
                },
            };
            if coin.coinbase && coin.height >= 0 && height - coin.height < self.maturity {
                return Err("immature coinbase spend");
            }
            if !verify_spend(&vin.script, &coin.spk, &tx, i) {
                return Err("input script does not satisfy output");
            }
            value_in += coin.value;
        }
        if tx.vout.iter().any(|o| o.value < 0) {
            return Err("negative output");
        }
        let value_out: i64 = tx.vout.iter().map(|o| o.value).sum();
        if value_in < value_out {
            return Err("inflation (inputs < outputs)");
        }
        let fee = value_in - value_out;
        for vin in &tx.vin {
            self.spent.insert((vin.prevhash, vin.n), txid);
        }
        self.txs.push(Entry { tx, raw: raw.to_vec(), txid, fee });
        Ok(fee)
    }

    /// A topologically-ordered batch (parents before children) whose inputs are all available.
    pub fn select(&self, utxo: &HashMap<Outpoint, Coin>) -> Vec<&Entry> {
        let mut chosen = Vec::new();
        let mut created: HashSet<Outpoint> = HashSet::new();
        for e in &self.txs {
            if e.tx.vin.iter().all(|v| {
                let k = (v.prevhash, v.n);
                utxo.contains_key(&k) || created.contains(&k)
            }) {
                for n in 0..e.tx.vout.len() {
                    created.insert((e.txid, n as u32));
                }
                chosen.push(e);
            }
        }
        chosen
    }

    pub fn total_fees(&self, selected: &[&Entry]) -> i64 {
        selected.iter().map(|e| e.fee).sum()
    }

    /// Re-validate the pool against a freshly-advanced chainstate, dropping mined / now-invalid txs.
    pub fn reconcile(&mut self, utxo: &HashMap<Outpoint, Coin>, height: i64) {
        let old = std::mem::take(&mut self.txs);
        self.spent.clear();
        for e in old {
            let _ = self.accept(&e.raw, utxo, height);
        }
    }
}
