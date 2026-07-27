# EvalScript MODEL (derivative)

**Evidence level: `MODEL`** — a reimplementation / harness, **not** `JAN09-EXECUTED`.
This is a DERIVATIVE (it lives under `derivatives/`, never in the canonical tree)
and carries **no authority on its own**. It re-expresses, in Python, the opcode
execution bodies of v0.1.0 `EvalScript` and the CBigNum number codec, so the
"broad vocabulary" of original Script can be *run* and inspected.

## Why this exists

The R1 inventory established, from source, that 94 of 106 opcodes have an
`EvalScript` execution branch (`../../inventory/OPCODES.md`) — including the
families later **disabled in BTC** (`OP_CAT`, `OP_SUBSTR`, `OP_LEFT/RIGHT`,
`OP_INVERT`, `OP_AND/OR/XOR`, `OP_MUL`, `OP_DIV`, `OP_MOD`, `OP_LSHIFT`,
`OP_RSHIFT`, `OP_2MUL`, `OP_2DIV`). This MODEL makes that claim **executable**: the
vectors show those opcodes actually compute their documented results.

## Source mapping (what this models)

Modeled from the extracted, hash-verified v0.1.0 source:

- `src/script.cpp` — `EvalScript` opcode bodies
  (sha256 `347c7526932d42a4d10ae487150b709e2ead737aa4b05f50aa9e2eefeb05a5b5`).
- `src/bignum.h` — `CBigNum::setvch/getvch/getint`, the sign-magnitude,
  little-endian number codec (sign bit = MSB of the last byte).

| MODEL area | `script.cpp` lines |
|---|---|
| number codec (`CastToBool`, `MakeSameSize`) | 21–33 |
| splice (`OP_CAT`/`OP_SUBSTR`/`OP_LEFT`/`OP_RIGHT`/`OP_SIZE`) | 377–438 |
| bitwise (`OP_INVERT`/`OP_AND`/`OP_OR`/`OP_XOR`) | 444–482 |
| equality (`OP_EQUAL`/`OP_EQUALVERIFY`) | 484–510 |
| numeric unary (`OP_1ADD`…`OP_0NOTEQUAL`) | 516–543 |
| numeric binary (`OP_ADD`…`OP_MAX`) | 545–631 |
| `OP_WITHIN` | 633–647 |
| hashes (`OP_SHA1/SHA256/HASH160/HASH256/RIPEMD160`) | 653–684 |

## What it deliberately does NOT model (yet)

To keep the MODEL honest about its scope, it omits — pending a real port/build:

- the **byte-level** script serializer/parser (`CScript::operator<<`, `GetOp`);
  scripts here are token lists, not raw bytes.
- **ECDSA** paths: `OP_CHECKSIG(VERIFY)`, `OP_CHECKMULTISIG(VERIFY)`,
  `SignatureHash`, and the `CTransaction` context.
- **control flow** `OP_IF/NOTIF/ELSE/ENDIF`, `OP_CODESEPARATOR`, alt-stack.
- consensus limits and standardness.

## Status in the evidence ladder

`OPCODES.md` establishes *declared* + *implemented* (rungs 1–2) from source. This
MODEL is a runnable cross-check of the **opcode semantics only**. It is **not**
proof of `JAN09-EXECUTED` (rung: reproduced with the historical implementation),
which requires building/porting the original C++ (blocked here: no C++ toolchain).
When a real port exists, these vectors become its **differential oracle**.

## Opcode coverage

`test_opcode_coverage.py` exercises **every opcode the model can execute** — each with a
Python vector that succeeds only if the opcode computes correctly (crypto opcodes use a real
secp256k1 checker). A **regression guard** derives the executable opcode set from the model
source and fails if any opcode lacks a vector, so the whole vocabulary stays covered in the
default (no‑C++) reproducible run.

## Run

```bash
python -m pytest derivatives/model/ -q      # full model suite incl. exhaustive opcode coverage
```
