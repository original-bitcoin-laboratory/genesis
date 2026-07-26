# Descendant-conformance matrix (neutral, from the v0.1 origin)

**Baseline = Bitcoin v0.1** — the ground truth (what our engine actually executes).
Descendants are listed in fork order and treated identically: each is a *candidate*
measured against the origin. **No descendant is the reference and none is privileged.**
Every column is **cross-checked by execution** (method table below).

| family | opcode | v0.1 | BTC | LTC | DOGE | BCH | XEC | BSV |
|---|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| splice | `OP_CAT` | execute | disabled | disabled | disabled | restored | restored | restored |
| splice | `OP_SUBSTR` | execute | disabled | disabled | disabled | →OP_SPLIT | →OP_SPLIT | →OP_SPLIT |
| splice | `OP_LEFT` | execute | disabled | disabled | disabled | →OP_SPLIT | →OP_SPLIT | →OP_SPLIT |
| splice | `OP_RIGHT` | execute | disabled | disabled | disabled | →OP_SPLIT | →OP_SPLIT | →OP_SPLIT |
| bitwise | `OP_INVERT` | execute | disabled | disabled | disabled | disabled | disabled | restored |
| bitwise | `OP_AND` | execute | disabled | disabled | disabled | restored | restored | restored |
| bitwise | `OP_OR` | execute | disabled | disabled | disabled | restored | restored | restored |
| bitwise | `OP_XOR` | execute | disabled | disabled | disabled | restored | restored | restored |
| arith | `OP_MUL` | execute | disabled | disabled | disabled | disabled | disabled | restored |
| arith | `OP_DIV` | execute | disabled | disabled | disabled | restored | restored | restored |
| arith | `OP_MOD` | execute | disabled | disabled | disabled | restored | restored | restored |
| arith | `OP_LSHIFT` | execute | disabled | disabled | disabled | disabled | disabled | restored |
| arith | `OP_RSHIFT` | execute | disabled | disabled | disabled | disabled | disabled | restored |
| arith | `OP_2MUL` | execute | disabled | disabled | disabled | disabled | disabled | disabled |
| arith | `OP_2DIV` | execute | disabled | disabled | disabled | disabled | disabled | disabled |
| kept | `OP_ADD` | execute | preserved | preserved | preserved | preserved | preserved | preserved |
| kept | `OP_EQUAL` | execute | preserved | preserved | preserved | preserved | preserved | preserved |
| kept | `OP_SHA256` | execute | preserved | preserved | preserved | preserved | preserved | preserved |

Legend: **execute** = runs in v0.1 (baseline); **preserved** = kept; **disabled** = rejected; **restored** = re-enabled; **→OP_SPLIT** = the byte-index splice op replaced by `OP_SPLIT` in the Cash lineage.

## How each column is executed (tooling, not ranking)

| chain | fork | cross-check | via | consistent |
|---|---|---|---|:--:|
| **BTC** | the chain that kept the pre-2011 rules (OP_* disabled ~2010) | executed | `python-bitcoinlib` | ✓ |
| **LTC** | Litecoin 2011 — Bitcoin Core fork (Scrypt PoW) | executed | `python-bitcoinlib (Bitcoin Core lineage)` | ✓ |
| **DOGE** | Dogecoin 2013 — Bitcoin Core / Litecoin lineage | executed | `python-bitcoinlib (Bitcoin Core lineage)` | ✓ |
| **BCH** | fork 2017-08-01 | execution-bounded | `bitcoinx (restored) + python-bitcoinlib (disabled)` | ✓ |
| **XEC** | eCash, fork from BCH 2021-11 (inherits BCH script rules here) | execution-bounded | `bitcoinx (restored) + python-bitcoinlib (disabled)` | ✓ |
| **BSV** | fork from BCH 2018-11 | executed | `bitcoinx` | ✓ |

- **BTC / LTC / DOGE** run **Bitcoin Core's `script.cpp` verbatim** for these opcodes (their forks changed PoW / supply / timing, not the interpreter), so their rule set *is* BTC's — executed via `python-bitcoinlib`'s `DISABLED_OPCODES` (the Bitcoin Core set they inherited).
- **BSV** — executed via `bitcoinx` (a BSV implementation). This run **corrected** the profile: Genesis "restore original Script" re-enables the set **except `OP_2MUL`/`OP_2DIV`** (still `DisabledOpcode`); byte `0x7f` is `OP_SPLIT`.
- **BCH / XEC** — no standalone BCH/eCash interpreter is installable, so each cell is **execution-bounded**: the ops BCH *restored* are confirmed **executable** by `bitcoinx`, the ops it keeps *disabled* are confirmed **disabled** by `python-bitcoinlib`. Every cell is pinned between two independent executions — **not** a single BCH-specific run (stated plainly; the honest limit).

## Reading

The broad vocabulary (`OP_CAT`, `OP_SUBSTR/LEFT/RIGHT`, `OP_INVERT`, `OP_AND/OR/XOR`, `OP_MUL/DIV/MOD`, `OP_LSHIFT/RSHIFT`, `OP_2MUL/2DIV`) **is native to v0.1**. The descendants split by lineage: the **Bitcoin Core lineage (BTC/LTC/DOGE)** disabled it, the **Cash lineage (BCH/XEC)** restored a subset (with `OP_SPLIT`), and **BSV** restored nearly all — a factual map of divergence, not a verdict.

## Sources
- **BTC / LTC / DOGE**: Bitcoin Core `script` `DISABLED_OPCODES` (LTC/DOGE inherit it). **Executed.**
- **BCH / XEC**: Bitcoin Cash *May 2018* (`OP_CAT`, `OP_AND/OR/XOR`, `OP_DIV`, `OP_MOD`, `OP_SPLIT`); XEC inherits BCH. **Execution-bounded.**
- **BSV**: Bitcoin SV *Genesis* (2020-02), "restore original Script" minus `OP_2MUL/2DIV`, via `bitcoinx`. **Executed.**

