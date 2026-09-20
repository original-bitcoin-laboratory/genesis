"""The difficulty-retarget surface, executed: v0.1's GetNextWorkRequired measures a 2016-block
window over only 2015 intervals (the fencepost), so the network's real spacing settles at
2016/2015 * 600 = 600.30 s -- a hair slow, at every retarget; and its boundary-only timespan lets a
timewarp collapse difficulty. Ported line-for-line from main.cpp:685-728. Evidence: MODEL.

The historical constants and the expected fixed point are written here as literals, independently of
the module, so a shared constant error cannot pass; the walk runs on a real index chain; and the
constants are checked against the January 2009 main.cpp itself when the archive is extracted."""

import pathlib
import re
import sys

import pytest

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from retarget import (                                                    # noqa: E402
    D1_BITS, N_INTERVAL, N_TARGET_SPACING, N_TARGET_TIMESPAN, POW_LIMIT, BlockIndex, chain,
    equilibrium_spacing, expected_hashes, get_compact, get_next_work_required,
    intervals_measured, set_compact, window_at_spacing,
)

# the values main.cpp:687-689 and main.h:22 carry, as literals (not imported from the module)
TWO_WEEKS_S = 1_209_600
TEN_MINUTES_S = 600
BLOCKS_PER_PERIOD = 2016
INTERVALS_WALKED = 2015
FIXED_POINT_S = 1_209_600 / 2015          # 600.2977667...
DIFFICULTY_ONE_TARGET = 0xFFFF * 2 ** 208


# ---- the finding: the fencepost makes blocks a hair SLOW ----------------------

def test_the_walk_on_a_real_chain_spans_2015_intervals():
    tip = chain([0] * 2016)
    assert tip.nHeight == 2015
    assert intervals_measured(tip) == INTERVALS_WALKED == BLOCKS_PER_PERIOD - 1
    # and a longer chain measures the same: the walk is bounded by nInterval-1, not by the chain
    assert intervals_measured(chain([0] * 5000)) == INTERVALS_WALKED


def test_the_walk_is_not_a_counter():
    # the walk follows pprev; a chain too short for it fails instead of returning a number
    with pytest.raises(ValueError):
        intervals_measured(chain([0] * 100))
    lone = BlockIndex(None, 0)
    with pytest.raises(ValueError):
        intervals_measured(lone)


def test_equilibrium_spacing_is_two_weeks_over_2015_and_slower_than_600():
    tau = equilibrium_spacing()
    assert tau == FIXED_POINT_S
    assert tau > TEN_MINUTES_S                           # SLOWER than 600, not faster
    assert round(tau, 2) == 600.30                       # 600.2977...
    assert abs((tau / TEN_MINUTES_S - 1) - 0.000496) < 1e-6   # ~+0.0496%


# ---- the mechanism: run the ported retarget on real windows ------------------

def test_naive_600s_is_not_the_fixed_point_and_goes_harder():
    old = DIFFICULTY_ONE_TARGET // 1000
    new = get_next_work_required(window_at_spacing(TEN_MINUTES_S), old)
    assert new < old                                     # under-measures time -> difficulty harder
    assert new == old * (2015 * 600) // TWO_WEEKS_S      # exactly: 2015 measured gaps over the 2016 budget


def test_equilibrium_spacing_holds_difficulty_exactly_stable():
    old = DIFFICULTY_ONE_TARGET // 1000
    # at 600.2977 s the 2015 measured gaps sum to exactly nTargetTimespan -> fixed point
    times = window_at_spacing(FIXED_POINT_S)
    assert times[-1] - times[-BLOCKS_PER_PERIOD] == TWO_WEEKS_S
    assert get_next_work_required(times, old) == old


# ---- the clamp (main.cpp:708-711) --------------------------------------------

def test_retarget_clamps_to_quarter_and_quadruple():
    old = DIFFICULTY_ONE_TARGET // 1000                   # room below the pow limit both ways
    fast = [0] * BLOCKS_PER_PERIOD                        # zero elapsed -> clamp to target/4
    assert get_next_work_required(fast, old) == old // 4
    slow = [i * (10 * TWO_WEEKS_S) for i in range(BLOCKS_PER_PERIOD)]  # huge -> clamp to target*4
    assert get_next_work_required(slow, old) == old * 4


# ---- (B) timewarp: boundary-only measurement collapses difficulty ------------

def test_timewarp_forging_the_boundary_timestamp_collapses_difficulty():
    old = DIFFICULTY_ONE_TARGET // 1000
    forged = window_at_spacing(TEN_MINUTES_S)
    forged[-1] += TWO_WEEKS_S * 8                         # stamp the last block far in the future
    once = get_next_work_required(forged, old)
    assert once == old * 4                                # forced the maximal 4x easier in one period
    # iterated: 4x per period until the pow limit clamps; the honest chain is unmoved
    honest = attack = old
    for period in range(1, 6):
        honest = get_next_work_required(window_at_spacing(FIXED_POINT_S), honest)
        f = window_at_spacing(TEN_MINUTES_S); f[-1] += TWO_WEEKS_S * 8
        attack = get_next_work_required(f, attack)
        assert attack == min(old * 4 ** period, DIFFICULTY_ONE_TARGET)
    assert honest == old
    assert attack == DIFFICULTY_ONE_TARGET                # 4^5 = 1024 > 1000: clamped at the limit


# ---- the pow-limit floor (difficulty cannot drop below 1) --------------------

def test_target_does_not_exceed_pow_limit():
    huge = [i * (10 * TWO_WEEKS_S) for i in range(BLOCKS_PER_PERIOD)]
    assert get_next_work_required(huge, DIFFICULTY_ONE_TARGET) == DIFFICULTY_ONE_TARGET   # capped, not 4x


# ---- fidelity checks: the constants are Satoshi's, read from the source when it is present -------

def test_module_constants_equal_the_literals_written_here():
    assert N_TARGET_TIMESPAN == TWO_WEEKS_S
    assert N_TARGET_SPACING == TEN_MINUTES_S
    assert N_INTERVAL == BLOCKS_PER_PERIOD
    assert POW_LIMIT == DIFFICULTY_ONE_TARGET


def test_constants_match_the_january_2009_main_cpp():
    src = _HERE.parents[1] / "extracted" / "bitcoin" / "src"
    main_cpp = src / "main.cpp"
    main_h = src / "main.h"
    if not (main_cpp.exists() and main_h.exists()):
        pytest.skip("extracted/bitcoin/src is not present (scripts/fetch-artifacts.sh); the constants "
                    "are checked against the literals above only")
    cpp = main_cpp.read_text(encoding="latin-1")
    h = main_h.read_text(encoding="latin-1")
    assert re.search(r"const unsigned int nTargetTimespan = 14 \* 24 \* 60 \* 60;", cpp)
    assert re.search(r"const unsigned int nTargetSpacing = 10 \* 60;", cpp)
    assert re.search(r"const unsigned int nInterval = nTargetTimespan / nTargetSpacing;", cpp)
    assert re.search(r"for \(int i = 0; pindexFirst && i < nInterval-1; i\+\+\)", cpp)
    assert "static const CBigNum bnProofOfWorkLimit(~uint256(0) >> 32);" in h
    assert 14 * 24 * 60 * 60 == TWO_WEEKS_S and 10 * 60 == TEN_MINUTES_S
    assert TWO_WEEKS_S // TEN_MINUTES_S == BLOCKS_PER_PERIOD


# ---- difficulty-1 target exactness + the v0.1 nBits codec -------------------

def test_difficulty_one_target_and_nbits_roundtrip():
    val, neg = set_compact(D1_BITS)
    assert val == DIFFICULTY_ONE_TARGET and not neg
    assert get_compact(val) == 0x1d00ffff                 # canonical round-trip, the literal
    # ~uint256(0) >> 32 is 2^224 - 1; its compact form drops everything below the top 16 bits
    assert get_compact(2 ** 224 - 1) == 0x1d00ffff and set_compact(0x1d00ffff)[0] == 0xFFFF << 208


def test_expected_hashes_is_2p32_times_65536_over_65535():
    e = expected_hashes(DIFFICULTY_ONE_TARGET)
    assert e == 4_295_032_833                       # exact; NOT the round 2^32
    assert e != (1 << 32)
    assert abs(e / (1 << 32) - 65536 / 65535) < 1e-12   # the pdiff-vs-bdiff gap


def test_mpi_sign_bit_and_no_overflow_flag():
    assert set_compact(0x1d80ffff) == (0xFFFF << 208, True)   # the MPI sign bit: negative magnitude
    # v0.1's codec has no overflow: a 255-byte exponent decodes to a large positive number
    val, neg = set_compact(0xff123456)
    assert val == 0x123456 << (8 * (0xff - 3)) and not neg
    # a two-byte magnitude sits in the top two mantissa bytes (vch[4], vch[5]), the third byte unused
    assert get_compact(0x1234) == (2 << 24) | 0x123400 and set_compact((2 << 24) | 0x123400)[0] == 0x1234
