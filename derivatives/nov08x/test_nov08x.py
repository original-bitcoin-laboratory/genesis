"""NOV08-X (NOV08-Minimal) — the counterfactual runs, and it diverges from JAN09
exactly where the surviving November source says it should. Evidence: MODEL."""

import pathlib
import sys

import pytest

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "model"))
sys.path.insert(0, str(_HERE.parent / "p2p"))

from consensus import Rules
from node import Nov08xNode
from evalscript_model import num, run          # the lab's Script engine (full vocabulary)

NOV = Rules.load("nov08")
JAN = Rules.load("jan09")


# ---- A3/A4 subsidy schedule ---------------------------------------------------

def test_nov08_subsidy_is_100_coins_halving_every_100k():
    assert NOV.get_block_value(0) == 100 * NOV.COIN
    assert NOV.get_block_value(99_999) == 100 * NOV.COIN
    assert NOV.get_block_value(100_000) == 50 * NOV.COIN      # one halving
    assert NOV.get_block_value(200_000) == 25 * NOV.COIN      # two
    # faithful to the explicit loop (main.cpp:655), on the global best height
    assert NOV.get_block_value(400_000) == 100 * NOV.COIN // 16


def test_jan09_subsidy_diverges():
    assert JAN.get_block_value(0) == 50 * JAN.COIN
    assert JAN.get_block_value(210_000) == 25 * JAN.COIN
    # same height, different reward — the fork is real
    assert NOV.get_block_value(0) // NOV.COIN == 100
    assert JAN.get_block_value(0) // JAN.COIN == 50


# ---- A1/A2 denomination + A7 fee ---------------------------------------------

def test_denomination_and_fixed_fee():
    assert NOV.COIN == 1_000_000 and NOV.CENT == 10_000       # no 'satoshi' in November
    assert NOV.fee_fixed == 10_000                            # fixed 1*CENT (0.01 coin)
    assert JAN.COIN == 100_000_000                            # the satoshi is genesis-born


# ---- proof-of-work encoding (leading-zero bits) ------------------------------

def test_nov08_pow_is_leading_zero_bits():
    # target = (~0) >> nBits; MINPROOFOFWORK gates validity
    assert NOV.pow_target(20) == (1 << (256 - 20)) - 1
    assert NOV.min_pow == 20
    # a hash with >=20 leading zero bits passes; fewer fails
    good = (1 << (256 - 24)).to_bytes(32, "little")           # 24 leading zero bits
    bad = (1 << (256 - 8)).to_bytes(32, "little")             # only 8
    assert NOV.pow_ok(good, 20)
    assert not NOV.pow_ok(bad, 20)
    # below MINPROOFOFWORK is rejected outright
    assert not NOV.pow_ok(b"\x00" * 32, 19)


def test_jan09_pow_is_compact_not_leading_zero_bits():
    assert JAN.pow_encoding == "compact"
    assert JAN.pow_target(0x1d00ffff) == 0x00ffff * (1 << (8 * (0x1d - 3)))


# ---- retarget (±1-bit nudge vs proportional) ---------------------------------

def test_nov08_retarget_nudges_one_bit():
    slow, _ = NOV.next_work(24, NOV.timespan * 3)             # 3x too slow -> easier
    fast, _ = NOV.next_work(24, NOV.timespan // 3)            # 3x too fast -> harder
    band, _ = NOV.next_work(24, NOV.timespan)                # on target -> unchanged
    assert (slow, fast, band) == (23, 25, 24)
    assert NOV.retarget_algo == "nudge" and JAN.retarget_algo == "proportional"


# ---- A8 coinbase value rule --------------------------------------------------

def test_coinbase_rule_equal_vs_le():
    bv = NOV.get_block_value(0)
    assert NOV.coinbase_ok(bv, bv)                 # exact pays: ok both
    assert not NOV.coinbase_ok(bv - 1, bv)         # underpay: NOV08 REJECTS (exact equality)
    assert JAN.coinbase_ok(JAN.get_block_value(0) - 1, JAN.get_block_value(0))  # JAN09 ACCEPTS (<=)


# ---- the node actually runs (mines under NOV08 rules) ------------------------

def test_node_mines_a_nov08_chain():
    node = Nov08xNode(NOV)
    b0 = node.mine_and_add()
    b1 = node.mine_and_add(tag=1)
    assert node.best_height == 1
    for b in (b0, b1):
        assert b["value"] == 100 * NOV.COIN                  # 100-coin reward
        assert NOV.pow_ok(b["hash"], 20)                     # 20 leading-zero-bit PoW
        assert int.from_bytes(b["hash"], "little") <= NOV.pow_target(20)


def test_node_rejects_underpaid_coinbase():
    node = Nov08xNode(NOV)
    with pytest.raises(ValueError):                          # exact-equality rule enforced on connect
        node.mine_and_add(claim=100 * NOV.COIN - 1)


# ---- "nothing disabled": full original vocabulary lives in NOV08-X -----------

@pytest.mark.parametrize("tokens", [
    [b"\x11", b"\x22", "OP_CAT"],
    [num(6), num(7), "OP_MUL"],
    [b"\xf0", b"\x3c", "OP_AND"],
    [num(1), num(8), "OP_LSHIFT"],
    [b"\x0f", "OP_INVERT"],
])
def test_full_vocabulary_executes(tokens):
    ok, _ = run(tokens)                    # NOV08-X's reconstructed engine disables nothing
    assert ok
