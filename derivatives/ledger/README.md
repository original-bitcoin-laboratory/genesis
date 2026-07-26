# Rules‑parameterised UTXO ledger (R8 — transacting)

**Evidence level: `MODEL`.** The Python counterpart of `../node/chain_port.cpp`
(`ConnectInputs` / `ConnectBlock`), but driven by a `consensus.Rules` so it enforces
**whichever chain's constitution** — NOV08‑X or JAN09‑X. This is what makes the
full‑capability networks actually **transact**.

## What it enforces (main.cpp ConnectInputs / ConnectBlock)

- **no double‑spend** — spent inputs leave the UTXO set;
- **no inflation** — `sum(inputs) ≥ sum(outputs)`;
- **coinbase maturity** — `COINBASE_MATURITY = 100` (main.h);
- **the chain's coinbase value rule** — NOV08‑X `==` (exact), JAN09‑X `≤` (upper bound);
- **every input satisfies its scriptPubKey** — via `model/spend.verify_spend`, the v0.1
  `VerifySignature` path (`EvalScript(scriptSig + OP_CODESEPARATOR + scriptPubKey)`)
  over the **full opcode vocabulary**.

It reuses the lab's already‑executed pieces (`model` EvalScript + sighash, `wallet`
CreateTransaction, `consensus` Rules) — no new consensus code, just the UTXO
bookkeeping that ties them into a spendable ledger.

## What the tests show (`test_ledger.py`, 8)

- a **wallet payment settles** on JAN09‑X: a matured coinbase is spent, the UTXO set
  updates (payee + change), value is conserved;
- the safety rules reject **immature‑coinbase**, **double‑spend**, and **inflation**;
- each chain's **coinbase value rule** holds (JAN09‑X `≤`, NOV08‑X `==`);
- **full capability** — a coin locked by an **`OP_CAT` hash‑lock**
  (`OP_CAT OP_SHA256 <h> OP_EQUAL`, spendable by revealing two preimage halves) is
  **spent and validated on both X‑chains**, and a wrong preimage is rejected. BTC
  disables `OP_CAT`, so that coin would be **unspendable there** — the whole point of
  the "nothing disabled" chains: contracts the origin could express, live again.

## Run

```bash
python -m pytest        # 8 passed
```

## Boundary

Rules‑level UTXO validation (signatures real, scripts executed, value/maturity/
double‑spend enforced). It is not block assembly or the P2P layer — those are
`../nov08x/net.py` / `../jan09x/net.py` and `../p2p`. Wiring a mined block's txs
through this ledger on a running X‑chain node is the natural next step.
