"""Executable reproduction of v0.1's difficulty-retarget surface -- MODEL.

Ports GetNextWorkRequired (extracted/bitcoin/src/main.cpp:685-728) line-for-line and exhibits two
era-authentic properties of Satoshi's retarget that a faithful reconstruction must reproduce:

  (A) the fencepost off-by-one. The loop `for (int i = 0; pindexFirst && i < nInterval-1; i++)`
      (main.cpp:701) walks pindexFirst back nInterval-1 = 2015 blocks, so nActualTimespan
      (main.cpp:706) spans 2015 intervals, yet it is divided by nTargetTimespan = nInterval *
      nTargetSpacing = 2016 * 600 (main.cpp:717). The retarget's fixed point is therefore
      nActualTimespan == nTargetTimespan, i.e. 2015 * tau == 2016 * 600, so the network's real
      spacing settles at tau = 2016/2015 * 600 = 600.2977s -- about 0.05% SLOWER than the nominal
      ten minutes, permanently. (Mechanism: the code under-measures elapsed time by one interval,
      reads blocks as slightly too fast, and sets difficulty very slightly harder.)

  (B) boundary-only measurement. nActualTimespan = time(pindexLast) - time(pindexFirst) of the
      window, with nothing binding the last block of one period to the first of the next
      (main.cpp:706). This is the property the timewarp attack uses: majority hashpower stamping
      period-boundary blocks with inflated timestamps forces the maximal 4x-per-period difficulty
      drop (the clamp at main.cpp:708-711). Never fired on Bitcoin mainnet; the point here is only
      that the v0.1 code has this boundary behaviour.

Everything below is exact arithmetic over Satoshi's own constants; the difficulty-1 target is the
v0.1 bnProofOfWorkLimit (compact 0x1d00ffff). Evidence level: MODEL.
"""

from __future__ import annotations

# -- Satoshi's exact retarget constants (main.cpp:687-689) -------------------
N_TARGET_TIMESPAN = 14 * 24 * 60 * 60          # 1,209,600 s ("two weeks")
N_TARGET_SPACING = 10 * 60                      # 600 s
N_INTERVAL = N_TARGET_TIMESPAN // N_TARGET_SPACING  # 2016

# bnProofOfWorkLimit, compact 0x1d00ffff = 0xFFFF * 2^(8*(0x1d-3)) = 0xFFFF << 208 (difficulty 1)
POW_LIMIT = 0xFFFF << 208
D1_BITS = 0x1d00ffff

# ---- the difficulty-1 target: nBits codec + the exact (pdiff-vs-bdiff) expected work --------
def set_compact(c):
    """Bitcoin SetCompact -> (target, negative, overflow)."""
    size = c >> 24; word = c & 0x007fffff
    val = word >> (8*(3-size)) if size <= 3 else word << (8*(size-3))
    negative = word != 0 and (c & 0x00800000) != 0
    overflow = word != 0 and (size > 34 or (word > 0xff and size > 33) or (word > 0xffff and size > 32))
    return val, negative, overflow

def get_compact(value):
    """Bitcoin GetCompact -> canonical nBits for a positive target."""
    size = (value.bit_length() + 7) // 8
    compact = (value << (8*(3-size))) if size <= 3 else (value >> (8*(size-3)))
    if compact & 0x00800000: compact >>= 8; size += 1
    return compact | (size << 24)

def expected_hashes(target):
    """Expected hashes to find a block at this target = 2^256 / (target+1)."""
    return (1 << 256) // (target + 1)


def intervals_measured() -> int:
    """Run the pindexFirst walk exactly as main.cpp:700-702 and count the intervals it spans.

    `pindexFirst = pindexLast; for (i=0; i < nInterval-1; i++) pindexFirst = pindexFirst->pprev;`
    leaves pindexFirst nInterval-1 blocks behind pindexLast -> the timespan spans nInterval-1 gaps.
    """
    steps = 0
    for _i in range(N_INTERVAL - 1):           # i < nInterval-1
        steps += 1
    return steps                                # == 2016 - 1 == 2015


def get_next_work_required(times: list[int], old_target: int) -> int:
    """Port of GetNextWorkRequired (main.cpp:685-728).

    `times` are the block timestamps with times[-1] == pindexLast->nTime; pindexFirst is
    nInterval-1 blocks earlier, i.e. times[-N_INTERVAL]. Returns the new target (bigger = easier).
    """
    if len(times) < N_INTERVAL:
        raise ValueError("need at least nInterval block timestamps")
    # main.cpp:700-706 -- go back nInterval-1 blocks, measure last - first
    n_actual_timespan = times[-1] - times[-N_INTERVAL]
    # main.cpp:708-711 -- clamp to [target/4, target*4]
    if n_actual_timespan < N_TARGET_TIMESPAN // 4:
        n_actual_timespan = N_TARGET_TIMESPAN // 4
    if n_actual_timespan > N_TARGET_TIMESPAN * 4:
        n_actual_timespan = N_TARGET_TIMESPAN * 4
    # main.cpp:714-717 -- bnNew = old * actual / target
    new_target = old_target * n_actual_timespan // N_TARGET_TIMESPAN
    # main.cpp:719-720 -- cap at the pow limit (difficulty can't drop below 1)
    if new_target > POW_LIMIT:
        new_target = POW_LIMIT
    return new_target


def window_at_spacing(spacing: float, t0: int = 0) -> list[int]:
    """nInterval block timestamps at a constant real spacing (integer-rounded)."""
    return [t0 + round(i * spacing) for i in range(N_INTERVAL)]


def equilibrium_spacing() -> float:
    """The real block spacing at which the retarget holds difficulty constant.

    Fixed point: n_actual_timespan == N_TARGET_TIMESPAN, and n_actual_timespan spans
    intervals_measured() gaps, so tau = N_TARGET_TIMESPAN / intervals_measured().
    """
    return N_TARGET_TIMESPAN / intervals_measured()


def demo() -> None:
    m = intervals_measured()
    tau = equilibrium_spacing()
    print(f"nInterval = {N_INTERVAL}, nTargetTimespan = {N_TARGET_TIMESPAN} s, nTargetSpacing = {N_TARGET_SPACING} s")
    print(f"(A) fencepost: the retarget measures {m} intervals but divides by a {N_INTERVAL}-interval budget")
    print(f"    -> equilibrium real spacing = {N_TARGET_TIMESPAN}/{m} = {tau:.4f} s "
          f"({(tau/N_TARGET_SPACING - 1) * 100:+.4f}% vs 600 s, i.e. a hair SLOW)")

    base = POW_LIMIT // 1000                     # difficulty ~1000, room to move either way
    # naive 600 s spacing is NOT the fixed point: the ported retarget makes difficulty HARDER
    t_naive = get_next_work_required(window_at_spacing(N_TARGET_SPACING), base)
    print(f"    at a naive 600 s spacing the ported retarget returns target {t_naive} "
          f"({'harder' if t_naive < base else 'easier'} than {base}) -> not stable at 600 s")

    print("(B) timewarp: boundary-only measurement + the 4x clamp")
    honest = attack = base
    for period in range(1, 6):
        honest = get_next_work_required(window_at_spacing(tau), honest)          # blocks really ~600.30 s
        forged = window_at_spacing(N_TARGET_SPACING)
        forged[-1] += N_TARGET_TIMESPAN * 8      # stamp the boundary block far in the future
        attack = get_next_work_required(forged, attack)
        print(f"    period {period}: honest target {honest:>68}")
        print(f"               timewarp target {attack:>66}")
    print(f"    -> after 5 periods the attacker's target is ~{attack // max(honest, 1)}x easier "
          f"(difficulty collapsed by the max 4x/period)")

    print("(C) difficulty-1 target exactness + the nBits codec")
    val, neg, ovf = set_compact(D1_BITS)
    print(f"    SetCompact(0x1d00ffff) == 0xFFFF<<208 : {val == POW_LIMIT}  (round-trip {get_compact(val) == D1_BITS};"
          f" negative={neg} overflow={ovf})")
    e = expected_hashes(POW_LIMIT)
    print(f"    expected hashes/block = 2^256/(target+1) = {e:,}  = 2^32 * 65536/65535")
    print(f"    (NOT the round 2^32 = {1<<32:,}; that gap 65536/65535 is the pdiff-vs-bdiff discrepancy)")
    print(f"    sign-bit edge: SetCompact(0x1d80ffff) negative = {set_compact(0x1d80ffff)[1]} (invalid target)")


if __name__ == "__main__":
    demo()
