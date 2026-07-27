# Temporal consensus rules, executed — v0.1's block timestamps + tx finality

**Evidence level: `MODEL`.** Where [`../overflow/`](../overflow/) and
[`../script_limits/`](../script_limits/) execute the bounds v0.1 *lacked*, this executes two
"present machinery" rules v0.1 *had* — completing that column of
[`CONSENSUS_SURFACE.md`](https://github.com/original-bitcoin-laboratory/common/blob/main/conformance/CONSENSUS_SURFACE.md). Faithful ports of:

- **`GetMedianTimePast`** (`main.h:1086`, `nMedianTimeSpan = 11`) — median of the last 11
  block times.
- **The two block‑timestamp checks** — `CheckBlock` rejects a block more than **2h in the
  future** (`main.cpp:1164`); `AcceptBlock` rejects a block whose time is **not strictly
  after** the median‑past (`main.cpp:1206`).
- **`CTransaction::IsFinal` / `CTxIn::IsFinal`** (`main.h`) — transaction finality.

## What it shows

```
BLOCK TIMESTAMPS
  median-time-past of last 11 blocks : 1231009505
  block at mtp+1                      : accept=True
  block at mtp (not strictly after)   : accept=False
  block 3h in the future              : accept=False
TX FINALITY (best_height = 100000)
  locktime 0                          : final=True
  locktime 90000 (< height)           : final=True
  locktime 200000 (future height)     : final=False
  ... same, all inputs nSequence=MAX  : final=True
  locktime 500000000 (v0.1 = HEIGHT)  : final=False
```

## The finding: v0.1's `nLockTime` is height‑only

`CTransaction::IsFinal` returns true when `nLockTime == 0 || nLockTime < nBestHeight`, else
only if every input has `nSequence == 2^32-1`. Crucially, `nLockTime` is compared **purely as
a block height** — v0.1 has **no `LOCKTIME_THRESHOLD` (500000000)** to switch between
height‑locks and time‑locks (confirmed: 0 occurrences in the v0.1 source). So a value like
`500000000`, which modern Bitcoin reads as a Unix timestamp, v0.1 treats as a **block
height** — final only past that height. The height/time split is a later refinement, in the
same spirit as the other "not yet installed" refinements this lab maps.

## Tests (`test_temporal.py`, 12)

Median‑time‑past (sorted middle of 11; only the newest 11 count; fewer‑than‑11 and even‑count
upper‑median; order‑independence); the two block checks (exactly +2h ok, +2h+1s rejected;
strictly‑after‑median); finality (sequence override, locktime 0 / below‑height / future‑height
with and without the `nSequence` override, becoming final once height passes); and the
height‑only `500000000` finding.

```bash
python temporal.py     # the demo above
python -m pytest       # 12 passed
```

## Boundary

MODEL; line‑for‑line port of the v0.1 rules; not a live‑exploit claim (these are the rules the
origin *had*). A tool, never authority (`common/AUTHORITY.md`).
