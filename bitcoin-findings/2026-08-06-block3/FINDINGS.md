# Block 3 — the Bitcoin chain (genesis 00000000ad12f3ec…)

Mined **2026-08-06 01:40:22 UTC** (07:10 IST). Verified from the raw `blk0001.dat`.

```
height 0  00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a  nonce   33394338
height 1  000000007beb32b8380089595a91261a5ce4fbd4ece0cd661683cb1ce81e407c  nonce  895691393
height 2  000000001690a604f122ddf97c77d2580535fde2b2d700dc8a4478aea7ed75d5  nonce 1510572694
height 3  00000000428303928c985745792c7ad7644cb5f310b417263a66108fa7f49dcf  nonce  612491648
          merkle/nTime in the file; nBits 0x1d00ffff throughout; magic f00ba726
```

All four link; **all four satisfy their proof-of-work target** (checked against the difficulty
arithmetic, not by eye). 947 bytes.

## Binding

```
process started   2026-08-06 00:43:18 UTC   pid 5984
PRE  binding      2026-08-06 00:43:56 UTC
block 3 nTime     2026-08-06 01:40:22 UTC   <-- inside the bracket
POST binding      2026-08-06 01:44:16 UTC
bitcoin.exe       c3f15fc5b7bd80f4d08fe5ff356256214734eb1a3e4a7c953c9e8fc8453d2c7d
                  bitcoin_exe_matches_oracle = true, both phases
```

Same pattern as block 2: the block's own timestamp falls **between two captures of one live
process**, each bound to the reproducible v0.1.3 binary.

`NEXT-SESSION_block4_pre.json` is the binding taken after relaunching — it belongs to the block-4
session and is kept here only so it is not lost to the next overwrite.

## Interval — and what it does NOT measure

```
genesis -> 1   28.2 h
1 -> 2         23.9 h
2 -> 3          1.3 h
```

**These are wall-clock gaps between block timestamps, NOT mining time.** The miner is run
intermittently: the operator stops the client between blocks to take the post binding, exit cleanly,
copy the wallet and chain files, and restart. Idle periods are therefore folded into every interval
above.

*An earlier version of this file described the 1.3-hour gap as "ordinary variance, not a change in
hashrate". That was wrong — it assumed continuous mining. Nothing here supports any statement about
hashrate, and the intervals should not be read as inter-block times in the usual sense.*

What can be said: each block required roughly 2^32 hashes at difficulty 1 on a single-threaded
miner, and the elapsed *mining* time per block is not recorded by this evidence set.

**NOT money.**
