# NOV08‑X — NOV08‑Minimal (R8, headless)

**Evidence level: `MODEL`.** The first executable slice of **NOV08‑X**: a
counterfactual network that runs **November 2008's constitution** on the lab's
existing engines — no period‑toolchain compile. Design contract:
[`common/nov08x/DESIGN_LEDGER.md`](https://github.com/original-bitcoin-laboratory/common/blob/main/nov08x/DESIGN_LEDGER.md).

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
- `net.py` — **the live network**: mints the NOV08‑X genesis + identity and runs two
  isolated nodes that synchronise the chain. `python net.py` mints the genesis and
  syncs two nodes end‑to‑end.
- `differential.py` — writes `DIFFERENTIAL.md` (NOV08‑X vs JAN09) + `PROVENANCE.json`.
- `test_nov08x.py` / `test_net.py` — 20 tests: subsidy, PoW encoding, retarget,
  coinbase rule, denomination, the node mining a real chain, an underpaid‑coinbase
  rejection, the full vocabulary executing, and the two‑node network (below).

## The live network (`net.py`)

NOV08‑X now runs as an actual network, reusing the `../p2p/chainsync` sync path
(version → getblocks → inv → getdata → block, orphan + height‑based reorg) with its
**own identity** (all NEW‑EXP — never a NOV08 semantics change) and NOV08's
leading‑zero‑bits PoW:

| Item | NOV08‑X | vs |
|---|---|---|
| network magic | `f0 0b a7 08` | mainnet `f9 be b4 d9` |
| default port | `18008` | `8333` |
| address version | `0x35` | `0x00` |
| genesis | freshly mined, 20 leading‑zero‑bit PoW, coinbase *"NOV08‑X lab chain: 15 Nov 2008 pre‑release, not money"*, 100‑coin reward | JAN09 `000000000019d668…` |

A mainnet‑framed message is refused by a NOV08‑X reader, and two nodes with only the
genesis + the seeded chain synchronise to the same tip — a *live* counterfactual net,
provably isolated from any historical or live chain.

## Run

```bash
python differential.py     # -> DIFFERENTIAL.md + PROVENANCE.json, prints the comparison
python node.py             # mines a 3-block NOV08-X chain (nBits=20)
python -m pytest           # 14 passed
```

## Boundary

**NOV08‑Minimal + the live network are done**: the monetary + PoW + coinbase
constitution executes, differentially tested against JAN09, and two isolated nodes
synchronise a NOV08‑X chain under a distinct network identity. Still open (per the
ledger): the interpretive **NOV08‑Full** completion, which stays walled off as
speculation. NOV08‑X is **not** recovered history and **not** "true Bitcoin" — a new
experimental descendant, treated as neutrally as any other.
