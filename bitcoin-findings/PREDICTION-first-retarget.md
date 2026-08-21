# Prediction — the first difficulty retarget, height 2016

**Written 21 August 2026, at height 272 — roughly 71 to 113 days before the event.**
Published in advance so it can be judged, not explained afterwards. Every number
below is derived from the released v0.1 source and the chain's own captured bytes.

---

## The prediction, in one line

> **The first retarget will change nothing. `nBits` will remain `0x1d00ffff`.**

It will be *computed*, logged by the client as a `RETARGET *****` event, and then
discarded by a clamp — the chain's difficulty is already at its floor.

## Why, from the released source

`GetNextWorkRequired()` in `derivatives/bitcoin/src/main.cpp` (unmodified 2009 code):

```c
const unsigned int nTargetTimespan = 14 * 24 * 60 * 60;   // two weeks
const unsigned int nTargetSpacing  = 10 * 60;
const unsigned int nInterval       = nTargetTimespan / nTargetSpacing;   // 2016

if ((pindexLast->nHeight+1) % nInterval != 0)
    return pindexLast->nBits;                    // only every 2016 blocks

const CBlockIndex* pindexFirst = pindexLast;
for (int i = 0; pindexFirst && i < nInterval-1; i++)   // <-- 2015, not 2016
    pindexFirst = pindexFirst->pprev;

unsigned int nActualTimespan = pindexLast->nTime - pindexFirst->nTime;
if (nActualTimespan < nTargetTimespan/4) nActualTimespan = nTargetTimespan/4;
if (nActualTimespan > nTargetTimespan*4) nActualTimespan = nTargetTimespan*4;

bnNew.SetCompact(pindexLast->nBits);
bnNew *= nActualTimespan;
bnNew /= nTargetTimespan;

if (bnNew > bnProofOfWorkLimit)                  // <-- the clamp that decides this
    bnNew = bnProofOfWorkLimit;
```

Three facts settle it:

1. **The trigger.** `(height+1) % 2016 == 0` first holds at `pindexLast->nHeight = 2015`,
   so the retarget computes the `nBits` **for block 2016**.
2. **The off-by-one.** The walk back is `nInterval-1 = 2015` blocks, so the measured
   span is `nTime(2015) − nTime(0)` — 2015 intervals, not 2016. This is the original
   "off-by-one" present in the 2009 code and preserved here unmodified. It biases the
   measurement slightly, and on this chain it is irrelevant (see below).
3. **The clamp.** This chain has always mined *slower* than the 10-minute target, so
   the ratio pushes the target **upward** (difficulty down) — but difficulty is already
   `0x1d00ffff`, the proof-of-work limit. `bnNew` is clamped straight back to it.

## The numbers, from the chain's own bytes

Captured at height 272, 2026-08-21:

```
genesis nTime            1785781375   (2026-08-03)
elapsed to height 272    1,527,996 s = 17.7 days over 272 blocks
observed mean spacing    93.6 min/block      (target: 10 min)
recent 100-block mean    59.0 min/block
```

Projecting to height 2015 at each rate:

| assumed rate | height 2015 around | nActualTimespan | vs 14-day target | after bounds |
|---|---|---|---|---|
| 93.6 min/blk (all-time) | **2026-12-12** | 131.0 days | 9.4× | clamped to 56 days (4×) |
| 59.0 min/blk (recent) | **2026-10-31** | 89.1 days | 6.4× | clamped to 56 days (4×) |

Either way the timespan is far past the 4× bound, so `nActualTimespan` becomes
exactly `nTargetTimespan*4`, the new target is `old × 4`, and `old` is already the
limit — so the clamp returns `0x1d00ffff` unchanged.

**This conclusion is robust.** It does not depend on the projected date, the mining
rate, the off-by-one, or how many miners are running. Any spacing slower than
10 minutes produces it. Only a chain mining *faster* than 10 min/block for 2015
consecutive blocks could move `nBits` — which at difficulty 1, with the hash rates
observed here (~1.1 MH/s for `BITCOIN-NODE-1`, ~4 MH/s for the external miner when
it runs), will not happen by accident.

## What would falsify this

- `nBits` at block 2016 is anything other than `0x1d00ffff`.
- The retarget triggers at a height other than 2016.
- The client measures a span other than `nTime(2015) − nTime(0)`.
- A sustained mining rate faster than 10 min/block appears before height 2015 —
  which is possible if enough hash power joins, and would make this prediction
  wrong for an interesting reason rather than a boring one.

## Why bother predicting a no-op

Because "nothing happens" is a *result*, and one that is easy to assert after the
fact and impossible to check. Stating it in advance, with the source lines and the
arithmetic, makes it falsifiable. It also records the first exercise of a consensus
path this chain has never taken: 2,016 blocks in, the retarget code will finally run,
and the honest expectation is that it will run correctly and change nothing.

The block that triggers it — height 2016 — is worth capturing when it arrives:
the client's own `RETARGET *****` debug output will show `nActualTimespan` before and
after bounds, and the before/after `nBits`. That log line is the evidence this
prediction should be judged against.

---

*Recorded at height 272. Related: [`2026-08-21-first-reorganization/`](2026-08-21-first-reorganization/FINDINGS.md)*
