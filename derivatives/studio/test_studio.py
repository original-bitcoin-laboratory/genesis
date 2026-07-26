"""The Transaction Studio's script tracer steps EvalScript faithfully and reports
the right verdict — over the full vocabulary. Evidence: MODEL."""

import hashlib
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "model"))
sys.path.insert(0, str(_HERE))

from studio import disasm, render, trace
from evalscript_model import num
from cscript import assemble


def test_op_cat_trace_shows_concatenation_and_validity():
    h1, h2 = b"\x11\x22", b"\x33\x44"
    lock = hashlib.sha256(h1 + h2).digest()
    rows, ok, is_valid = trace([h1, h2, "OP_CAT", "OP_SHA256", lock, "OP_EQUAL"])
    assert ok and is_valid
    # after OP_CAT the top of stack is the concatenation 11223344
    cat_row = next(st for op, st in rows if op == "OP_CAT")
    assert "11223344" in cat_row


def test_arithmetic_trace_final_value():
    rows, ok, is_valid = trace([num(6), num(7), "OP_MUL", num(2), "OP_ADD"])
    assert ok and is_valid
    assert rows[-1][1] == "[2c]"                     # 6*7+2 = 44 = 0x2c


def test_invalid_script_reports_not_true():
    rows, ok, is_valid = trace([b"\xaa", b"\xbb", "OP_EQUAL"])   # unequal -> false top
    assert ok and not is_valid


def test_structural_failure_is_flagged():
    rows, ok, is_valid = trace(["OP_ADD"])           # underflow -> structural error
    assert not ok and not is_valid


def test_render_and_disasm_roundtrip():
    tokens = [b"\x11", b"\x22", "OP_CAT"]
    text = render(tokens, title="demo")
    assert "OP_CAT" in text and "stack (after)" in text
    assert disasm(assemble(tokens)) == tokens        # bytes -> tokens matches
