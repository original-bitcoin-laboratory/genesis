"""MODEL of Bitcoin v0.1.0 EvalScript opcode semantics.

Evidence level: **MODEL** (a reimplementation / harness), NOT JAN09-EXECUTED.
This is a DERIVATIVE — it re-expresses, in Python, the opcode execution bodies of
`script.cpp` (EvalScript) and the CBigNum number codec of `bignum.h`. See README.

Number codec (from bignum.h setvch/getvch via OpenSSL MPI): sign-magnitude,
little-endian, with the sign bit in the most-significant bit of the last byte.

Coverage: push, control flow (fExec/vfExec), stack + alt-stack ops, splice,
bitwise, numeric, crypto hashes, OP_CODESEPARATOR, and OP_CHECKSIG(VERIFY) /
OP_CHECKMULTISIG(VERIFY) (see tx_sighash.py; needs a transaction context).
Out of scope: byte-level parser (scripts are token lists), OP_VER/VERIF/VERNOTIF.
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


def run(script: list, checker=None) -> tuple[bool, list]:
    """Execute a token list. Tokens: bytes (push) or an OP_ name string.

    Mirrors EvalScript: `ok` is False only on the structural `return false` paths
    (underflow, bad opcode, bad IF nesting, div-by-zero, ...). OP_VERIFY-false and
    OP_RETURN stop execution but are not structural errors; the caller decides
    validity via cast_to_bool(stack[-1]). `checker` provides signature checking
    for OP_CHECKSIG/OP_CHECKMULTISIG (see tx_sighash.SigChecker); without it those
    opcodes fail.
    """
    stack: list[bytes] = []
    altstack: list[bytes] = []
    vfexec: list[bool] = []
    codesep = 0          # token index just after the most recent OP_CODESEPARATOR
    try:
        for pc, op in enumerate(script):
            fexec = all(vfexec)
            is_push = isinstance(op, (bytes, bytearray)) or op in _PUSH_NUM
            is_ifelse = op in ("OP_IF", "OP_NOTIF", "OP_ELSE", "OP_ENDIF")
            if fexec and isinstance(op, (bytes, bytearray)):
                stack.append(bytes(op))
                continue
            if not (fexec or is_ifelse):
                continue
            if is_push and not isinstance(op, (bytes, bytearray)):
                stack.append(bn_to_vch(_PUSH_NUM[op]))
            # ---- control ----
            elif op == "OP_NOP":
                pass
            elif op in ("OP_IF", "OP_NOTIF"):
                v = False
                if fexec:
                    v = cast_to_bool(stack.pop())
                    if op == "OP_NOTIF":
                        v = not v
                vfexec.append(v)
            elif op == "OP_ELSE":
                if not vfexec:
                    return False, stack
                vfexec[-1] = not vfexec[-1]
            elif op == "OP_ENDIF":
                if not vfexec:
                    return False, stack
                vfexec.pop()
            elif op == "OP_VERIFY":
                if not cast_to_bool(stack[-1]):
                    return True, stack          # pc=pend: stop, leave false on top
                stack.pop()
            elif op == "OP_RETURN":
                return True, stack
            elif op == "OP_CODESEPARATOR":
                codesep = pc + 1
            # ---- stack / alt-stack ----
            elif op == "OP_TOALTSTACK":
                altstack.append(stack.pop())
            elif op == "OP_FROMALTSTACK":
                stack.append(altstack.pop())
            elif op == "OP_2DROP":
                stack.pop(); stack.pop()
            elif op == "OP_2DUP":
                stack += [stack[-2], stack[-1]]
            elif op == "OP_3DUP":
                stack += [stack[-3], stack[-2], stack[-1]]
            elif op == "OP_2OVER":
                stack += [stack[-4], stack[-3]]
            elif op == "OP_2ROT":
                a = stack[-6:]; del stack[-6:]; stack += a[2:] + a[:2]
            elif op == "OP_2SWAP":
                stack[-4:] = stack[-2:] + stack[-4:-2]
            elif op == "OP_IFDUP":
                if cast_to_bool(stack[-1]):
                    stack.append(stack[-1])
            elif op == "OP_DEPTH":
                stack.append(bn_to_vch(len(stack)))
            elif op == "OP_DROP":
                stack.pop()
            elif op == "OP_DUP":
                stack.append(stack[-1])
            elif op == "OP_NIP":
                del stack[-2]
            elif op == "OP_OVER":
                stack.append(stack[-2])
            elif op in ("OP_PICK", "OP_ROLL"):
                n = _getint(stack.pop())
                if n < 0 or n >= len(stack):
                    return False, stack
                v = stack[-n - 1]
                if op == "OP_ROLL":
                    del stack[-n - 1]
                stack.append(v)
            elif op == "OP_ROT":
                stack[-3:] = stack[-2:] + stack[-3:-2]
            elif op == "OP_SWAP":
                stack[-2], stack[-1] = stack[-1], stack[-2]
            elif op == "OP_TUCK":
                stack.insert(-2, stack[-1])
            # ---- splice ----
            elif op == "OP_CAT":
                b = stack.pop(); stack[-1] = stack[-1] + b
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
                        return True, stack
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
                        return True, stack
            elif op == "OP_WITHIN":
                mx = bn_from_vch(stack.pop()); mn = bn_from_vch(stack.pop()); x = bn_from_vch(stack.pop())
                stack.append(VCH_TRUE if (mn <= x < mx) else VCH_FALSE)
            elif op in _HASH:
                stack.append(_hash(op, stack.pop()))
            # ---- signatures ----
            elif op in ("OP_CHECKSIG", "OP_CHECKSIGVERIFY"):
                if checker is None:
                    return False, stack
                pub = stack.pop(); sig = stack.pop()
                ok = checker.check_sig(sig, pub, script[codesep:pc])
                stack.append(VCH_TRUE if ok else VCH_FALSE)
                if op == "OP_CHECKSIGVERIFY":
                    if ok:
                        stack.pop()
                    else:
                        return True, stack
            elif op in ("OP_CHECKMULTISIG", "OP_CHECKMULTISIGVERIFY"):
                if checker is None:
                    return False, stack
                ok = _checkmultisig(stack, checker, script[codesep:pc])
                if ok is None:
                    return False, stack
                stack.append(VCH_TRUE if ok else VCH_FALSE)
                if op == "OP_CHECKMULTISIGVERIFY":
                    if ok:
                        stack.pop()
                    else:
                        return True, stack
            else:
                raise ScriptError(f"unsupported opcode in MODEL: {op}")
    except (IndexError, ScriptError):
        return False, stack
    # NOTE: v0.1 EvalScript does not reject an unterminated OP_IF (vfexec non-empty)
    # here — that check was added to Bitcoin only later. Kept faithful on purpose.
    return True, stack


def _checkmultisig(stack, checker, subscript):
    # ([dummy] sig..sig <m> pub..pub <n> -- bool); faithfully replicates the v0.1
    # off-by-one that consumes one extra element below the sigs.
    i = 1
    if len(stack) < i:
        return None
    nkeys = _getint(stack[-i])
    if nkeys < 0:
        return None
    ikey = i + 1; i = ikey + nkeys
    if len(stack) < i:
        return None
    nsigs = _getint(stack[-i])
    if nsigs < 0 or nsigs > nkeys:
        return None
    isig = i + 1; i = isig + nsigs
    if len(stack) < i:
        return None
    keys = [stack[-(ikey + k)] for k in range(nkeys)]
    sigs = [stack[-(isig + s)] for s in range(nsigs)]
    success = True
    si = ki = 0
    remaining_sigs = nsigs
    while success and remaining_sigs > 0:
        if checker.check_sig(sigs[si], keys[ki], subscript):
            si += 1; remaining_sigs -= 1
        ki += 1
        if remaining_sigs > (nkeys - ki):
            success = False
    del stack[-i:]           # pops nsigs+nkeys+2 + 1 extra (the off-by-one)
    return success


def valid(script: list, checker=None) -> bool:
    """VerifyScript-style predicate: ran without structural error and top is true."""
    ok, stack = run(script, checker)
    return ok and len(stack) > 0 and cast_to_bool(stack[-1])
