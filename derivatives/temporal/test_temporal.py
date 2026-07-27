"""v0.1's temporal consensus rules, executed: median-time-past, the two block-timestamp
checks (future +2h, strictly-after-median), and transaction finality (height-only nLockTime
with the nSequence override). Faithful to main.h:1086 / main.cpp:1164,1206 / main.h IsFinal.
Evidence: MODEL."""

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent / "model"))

from temporal import (                                                   # noqa: E402
    MEDIAN_TIME_SPAN, TWO_HOURS, UINT_MAX, block_time_ok_future,
    block_time_ok_vs_prev, get_median_time_past, tx_is_final, txin_is_final,
)
from tx_sighash import Tx, TxIn, TxOut                                    # noqa: E402


def _tx(locktime, seqs):
    return Tx(1, [TxIn(b"\x11" * 32, i, b"", s) for i, s in enumerate(seqs)],
              [TxOut(1, b"\x51")], locktime)


# ---- GetMedianTimePast (main.h:1086) -----------------------------------------

def test_median_of_eleven_is_the_sorted_middle():
    times = [100, 90, 80, 70, 60, 50, 40, 30, 20, 10, 0]     # 11, newest-first
    assert get_median_time_past(times) == 50                 # sorted middle (index 5)


def test_median_uses_only_the_last_eleven():
    # 20 blocks; only the newest 11 (times 9..19 here) enter the window
    times = list(range(19, -1, -1))                          # 19,18,...,0 newest-first
    window = sorted(times[:MEDIAN_TIME_SPAN])                # 9..19
    assert get_median_time_past(times) == window[len(window) // 2] == 14


def test_median_with_fewer_than_eleven_blocks():
    assert get_median_time_past([30, 20, 10]) == 20          # early chain: median of 3
    assert get_median_time_past([40, 30, 20, 10]) == 30      # even count -> upper median (C++ /2)


def test_median_is_order_independent():
    assert get_median_time_past([50, 10, 30, 20, 40]) == 30


# ---- block timestamp checks (main.cpp:1164, 1206) ----------------------------

def test_block_rejected_if_more_than_two_hours_in_future():
    now = 1_231_006_505
    assert block_time_ok_future(now + TWO_HOURS, now)         # exactly +2h: ok (<=)
    assert not block_time_ok_future(now + TWO_HOURS + 1, now)  # +2h+1s: rejected


def test_block_must_be_strictly_after_median_past():
    prev = [100, 90, 80, 70, 60, 50, 40, 30, 20, 10, 0]      # mtp = 50
    assert block_time_ok_vs_prev(51, prev)                    # after median: ok
    assert not block_time_ok_vs_prev(50, prev)                # equal to median: rejected
    assert not block_time_ok_vs_prev(49, prev)                # before median: rejected


# ---- CTxIn::IsFinal / CTransaction::IsFinal (main.h) --------------------------

def test_txin_final_only_when_sequence_is_uint_max():
    assert txin_is_final(UINT_MAX)
    assert not txin_is_final(0)
    assert not txin_is_final(UINT_MAX - 1)


def test_tx_final_when_locktime_zero():
    assert tx_is_final(_tx(0, [0]), best_height=100000)       # locktime 0 -> always final


def test_tx_final_when_locktime_below_best_height():
    assert tx_is_final(_tx(90000, [0]), best_height=100000)   # 90000 < 100000 -> final


def test_tx_nonfinal_at_future_height_unless_inputs_final():
    future = _tx(200000, [0, 0])                              # locktime above height, inputs not final
    assert not tx_is_final(future, best_height=100000)
    # the nSequence=UINT_MAX override makes it final even with a future locktime
    overridden = _tx(200000, [UINT_MAX, UINT_MAX])
    assert tx_is_final(overridden, best_height=100000)
    # one non-final input is enough to keep it non-final
    mixed = _tx(200000, [UINT_MAX, 0])
    assert not tx_is_final(mixed, best_height=100000)


def test_tx_becomes_final_once_height_passes_locktime():
    tx = _tx(150000, [0])
    assert not tx_is_final(tx, best_height=100000)            # 150000 not < 100000
    assert tx_is_final(tx, best_height=150001)                # now 150000 < 150001 -> final


# ---- the finding: v0.1 nLockTime is HEIGHT-only (no time threshold) ----------

def test_v01_locktime_500000000_is_treated_as_a_height_not_a_time():
    # Modern Bitcoin reads >= 500,000,000 as a Unix time; v0.1 has no such threshold,
    # so it treats 500000000 as a block HEIGHT (final only past that height).
    tx = _tx(500_000_000, [0])
    assert not tx_is_final(tx, best_height=100_000)           # far below height 500,000,000
    assert tx_is_final(tx, best_height=500_000_001)           # only final past that height
