# Descendant-conformance matrix (v0.1 baseline)

BTC column: **EXECUTED against python-bitcoinlib**. v0.1 = our MODEL (cross-validated by derivatives/port). BCH/BSV = DOCUMENTED (cited below), not executed here.

| family | opcode | v0.1 | BTC | BCH | BSV |
|---|---|:--:|:--:|:--:|:--:|
| splice | `OP_CAT` | execute | disabled | restored | restored |
| splice | `OP_SUBSTR` | execute | disabled | →OP_SPLIT | →OP_SPLIT |
| splice | `OP_LEFT` | execute | disabled | →OP_SPLIT | →OP_SPLIT |
| splice | `OP_RIGHT` | execute | disabled | →OP_SPLIT | →OP_SPLIT |
| bitwise | `OP_INVERT` | execute | disabled | disabled | restored |
| bitwise | `OP_AND` | execute | disabled | restored | restored |
| bitwise | `OP_OR` | execute | disabled | restored | restored |
| bitwise | `OP_XOR` | execute | disabled | restored | restored |
| arith | `OP_MUL` | execute | disabled | disabled | restored |
| arith | `OP_DIV` | execute | disabled | restored | restored |
| arith | `OP_MOD` | execute | disabled | restored | restored |
| arith | `OP_LSHIFT` | execute | disabled | disabled | restored |
| arith | `OP_RSHIFT` | execute | disabled | disabled | restored |
| arith | `OP_2MUL` | execute | disabled | disabled | restored |
| arith | `OP_2DIV` | execute | disabled | disabled | restored |
| kept | `OP_ADD` | execute | execute | kept | kept |
| kept | `OP_EQUAL` | execute | execute | kept | kept |
| kept | `OP_SHA256` | execute | execute | kept | kept |

Legend: **execute** = runs / accepted; **disabled** = rejected by consensus; **restored** = re-enabled by that chain; **→OP_SPLIT** = the byte-splice op was replaced by `OP_SPLIT`; **kept** = never disabled.

## Reading

The whole *broad vocabulary* (`OP_CAT`, `OP_SUBSTR/LEFT/RIGHT`, `OP_INVERT`, `OP_AND/OR/XOR`, `OP_MUL/DIV/MOD`, `OP_LSHIFT/RSHIFT`, `OP_2MUL/2DIV`) **executes in v0.1** and is **disabled in BTC** — confirmed by running the vectors through an independent BTC implementation, not by reading BIPs. BCH restored a subset (splice/bitwise/DIV/MOD, with `OP_SPLIT` replacing the byte-index ops); BSV restored the original set (Genesis). This is the executable form of "who preserved what".

## Sources (documented columns)
- BTC disabled set: python-bitcoinlib `bitcoin.core.script.DISABLED_OPCODES` (mirrors Bitcoin Core consensus).
- BCH: Bitcoin Cash May 2018 upgrade (re-enabled opcodes; `OP_SPLIT`).
- BSV: Bitcoin SV *Genesis* upgrade (Feb 2020), "restore original Script".

> DESCENDANT rows for BCH/BSV are documented, not executed here — running vectors against BCH/BSV nodes needs their software (a later step). The v0.1↔BTC contrast IS executed.
