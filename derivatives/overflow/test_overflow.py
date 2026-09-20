"""The value-overflow surface, executed: v0.1's CheckTransaction accepts a two-output
transaction whose int64 sum wraps, while the post-Aug-2010 (d4c6b90ca) rule rejects it; v0.1's
ConnectInputs value clause, ported, then passes the spend against a one-satoshi input.
The historical block-74638 satoshi amounts are used verbatim. Evidence: MODEL.

Every assertion on a verdict names the CLAUSE that fired (a fixed identifier), not a substring of a
message; the expected clauses are written here as literals, independently of the module."""

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent / "model"))

from overflow import (                                                   # noqa: E402
    CLAUSES, COIN, MAX_MONEY, OVERFLOW_SAT, add_i64, check_transaction_hardened,
    check_transaction_v01, connect_inputs_value_check_v01, money_range, output_total_int64,
    output_total_true, overflow_tx, sum_overflow_tx, to_int64,
)
from tx_sighash import Tx, TxIn, TxOut                                    # noqa: E402

ZERO = b"\x00" * 32
_IN = b"\x11" * 32


# ---- the finding: one accepts, the other rejects, the same tx ----------------

def test_v01_accepts_the_overflow_tx():
    assert check_transaction_v01(overflow_tx()) == (True, "ok")     # the bug: v0.1 accepts it


def test_hardened_rejects_the_overflow_tx_on_the_per_output_bound():
    # each output is 92 billion BTC: the per-output bound fires before the sum is ever formed
    assert check_transaction_hardened(overflow_tx()) == (False, "output-above-max-money")


def test_hardened_running_sum_clause_catches_what_the_per_output_bound_does_not():
    # two outputs each inside [0, MAX_MONEY] whose sum is outside: only the running-sum clause sees it
    tx = sum_overflow_tx()
    assert check_transaction_v01(tx) == (True, "ok")
    assert check_transaction_hardened(tx) == (False, "output-sum-out-of-range")


# ---- the mechanism: fixed-width sum wraps; true value is astronomical ---------

def test_int64_sum_wraps_negative_while_true_value_is_enormous():
    tx = overflow_tx()
    assert output_total_int64(tx) == -997_538            # C++ int64 accumulator wraps
    assert output_total_true(tx) == 2 * OVERFLOW_SAT     # big-int: no wrap
    assert output_total_true(tx) // COIN > 184_000_000_000   # > 184 billion BTC minted


def test_the_divergence_is_the_whole_bug():
    # v0.1's ConnectInputs value clause, ported: `nValueIn < GetValueOut()` on the int64 total
    # passes with a one-satoshi input, while the true value created is enormous
    tx = overflow_tx()
    assert connect_inputs_value_check_v01(tx, 1) == (True, "ok")          # v0.1: PASSES
    assert 1 < output_total_true(tx)                                       # reality: inflationary
    # the same clause with a sane transaction still refuses an underfunded spend
    normal = Tx(1, [TxIn(_IN, 0, b"\x51", 0xFFFFFFFF)], [TxOut(50 * COIN, b"\x51")], 0)
    assert connect_inputs_value_check_v01(normal, 50 * COIN - 1) == (False, "value-in-below-value-out")
    assert connect_inputs_value_check_v01(normal, 50 * COIN) == (True, "ok")


# ---- controls: the two rules agree where v0.1 was already correct -------------

def test_both_rules_reject_a_negative_output():
    tx = Tx(1, [TxIn(_IN, 0, b"\x51", 0xFFFFFFFF)], [TxOut(-1, b"\x51")], 0)
    assert check_transaction_v01(tx) == (False, "output-negative")
    assert check_transaction_hardened(tx) == (False, "output-negative")


def test_both_rules_accept_a_normal_tx():
    tx = Tx(1, [TxIn(_IN, 0, b"\x51", 0xFFFFFFFF)], [TxOut(50 * COIN, b"\x51")], 0)
    assert check_transaction_v01(tx) == (True, "ok")
    assert check_transaction_hardened(tx) == (True, "ok")


def test_the_gap_is_the_missing_upper_bound():
    # an output of MAX_MONEY+1 (positive, above the cap, no wrap needed): v0.1 accepts
    # because it has no upper bound at all; the 2010 rule rejects on the per-output clause.
    tx = Tx(1, [TxIn(_IN, 0, b"\x51", 0xFFFFFFFF)], [TxOut(MAX_MONEY + 1, b"\x51")], 0)
    assert check_transaction_v01(tx) == (True, "ok")
    assert check_transaction_hardened(tx) == (False, "output-above-max-money")


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
    assert MAX_MONEY == 21_000_000 * 100_000_000          # the 2010 constant, as a literal


def test_every_clause_a_check_can_return_is_in_the_vocabulary():
    assert set(CLAUSES) == {"ok", "vin-or-vout-empty", "output-negative", "coinbase-script-size",
                            "prevout-null", "output-above-max-money", "output-sum-out-of-range"}


def test_coinbase_script_size_bound_present_in_both():
    # both keep the structural coinbase-script-size check (2..100 bytes)
    bad = Tx(1, [TxIn(ZERO, 0xFFFFFFFF, b"\x01", 0xFFFFFFFF)], [TxOut(50 * COIN, b"\x51")], 0)
    assert check_transaction_v01(bad) == (False, "coinbase-script-size")
    assert check_transaction_hardened(bad) == (False, "coinbase-script-size")
    ok = Tx(1, [TxIn(ZERO, 0xFFFFFFFF, b"\x02\x00", 0xFFFFFFFF)], [TxOut(50 * COIN, b"\x51")], 0)
    assert check_transaction_v01(ok) == (True, "ok")
    assert check_transaction_hardened(ok) == (True, "ok")
