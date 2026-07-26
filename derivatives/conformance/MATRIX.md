# Descendant-conformance matrix (neutral, from the v0.1 origin)

**Baseline = Bitcoin v0.1** — the ground truth (what our engine actually executes).
Descendants are listed in fork order and treated identically: each is a *candidate*
measured against the origin, described by a documented rule-profile. **No descendant
is the reference and none is privileged.**

| family | opcode | v0.1 (baseline) | BTC | BCH | BSV | XEC |
|---|---|:--:|:--:|:--:|:--:|:--:|
| splice | `OP_CAT` | execute | disabled | restored | restored | restored |
| splice | `OP_SUBSTR` | execute | disabled | →OP_SPLIT | →OP_SPLIT | →OP_SPLIT |
| splice | `OP_LEFT` | execute | disabled | →OP_SPLIT | →OP_SPLIT | →OP_SPLIT |
| splice | `OP_RIGHT` | execute | disabled | →OP_SPLIT | →OP_SPLIT | →OP_SPLIT |
| bitwise | `OP_INVERT` | execute | disabled | disabled | restored | disabled |
| bitwise | `OP_AND` | execute | disabled | restored | restored | restored |
| bitwise | `OP_OR` | execute | disabled | restored | restored | restored |
| bitwise | `OP_XOR` | execute | disabled | restored | restored | restored |
| arith | `OP_MUL` | execute | disabled | disabled | restored | disabled |
| arith | `OP_DIV` | execute | disabled | restored | restored | restored |
| arith | `OP_MOD` | execute | disabled | restored | restored | restored |
| arith | `OP_LSHIFT` | execute | disabled | disabled | restored | disabled |
| arith | `OP_RSHIFT` | execute | disabled | disabled | restored | disabled |
| arith | `OP_2MUL` | execute | disabled | disabled | disabled | disabled |
| arith | `OP_2DIV` | execute | disabled | disabled | disabled | disabled |
| kept | `OP_ADD` | execute | preserved | preserved | preserved | preserved |
| kept | `OP_EQUAL` | execute | preserved | preserved | preserved | preserved |
| kept | `OP_SHA256` | execute | preserved | preserved | preserved | preserved |

Legend: **execute** = runs in v0.1 (baseline); **preserved** = descendant kept it; **disabled** = descendant rejects it; **restored** = descendant re-enabled it; **→OP_SPLIT** = the byte-index splice op was replaced by `OP_SPLIT` in the Cash lineage.

## Neutrality & method

- The only executed, authoritative column is **v0.1** (our MODEL, cross-validated by `../port` / `../node`). Everything else is measured *against* it.
- Every descendant uses the **same** method: a documented rule-profile from that chain's own consensus spec, and is **cross-checked by execution wherever an independent implementation of that chain is installable**. This project takes no position on which chain is "Bitcoin".
- Column order is fork-chronological, not a ranking.

## Independent cross-checks (tooling, not ranking)

Two chains have an independent implementation installed, so their profiles were **executed** (not just documented) — applied identically, a rigor bonus that reflects which libraries happened to be installable, **not** a preference:

- **BTC** — `python-bitcoinlib`: **consistent** with the documented profile (every broad-vocabulary opcode rejected via `DISABLED_OPCODES`; control opcodes run).
- **BSV** — `bitcoinx` (a BSV implementation): **consistent** with the documented profile. This execution **corrected** the profile: BSV's Genesis "restore original Script" re-enables the arithmetic/bitwise set **except `OP_2MUL` / `OP_2DIV`**, which `bitcoinx` still rejects as `DisabledOpcode`; and `OP_SUBSTR/LEFT/RIGHT` do not exist (byte `0x7f` is `OP_SPLIT`).

**BCH** and **XEC** stay documented-only here — no BCH/eCash-specific interpreter was installable. The same standard is applied to every chain (availability-driven). As corroboration, BCH's restored subset (`OP_CAT`, `OP_AND/OR/XOR`, `OP_DIV`, `OP_MOD`, `OP_SPLIT`) is a **subset of BSV's executed-restored set** above, and its still-disabled set is covered by **BTC's executed-disabled set** — but neither is a BCH-specific run.

## Reading

The broad vocabulary (`OP_CAT`, `OP_SUBSTR/LEFT/RIGHT`, `OP_INVERT`, `OP_AND/OR/XOR`, `OP_MUL/DIV/MOD`, `OP_LSHIFT/RSHIFT`, `OP_2MUL/2DIV`) **is native to v0.1**. From the origin, the descendants simply made different selections: some disabled it, some restored parts, some restored nearly all — a factual map of divergence, not a verdict.

## Sources
- **BTC**: `bitcoin.core.script.DISABLED_OPCODES` (independent lib; matches Bitcoin Core). **Executed.**
- **BCH**: Bitcoin Cash *May 2018* upgrade (`OP_CAT`, `OP_AND/OR/XOR`, `OP_DIV`, `OP_MOD`; `OP_SPLIT`). Documented.
- **BSV**: Bitcoin SV *Genesis* (2020-02), "restore original Script" (minus `OP_2MUL/2DIV`), cross-checked with `bitcoinx`. **Executed.**
- **XEC** (eCash): fork of BCH (2021-11); inherits BCH's script rules for these opcodes. Documented.

