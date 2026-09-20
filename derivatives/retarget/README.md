# Difficulty-retarget surface, executed — v0.1's `GetNextWorkRequired` fencepost + timewarp

**Evidence level: `MODEL`.** This ports Satoshi's difficulty retarget
(`extracted/bitcoin/src/main.cpp:685-728`, present after `scripts/fetch-artifacts.sh` has fetched and extracted the archive) line-for-line and
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
    -> period n: 4^n times the honest target, until the pow limit clamps it
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
τ = 2016/2015 × 600 = 600.2978 s   (~+0.0496%, a hair SLOW, at every retarget)
```

A naive reading of the constants gives 600 s (`1209600 / 2016`), and dividing the other way gives
599.7 s (`2015/2016 × 600`); the ported code gives neither. Verified against the ported function (a
naive 600 s window is not the fixed point — the retarget returns a harder target; a 600.2978 s window is
exactly stable). The walk runs on a real index chain (`BlockIndex` with `pprev`), not a counter.

## (B) Boundary-only measurement (the timewarp property)

`nActualTimespan` is `time(last) − time(first)` of the window, with nothing binding the last block of
one period to the first of the next (`main.cpp:706`). Majority hashpower can stamp the period-boundary
block with an inflated timestamp so each window *looks* far too long, forcing the maximal `×4`
difficulty drop per period (the clamp at `main.cpp:708-711`). Modelled here as the boundary forge: after
n forged periods the target is `4^n` times the honest one until the pow limit (`main.cpp:719-720`) clamps
it, while an honest chain is unmoved. The demo starts 1000× below the limit so that there is room to
move in both directions; that starting point is the demo's choice, and the figure it produces after
five periods (the clamp) is a property of the starting point, not of the code. **Has not fired on
Bitcoin mainnet** (needs a hashpower majority and is glaring); the point is only that the v0.1 code has
this boundary behaviour, latent in the executable.

## Why it's a MODEL

Ported to Python integers over Satoshi's exact constants (`nTargetTimespan`, `nTargetSpacing`,
`nInterval`, and `bnProofOfWorkLimit = ~uint256(0) >> 32`, compact `0x1d00ffff`). Honest boundary:
this is a **port** of `main.cpp:685-728`, not the original binary executing; its value is exhibiting
the fixed point and the boundary behaviour from the real constants. The lab's live engines
(`../../derivatives/validator-rs/src/difficulty.rs`, `../netnode/difficulty.py`) deliberately run a
short experimental retarget interval for the X-chains, so this module is where the *mainnet* 2016-block
fencepost is made explicit.

## Difficulty-1 target exactness + v0.1's nBits codec (section C)

The demo also nails the difficulty-1 target and its encoding: `SetCompact(0x1d00ffff)` decodes to
`0xFFFF·2²⁰⁸` (round-trips canonically), and the **expected hashes per block** is
`2²⁵⁶/(target+1) = 4,295,032,833` — **not** the round `2³²`. The gap is exactly `65536/65535`, the
well-known **pdiff-vs-bdiff** discrepancy (pool difficulty uses `2²⁴`, Bitcoin difficulty uses the real
`0xFFFF·2²⁰⁸`). The codec is `CBigNum::SetCompact` / `GetCompact` from v0.1's `bignum.h:257-282`, over
OpenSSL's MPI encoding: a four-byte length, then the magnitude, whose first byte's `0x80` bit marks a
negative number. v0.1 has no overflow flag; any exponent up to 255 decodes. *(Until 20 September 2026 this
module carried Bitcoin Core's later `arith_uint256::SetCompact`, with its negative/overflow triple and
its `size > 34` bound, and called it v0.1's; an adversarial review caught the substitution.)*

## Tests (`test_retarget.py`, 13)

The walk on a real chain spans 2015 intervals and is not a counter (a short chain fails); the
equilibrium 600.30 s, slower than 600, against the literal `1209600 / 2015` written in the test; naive
600 s is not the fixed point and goes harder, by exactly `2015·600 / 1209600`; 600.2978 s is exactly
stable; the clamp (`×¼`/`×4`); the timewarp (one forged boundary forces `×4`; iterated, `4^n` until the
pow limit clamps, the honest chain unchanged); the pow-limit floor; the module's constants against the
literals in the test and, when `extracted/bitcoin/src` is present, against the January 2009 `main.cpp`
and `main.h` themselves; the difficulty-1 target / nBits round-trip; the exact `4,295,032,833` expected
hashes (pdiff-vs-bdiff); the MPI sign bit and the absence of an overflow flag.

```bash
python retarget.py     # the demo above
python -m pytest       # 13 passed
```

## Boundary

MODEL; objective source port of `main.cpp:685-728` and `bignum.h:257-282`; no chain privileged; not a
live-exploit claim (timewarp needs majority hashpower and has not run on Bitcoin mainnet). It is a
*tool*, not authority (`common/AUTHORITY.md`).
