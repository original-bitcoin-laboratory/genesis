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

### Independent cross-checks ≠ ranking

Where a chain's implementation is installable, its profile is additionally
*executed* as a cross-check — applied identically, a rigor bonus reflecting **which
libraries happened to be installable**, not a preference. Two chains qualify today:

- **BTC** — `python-bitcoinlib`: every broad-vocabulary opcode rejected via
  `DISABLED_OPCODES`; control opcodes run. Profile **consistent** with execution.
- **BSV** — `bitcoinx` (a BSV implementation): the profile was **executed and it
  corrected our documentation** — BSV's Genesis "restore original Script" re-enables
  the arithmetic/bitwise set **except `OP_2MUL` / `OP_2DIV`** (still `DisabledOpcode`
  in `bitcoinx`), and `OP_SUBSTR/LEFT/RIGHT` don't exist (byte `0x7f` is `OP_SPLIT`).

**BCH** and **XEC** remain documented-only — no BCH/eCash-specific interpreter was
installable; the *same* standard applies to all. (As corroboration only: BCH's
restored subset is a subset of BSV's executed-restored set, and its disabled set is
covered by BTC's executed-disabled set — but that is not a BCH-specific run.)

## What it shows

The broad vocabulary (`OP_CAT`, `OP_SUBSTR/LEFT/RIGHT`, `OP_INVERT`, `OP_AND/OR/XOR`,
`OP_MUL/DIV/MOD`, `OP_LSHIFT/RSHIFT`, `OP_2MUL/2DIV`) **is native to v0.1**. From the
origin, the descendants made different selections — some disabled it, some restored
parts, some restored (nearly) all. See `MATRIX.md` / `conformance.json`.

## Run

```bash
python conformance.py     # -> MATRIX.md + conformance.json
python -m pytest          # baseline executes; BTC + BSV profiles cross-checked (skip if lib absent)
```

Optional independent implementations: **`python-bitcoinlib`** (BTC cross-check; the
code points its OpenSSL at a local install best-effort) and **`bitcoinx`** (BSV
cross-check). Both degrade gracefully if absent — those tests simply skip.

## Honest boundary

**BCH / XEC** rows are **documented, not executed here** — no BCH/eCash-specific
interpreter was installable; running vectors against their consensus needs their node
software, a later step applied **equally** to every candidate. Placed at Tier 4
(interpretation) per `../../../common/AUTHORITY.md`. **BTC and BSV** are additionally
executed (above).

## Sources

- **BTC**: `bitcoin.core.script.DISABLED_OPCODES` (independent lib; matches Bitcoin Core). **Executed.**
- **BCH**: Bitcoin Cash *May 2018* upgrade (`OP_CAT`, `OP_AND/OR/XOR`, `OP_DIV`, `OP_MOD`; `OP_SPLIT`). Documented.
- **BSV**: Bitcoin SV *Genesis* (2020-02), "restore original Script" **minus `OP_2MUL`/`OP_2DIV`**, cross-checked with `bitcoinx`. **Executed.**
- **XEC** (eCash): fork of BCH (2021-11); inherits BCH's script rules for these opcodes. Documented.
