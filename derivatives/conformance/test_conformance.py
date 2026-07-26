"""Neutral conformance checks. v0.1 is the executed baseline; every descendant is
treated identically via a documented profile. Two chains have an independent
implementation installed and are CROSS-CHECKED by execution — applied equally,
not to rank them: BTC (python-bitcoinlib) and BSV (bitcoinx)."""

import pytest

from conformance import (BSV_LIB, BTC_LIB, DESCENDANTS, bsv_execute, btc_execute,
                         profile, v01_baseline)
from evalscript_model import num

BROAD = ["OP_CAT", "OP_SUBSTR", "OP_LEFT", "OP_RIGHT", "OP_INVERT", "OP_AND", "OP_OR",
         "OP_XOR", "OP_MUL", "OP_DIV", "OP_MOD", "OP_LSHIFT", "OP_RSHIFT", "OP_2MUL", "OP_2DIV"]
KEPT = ["OP_ADD", "OP_EQUAL", "OP_SHA256"]

# profile status -> the verdict an independent execution should produce
_EXPECT = {"preserved": "execute", "restored": "execute",
           "disabled": "disabled", "→OP_SPLIT": "→OP_SPLIT"}


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


# ---- BTC cross-check (python-bitcoinlib) --------------------------------------

@pytest.mark.skipif(BTC_LIB is None, reason="python-bitcoinlib not installed")
@pytest.mark.parametrize("op", BROAD)
def test_btc_profile_matches_independent_execution(op):
    assert profile("BTC", op) == "disabled"
    assert btc_execute(op) == "disabled"


# ---- BSV cross-check (bitcoinx) ----------------------------------------------

@pytest.mark.skipif(BSV_LIB is None, reason="bitcoinx not installed")
@pytest.mark.parametrize("op", BROAD)
def test_bsv_profile_matches_independent_execution(op):
    # the documented BSV profile must match what an independent BSV impl actually does
    assert bsv_execute(op) == _EXPECT[profile("BSV", op)]


@pytest.mark.skipif(BSV_LIB is None, reason="bitcoinx not installed")
def test_bsv_keeps_2mul_2div_disabled():
    # the correction the cross-check caught: Genesis restored the set EXCEPT these two
    for op in ("OP_2MUL", "OP_2DIV"):
        assert profile("BSV", op) == "disabled"
        assert bsv_execute(op) == "disabled"


@pytest.mark.skipif(BSV_LIB is None, reason="bitcoinx not installed")
def test_bsv_restores_the_rest_of_the_broad_vocabulary():
    for op in ("OP_CAT", "OP_INVERT", "OP_AND", "OP_OR", "OP_XOR",
               "OP_MUL", "OP_DIV", "OP_MOD", "OP_LSHIFT", "OP_RSHIFT"):
        assert profile("BSV", op) == "restored"
        assert bsv_execute(op) == "execute"


# ---- kept opcodes preserved everywhere (both cross-checks) --------------------

@pytest.mark.parametrize("op", KEPT)
def test_kept_opcodes_preserved_everywhere(op):
    for c in DESCENDANTS:
        assert profile(c, op) == "preserved"
    if BTC_LIB is not None:
        assert btc_execute(op) == "execute"
    if BSV_LIB is not None:
        assert bsv_execute(op) == "execute"
