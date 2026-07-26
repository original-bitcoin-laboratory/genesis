# NOV08‑X — NOV08‑Minimal (R8, headless)

**Evidence level: `MODEL`.** The first executable slice of **NOV08‑X**: a
counterfactual network that runs **November 2008's constitution** on the lab's
existing engines — no period‑toolchain compile. Design contract:
[`common/nov08x/DESIGN_LEDGER.md`](../../../common/nov08x/DESIGN_LEDGER.md).

November's rules are read **verbatim** from the surviving pre‑release source
(class **N‑ORIG**); January is only the differential baseline. Every rule carries a
source anchor in `rules_nov08.json` and a provenance class in `PROVENANCE.json`.

## The four divergences it executes (each faithful to source)

| | NOV08‑X (N‑ORIG) | JAN09 | anchor |
|---|---|---|---|
| **subsidy** | **100 coins**, halving every **100,000** blocks (explicit loop) | 50, every 210,000 | `main.cpp:654‑655` |
| **proof‑of‑work** | `nBits` = **leading‑zero bits**, `target = ~0 >> nBits`, `MINPROOFOFWORK=20` | compact mantissa/exponent | `main.h:38,875` |
| **retarget** | **±1‑bit nudge**, ≤ one change per 30‑day window | proportional scale, 14‑day | `main.cpp:660‑705` |
| **coinbase** | must **equal** subsidy+fees (`!=` rejects) | must be **≤** (`>` rejects) | `main.cpp:739` |

plus denomination `COIN = 1,000,000` (no "satoshi") and a **fixed** `1*CENT` fee.

> Satoshi's own comment on `MINPROOFOFWORK = 20`: *"ridiculously easy for testing."*

## Nothing disabled

November never had a Script file, so it disabled nothing. NOV08‑X's Script engine is
reconstructed from the interface `main.cpp` references (`CScript`, `OP_CHECKSIG`)
using the lab's own MODEL/PORT — carrying the **complete original opcode vocabulary**
(`OP_CAT`, `OP_MUL`, `OP_LSHIFT`, `OP_INVERT`, …). `test_nov08x.py` runs them live.

## Files

- `rules_nov08.json` / `rules_jan09.json` — the frozen rule sets (source‑anchored).
- `consensus.py` — one parameterised engine (subsidy / PoW / retarget / coinbase).
- `node.py` — `Nov08xNode`: mines + validates a chain under NOV08 rules (reuses
  `../p2p/chainsync` plumbing). `python node.py` mines three 100‑coin blocks.
- `differential.py` — writes `DIFFERENTIAL.md` (NOV08‑X vs JAN09) + `PROVENANCE.json`.
- `test_nov08x.py` — 14 tests: subsidy, PoW encoding, retarget, coinbase rule,
  denomination, the node mining a real chain, an underpaid‑coinbase rejection, and
  the full vocabulary executing.

## Run

```bash
python differential.py     # -> DIFFERENTIAL.md + PROVENANCE.json, prints the comparison
python node.py             # mines a 3-block NOV08-X chain (nBits=20)
python -m pytest           # 14 passed
```

## Boundary

This is **NOV08‑Minimal** — the monetary + PoW + coinbase constitution, executed and
differentially tested. Still open (per the ledger): mint the NOV08‑X **genesis +
network identity** (new magic/ports/address version) and bring up two isolated
nodes; and the interpretive **NOV08‑Full**, which stays walled off as speculation.
It is **not** recovered history and **not** "true Bitcoin" — a new experimental
descendant, treated as neutrally as any other.
