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

### Independent cross-check ≠ ranking

Where a chain's implementation is installable, its profile is additionally
*executed* as a cross-check. Today that is true for exactly one chain — **BTC**
(`python-bitcoinlib`) — so its documented profile was executed and confirmed
(every broad-vocabulary opcode rejected, every control opcode runs). This is a
rigor bonus reflecting **which library happened to be installable**, and the
identical cross-check would be applied to BCH / BSV / XEC given their software. It
does **not** elevate BTC above the others.

## What it shows

The broad vocabulary (`OP_CAT`, `OP_SUBSTR/LEFT/RIGHT`, `OP_INVERT`, `OP_AND/OR/XOR`,
`OP_MUL/DIV/MOD`, `OP_LSHIFT/RSHIFT`, `OP_2MUL/2DIV`) **is native to v0.1**. From the
origin, the descendants made different selections — some disabled it, some restored
parts, some restored (nearly) all. See `MATRIX.md` / `conformance.json`.

## Run

```bash
python conformance.py     # -> MATRIX.md + conformance.json
python -m pytest          # baseline executes; BTC profile cross-checked (skips if lib absent)
```

`python-bitcoinlib` (optional) provides the independent BTC cross-check; the code
points its OpenSSL at a local install best-effort and degrades gracefully if absent.

## Honest boundary

BCH / BSV / XEC rows are **documented, not executed here** — running vectors against
their consensus needs their node software, a later step applied **equally** to every
candidate. Placed at Tier 4 (interpretation) per `../../../common/AUTHORITY.md`.

## Sources

- **BTC**: `bitcoin.core.script.DISABLED_OPCODES` (independent lib; matches Bitcoin Core).
- **BCH**: Bitcoin Cash *May 2018* upgrade (`OP_CAT`, `OP_AND/OR/XOR`, `OP_DIV`, `OP_MOD`; `OP_SPLIT`).
- **BSV**: Bitcoin SV *Genesis* (2020-02), "restore original Script".
- **XEC** (eCash): fork of BCH (2021-11); inherits BCH's script rules for these opcodes.
