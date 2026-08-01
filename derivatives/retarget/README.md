# Difficulty-retarget surface, executed — v0.1's `GetNextWorkRequired` fencepost + timewarp

**Evidence level: `MODEL`.** This ports Satoshi's difficulty retarget
([`extracted/bitcoin/src/main.cpp:685-728`](../../extracted/bitcoin/src/main.cpp)) line-for-line and
exhibits two era-authentic properties a faithful reconstruction must reproduce — the same way
[`../overflow/`](../overflow/) made the value-overflow surface runnable. Both are consequences of the
*executed* arithmetic, not of the design's intent.

## What it shows

```
nInterval = 2016, nTargetTimespan = 1209600 s, nTargetSpacing = 600 s
(A) fencepost: the retarget measures 2015 intervals but divides by a 2016-interval budget
    -> equilibrium real spacing = 1209600/2015 = 600.2978 s (+0.0496% vs 600 s, i.e. a hair SLOW)
    at a naive 600 s spacing the ported retarget returns a HARDER target -> not stable at 600 s
(B) timewarp: forging the boundary block's timestamp forces the maximal 4x-per-period drop
    -> after 5 periods the attacker's target is ~1000x easier (difficulty collapsed to the floor)
```

## (A) The fencepost off-by-one

`GetNextWorkRequired` walks `pindexFirst` back `nInterval-1 = 2015` blocks
(`main.cpp:701`, `for (int i = 0; pindexFirst && i < nInterval-1; i++)`) and measures
`nActualTimespan = pindexLast->nTime - pindexFirst->nTime` (`main.cpp:706`) over those **2015**
intervals — then divides by `nTargetTimespan = nInterval * nTargetSpacing = 2016 * 600`
(`main.cpp:717`). It **under-measures** the elapsed time by one interval, reads blocks as slightly
too fast, and sets difficulty very slightly **harder**. The fixed point is `nActualTimespan ==
nTargetTimespan`, i.e. `2015 · τ = 2016 · 600`, so the network's real spacing settles at

```
τ = 2016/2015 × 600 = 600.2978 s   (~+0.0496%, a hair SLOW — permanently)
```

This is the opposite direction from the common "~599.7 s, a hair fast" phrasing: the code compares
2015 measured intervals against a 2016-interval budget, so blocks come *slower* than ten minutes, not
faster. Verified against the ported function (a naive 600 s window is not the fixed point — the
retarget returns a harder target; a 600.2978 s window is exactly stable).

## (B) Boundary-only measurement (the timewarp property)

`nActualTimespan` is `time(last) − time(first)` of the window, with nothing binding the last block of
one period to the first of the next (`main.cpp:706`). Majority hashpower can stamp the period-boundary
block with an inflated timestamp so each window *looks* far too long, forcing the maximal `×4`
difficulty drop per period (the clamp at `main.cpp:708-711`). Modelled here as the boundary forge; it
collapses difficulty to the pow-limit floor within a few periods, while an honest chain is unmoved.
**Never fired on Bitcoin mainnet** (needs 51% and is glaring); the point is only that the v0.1 code
has this boundary behaviour, latent in the executable.

## Why it's a MODEL

Ported to Python integers over Satoshi's exact constants (`nTargetTimespan`, `nTargetSpacing`,
`nInterval`, and `bnProofOfWorkLimit` = compact `0x1d00ffff` = `0xFFFF << 208`). Honest boundary:
this is a **port** of `main.cpp:685-728`, not the original binary executing; its value is exhibiting
the fixed point and the boundary behaviour from the real constants. The lab's live engines
(`../../derivatives/validator-rs/src/difficulty.rs`, `../netnode/difficulty.py`) deliberately run a
short experimental retarget interval for the X-chains, so this module is where the *mainnet* 2016-block
fencepost is made explicit.

## Difficulty-1 target exactness + the nBits codec (section C)

The demo also nails the difficulty-1 target and its encoding: `SetCompact(0x1d00ffff)` decodes to
`0xFFFF·2²⁰⁸` (round-trips canonically), and the **expected hashes per block** is
`2²⁵⁶/(target+1) = 4,295,032,833` — **not** the round `2³²`. The gap is exactly `65536/65535`, the
well-known **pdiff-vs-bdiff** discrepancy (pool difficulty uses `2²⁴`, Bitcoin difficulty uses the real
`0xFFFF·2²⁰⁸`). The `nBits` codec's edges are shown too: the mantissa's `0x00800000` sign bit marks a
**negative** (invalid) target, and an over-large exponent **overflows**. (`set_compact`, `get_compact`,
`expected_hashes`.)

## Tests (`test_retarget.py`, 11)

The finding (2015 measured intervals; equilibrium 600.30 s, slower than 600); the mechanism (naive
600 s is not the fixed point and goes harder; 600.2978 s is exactly stable); the clamp (`×¼`/`×4`);
the timewarp (one forged boundary forces `×4`, iterated it collapses ~1000× while the honest chain is
unchanged); the pow-limit floor; the constants match `main.cpp`; and the difficulty-1 target / nBits
round-trip, the exact `4,295,032,833` expected hashes (pdiff-vs-bdiff), and the sign-bit/overflow edges.

```bash
python retarget.py     # the demo above
python -m pytest       # 11 passed
```

## Boundary

MODEL; objective source port of `main.cpp:685-728`; no chain privileged; not a live-exploit claim
(timewarp needs majority hashpower and has never run on Bitcoin mainnet). It is a *tool*, never
authority (`common/AUTHORITY.md`).
