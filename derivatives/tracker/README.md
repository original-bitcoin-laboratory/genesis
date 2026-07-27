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
reference = whitepaper :  BTC 0   nov08 0   v0.1.0 0   ...   (all zero)
reference = nov08      :  v0.1.0 2   BTC 2   BCH 2   BSV 2   ...
reference = v0.1.0      :  nov08 2   BSV 6   BCH 7   BTC 7   XEC 7   (2026)
```

- **Origin = whitepaper → everyone is distance 0.** The design constrains **none** of the nine
  implementation axes, so it does not discriminate — the executable form of "the design is too
  thin to pick a winner."
- **Origin = nov08 → v0.1.0 is itself distance 2** (it differs on `monetary` and `pow_algo`,
  the only axes the pre‑release fixes). So the whole BTC family starts *nonzero* under this
  anchor — v0.1.0 is **not** the zero point here.
- **Origin = v0.1.0 → the familiar drift:** BTC moves to 7 of 9 axes by 2016; BSV's 2020
  Genesis moves it *back* on `script_limits` (to 6) while `script_vocabulary` stays different
  ("near‑full" ≠ "full"); nov08 sits at 2.

The same chain has three different distances under three origins. **v0.1.0 is the zero point
only if you choose it as the origin** — the tool makes that choice explicit and swappable.

## Model

- **Axes** — 9 properties a codebase takes a *value* on (opcode vocabulary, value bounds, block
  size, script limits, sig encoding, crypto lib, PoW, monetary, consensus DB).
- **Frozen references** — `whitepaper` (all axes unspecified — the design fixes none),
  `nov08` (only `monetary` + `pow_algo` fixed — a partial 5‑file snapshot), `v0.1.0` (all nine).
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
python tracker.py          # every origin × milestone dates
python -m pytest           # 9 passed
```

`references()` lists the origins; `track(reference, date)` returns every version's distance +
differing axes at that date; `distance(reference, candidate, date)` the scalar; `define(ref)`
the reference's axis‑values.

## Boundary

MODEL; v0.1.0/nov08 axis‑values source‑verified, chain event dates documented; distance is
neutral displacement from a **chosen** reference, **not** identity ("which is the real Bitcoin"
is convention) and **not** quality. A tool, never authority (`AUTHORITY.md`).
