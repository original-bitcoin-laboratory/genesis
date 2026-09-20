"""Executable reproduction of v0.1's difficulty-retarget surface -- MODEL.

Ports GetNextWorkRequired (extracted/bitcoin/src/main.cpp:685-728) line-for-line and exhibits two
era-authentic properties of Satoshi's retarget that a faithful reconstruction must reproduce:

  (A) the fencepost off-by-one. The loop `for (int i = 0; pindexFirst && i < nInterval-1; i++)`
      (main.cpp:701) walks pindexFirst back nInterval-1 = 2015 blocks, so nActualTimespan
      (main.cpp:706) spans 2015 intervals, yet it is divided by nTargetTimespan = nInterval *
      nTargetSpacing = 2016 * 600 (main.cpp:717). The retarget's fixed point is therefore
      nActualTimespan == nTargetTimespan, i.e. 2015 * tau == 2016 * 600, so the network's real
      spacing settles at tau = 2016/2015 * 600 = 600.2977s -- about 0.05% SLOWER than the nominal
      ten minutes, at every retarget. (Mechanism: the code under-measures elapsed time by one
      interval, reads blocks as slightly too fast, and sets difficulty very slightly harder.)

  (B) boundary-only measurement. nActualTimespan = time(pindexLast) - time(pindexFirst) of the
      window, with nothing binding the last block of one period to the first of the next
      (main.cpp:706). This is the property the timewarp attack uses: majority hashpower stamping
      period-boundary blocks with inflated timestamps forces the maximal 4x-per-period difficulty
      drop (the clamp at main.cpp:708-711). Has not fired on Bitcoin mainnet; the point here is only
      that the v0.1 code has this boundary behaviour.

Everything below is exact arithmetic over Satoshi's own constants; the difficulty-1 target is the
v0.1 bnProofOfWorkLimit (`~uint256(0) >> 32`, main.h:22; compact 0x1d00ffff). The nBits codec is
CBigNum::SetCompact / GetCompact from v0.1's bignum.h:257-282, over OpenSSL's MPI encoding. (Until
20 September 2026 this module carried Bitcoin Core's later arith_uint256::SetCompact, with its
negative/overflow triple, and called it v0.1; an adversarial review caught the substitution.)
Evidence level: MODEL.
"""

from __future__ import annotations

# -- Satoshi's exact retarget constants (main.cpp:687-689) -------------------
N_TARGET_TIMESPAN = 14 * 24 * 60 * 60          # 1,209,600 s ("two weeks")
N_TARGET_SPACING = 10 * 60                      # 600 s
N_INTERVAL = N_TARGET_TIMESPAN // N_TARGET_SPACING  # 2016

# bnProofOfWorkLimit = ~uint256(0) >> 32 (main.h:22) = 2^224 - 1; its compact form is 0x1d00ffff and
# SetCompact(0x1d00ffff) = 0xFFFF << 208, which is what every comparison in the code uses
POW_LIMIT = 0xFFFF << 208
D1_BITS = 0x1d00ffff


# ---- the nBits codec, as v0.1's CBigNum does it (bignum.h:257-282) --------------------------------
def set_compact(c: int) -> tuple[int, bool]:
    """CBigNum::SetCompact(nCompact): build a 4 + nSize byte MPI (big-endian length, then magnitude,
    of which only the first three bytes come from the compact word) and hand it to BN_mpi2bn.
    Returns (magnitude, negative): MPI marks a negative number with the 0x80 bit of the first
    magnitude byte, which BN_mpi2bn clears and records as the sign. There is no overflow: any
    nSize up to 255 decodes."""
    n_size = c >> 24
    mant = [(c >> 16) & 0xff, (c >> 8) & 0xff, c & 0xff][:n_size] + [0] * max(0, n_size - 3)
    negative = n_size >= 1 and bool(mant[0] & 0x80)
    if negative:
        mant[0] &= 0x7f
    return int.from_bytes(bytes(mant), "big") if mant else 0, negative


def get_compact(value: int) -> int:
    """CBigNum::GetCompact(): BN_bn2mpi, then nSize = MPI length - 4 and the first three magnitude
    bytes into the word. BN_bn2mpi prefixes a 0x00 byte when the top bit of the magnitude is set
    (so the sign bit stays free), which is why 0xFFFF << 208 encodes as size 0x1d with 0x00ffff."""
    if value < 0:
        raise ValueError("this port encodes the non-negative targets the retarget produces")
    mag = value.to_bytes((value.bit_length() + 7) // 8, "big") if value else b""
    if mag and mag[0] & 0x80:
        mag = b"\x00" + mag
    n_size = len(mag)
    compact = n_size << 24
    if n_size >= 1:
        compact |= mag[0] << 16
    if n_size >= 2:
        compact |= mag[1] << 8
    if n_size >= 3:
        compact |= mag[2]
    return compact


def expected_hashes(target: int) -> int:
    """Expected hashes to find a block at this target = 2^256 / (target+1)."""
    return (1 << 256) // (target + 1)


# ---- the block index, enough of CBlockIndex for the walk -------------------------------------------
class BlockIndex:
    """`pprev`, `nHeight`, `nTime`: the three fields GetNextWorkRequired reads."""

    def __init__(self, pprev, ntime: int):
        self.pprev = pprev
        self.nHeight = 0 if pprev is None else pprev.nHeight + 1
        self.nTime = ntime


def chain(times: list[int]) -> BlockIndex:
    """An index chain with these timestamps, oldest first; returns pindexLast."""
    idx = None
    for t in times:
        idx = BlockIndex(idx, t)
    return idx


def intervals_measured(pindex_last: BlockIndex) -> int:
    """Run the pindexFirst walk exactly as main.cpp:700-702 on a real index chain and return how many
    block intervals separate pindexFirst from pindexLast:

        const CBlockIndex* pindexFirst = pindexLast;
        for (int i = 0; pindexFirst && i < nInterval-1; i++)
            pindexFirst = pindexFirst->pprev;
    """
    pindex_first = pindex_last
    i = 0
    while pindex_first is not None and i < N_INTERVAL - 1:
        pindex_first = pindex_first.pprev
        i += 1
    if pindex_first is None:
        raise ValueError("chain shorter than the walk")
    return pindex_last.nHeight - pindex_first.nHeight


def get_next_work_required(times: list[int], old_target: int) -> int:
    """Port of GetNextWorkRequired (main.cpp:685-728) over an index chain built from `times`
    (oldest first, times[-1] == pindexLast->nTime). Returns the new target (bigger = easier).
    The retarget itself is only reached when (pindexLast->nHeight+1) % nInterval == 0; this port
    exhibits that branch."""
    if len(times) < N_INTERVAL:
        raise ValueError("need at least nInterval block timestamps")
    pindex_last = chain(times)
    # main.cpp:700-702 -- go back nInterval-1 blocks
    pindex_first = pindex_last
    i = 0
    while pindex_first is not None and i < N_INTERVAL - 1:
        pindex_first = pindex_first.pprev
        i += 1
    # main.cpp:705-706 -- limit adjustment step; nActualTimespan = last - first
    n_actual_timespan = pindex_last.nTime - pindex_first.nTime
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

    Fixed point: n_actual_timespan == N_TARGET_TIMESPAN, and n_actual_timespan spans the intervals
    the walk measures on a real chain, so tau = N_TARGET_TIMESPAN / intervals_measured(chain).
    """
    return N_TARGET_TIMESPAN / intervals_measured(chain([0] * N_INTERVAL))


def demo() -> None:
    m = intervals_measured(chain([0] * N_INTERVAL))
    tau = equilibrium_spacing()
    print(f"nInterval = {N_INTERVAL}, nTargetTimespan = {N_TARGET_TIMESPAN} s, nTargetSpacing = {N_TARGET_SPACING} s")
    print(f"(A) fencepost: the retarget measures {m} intervals but divides by a {N_INTERVAL}-interval budget")
    print(f"    -> equilibrium real spacing = {N_TARGET_TIMESPAN}/{m} = {tau:.4f} s "
          f"({(tau/N_TARGET_SPACING - 1) * 100:+.4f}% vs 600 s, i.e. a hair SLOW)")

    base = POW_LIMIT // 1000                     # a starting target 1000x below the pow limit: room to move either way
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
        print(f"               timewarp target {attack:>66}  (x{attack // honest} the honest target;"
              f" 4^{period} = {4**period}, clamped at the pow limit)")
    print("    -> each forged period multiplies the target by the clamp's 4x until the pow limit stops it;")
    print("       the starting point (1000x below the limit) is this demo's choice, not a property of the code")

    print("(C) the difficulty-1 target and v0.1's nBits codec (bignum.h:257-282, MPI)")
    val, neg = set_compact(D1_BITS)
    print(f"    SetCompact(0x1d00ffff) == 0xFFFF<<208 : {val == POW_LIMIT}  (round-trip {get_compact(val) == D1_BITS};"
          f" negative={neg})")
    e = expected_hashes(POW_LIMIT)
    print(f"    expected hashes/block = 2^256/(target+1) = {e:,}  = 2^32 * 65536/65535")
    print(f"    (NOT the round 2^32 = {1<<32:,}; that gap 65536/65535 is the pdiff-vs-bdiff discrepancy)")
    print(f"    MPI sign bit: SetCompact(0x1d80ffff) negative = {set_compact(0x1d80ffff)[1]} (a negative target; v0.1 has no overflow flag)")


if __name__ == "__main__":
    demo()
