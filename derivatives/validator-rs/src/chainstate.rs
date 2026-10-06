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
    // Value sums are int64 and WRAP, exactly as v0.1's do (main.h:492 GetValueOut; main.cpp:845-854
    // ConnectInputs; main.cpp:953 vs GetBlockValue). So the Aug 2010 overflow transaction is
    // ACCEPTED, as by the 2009 client this chain runs.
    //
    // SUPERSEDES the 20 Sep 2026 widening to i128, which made this node reject that transaction to
    // agree with the Python oracle's unbounded integers. On 6 Oct 2026 executed tests
    // (netnode/test_fidelity_2009.py) showed the Python oracle itself diverged from v0.1 -- a split
    // any miner could trigger between our nodes and the 2009 binary -- and it was brought back to
    // int64. This node follows. The 20 Sep concern (panic in debug, silent wrap in release) is met
    // by explicit wrapping_* arithmetic, identical in both builds.
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

    for (tx, _) in &txs {
        if let Some(why) = crate::check_transaction_2009(tx, strict) {
            bail!(why); // CheckBlock -> CheckTransaction, authoritative on connect
        }
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
                value_in = value_in.wrapping_add(coin.value); // main.cpp:845
                utxo.remove(&key);
                if let Some(pos) = created.iter().position(|k| *k == key) {
                    created.remove(pos); // same-block output consumed -> nets out
                } else {
                    spent_prior.push((key, coin));
                }
            }
            let fee = value_in.wrapping_sub(crate::sum_outputs(tx)); // main.cpp:849
            if fee < 0 {
                bail!("inflation (inputs < outputs)"); // main.cpp:850 nTxFee < 0
            }
            fees = fees.wrapping_add(fee); // main.cpp:854
        }
        for (n, o) in tx.vout.iter().enumerate() {
            let k = (*tid, n as u32);
            utxo.insert(k, Coin { value: o.value, spk: o.script.clone(), height, coinbase });
            created.push(k);
        }
    }

    if !is_genesis {
        let claimed = crate::sum_outputs(&txs[0].0); // main.cpp:953, int64
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
        self.utxo.values().map(|c| c.value as i128).sum::<i128>().clamp(i64::MIN as i128, i64::MAX as i128) as i64
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
