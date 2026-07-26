"""Vectors for the EvalScript MODEL. Evidence level: MODEL (not JAN09-EXECUTED).

Focus: the "broad vocabulary" opcodes that later Bitcoin (BTC) disabled but which
are *implemented and executable* in v0.1 EvalScript (script.cpp), plus the
sign-magnitude number codec (bignum.h).
"""

import hashlib

import pytest

from evalscript_model import bn_from_vch, bn_to_vch, cast_to_bool, num, run, valid

try:
    hashlib.new("ripemd160")
    HAVE_RIPEMD160 = True
except Exception:
    HAVE_RIPEMD160 = False


# ---- number codec (bignum.h) -------------------------------------------------

@pytest.mark.parametrize("n,vch", [
    (0, b""), (1, b"\x01"), (-1, b"\x81"), (127, b"\x7f"),
    (128, b"\x80\x00"), (255, b"\xff\x00"), (256, b"\x00\x01"), (-128, b"\x80\x80"),
])
def test_number_encoding(n, vch):
    assert bn_to_vch(n) == vch
    assert bn_from_vch(vch) == n


def test_negative_zero_is_false():
    assert bn_from_vch(b"\x80") == 0
    assert cast_to_bool(b"\x80") is False
    assert cast_to_bool(b"\x01") is True


def _top(script):
    ok, stack = run(script)
    assert ok, f"script failed: {script}"
    return stack[-1]


# ---- splice ops (disabled in BTC) --------------------------------------------

def test_op_cat():
    assert _top([b"\xde\xad", b"\xbe\xef", "OP_CAT"]) == b"\xde\xad\xbe\xef"

def test_op_substr():
    assert _top([b"abcdef", num(1), num(3), "OP_SUBSTR"]) == b"bcd"

def test_op_left_right():
    assert _top([b"abcdef", num(2), "OP_LEFT"]) == b"ab"
    assert _top([b"abcdef", num(2), "OP_RIGHT"]) == b"ef"

def test_op_size_keeps_input():
    ok, stack = run([b"abc", "OP_SIZE"])
    assert ok and stack[-1] == num(3) and stack[-2] == b"abc"


# ---- bitwise ops (disabled in BTC) -------------------------------------------

def test_op_invert():
    assert _top([b"\x0f", "OP_INVERT"]) == b"\xf0"

def test_op_and_or_xor():
    assert _top([b"\xf0", b"\x3c", "OP_AND"]) == b"\x30"
    assert _top([b"\xf0", b"\x3c", "OP_OR"]) == b"\xfc"
    assert _top([b"\xf0", b"\x3c", "OP_XOR"]) == b"\xcc"


# ---- arithmetic (mul/div/mod/shift disabled in BTC) --------------------------

def test_op_mul_div_mod():
    assert _top([num(6), num(7), "OP_MUL"]) == num(42)
    assert _top([num(20), num(6), "OP_DIV"]) == num(3)
    assert _top([num(20), num(6), "OP_MOD"]) == num(2)

def test_signed_div_mod_truncate_toward_zero():
    assert _top([num(-20), num(6), "OP_DIV"]) == num(-3)   # trunc, not floor
    assert _top([num(-20), num(6), "OP_MOD"]) == num(-2)   # remainder sign = dividend

def test_shifts_are_magnitude_preserving():
    assert _top([num(1), num(8), "OP_LSHIFT"]) == num(256)
    assert _top([num(256), num(4), "OP_RSHIFT"]) == num(16)
    assert _top([num(21), "OP_2MUL"]) == num(42)
    assert _top([num(-3), "OP_2DIV"]) == num(-1)           # -(3>>1), not floor(-1.5)

def test_div_by_zero_fails():
    ok, _ = run([num(5), num(0), "OP_DIV"])
    assert ok is False


# ---- comparisons / within ----------------------------------------------------

def test_numeric_compare_and_within():
    assert _top([num(3), num(5), "OP_LESSTHAN"]) == b"\x01"
    assert _top([num(5), num(1), num(10), "OP_WITHIN"]) == b"\x01"
    assert _top([num(10), num(1), num(10), "OP_WITHIN"]) == b""   # max is exclusive


# ---- realistic predicates ----------------------------------------------------

def test_multiply_and_equal_predicate():
    assert valid([num(6), num(7), "OP_MUL", num(42), "OP_EQUAL"]) is True
    assert valid([num(6), num(7), "OP_MUL", num(43), "OP_EQUAL"]) is False

def test_hash_lock_predicate():
    secret = b"correct horse battery staple"
    h = hashlib.sha256(secret).digest()
    assert valid([secret, "OP_SHA256", h, "OP_EQUAL"]) is True
    assert valid([b"wrong", "OP_SHA256", h, "OP_EQUAL"]) is False

def test_equalverify_consumes_and_continues():
    assert valid([num(1), num(1), "OP_EQUALVERIFY", "OP_1"]) is True
    assert valid([num(1), num(2), "OP_EQUALVERIFY", "OP_1"]) is False

@pytest.mark.skipif(not HAVE_RIPEMD160, reason="ripemd160 unavailable in this hashlib")
def test_hash160_predicate():
    data = b"\x02" + b"\x11" * 32
    h160 = hashlib.new("ripemd160", hashlib.sha256(data).digest()).digest()
    assert valid([data, "OP_HASH160", h160, "OP_EQUAL"]) is True
