# Descendant-conformance matrix

The charter's neutral comparison, made executable: take v0.1's **broad vocabulary**
(the opcodes later disabled in BTC) and measure each descendant against the v0.1
baseline — not the other way round.

| column | evidence level |
|---|---|
| **v0.1** | `MODEL` — our reproduction (cross-validated by `../port`, `../node`) |
| **BTC** | **`EXECUTED`** against `python-bitcoinlib` (an *independent* BTC implementation) |
| **BCH** | `DOCUMENTED` — cited spec, **not executed here** |
| **BSV** | `DOCUMENTED` — cited spec, **not executed here** |

`conformance.py` runs each vector through our interpreter **and** through BTC's
`EvalScript`, and writes `MATRIX.md` + `conformance.json`. Result: the whole
vocabulary (`OP_CAT`, `OP_SUBSTR/LEFT/RIGHT`, `OP_INVERT`, `OP_AND/OR/XOR`,
`OP_MUL/DIV/MOD`, `OP_LSHIFT/RSHIFT`, `OP_2MUL/2DIV`) **executes in v0.1** and is
**disabled in BTC** — verified by *running* it, not by reading BIPs. Control
opcodes (`OP_ADD`, `OP_EQUAL`, `OP_SHA256`) execute on both.

## Run

```bash
python -m pip install python-bitcoinlib     # independent BTC implementation
python conformance.py                       # -> MATRIX.md + conformance.json
python -m pytest                            # asserts the v0.1<->BTC contrast
```

`python-bitcoinlib`'s `scripteval` loads OpenSSL via `ctypes`; `conformance.py`
points it at a local OpenSSL (MSYS2 / OpenSSL-Win64) best-effort. If OpenSSL isn't
found, it falls back to the library's `DISABLED_OPCODES` set (still authoritative,
just not "executed"). If `python-bitcoinlib` is absent, the BTC/BCH/BSV columns
degrade gracefully and the BTC tests skip.

## Honest boundary

The **v0.1 ↔ BTC** contrast is *executed*. **BCH/BSV are documented** (cited),
because running vectors against BCH/BSV consensus needs their node software — a
separate setup, not a VM issue. Placed at Tier 4 (interpretation) per
`../../../common/AUTHORITY.md` until executed.

## Sources (documented columns)

- **BTC** disabled set: `bitcoin.core.script.DISABLED_OPCODES` (mirrors Bitcoin Core).
- **BCH**: Bitcoin Cash *May 2018* upgrade — re-enabled `OP_CAT`, `OP_AND/OR/XOR`,
  `OP_DIV`, `OP_MOD`; `OP_SPLIT` replaces the byte-index splice ops.
- **BSV**: Bitcoin SV *Genesis* (Feb 2020) — "restore original Script" (arithmetic,
  bitwise, splice via `OP_SPLIT`).
