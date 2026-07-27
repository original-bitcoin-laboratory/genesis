# Full-stack console (R7 capstone)

**Evidence level: `MODEL`.** One object that drives a full-capability X-chain end to
end — the whole lab, wired together:

`Rules` (constitution) + `Ledger` (ConnectBlock/UTXO) + `Wallet` (real secp256k1) +
`studio` (script tracer) + `market` (signed listings + atoms reputation).

## Drive it

```python
from console import run_session
from consensus import Rules
c = run_session(Rules.load("nov08"), "NOV08-X", export_path="bundle.json")
```

`XConsole` gives you: `mine()`, `pay(dest, amount, fee)`, `create_hashlock` /
`spend_hashlock` (a full-vocabulary **`OP_CAT` contract BTC cannot run**),
`list_product` / `receive_review` (signed commerce + reputation), `utxo_view()`, and
`export()` (a deterministic evidence bundle). `python console.py` runs a full session
on **both** NOV08-X and JAN09-X and prints the event trail + a studio trace.

## What one session demonstrates

- coinbases mined under the chain's rules (**100 coins** on NOV08-X, **50** on JAN09-X);
- a P2PK payment, settled in a block and validated by `ConnectBlock`;
- a coin **locked under an `OP_CAT` hash-lock and later spent** by revealing the
  preimage — a contract that is **unspendable on BTC**, live on both X-chains;
- a **signed product listing** and a **review** that raises the seller's atom
  reputation;
- an exported JSON bundle recording the constitution, height, UTXO set, products, and
  the full event log.

Same driver, two constitutions — so the identical financial machine runs on
November's rules and on January's. NOV08-X here is **NOV08-Full's executable form**
(`common/nov08x/NOV08_FULL.md`): a counterfactual completion, **not**
recovered code and **not** "true Bitcoin".

## Run

```bash
python console.py        # full session on both chains + a studio trace
python -m pytest         # 6 passed
```
