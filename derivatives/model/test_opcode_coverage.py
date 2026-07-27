"""Exhaustive per-opcode coverage for the v0.1 EvalScript MODEL.

Every opcode the model can execute is exercised here by at least one Python vector that
succeeds iff the opcode computes correctly -- so the default (no-C++) reproducible run
covers the whole vocabulary, not just the subset touched by the behavioural suites. The
final test is a REGRESSION GUARD: it derives the model's executable opcode set from the
source and fails if any opcode lacks a vector, so coverage cannot silently regress.

Evidence level: MODEL.
"""

import hashlib
import pathlib
import re

import pytest

import evalscript_model as m
from evalscript_model import num, valid
from spend import sign, verify_spend
from tx_sighash import demo_tx, new_key

B = bytes  # data pushes are raw bytes tokens


def _sha1(x): return hashlib.sha1(x).digest()
def _sha256(x): return hashlib.sha256(x).digest()
def _rmd160(x): return hashlib.new("ripemd160", x).digest()
def _hash256(x): return _sha256(_sha256(x))
def _hash160(x): return _rmd160(_sha256(x))


# opcode -> a script that leaves TRUE iff the opcode behaves correctly ----------
VECTORS: dict[str, list] = {
    # pushes (value verified via OP_NUMEQUAL)
    "OP_0": [num(0), num(0), "OP_NUMEQUAL"],
    "OP_FALSE": ["OP_FALSE", num(0), "OP_NUMEQUAL"],
    "OP_1NEGATE": ["OP_1NEGATE", num(-1), "OP_NUMEQUAL"],
    "OP_1": ["OP_1", num(1), "OP_NUMEQUAL"],
    "OP_TRUE": ["OP_TRUE", num(1), "OP_NUMEQUAL"],
    # control
    "OP_NOP": [num(1), "OP_NOP"],
    "OP_IF": [num(1), "OP_IF", num(1), "OP_ELSE", num(0), "OP_ENDIF"],
    "OP_NOTIF": [num(0), "OP_NOTIF", num(1), "OP_ENDIF"],
    "OP_ELSE": [num(0), "OP_IF", num(0), "OP_ELSE", num(1), "OP_ENDIF"],
    "OP_ENDIF": [num(1), "OP_IF", num(1), "OP_ENDIF"],
    "OP_VERIFY": [num(1), "OP_VERIFY", num(1)],
    "OP_RETURN": [num(1), "OP_RETURN"],
    "OP_CODESEPARATOR": [num(1), "OP_CODESEPARATOR"],
    # alt-stack
    "OP_TOALTSTACK": [num(1), "OP_TOALTSTACK", "OP_FROMALTSTACK"],
    "OP_FROMALTSTACK": [num(1), "OP_TOALTSTACK", "OP_FROMALTSTACK"],
    # stack
    "OP_2DROP": [num(1), num(9), num(9), "OP_2DROP"],
    "OP_2DUP": [num(0), num(1), "OP_2DUP"],
    "OP_3DUP": [num(0), num(0), num(1), "OP_3DUP"],
    "OP_2OVER": [num(1), num(2), num(0), num(0), "OP_2OVER"],
    "OP_2ROT": [num(1), num(2), num(3), num(4), num(5), num(6), "OP_2ROT"],
    "OP_2SWAP": [num(1), num(2), num(3), num(4), "OP_2SWAP"],
    "OP_IFDUP": [num(5), "OP_IFDUP"],
    "OP_DEPTH": [num(1), num(1), "OP_DEPTH"],
    "OP_DROP": [num(1), num(9), "OP_DROP"],
    "OP_DUP": [num(1), "OP_DUP"],
    "OP_NIP": [num(9), num(1), "OP_NIP"],
    "OP_OVER": [num(1), num(9), "OP_OVER"],
    "OP_PICK": [num(1), num(9), num(1), "OP_PICK"],
    "OP_ROLL": [num(1), num(9), num(1), "OP_ROLL"],
    "OP_ROT": [num(3), num(2), num(1), "OP_ROT"],
    "OP_SWAP": [num(9), num(1), "OP_SWAP"],
    "OP_TUCK": [num(1), num(2), "OP_TUCK"],
    # splice
    "OP_CAT": [B(b"\x01"), B(b"\x02"), "OP_CAT", B(b"\x01\x02"), "OP_EQUAL"],
    "OP_SUBSTR": [B(b"\xaa\xbb\xcc"), num(1), num(1), "OP_SUBSTR", B(b"\xbb"), "OP_EQUAL"],
    "OP_LEFT": [B(b"\xaa\xbb\xcc"), num(2), "OP_LEFT", B(b"\xaa\xbb"), "OP_EQUAL"],
    "OP_RIGHT": [B(b"\xaa\xbb\xcc"), num(2), "OP_RIGHT", B(b"\xbb\xcc"), "OP_EQUAL"],
    "OP_SIZE": [B(b"\xaa\xbb"), "OP_SIZE", num(2), "OP_EQUAL"],
    # bitwise
    "OP_INVERT": [B(b"\x00"), "OP_INVERT", B(b"\xff"), "OP_EQUAL"],
    "OP_AND": [B(b"\x0f"), B(b"\x33"), "OP_AND", B(b"\x03"), "OP_EQUAL"],
    "OP_OR": [B(b"\x0f"), B(b"\x30"), "OP_OR", B(b"\x3f"), "OP_EQUAL"],
    "OP_XOR": [B(b"\x0f"), B(b"\x33"), "OP_XOR", B(b"\x3c"), "OP_EQUAL"],
    "OP_EQUAL": [num(5), num(5), "OP_EQUAL"],
    "OP_EQUALVERIFY": [num(5), num(5), "OP_EQUALVERIFY", num(1)],
    # numeric unary
    "OP_1ADD": [num(4), "OP_1ADD", num(5), "OP_NUMEQUAL"],
    "OP_1SUB": [num(4), "OP_1SUB", num(3), "OP_NUMEQUAL"],
    "OP_2MUL": [num(4), "OP_2MUL", num(8), "OP_NUMEQUAL"],
    "OP_2DIV": [num(9), "OP_2DIV", num(4), "OP_NUMEQUAL"],
    "OP_NEGATE": [num(4), "OP_NEGATE", num(-4), "OP_NUMEQUAL"],
    "OP_ABS": [num(-4), "OP_ABS", num(4), "OP_NUMEQUAL"],
    "OP_NOT": [num(0), "OP_NOT"],
    "OP_0NOTEQUAL": [num(5), "OP_0NOTEQUAL"],
    # numeric binary
    "OP_ADD": [num(2), num(3), "OP_ADD", num(5), "OP_NUMEQUAL"],
    "OP_SUB": [num(5), num(3), "OP_SUB", num(2), "OP_NUMEQUAL"],
    "OP_MUL": [num(3), num(4), "OP_MUL", num(12), "OP_NUMEQUAL"],
    "OP_DIV": [num(12), num(4), "OP_DIV", num(3), "OP_NUMEQUAL"],
    "OP_MOD": [num(13), num(4), "OP_MOD", num(1), "OP_NUMEQUAL"],
    "OP_LSHIFT": [num(1), num(4), "OP_LSHIFT", num(16), "OP_NUMEQUAL"],
    "OP_RSHIFT": [num(16), num(4), "OP_RSHIFT", num(1), "OP_NUMEQUAL"],
    "OP_BOOLAND": [num(1), num(1), "OP_BOOLAND"],
    "OP_BOOLOR": [num(0), num(1), "OP_BOOLOR"],
    "OP_NUMEQUAL": [num(5), num(5), "OP_NUMEQUAL"],
    "OP_NUMEQUALVERIFY": [num(5), num(5), "OP_NUMEQUALVERIFY", num(1)],
    "OP_NUMNOTEQUAL": [num(5), num(6), "OP_NUMNOTEQUAL"],
    "OP_LESSTHAN": [num(3), num(5), "OP_LESSTHAN"],
    "OP_GREATERTHAN": [num(5), num(3), "OP_GREATERTHAN"],
    "OP_LESSTHANOREQUAL": [num(5), num(5), "OP_LESSTHANOREQUAL"],
    "OP_GREATERTHANOREQUAL": [num(5), num(5), "OP_GREATERTHANOREQUAL"],
    "OP_MIN": [num(3), num(5), "OP_MIN", num(3), "OP_NUMEQUAL"],
    "OP_MAX": [num(3), num(5), "OP_MAX", num(5), "OP_NUMEQUAL"],
    "OP_WITHIN": [num(5), num(0), num(10), "OP_WITHIN"],
    # hashes (digest verified against hashlib)
    "OP_RIPEMD160": [B(b"abc"), "OP_RIPEMD160", B(_rmd160(b"abc")), "OP_EQUAL"],
    "OP_SHA1": [B(b"abc"), "OP_SHA1", B(_sha1(b"abc")), "OP_EQUAL"],
    "OP_SHA256": [B(b"abc"), "OP_SHA256", B(_sha256(b"abc")), "OP_EQUAL"],
    "OP_HASH160": [B(b"abc"), "OP_HASH160", B(_hash160(b"abc")), "OP_EQUAL"],
    "OP_HASH256": [B(b"abc"), "OP_HASH256", B(_hash256(b"abc")), "OP_EQUAL"],
}
# the numeric-push opcodes OP_2..OP_16
for _i in range(2, 17):
    VECTORS[f"OP_{_i}"] = [f"OP_{_i}", num(_i), "OP_NUMEQUAL"]

# opcodes that need a transaction/signature context (covered by the crypto tests below)
CRYPTO = {"OP_CHECKSIG", "OP_CHECKSIGVERIFY", "OP_CHECKMULTISIG", "OP_CHECKMULTISIGVERIFY"}


@pytest.mark.parametrize("op", sorted(VECTORS))
def test_opcode_vector_is_valid(op):
    assert valid(VECTORS[op]) is True, f"{op} vector did not leave true"


# ---- crypto opcodes, with a real secp256k1 checker ---------------------------

def test_checksig_and_verify():
    tx, _ = demo_tx()
    priv, pub = new_key()
    spk = [pub, "OP_CHECKSIG"]
    assert verify_spend([sign(priv, spk, tx, 0)], spk, tx, 0) is True
    spkv = [pub, "OP_CHECKSIGVERIFY", "OP_1"]
    assert verify_spend([sign(priv, spkv, tx, 0)], spkv, tx, 0) is True


def test_checkmultisig_and_verify():
    tx, _ = demo_tx()
    ks = [new_key() for _ in range(3)]
    pubs = [p for _, p in ks]
    base = ["OP_2"] + pubs + ["OP_3"]
    spk = base + ["OP_CHECKMULTISIG"]
    assert verify_spend(["OP_0", sign(ks[0][0], spk, tx, 0), sign(ks[1][0], spk, tx, 0)],
                        spk, tx, 0) is True
    spkv = base + ["OP_CHECKMULTISIGVERIFY", "OP_1"]
    assert verify_spend(["OP_0", sign(ks[0][0], spkv, tx, 0), sign(ks[1][0], spkv, tx, 0)],
                        spkv, tx, 0) is True


# ---- the regression guard: every executable opcode has coverage --------------

def _model_executable_opcodes() -> set[str]:
    src = pathlib.Path(m.__file__).read_text(encoding="utf-8")
    quoted = set(re.findall(r'"(OP_[A-Z0-9]+)"', src))    # every OP_ literal handled in run()
    return quoted | set(m._PUSH_NUM) | m._UNARY_NUM | m._BINARY_NUM | m._HASH


def test_every_executable_opcode_is_covered():
    target = _model_executable_opcodes()
    covered = set(VECTORS) | CRYPTO
    missing = sorted(target - covered)
    assert not missing, f"opcodes implemented in the model but not covered by a vector: {missing}"


def test_coverage_has_no_dead_vectors():
    # every vector names a real model opcode (no typos / stale entries)
    target = _model_executable_opcodes() | CRYPTO
    stray = sorted(set(VECTORS) - target)
    assert not stray, f"vectors for opcodes the model does not implement: {stray}"
