"""The core executed contrast: v0.1 runs the broad vocabulary; BTC disables it.
BTC cells run against python-bitcoinlib (skipped if it isn't installed)."""

import pytest

from conformance import BTC_OPS, bs, btc_verdict, v01_verdict
from evalscript_model import num

BROAD = ["OP_CAT", "OP_SUBSTR", "OP_INVERT", "OP_AND", "OP_MUL", "OP_DIV",
         "OP_LSHIFT", "OP_2MUL"]


def test_v01_executes_the_broad_vocabulary():
    assert v01_verdict([b"\x11", b"\x22", "OP_CAT"]) == "execute"
    assert v01_verdict([num(6), num(7), "OP_MUL"]) == "execute"
    assert v01_verdict([num(1), num(8), "OP_LSHIFT"]) == "execute"
    assert v01_verdict([b"\xf0", b"\x3c", "OP_AND"]) == "execute"


@pytest.mark.skipif(bs is None, reason="python-bitcoinlib not installed")
@pytest.mark.parametrize("op", BROAD)
def test_btc_disables_each_broad_opcode(op):
    assert btc_verdict(BTC_OPS[op](), op) == "disabled"


@pytest.mark.skipif(bs is None, reason="python-bitcoinlib not installed")
@pytest.mark.parametrize("op,tokens", [
    ("OP_ADD", [num(2), num(2), "OP_ADD"]),
    ("OP_EQUAL", [b"\xaa", b"\xaa", "OP_EQUAL"]),
    ("OP_SHA256", [b"\xaa", "OP_SHA256"]),
])
def test_kept_opcodes_agree(op, tokens):
    assert v01_verdict(tokens) == "execute"          # v0.1 runs it
    assert btc_verdict(BTC_OPS[op](), op) == "execute"   # and BTC kept it
