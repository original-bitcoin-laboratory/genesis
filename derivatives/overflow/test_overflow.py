"""The value-overflow surface, executed: v0.1's CheckTransaction accepts a two-output
transaction whose int64 sum wraps, while the post-Aug-2010 (MoneyRange) rule rejects it.
The historical block-74638 satoshi amounts are used verbatim. Evidence: MODEL."""

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent / "model"))

from overflow import (                                                   # noqa: E402
    COIN, MAX_MONEY, OVERFLOW_SAT, add_i64, check_transaction_hardened,
    check_transaction_v01, money_range, output_total_int64, output_total_true,
    overflow_tx, to_int64,
)
from tx_sighash import Tx, TxIn, TxOut                                    # noqa: E402

ZERO = b"\x00" * 32
_IN = b"\x11" * 32


# ---- the finding: one accepts, the other rejects, the same tx ----------------

def test_v01_accepts_the_overflow_tx():
    ok, why = check_transaction_v01(overflow_tx())
    assert ok, why                               # the bug: v0.1 accepts it


def test_hardened_rejects_the_overflow_tx():
    ok, why = check_transaction_hardened(overflow_tx())
    assert not ok and "MoneyRange" in why        # the Aug-2010 fix rejects it


# ---- the mechanism: fixed-width sum wraps; true value is astronomical ---------

def test_int64_sum_wraps_negative_while_true_value_is_enormous():
    tx = overflow_tx()
    assert output_total_int64(tx) == -997_538            # C++ int64 accumulator wraps
    assert output_total_true(tx) == 2 * OVERFLOW_SAT     # big-int: no wrap
    assert output_total_true(tx) // COIN > 184_000_000_000   # > 184 billion BTC minted


def test_the_divergence_is_the_whole_bug():
    # a downstream `value_in >= value_out` on the int64 total passes with a tiny input,
    # yet the true minted value is enormous -- that gap is the vulnerability.
    tx = overflow_tx()
    tiny_input = 1
    assert tiny_input >= output_total_int64(tx)          # v0.1's check: PASSES
    assert not (tiny_input >= output_total_true(tx))     # reality: massively inflationary


# ---- controls: the two rules agree where v0.1 was already correct -------------

def test_both_rules_reject_a_negative_output():
    tx = Tx(1, [TxIn(_IN, 0, b"\x51", 0xFFFFFFFF)], [TxOut(-1, b"\x51")], 0)
    assert not check_transaction_v01(tx)[0]
    assert not check_transaction_hardened(tx)[0]


def test_both_rules_accept_a_normal_tx():
    tx = Tx(1, [TxIn(_IN, 0, b"\x51", 0xFFFFFFFF)], [TxOut(50 * COIN, b"\x51")], 0)
    assert check_transaction_v01(tx)[0]
    assert check_transaction_hardened(tx)[0]


def test_the_gap_is_the_missing_upper_bound():
    # an output of MAX_MONEY+1 (positive, above the cap, no wrap needed): v0.1 accepts
    # because it has no upper bound at all; the 2010 rule rejects via MoneyRange.
    tx = Tx(1, [TxIn(_IN, 0, b"\x51", 0xFFFFFFFF)], [TxOut(MAX_MONEY + 1, b"\x51")], 0)
    assert check_transaction_v01(tx)[0]                  # no upper bound in v0.1
    assert not check_transaction_hardened(tx)[0]         # MoneyRange rejects


# ---- fidelity checks ---------------------------------------------------------

def test_historical_values_are_the_block_74638_amounts():
    # two outputs of 92,233,720,368.54277039 BTC each (the tx in block 74638)
    assert OVERFLOW_SAT == 9_223_372_036_854_277_039
    # each is below the signed-int64 max (2^63-1), but two of them exceed it -> wrap
    assert OVERFLOW_SAT < 2 ** 63 <= 2 * OVERFLOW_SAT


def test_int64_and_money_range_helpers():
    assert to_int64(2 ** 63 - 1) == 2 ** 63 - 1
    assert to_int64(2 ** 63) == -(2 ** 63)
    assert add_i64(2 ** 63 - 1, 1) == -(2 ** 63)         # overflow wraps
    assert money_range(0) and money_range(MAX_MONEY)
    assert not money_range(-1) and not money_range(MAX_MONEY + 1)


def test_coinbase_script_size_bound_present_in_both():
    # both keep the structural coinbase-script-size check (2..100 bytes)
    bad = Tx(1, [TxIn(ZERO, 0xFFFFFFFF, b"\x01", 0xFFFFFFFF)], [TxOut(50 * COIN, b"\x51")], 0)
    assert not check_transaction_v01(bad)[0]             # 1-byte coinbase script < 2
    assert not check_transaction_hardened(bad)[0]
    ok = Tx(1, [TxIn(ZERO, 0xFFFFFFFF, b"\x02\x00", 0xFFFFFFFF)], [TxOut(50 * COIN, b"\x51")], 0)
    assert check_transaction_v01(ok)[0]
    assert check_transaction_hardened(ok)[0]
