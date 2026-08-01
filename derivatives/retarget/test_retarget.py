"""The difficulty-retarget surface, executed: v0.1's GetNextWorkRequired measures a 2016-block
window over only 2015 intervals (the fencepost), so the network's real spacing settles at
2016/2015 * 600 = 600.30 s -- a hair slow, forever; and its boundary-only timespan lets a timewarp
collapse difficulty. Ported line-for-line from main.cpp:685-728. Evidence: MODEL."""

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from retarget import (                                                    # noqa: E402
    D1_BITS, N_INTERVAL, N_TARGET_SPACING, N_TARGET_TIMESPAN, POW_LIMIT,
    equilibrium_spacing, expected_hashes, get_compact, get_next_work_required,
    intervals_measured, set_compact, window_at_spacing,
)


# ---- the finding: the fencepost makes blocks a hair SLOW ----------------------

def test_intervals_measured_is_off_by_one():
    # the walk `for (i=0; i < nInterval-1; i++)` spans nInterval-1 gaps, not nInterval
    assert intervals_measured() == N_INTERVAL - 1 == 2015


def test_equilibrium_spacing_is_2016_over_2015_and_slower_than_600():
    tau = equilibrium_spacing()
    assert tau == N_TARGET_TIMESPAN / 2015 == (2016 / 2015) * N_TARGET_SPACING
    assert tau > N_TARGET_SPACING                        # SLOWER than 600, not faster
    assert round(tau, 2) == 600.30                       # 600.2977...
    assert abs((tau / N_TARGET_SPACING - 1) - 0.000496) < 1e-6   # ~+0.0496%


# ---- the mechanism: run the ported retarget on real windows ------------------

def test_naive_600s_is_not_the_fixed_point_and_goes_harder():
    old = POW_LIMIT // 1000
    new = get_next_work_required(window_at_spacing(N_TARGET_SPACING), old)
    assert new < old                                     # under-measures time -> difficulty harder


def test_equilibrium_spacing_holds_difficulty_exactly_stable():
    old = POW_LIMIT // 1000
    # at 600.2977 s the 2015 measured gaps sum to exactly nTargetTimespan -> fixed point
    times = window_at_spacing(equilibrium_spacing())
    assert times[-1] - times[-N_INTERVAL] == N_TARGET_TIMESPAN
    assert get_next_work_required(times, old) == old


# ---- the clamp (main.cpp:708-711) --------------------------------------------

def test_retarget_clamps_to_quarter_and_quadruple():
    old = POW_LIMIT // 1000                               # room below the pow limit both ways
    fast = [0] * N_INTERVAL                               # zero elapsed -> clamp to target/4
    assert get_next_work_required(fast, old) == old // 4
    slow = [i * (10 * N_TARGET_TIMESPAN) for i in range(N_INTERVAL)]  # huge -> clamp to target*4
    assert get_next_work_required(slow, old) == old * 4


# ---- (B) timewarp: boundary-only measurement collapses difficulty ------------

def test_timewarp_forging_the_boundary_timestamp_collapses_difficulty():
    old = POW_LIMIT // 1000
    forged = window_at_spacing(N_TARGET_SPACING)
    forged[-1] += N_TARGET_TIMESPAN * 8                   # stamp the last block far in the future
    once = get_next_work_required(forged, old)
    assert once == old * 4                                # forced the maximal 4x easier in one period
    # iterated, it runs difficulty down to the floor within a few periods
    honest = attack = old
    for _ in range(5):
        honest = get_next_work_required(window_at_spacing(equilibrium_spacing()), honest)
        f = window_at_spacing(N_TARGET_SPACING); f[-1] += N_TARGET_TIMESPAN * 8
        attack = get_next_work_required(f, attack)
    assert honest == old                                 # honest chain unchanged
    assert attack > honest * 100                          # timewarped chain collapsed


# ---- the pow-limit floor (difficulty cannot drop below 1) --------------------

def test_target_never_exceeds_pow_limit():
    huge = [i * (10 * N_TARGET_TIMESPAN) for i in range(N_INTERVAL)]
    assert get_next_work_required(huge, POW_LIMIT) == POW_LIMIT   # capped, not 4*POW_LIMIT


# ---- fidelity checks: the constants are Satoshi's ----------------------------

def test_constants_match_main_cpp():
    assert N_TARGET_TIMESPAN == 14 * 24 * 60 * 60        # main.cpp:687
    assert N_TARGET_SPACING == 10 * 60                   # main.cpp:688
    assert N_INTERVAL == 2016                            # main.cpp:689
    assert POW_LIMIT == 0xFFFF << 208                    # bnProofOfWorkLimit, compact 0x1d00ffff


# ---- difficulty-1 target exactness + the nBits codec ------------------------

def test_difficulty_one_target_and_nbits_roundtrip():
    val, neg, ovf = set_compact(D1_BITS)
    assert val == POW_LIMIT and not neg and not ovf
    assert get_compact(val) == D1_BITS             # canonical round-trip


def test_expected_hashes_is_2p32_times_65536_over_65535():
    e = expected_hashes(POW_LIMIT)
    assert e == 4_295_032_833                       # exact; NOT the round 2^32
    assert e != (1 << 32)
    assert abs(e / (1 << 32) - 65536 / 65535) < 1e-12   # the pdiff-vs-bdiff gap


def test_nbits_sign_bit_and_overflow_edges():
    assert set_compact(0x1d80ffff)[1] is True       # sign bit set -> negative target (invalid)
    assert set_compact(0xff123456)[2] is True       # exponent too large -> overflow (invalid)
