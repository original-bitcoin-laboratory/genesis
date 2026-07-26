"""Neutral conformance checks over SIX descendants — v0.1 is the executed baseline;
every column is cross-checked by execution, applied equally, none privileged:
BTC/LTC/DOGE via python-bitcoinlib (they share Bitcoin Core's engine), BSV via
bitcoinx, and BCH/XEC execution-bounded (restored ops confirmed by bitcoinx, disabled
ops by python-bitcoinlib — no standalone BCH interpreter exists)."""

import pytest

from conformance import (BSV_LIB, BTC_LIB, DESCENDANTS, _CORE_LINEAGE, _cell_ref,
                         _method, bsv_execute, btc_execute, profile, v01_baseline)
from evalscript_model import num

BROAD = ["OP_CAT", "OP_SUBSTR", "OP_LEFT", "OP_RIGHT", "OP_INVERT", "OP_AND", "OP_OR",
         "OP_XOR", "OP_MUL", "OP_DIV", "OP_MOD", "OP_LSHIFT", "OP_RSHIFT", "OP_2MUL", "OP_2DIV"]
KEPT = ["OP_ADD", "OP_EQUAL", "OP_SHA256"]
_EXPECT = {"preserved": "execute", "restored": "execute",
           "disabled": "disabled", "→OP_SPLIT": "→OP_SPLIT"}


def test_baseline_and_six_descendants():
    assert DESCENDANTS == ["BTC", "LTC", "DOGE", "BCH", "XEC", "BSV"]
    assert v01_baseline([b"\x11", b"\x22", "OP_CAT"]) == "execute"
    assert v01_baseline([num(6), num(7), "OP_MUL"]) == "execute"


def test_every_descendant_has_a_defined_status_uniformly():
    for c in DESCENDANTS:
        for op in BROAD + KEPT:
            assert profile(c, op) in ("preserved", "disabled", "restored", "→OP_SPLIT")


# ---- completeness: every cell of every chain is confirmed by an independent execution ----

@pytest.mark.skipif(BTC_LIB is None or BSV_LIB is None, reason="need python-bitcoinlib + bitcoinx")
@pytest.mark.parametrize("chain", ["BTC", "LTC", "DOGE", "BCH", "XEC", "BSV"])
def test_every_cell_is_execution_confirmed(chain):
    for op in BROAD + KEPT:
        be, se = btc_execute(op), bsv_execute(op)
        assert _cell_ref(chain, profile(chain, op), be, se), f"{chain}:{op} not confirmed"


# ---- Bitcoin Core lineage: BTC == LTC == DOGE, all disabled, via python-bitcoinlib ----

@pytest.mark.parametrize("op", BROAD)
def test_bitcoin_core_lineage_identical_and_disabled(op):
    assert profile("BTC", op) == profile("LTC", op) == profile("DOGE", op) == "disabled"


@pytest.mark.skipif(BTC_LIB is None, reason="python-bitcoinlib not installed")
@pytest.mark.parametrize("op", BROAD)
def test_core_lineage_confirmed_disabled_by_execution(op):
    assert btc_execute(op) == "disabled"                 # the shared Bitcoin Core rule set
    for c in _CORE_LINEAGE:
        assert _method(c)[0] == "executed"


# ---- Cash lineage: BCH == XEC, execution-bounded ----

def test_cash_lineage_identical():
    for op in BROAD:
        assert profile("BCH", op) == profile("XEC", op)
    assert _method("BCH")[0] == _method("XEC")[0] == "execution-bounded"


@pytest.mark.skipif(BTC_LIB is None or BSV_LIB is None, reason="need both references")
@pytest.mark.parametrize("op", BROAD)
def test_bch_cells_bounded_by_two_executions(op):
    st = profile("BCH", op)
    if st == "restored":
        assert bsv_execute(op) == "execute"              # restored -> confirmed executable
    elif st == "disabled":
        assert btc_execute(op) == "disabled"             # disabled -> confirmed disabled
    elif st == "→OP_SPLIT":
        assert bsv_execute(op) == "→OP_SPLIT"


# ---- BSV cross-check (bitcoinx), incl. the OP_2MUL/2DIV correction ----

@pytest.mark.skipif(BSV_LIB is None, reason="bitcoinx not installed")
@pytest.mark.parametrize("op", BROAD)
def test_bsv_profile_matches_independent_execution(op):
    assert bsv_execute(op) == _EXPECT[profile("BSV", op)]


@pytest.mark.skipif(BSV_LIB is None, reason="bitcoinx not installed")
def test_bsv_keeps_2mul_2div_disabled():
    for op in ("OP_2MUL", "OP_2DIV"):
        assert profile("BSV", op) == "disabled" and bsv_execute(op) == "disabled"


# ---- kept opcodes preserved on every chain ----

@pytest.mark.parametrize("op", KEPT)
def test_kept_opcodes_preserved_everywhere(op):
    for c in DESCENDANTS:
        assert profile(c, op) == "preserved"
    if BTC_LIB is not None:
        assert btc_execute(op) == "execute"
    if BSV_LIB is not None:
        assert bsv_execute(op) == "execute"
