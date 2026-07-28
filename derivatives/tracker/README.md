# Reference-distance tracker — pick any origin, pick any date

The runnable, now **reference‑selectable** form of
[`WHAT_IS_BITCOIN.md` §9](https://github.com/original-bitcoin-laboratory/common/blob/main/WHAT_IS_BITCOIN.md)
and [`DEFINITIONAL_FIDELITY.md`](https://github.com/original-bitcoin-laboratory/common/blob/main/DEFINITIONAL_FIDELITY.md).
An interactive page is at [`../../docs/tracker.html`](../../docs/tracker.html).

## What it does — and does not — do

It does **not** identify "*the* real Bitcoin" (convention — no fact of the matter). It lets you
**choose an origin, choose a date, and see every version that existed then and how far each
stood from that origin.** The **origin is a parameter** on purpose: "the origin" is itself a
*choice*, not a fact (WHAT_IS_BITCOIN §8), so the tracker names it rather than smuggling one in.

**Distance is neutral** — the number of axes on which a version's *value* differs from the
reference's. A safety fix (`MoneyRange`) and a feature removal (disabling opcodes) both change
a value, so both add distance; nothing is ranked better or worse.

## Choosing the origin changes everything — that's the point

```
reference = whitepaper :  everyone 0                              (all zero)
reference = nov08      :  NOV08-X 0   v0.1.0 2   BTC 2   BCH 2   BSV 2   JAN09-X 2 ...
reference = v0.1.0      :  JAN09-X 1   nov08 2   NOV08-X 3   BSV 6   BCH 8   BTC 9   XEC 9   (2026)
```

- **Origin = whitepaper → everyone is distance 0.** The design constrains **none** of the
  eleven implementation axes, so it does not discriminate — the executable form of "the design
  is too thin to pick a winner."
- **Origin = nov08 → v0.1.0 is itself distance 2** (it differs on `monetary` and `pow_algo`,
  the only axes the pre‑release fixes), and the lab's `NOV08-X` reads **0**. So v0.1.0 is
  **not** the zero point here.
- **Origin = v0.1.0 → the drift, over 11 axes:** BTC moves to **9 of 11** by 2026 (adding
  SegWit 2017 + Taproot/Schnorr 2021 on top of the 2010–2016 changes); **BSV is the *closest*
  big chain at 6** — it rejected SegWit/Schnorr and restored the script vocabulary/limits;
  BCH sits at 8, XEC at 9 (eCash redenomination). None of this is a quality ranking — just
  displacement.

The same chain has three different distances under three origins. **v0.1.0 is the zero point
only if you choose it as the origin** — the tool makes that choice explicit and swappable.

## Model

- **Axes** — 11 properties a codebase takes a *value* on (opcode vocabulary, value bounds, block
  size, script limits, sig encoding, crypto lib, PoW, monetary, consensus DB, **witness/SegWit**,
  **signature scheme/Schnorr**). Each has an **operational definition** in `AXIS_DEFS` — the
  checkable property that fixes its value (e.g. `block_size` records that v0.1.0 has no dedicated
  `MAX_BLOCK_SIZE` but a 32 MiB `MAX_SIZE` serialization ceiling, distinct from BSV's removed cap),
  so a value is contested against evidence, not opinion. The set is itself a choice and is
  extensible — difficulty algorithm, address formats, and finer chain‑splits are natural additions.
- **Frozen references** — `whitepaper` (all axes unspecified — the design fixes none),
  `nov08` (only `monetary` + `pow_algo` fixed — a partial 5‑file snapshot), `v0.1.0` (all eleven).
  `[S]` for nov08/v0.1.0 values.
- **Events `[D]`** — dated changes a chain makes to an axis (public record; a curated scaffold,
  refinable). Forks inherit the parent's state at the fork date, then diverge.
- **Distance(ref, cand)** = axes where **both specify a value and differ** (axes the reference
  does not constrain are skipped).

Genesis‑*sharing* continuations only (BTC/BCH/BSV/XEC). Separate‑genesis instances (LTC/DOGE)
are a different category — genesis‑divergent from launch — the model could be extended to.

**The lab's reconstructions** (`NOV08-X`, `JAN09-X`) join the candidate set from **26 Jul 2026** —
frozen MODEL builds carrying the full original vocabulary (nothing disabled, `full+ne`) under each
constitution. So `NOV08-X` reads **0** from the `nov08` anchor and `JAN09-X` reads **1** from
`v0.1.0` (it differs only by re‑opening the one opcode v0.1 disabled). They are candidates *for
reference*, not "the real Bitcoin." `crypto_lib`/`consensus_db` are unspecified for them (a Python
MODEL abstracts that layer).

**Anchors vs senses:** the three origins are the whitepaper (design, sense 1) and nov08/v0.1.0
(reference implementation, sense 2). The network/ledger/unit/genus senses (3–7) are *not* offered
as anchors — an origin you measure *from* must be a fixed artifact; a network‑state anchor
("BTC @ 2015") is the one sensible extension, and the engine already supports it.

```bash
python tracker.py          # every origin × milestone dates + a robustness line
python -m pytest           # 18 passed
```

`references()` lists the origins; `track(reference, date)` returns every version's distance +
differing axes at that date; `distance(reference, candidate, date)` the scalar; `define(ref)`
the reference's axis‑values; `differing_axes(ref, cand, date)` the axis list.

**Robustness (does the answer depend on which axes we chose?)** — because the axis set is a choice,
a conclusion is only worth stating if it survives that choice. `robustness(ref, closer, farther,
date)` enumerates all axis subsets and reports the fraction in which the ordering holds;
`subset_lattice(ref, date)` shows which chains' differing‑axis sets contain which. When one
differing set is a subset of another the ordering holds in **every** subset (structurally) — e.g.
from the `v0.1.0` origin, BSV's differing set is a subset of BTC's, so "BSV at least as close as
BTC" holds in 2047/2047 axis subsets. Absolute distances are not so robust and are always reported
with their `(origin, axis‑set)`.

## Boundary

MODEL; v0.1.0/nov08 axis‑values source‑verified, chain event dates documented; distance is
neutral displacement from a **chosen** reference, **not** identity ("which is the real Bitcoin"
is convention) and **not** quality. A tool, never authority (`AUTHORITY.md`).
