//! The stateful validator: a UTXO set and `connect_block`, enforcing the *value* consensus rules
//! the Python `ChainState._connect` does — every input exists and is unspent, coinbase maturity,
//! the input script is satisfied (via `script::verify_spend`), no inflation, and the coinbase-value
//! rule with fees. Reorg/disconnect and the difficulty retarget are out of scope for this slice.
//! NOT money.

use std::collections::HashMap;

use crate::script::verify_spend;
use crate::{check_coinbase_value, is_coinbase, parse_block_txs};

/// An unspent output.
pub struct Coin {
    pub value: i64,
    pub spk: Vec<u8>,
    pub height: i64,
    pub coinbase: bool,
}

/// A UTXO set plus the value-rule connect logic. Connecting is **atomic**: on any failure the set
/// is left unchanged (like the Python's rollback), so an invalid block can be tried and rejected
/// without corrupting state.
pub struct ChainState {
    utxo: HashMap<([u8; 32], u32), Coin>,
    maturity: i64,
    strict: bool, // coinbase-value rule: NOV08 `==` (strict) vs JAN09 `<=`
    pub height: i64,
}

impl ChainState {
    pub fn new(maturity: i64, strict: bool) -> Self {
        ChainState { utxo: HashMap::new(), maturity, strict, height: -1 }
    }

    pub fn utxo_count(&self) -> usize {
        self.utxo.len()
    }

    pub fn balance(&self) -> i64 {
        self.utxo.values().map(|c| c.value).sum()
    }

    /// Connect `raw` at `height` (with the block's `subsidy`); `is_genesis` skips the coinbase-value
    /// rule. Returns `Ok(())` on success (UTXO updated) or the first failing reason (UTXO unchanged).
    pub fn connect_block(
        &mut self,
        raw: &[u8],
        height: i64,
        subsidy: i64,
        is_genesis: bool,
    ) -> Result<(), &'static str> {
        let txs = parse_block_txs(raw);
        let mut work: HashMap<([u8; 32], u32), Coin> = HashMap::new();
        for (k, v) in &self.utxo {
            work.insert(*k, Coin { value: v.value, spk: v.spk.clone(), height: v.height, coinbase: v.coinbase });
        }
        let mut fees: i64 = 0;

        for (tx, tid) in &txs {
            let coinbase = is_coinbase(tx);
            if !coinbase {
                let mut value_in: i64 = 0;
                for (i_in, vin) in tx.vin.iter().enumerate() {
                    let key = (vin.prevhash, vin.n);
                    let (cval, ccoinbase, cheight, cspk) = match work.get(&key) {
                        Some(c) => (c.value, c.coinbase, c.height, c.spk.clone()),
                        None => return Err("input missing or already spent"),
                    };
                    if ccoinbase && height - cheight < self.maturity {
                        return Err("immature coinbase spend");
                    }
                    if !verify_spend(&vin.script, &cspk, tx, i_in) {
                        return Err("input script does not satisfy output");
                    }
                    value_in += cval;
                    work.remove(&key);
                }
                let value_out: i64 = tx.vout.iter().map(|o| o.value).sum();
                if value_in < value_out {
                    return Err("inflation (inputs < outputs)");
                }
                fees += value_in - value_out;
            }
            for (n, o) in tx.vout.iter().enumerate() {
                work.insert(
                    (*tid, n as u32),
                    Coin { value: o.value, spk: o.script.clone(), height, coinbase },
                );
            }
        }

        if !is_genesis {
            let claimed: i64 = txs[0].0.vout.iter().map(|o| o.value).sum();
            if !check_coinbase_value(claimed, subsidy, fees, self.strict) {
                return Err("coinbase value violates the chain rule");
            }
        }

        self.utxo = work;
        self.height = height;
        Ok(())
    }
}
