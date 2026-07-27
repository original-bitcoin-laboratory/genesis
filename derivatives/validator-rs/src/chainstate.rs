//! The stateful validator's UTXO + value rules — mirrors the Python `ChainState._connect`. NOT money.
//!
//! `apply_txs` is the shared value/script logic (used by the simple `ChainState` here and by the
//! reorg‑capable `NodeState` in `reorg`): every input exists and is unspent, coinbase maturity, the
//! input script is satisfied (the full v0.1 interpreter, `script::verify_spend`), no inflation, and
//! the coinbase‑value rule with fees — applied with rollback so a rejected block leaves the UTXO
//! unchanged.

use std::collections::HashMap;

use crate::script::verify_spend;
use crate::{check_coinbase_value, is_coinbase, parse_block_txs};

pub type Outpoint = ([u8; 32], u32);

/// An unspent output.
#[derive(Clone)]
pub struct Coin {
    pub value: i64,
    pub spk: Vec<u8>,
    pub height: i64,
    pub coinbase: bool,
}

/// Undo data for one connected block: (pre‑block coins consumed, outputs created).
pub type Undo = (Vec<(Outpoint, Coin)>, Vec<Outpoint>);

/// Apply a block's transactions to `utxo`, enforcing the value rules. On success returns the undo
/// data (UTXO mutated); on the first failing rule it **rolls back** and returns the reason.
pub(crate) fn apply_txs(
    utxo: &mut HashMap<Outpoint, Coin>,
    raw: &[u8],
    height: i64,
    subsidy: i64,
    strict: bool,
    maturity: i64,
    is_genesis: bool,
) -> Result<Undo, &'static str> {
    let txs = parse_block_txs(raw);
    let mut created: Vec<Outpoint> = Vec::new();
    let mut spent_prior: Vec<(Outpoint, Coin)> = Vec::new();
    let mut fees: i64 = 0;

    macro_rules! bail {
        ($e:expr) => {{
            for k in &created {
                utxo.remove(k);
            }
            for (k, c) in spent_prior.into_iter().rev() {
                utxo.insert(k, c);
            }
            return Err($e);
        }};
    }

    for (tx, tid) in &txs {
        let coinbase = is_coinbase(tx);
        if !coinbase {
            let mut value_in: i64 = 0;
            for (i_in, vin) in tx.vin.iter().enumerate() {
                let key = (vin.prevhash, vin.n);
                let coin = match utxo.get(&key) {
                    Some(c) => c.clone(),
                    None => bail!("input missing or already spent"),
                };
                if coin.coinbase && height - coin.height < maturity {
                    bail!("immature coinbase spend");
                }
                if !verify_spend(&vin.script, &coin.spk, tx, i_in) {
                    bail!("input script does not satisfy output");
                }
                value_in += coin.value;
                utxo.remove(&key);
                if let Some(pos) = created.iter().position(|k| *k == key) {
                    created.remove(pos); // same-block output consumed -> nets out
                } else {
                    spent_prior.push((key, coin));
                }
            }
            let value_out: i64 = tx.vout.iter().map(|o| o.value).sum();
            if value_in < value_out {
                bail!("inflation (inputs < outputs)");
            }
            fees += value_in - value_out;
        }
        for (n, o) in tx.vout.iter().enumerate() {
            let k = (*tid, n as u32);
            utxo.insert(k, Coin { value: o.value, spk: o.script.clone(), height, coinbase });
            created.push(k);
        }
    }

    if !is_genesis {
        let claimed: i64 = txs[0].0.vout.iter().map(|o| o.value).sum();
        if !check_coinbase_value(claimed, subsidy, fees, strict) {
            bail!("coinbase value violates the chain rule");
        }
    }
    Ok((spent_prior, created))
}

/// A single-chain UTXO validator (no reorg) — connect a block directly. For reorg + difficulty use
/// [`crate::reorg::NodeState`].
pub struct ChainState {
    utxo: HashMap<Outpoint, Coin>,
    maturity: i64,
    strict: bool,
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

    /// Connect `raw` at `height` (atomically). `Ok(())` on success, or the first failing reason
    /// (UTXO unchanged).
    pub fn connect_block(
        &mut self,
        raw: &[u8],
        height: i64,
        subsidy: i64,
        is_genesis: bool,
    ) -> Result<(), &'static str> {
        apply_txs(&mut self.utxo, raw, height, subsidy, self.strict, self.maturity, is_genesis)?;
        self.height = height;
        Ok(())
    }
}
