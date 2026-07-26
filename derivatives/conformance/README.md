# Descendant-conformance matrix (neutral, from the origin)

We operate from the **foundations**: Bitcoin v0.1 is the sole baseline / ground
truth (what our engine actually executes). Every later chain — BTC, BCH, BSV, XEC
(eCash), and any other genesis-descendant — is treated **identically**: a *candidate*
measured against the origin, described by a documented rule-profile (which v0.1
behaviours it preserves / disables / restores / replaces).

**No descendant is the reference, and none is privileged.** This project takes no
position on which chain is "Bitcoin"; it maps divergence from the source, factually.

## Method (uniform for every descendant)

- **v0.1** — the only executed, authoritative column (our MODEL, cross-validated by
  `../port` and `../node`).
- **Each descendant** — a documented rule-profile from that chain's own consensus
  spec, applied to the same v0.1 vectors. Same treatment for all; columns are in
  fork-chronological order, which is **not** a ranking.

### Six descendants, every column cross-checked by execution ≠ ranking

Each column is executed against the most direct independent implementation available —
applied identically, none privileged:

- **BTC / LTC / DOGE** run **Bitcoin Core's `script.cpp` verbatim** for these opcodes
  (their forks changed PoW / supply / timing, *not* the interpreter), so their rule set
  **is** BTC's. Executed via `python-bitcoinlib`'s `DISABLED_OPCODES` — the Bitcoin Core
  set they inherited. *(This is code lineage, not cherry-picking: LTC/DOGE literally
  reuse Bitcoin Core's script engine.)*
- **BSV** — executed via `bitcoinx` (a BSV implementation). This run **corrected the
  documentation**: Genesis "restore original Script" re-enables the set **except
  `OP_2MUL` / `OP_2DIV`** (still `DisabledOpcode`), and `OP_SUBSTR/LEFT/RIGHT` don't
  exist (byte `0x7f` is `OP_SPLIT`).
- **BCH / XEC** — no standalone BCH/eCash interpreter is installable, so each cell is
  **execution-bounded**: the ops BCH *restored* are confirmed **executable** by
  `bitcoinx`, the ops it keeps *disabled* are confirmed **disabled** by
  `python-bitcoinlib`. Every cell is pinned between two independent executions — **not**
  a single BCH-specific run (stated plainly; the honest limit).

The chains split by **lineage**: Bitcoin Core (BTC/LTC/DOGE, broad vocab disabled),
Cash (BCH/XEC, restored subset + `OP_SPLIT`), and BSV (restored nearly all).

## What it shows

The broad vocabulary (`OP_CAT`, `OP_SUBSTR/LEFT/RIGHT`, `OP_INVERT`, `OP_AND/OR/XOR`,
`OP_MUL/DIV/MOD`, `OP_LSHIFT/RSHIFT`, `OP_2MUL/2DIV`) **is native to v0.1**. From the
origin, the descendants made different selections — some disabled it, some restored
parts, some restored (nearly) all. See `MATRIX.md` / `conformance.json`.

## Run

```bash
python conformance.py     # -> MATRIX.md + conformance.json (6 chains + method table)
python -m pytest          # every cell execution-confirmed (skips gracefully if a lib is absent)
```

Optional independent implementations: **`python-bitcoinlib`** (BTC/LTC/DOGE — the shared
Bitcoin Core engine) and **`bitcoinx`** (BSV, and the restored‑op reference for BCH/XEC).
Both degrade gracefully if absent — those tests simply skip.

## Honest boundary

**BCH / XEC** have no standalone interpreter, so they are **execution‑bounded** (each cell
pinned between two independent executions), not run through a single BCH engine — said
plainly. Everything here is Tier 4 (interpretation) over Tier 0 source per
`../../../common/AUTHORITY.md`; a full run against each chain's own node software is the
further step, applied **equally** to every candidate.

## Sources

- **BTC**: `bitcoin.core.script.DISABLED_OPCODES` (independent lib; matches Bitcoin Core). **Executed.**
- **BCH**: Bitcoin Cash *May 2018* upgrade (`OP_CAT`, `OP_AND/OR/XOR`, `OP_DIV`, `OP_MOD`; `OP_SPLIT`). Documented.
- **BSV**: Bitcoin SV *Genesis* (2020-02), "restore original Script" **minus `OP_2MUL`/`OP_2DIV`**, cross-checked with `bitcoinx`. **Executed.**
- **XEC** (eCash): fork of BCH (2021-11); inherits BCH's script rules for these opcodes. Documented.
