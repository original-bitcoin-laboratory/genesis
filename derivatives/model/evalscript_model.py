"""MODEL of Bitcoin v0.1.0 EvalScript opcode semantics.

Evidence level: **MODEL** (a reimplementation / harness), NOT JAN09-EXECUTED.
This is a DERIVATIVE — it re-expresses, in Python, the opcode execution bodies of
`script.cpp` (EvalScript) and the CBigNum number codec of `bignum.h`, so that the
"broad vocabulary" of v0.1 Script can be *run*. It is not the original C++ and
carries no authority on its own; it exists to be differentially tested against a
real port/build once one is available. See README.md for the source mapping.

Number codec (from bignum.h setvch/getvch via OpenSSL MPI): sign-magnitude,
little-endian, with the sign bit in the most-significant bit of the last byte.
"""

from __future__ import annotations

import hashlib

# ---- number codec (bignum.h getvch/setvch; sign-magnitude LE) ----------------

def bn_from_vch(vch: bytes) -> int:
    if not vch:
        return 0
    b = bytearray(vch)
    neg = b[-1] & 0x80
    b[-1] &= 0x7F
    val = int.from_bytes(bytes(b), "little")
    return -val if neg else val


def bn_to_vch(n: int) -> bytes:
    if n == 0:
        return b""
    neg = n < 0
    v = abs(n)
    b = bytearray(v.to_bytes((v.bit_length() + 7) // 8, "little"))
    if b[-1] & 0x80:
        b.append(0x80 if neg else 0x00)
    elif neg:
        b[-1] |= 0x80
    return bytes(b)


def cast_to_bool(vch: bytes) -> bool:            # CastToBool: CBigNum(vch) != 0
    return bn_from_vch(vch) != 0


def _getint(vch: bytes) -> int:                  # CBigNum::getint (clamped)
    n = bn_from_vch(vch)
    if n > 0x7FFFFFFF:
        return 0x7FFFFFFF
    if n < -0x80000000:
        return -0x80000000
    return n


def _sgn(n: int) -> int:
    return -1 if n < 0 else (1 if n > 0 else 0)


VCH_TRUE = b"\x01"
VCH_FALSE = b""


def num(n: int) -> bytes:                        # test helper: push an integer
    return bn_to_vch(n)


# ---- opcodes that push a number ----------------------------------------------

_PUSH_NUM = {"OP_0": 0, "OP_FALSE": 0, "OP_1NEGATE": -1, "OP_1": 1, "OP_TRUE": 1,
             **{f"OP_{i}": i for i in range(2, 17)}}

_UNARY_NUM = {"OP_1ADD", "OP_1SUB", "OP_2MUL", "OP_2DIV", "OP_NEGATE", "OP_ABS",
              "OP_NOT", "OP_0NOTEQUAL"}
_BINARY_NUM = {"OP_ADD", "OP_SUB", "OP_MUL", "OP_DIV", "OP_MOD", "OP_LSHIFT",
               "OP_RSHIFT", "OP_BOOLAND", "OP_BOOLOR", "OP_NUMEQUAL",
               "OP_NUMEQUALVERIFY", "OP_NUMNOTEQUAL", "OP_LESSTHAN", "OP_GREATERTHAN",
               "OP_LESSTHANOREQUAL", "OP_GREATERTHANOREQUAL", "OP_MIN", "OP_MAX"}
_HASH = {"OP_RIPEMD160", "OP_SHA1", "OP_SHA256", "OP_HASH160", "OP_HASH256"}


class ScriptError(Exception):
    pass


def _hash(name: str, data: bytes) -> bytes:
    if name == "OP_SHA1":
        return hashlib.sha1(data).digest()
    if name == "OP_SHA256":
        return hashlib.sha256(data).digest()
    if name == "OP_HASH256":
        return hashlib.sha256(hashlib.sha256(data).digest()).digest()
    if name == "OP_RIPEMD160":
        return hashlib.new("ripemd160", data).digest()
    if name == "OP_HASH160":
        return hashlib.new("ripemd160", hashlib.sha256(data).digest()).digest()
    raise ScriptError(name)


def run(script: list) -> tuple[bool, list]:
    """Execute a token list. Tokens: bytes (push) or an OP_ name string.

    Returns (ok, stack). ok is False on any failure (mirrors EvalScript returning
    false); the caller decides validity via cast_to_bool(stack[-1]).
    """
    stack: list[bytes] = []
    try:
        for op in script:
            if isinstance(op, (bytes, bytearray)):
                stack.append(bytes(op))
                continue
            if op in _PUSH_NUM:
                stack.append(bn_to_vch(_PUSH_NUM[op]))
            elif op == "OP_DUP":
                stack.append(stack[-1])
            elif op == "OP_DROP":
                stack.pop()
            elif op == "OP_SWAP":
                stack[-2], stack[-1] = stack[-1], stack[-2]
            elif op == "OP_OVER":
                stack.append(stack[-2])
            elif op == "OP_VERIFY":
                if not cast_to_bool(stack.pop()):
                    return False, stack
            # ---- splice ----
            elif op == "OP_CAT":
                b = stack.pop(); a = stack.pop(); stack.append(a + b)
            elif op == "OP_SUBSTR":
                size = _getint(stack.pop()); begin = _getint(stack.pop()); vch = stack.pop()
                end = begin + size
                if begin < 0 or end < begin:
                    return False, stack
                begin = min(begin, len(vch)); end = min(end, len(vch))
                stack.append(vch[begin:end])
            elif op in ("OP_LEFT", "OP_RIGHT"):
                size = _getint(stack.pop()); vch = stack.pop()
                if size < 0:
                    return False, stack
                size = min(size, len(vch))
                stack.append(vch[:size] if op == "OP_LEFT" else vch[len(vch) - size:])
            elif op == "OP_SIZE":
                stack.append(bn_to_vch(len(stack[-1])))
            # ---- bitwise ----
            elif op == "OP_INVERT":
                stack.append(bytes((~x) & 0xFF for x in stack.pop()))
            elif op in ("OP_AND", "OP_OR", "OP_XOR"):
                b = bytearray(stack.pop()); a = bytearray(stack.pop())
                n = max(len(a), len(b)); a += b"\x00" * (n - len(a)); b += b"\x00" * (n - len(b))
                fn = {"OP_AND": lambda x, y: x & y, "OP_OR": lambda x, y: x | y,
                      "OP_XOR": lambda x, y: x ^ y}[op]
                stack.append(bytes(fn(a[i], b[i]) for i in range(n)))
            elif op in ("OP_EQUAL", "OP_EQUALVERIFY"):
                b = stack.pop(); a = stack.pop()
                eq = a == b
                stack.append(VCH_TRUE if eq else VCH_FALSE)
                if op == "OP_EQUALVERIFY":
                    if eq:
                        stack.pop()
                    else:
                        return False, stack
            # ---- numeric ----
            elif op in _UNARY_NUM:
                n = bn_from_vch(stack.pop())
                r = {"OP_1ADD": n + 1, "OP_1SUB": n - 1, "OP_2MUL": n * 2,
                     "OP_2DIV": _sgn(n) * (abs(n) >> 1), "OP_NEGATE": -n,
                     "OP_ABS": abs(n), "OP_NOT": int(n == 0),
                     "OP_0NOTEQUAL": int(n != 0)}[op]
                stack.append(bn_to_vch(r))
            elif op in _BINARY_NUM:
                b = bn_from_vch(stack.pop()); a = bn_from_vch(stack.pop())
                if op in ("OP_DIV", "OP_MOD") and b == 0:
                    return False, stack
                if op in ("OP_LSHIFT", "OP_RSHIFT") and b < 0:
                    return False, stack
                r = {
                    "OP_ADD": a + b, "OP_SUB": a - b, "OP_MUL": a * b,
                    "OP_DIV": _sgn(a) * _sgn(b) * (abs(a) // abs(b)) if b else 0,
                    "OP_MOD": _sgn(a) * (abs(a) % abs(b)) if b else 0,
                    "OP_LSHIFT": _sgn(a) * (abs(a) << b) if b >= 0 else 0,
                    "OP_RSHIFT": _sgn(a) * (abs(a) >> b) if b >= 0 else 0,
                    "OP_BOOLAND": int(a != 0 and b != 0), "OP_BOOLOR": int(a != 0 or b != 0),
                    "OP_NUMEQUAL": int(a == b), "OP_NUMEQUALVERIFY": int(a == b),
                    "OP_NUMNOTEQUAL": int(a != b), "OP_LESSTHAN": int(a < b),
                    "OP_GREATERTHAN": int(a > b), "OP_LESSTHANOREQUAL": int(a <= b),
                    "OP_GREATERTHANOREQUAL": int(a >= b), "OP_MIN": min(a, b), "OP_MAX": max(a, b),
                }[op]
                stack.append(bn_to_vch(r))
                if op == "OP_NUMEQUALVERIFY":
                    if cast_to_bool(stack[-1]):
                        stack.pop()
                    else:
                        return False, stack
            elif op == "OP_WITHIN":
                mx = bn_from_vch(stack.pop()); mn = bn_from_vch(stack.pop()); x = bn_from_vch(stack.pop())
                stack.append(VCH_TRUE if (mn <= x < mx) else VCH_FALSE)
            elif op in _HASH:
                stack.append(_hash(op, stack.pop()))
            else:
                raise ScriptError(f"unsupported opcode in MODEL: {op}")
    except (IndexError, ScriptError):
        return False, stack
    return True, stack


def valid(script: list) -> bool:
    """VerifyScript-style predicate: ran without error and top-of-stack is true."""
    ok, stack = run(script)
    return ok and len(stack) > 0 and cast_to_bool(stack[-1])
