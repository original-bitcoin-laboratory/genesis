"""Neutral conformance checks. v0.1 is the executed baseline; every descendant is
treated identically via a documented profile. The one independently-installable
implementation (BTC / python-bitcoinlib) is used only to CROSS-CHECK its own
profile — not to rank it above BCH / BSV / XEC."""

import pytest

from conformance import BTC_LIB, DESCENDANTS, btc_execute, profile, v01_baseline
from evalscript_model import num

BROAD = ["OP_CAT", "OP_SUBSTR", "OP_LEFT", "OP_RIGHT", "OP_INVERT", "OP_AND", "OP_OR",
         "OP_XOR", "OP_MUL", "OP_DIV", "OP_MOD", "OP_LSHIFT", "OP_RSHIFT", "OP_2MUL", "OP_2DIV"]
KEPT = ["OP_ADD", "OP_EQUAL", "OP_SHA256"]


def test_v01_baseline_executes_the_broad_vocabulary():
    assert v01_baseline([b"\x11", b"\x22", "OP_CAT"]) == "execute"
    assert v01_baseline([num(6), num(7), "OP_MUL"]) == "execute"
    assert v01_baseline([num(1), num(8), "OP_LSHIFT"]) == "execute"
    assert v01_baseline([b"\xf0", b"\x3c", "OP_AND"]) == "execute"


def test_every_descendant_has_a_defined_status_uniformly():
    # no chain is special: each has a defined profile status for every opcode
    for c in DESCENDANTS:
        for op in BROAD + KEPT:
            assert profile(c, op) in ("preserved", "disabled", "restored", "→OP_SPLIT")


@pytest.mark.skipif(BTC_LIB is None, reason="python-bitcoinlib not installed")
@pytest.mark.parametrize("op", BROAD)
def test_btc_profile_matches_independent_execution(op):
    # cross-check ONLY: our documented BTC profile == an independent BTC impl's verdict
    assert profile("BTC", op) == "disabled"
    assert btc_execute(op) == "disabled"


@pytest.mark.skipif(BTC_LIB is None, reason="python-bitcoinlib not installed")
@pytest.mark.parametrize("op", KEPT)
def test_kept_opcodes_preserved_everywhere(op):
    assert btc_execute(op) == "execute"
    for c in DESCENDANTS:
        assert profile(c, op) == "preserved"
