# Origin‑distance tracker — the "time axis," executed

The runnable form of [`WHAT_IS_BITCOIN.md` §9](https://github.com/original-bitcoin-laboratory/common/blob/main/WHAT_IS_BITCOIN.md)
and [`DEFINITIONAL_FIDELITY.md`](https://github.com/original-bitcoin-laboratory/common/blob/main/DEFINITIONAL_FIDELITY.md).

## What it does — and does not — do

It does **not** track "*the* real Bitcoin." Which live network *is* Bitcoin is **convention**
— no fact of the matter (see the docs). What it tracks is the one thing that *is* a fact: how
far each claimant has **drifted from the origin** at any date. The origin (v0.1.0) is a frozen
reference; the tracker measures displacement from it over time.

**Distance is neutral.** Adding `MoneyRange` (a safety fix) and disabling opcodes (a feature
removal) both *increase* distance equally. The tracker ranks nothing as better or worse — it
measures displacement, not quality. (Reading distance as "worse" is the exact move
[`THESIS.md`](https://github.com/original-bitcoin-laboratory/common/blob/main/THESIS.md)
disowns.)

## What it shows

```
2009-01-03  genesis                     BTC 0.0
2011-01-01  after the 2010 hardening    BTC 4.0   (vocabulary, value bounds, block size, script limits)
2016-01-01  after BIP66 + libsecp256k1  BTC 6.0
2018-01-01  after the BTC/BCH split     BTC 7.0   BCH 7.0  (BCH inherits BTC's drift at the fork)
2021-01-01  after BSV Genesis           BSV 6.0*  BCH 6.5* XEC 6.5*  BTC 7.0
2026-08-01  today                       JAN09-X 0.0   BSV 6.0  BCH/XEC 6.5  BTC 7.0
```

Three findings fall out, all neutral and all from the model:

- **At genesis the origin chain sits at 0** — it *is* the origin. Every claimant, **including
  the name‑bearing chain (BTC)**, drifts away from v0.1.0 over time; by 2016 BTC has moved on
  7 of 9 axes (only the monetary schedule and SHA‑256d PoW are unchanged).
- **Drift is not monotonic.** A chain can move *back* toward the origin: BCH re‑enabled opcodes
  (2018) and BSV's Genesis upgrade (2020) restored the script vocabulary and removed the script
  limits — so BSV's distance *fell* from 6.5 to 6.0 (`*` = restored toward origin, weight 0.5).
- **The only living zero‑distance thing today is a reconstruction** (the lab's JAN09‑X, full
  origin profile) — and it is a *new instance*, not a continuation. Nothing that carries the
  name is at the origin.

## Model

- **Axes `[S]`** — 9 origin‑defining properties from the lab's executed v0.1.0 conformance work
  (opcode vocabulary, value bounds, block size, script limits, sig encoding, crypto lib, PoW,
  monetary, consensus DB).
- **Events `[D]`** — dated changes curated from the public record (2010 hardening, LevelDB 2013,
  BIP66 2015, libsecp256k1 2016, BCH fork/restore 2017–18, BSV Genesis 2020). **A scaffold, not
  an authoritative history** — refinable, same executed‑vs‑documented discipline as
  `DEPENDENCY_MATRIX`.
- **Forks inherit** the parent's state at the fork date, then diverge independently.
- Genesis‑*sharing* continuations only (BTC/BCH/BSV/XEC). Separate‑genesis instances (LTC/DOGE)
  are a different category — genesis‑divergent from launch — that the model could be extended
  to; they are not continuations of the origin chain.

```bash
python tracker.py          # the timeline above
python -m pytest           # 10 passed
```

`define()` returns the fixed origin reference; `track(date)` returns every claimant's
origin‑distance and moved axes at that date; `distance(chain, date)` the scalar.

## Boundary

MODEL; origin axes source‑verified, event dates documented; distance is neutral displacement
from v0.1.0, **not** identity ("which is the real Bitcoin" is convention) and **not** quality.
A tool, never authority (`AUTHORITY.md`).
