"""Executable port of v0.1's temporal consensus rules -- MODEL.

Completes the "present machinery" column of ../../../common/conformance/CONSENSUS_SURFACE.md:
the block-timestamp rules and transaction finality v0.1 DID ship (unlike the value/resource
bounds it lacked). Faithful ports of:
  - CBlockIndex::GetMedianTimePast()          main.h:1086  (nMedianTimeSpan = 11)
  - CheckBlock timestamp-future check         main.cpp:1164 (> now + 2h -> reject)
  - AcceptBlock timestamp-vs-prev check       main.cpp:1206 (<= median-past -> reject)
  - CTransaction::IsFinal() / CTxIn::IsFinal() main.h:226 + the tx version

Finding surfaced here: v0.1's nLockTime is compared ONLY against block height
(`nLockTime < nBestHeight`). There is NO time/height `LOCKTIME_THRESHOLD` (500000000)
split -- that distinction is a later refinement (confirmed: 0 occurrences in v0.1 source).
So a v0.1 lock is purely height-based, unless overridden by every input's nSequence == 2^32-1.

Evidence level: MODEL (line-for-line port of the v0.1 logic).
"""

from __future__ import annotations

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "model"))
from tx_sighash import Tx, TxIn, TxOut                                   # noqa: E402  (re-exported for tests)

UINT_MAX = 0xFFFFFFFF
MEDIAN_TIME_SPAN = 11             # main.h:1084  enum { nMedianTimeSpan = 11 }
TWO_HOURS = 2 * 60 * 60          # main.cpp:1164


# -- block timestamps ---------------------------------------------------------
def get_median_time_past(times_newest_first: list[int]) -> int:
    """CBlockIndex::GetMedianTimePast (main.h:1086).

    Collects up to the last `nMedianTimeSpan` block times (this block + ancestors walked
    via pprev), sorts, and returns the middle element. `times_newest_first` is
    [nTime(this), nTime(prev), nTime(prev.prev), ...]. Integer-division median index
    matches the C++ `pbegin[(pend - pbegin) / 2]` (upper median for even counts)."""
    window = sorted(times_newest_first[:MEDIAN_TIME_SPAN])
    return window[len(window) // 2]


def block_time_ok_future(n_time: int, adjusted_now: int) -> bool:
    """CheckBlock (main.cpp:1164): a block more than 2h in the future is rejected."""
    return n_time <= adjusted_now + TWO_HOURS


def block_time_ok_vs_prev(n_time: int, prev_times_newest_first: list[int]) -> bool:
    """AcceptBlock (main.cpp:1206): a block's nTime must be strictly greater than the
    median-time-past of the preceding blocks."""
    return n_time > get_median_time_past(prev_times_newest_first)


# -- transaction finality -----------------------------------------------------
def txin_is_final(sequence: int) -> bool:
    """CTxIn::IsFinal (main.h:226): nSequence == UINT_MAX."""
    return sequence == UINT_MAX


def tx_is_final(tx: Tx, best_height: int) -> bool:
    """CTransaction::IsFinal (main.h).

    Final if nLockTime == 0, or nLockTime < nBestHeight (nLockTime is a BLOCK HEIGHT in
    v0.1 -- no time threshold); otherwise final only if EVERY input is final."""
    if tx.locktime == 0 or tx.locktime < best_height:
        return True
    return all(txin_is_final(vin.seq) for vin in tx.vin)


# -- demo ---------------------------------------------------------------------
def _tx(locktime: int, seqs: list[int]) -> Tx:
    vin = [TxIn(b"\x11" * 32, i, b"", s) for i, s in enumerate(seqs)]
    return Tx(1, vin, [TxOut(1, b"\x51")], locktime)


def demo() -> None:
    prev = [1231006505 + 600 * i for i in range(11)][::-1]   # 11 blocks, 10 min apart, newest-first
    mtp = get_median_time_past(prev)
    print("BLOCK TIMESTAMPS")
    print(f"  median-time-past of last 11 blocks : {mtp}")
    print(f"  block at mtp+1                      : accept={block_time_ok_vs_prev(mtp + 1, prev)}")
    print(f"  block at mtp (not strictly after)   : accept={block_time_ok_vs_prev(mtp, prev)}")
    print(f"  block 3h in the future              : accept={block_time_ok_future(mtp + 3*3600, mtp)}")
    print("TX FINALITY (best_height = 100000)")
    print(f"  locktime 0                          : final={tx_is_final(_tx(0, [0]), 100000)}")
    print(f"  locktime 90000 (< height)           : final={tx_is_final(_tx(90000, [0]), 100000)}")
    print(f"  locktime 200000 (future height)     : final={tx_is_final(_tx(200000, [0]), 100000)}")
    print(f"  ... same, all inputs nSequence=MAX  : final={tx_is_final(_tx(200000, [UINT_MAX]), 100000)}")
    print(f"  locktime 500000000 (v0.1 = HEIGHT)  : final={tx_is_final(_tx(500_000_000, [0]), 100000)}")


if __name__ == "__main__":
    demo()
