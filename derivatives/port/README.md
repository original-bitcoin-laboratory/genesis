# EvalScript C++/OpenSSL port (derivative)

**Evidence level: `PORT`** — a compiled derivative, stronger than the Python
`../model` MODEL but still not the unmodified original binary (`JAN09-EXECUTED`,
which means the released `bitcoin.exe` in an isolated VM). This harness runs the
opcode logic in C++ against the **real OpenSSL big-number library** — the same
`BN_*` engine v0.1 used — so the arithmetic edge cases (`BN_div` truncation,
`BN_mod` sign, `BN_lshift/BN_rshift` on negatives) are the library's, not a
reimplementation's.

## What is original vs ported

| Part | Status |
|---|---|
| number codec `setvch` / `getvch` / `getint` | **original logic** from `bignum.h` (BN_mpi2bn / BN_bn2mpi / BN_get_word) |
| arithmetic (`BN_add/sub/mul/div/mod/lshift/rshift`, `BN_cmp`) | **real OpenSSL** — the actual engine |
| opcode bodies (splice / bitwise / numeric / compare / within) | reproduced from `script.cpp` EvalScript |
| `CBigNum` **class shape** | **ported**: 2009 code did `class CBigNum : public BIGNUM`, impossible on OpenSSL 3.x (opaque `BIGNUM`), so this holds a `BIGNUM*` member instead |
| script parser, ECDSA (`OP_CHECKSIG`/`CHECKMULTISIG`), control flow | out of scope (as in the MODEL) |

## Differential result

`run.sh` builds the port, runs it and the Python MODEL over the same
`vectors.txt`, and diffs. Current result:

```
IDENTICAL on 39 vectors — Python MODEL == real OpenSSL BN port
```

i.e. the Python MODEL's number/opcode semantics are confirmed against real
OpenSSL across the "broad vocabulary" (`OP_CAT`, `OP_MUL/DIV/MOD`,
`OP_LSHIFT/RSHIFT`, `OP_2MUL/2DIV`, `OP_INVERT/AND/OR/XOR`, splice, compare,
`OP_WITHIN`, `SHA256`/`HASH256`/`SHA1`), **including all signed-operand cases**
(`-20/6 → -3`, `-20 mod 6 → -2`, `-256 >> 4 → -16`, …). This is the charter's
differential-testing method: the MODEL is validated against the original engine.

## Build & run

```bash
# MSYS2/MinGW (this machine): g++ 16.1.0 + OpenSSL 3.x
export GXX=/c/msys64/mingw64/bin/g++
export PATH="/c/msys64/mingw64/bin:$PATH"   # for libcrypto DLL at runtime
./run.sh
```

Build artifacts (`port.exe`, `cxx_out.txt`, `py_out.txt`) are gitignored.
