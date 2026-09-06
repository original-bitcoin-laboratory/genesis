# Blocks 296–297 — two blocks, a clean binding pair, and the first wallet split

**Captured 22 August 2026** on `BITCOIN-NODE-1`. The chain is now **298 blocks, heights 0–297**.
Every number below was re-derived from the captured bytes by
[`verify/verify_capture.py`](../../verify/verify_capture.py), not read from the node's own reporting.

---

## The chain, parsed independently

`blk0001.dat` parsed directly against this chain's magic `f0 0b a7 26`:

```
blocks in the file         300
on the ACTIVE chain        298        heights 0-297
OFF the active chain         2        the same two retained since 19 August
height 0                   00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a
tip                        00000000b104e014af243351efacdab8966c56b7f07ab9e06b1a7a2e91871c22
tip time                   1787424638 = 2026-08-22T18:50:38Z
prev-hash linkage breaks   0
proof-of-work failures     0          every header hash below its own nBits target
merkle roots recomputed    300/300    from each block's own transactions
nBits                      0x1d00ffff at every height -- the retarget has still never moved
timestamps monotonic       yes        0 non-monotonic on the active chain
stray bytes outside a framed block    0
```

**13 checks passed, 0 failed.**

## Cadence

```
this round        2 blocks     295 tip 2026-08-22T15:04:50Z -> 297 tip 18:50:38Z
                               3.76 h, 112.9 min/block
whole chain     297 blocks     456.5 h, 92.2 min/block
```

⚠️ Two blocks is far too small a sample to say anything about difficulty or hash rate, and nothing
here should be read as a trend. `nBits` has not moved since genesis, so the cadence is a fact about
how much work was pointed at the chain during those 3.76 hours and nothing more.

## The binary that mined them — the strongest binding form

```
pid                pre 7508          post 7508
process started    17:39:18.3974910Z (both ends -- the SAME process)
bitcoin.exe        c3f15fc5b7bd80f4d08fe5ff356256214734eb1a3e4a7c953c9e8fc8453d2c7d
oracle             c3f15fc5b7bd80f4d08fe5ff356256214734eb1a3e4a7c953c9e8fc8453d2c7d
on-disk re-hash    c3f15fc5b7bd80f4d08fe5ff356256214734eb1a3e4a7c953c9e8fc8453d2c7d
fields differing   captured_utc, phase
```

⇒ **The pre and post records describe one process, running throughout**, and the binary it was
executing hashes to the oracle at both ends and again on disk. This is the complete form of the
claim, and it is worth stating plainly here because the *next* series does not have it.

## Who mined what

```
heights paying the AGENT genesis key   [0, 221, 222, 253, 269]
coinbase outputs with a 65-byte key    298
distinct payees                        294
```

Unchanged from block 295. Neither of the two new blocks was externally mined; both pay fresh
per-block keys from the node's own wallet, as v0.1 does.

## Network behaviour

```
debug.log lines            239,132
ProcessBlock: ACCEPTED     298        cumulative, and counts blocks RECEIVED too
exceptions                 0
REORGANIZE                 0
InvalidChainFound          0
error lines                78         62 send error (peer dropped socket)
                                      16 GetMyExternalIP (dead 2009 host)
```

Both error classes are the expected 2009-client behaviour against a 2026 internet and neither
touches consensus.

## Cross-check against the public seed

The DigitalOcean seed `bitcoin.bitcoin-lab.org:18026` was asked for its inventory over the wire
(version handshake → `getblocks` from a genesis-only locator → count the `inv`). It advertised
**734 block hashes** and **heights 1–297 are identical to this capture** — same chain, no fork.

## ★ The wallet — and the first time the two copies differed

```
wallet-clean-blk296onward-20260809.dat   286,720 B   50ccd0d6...
datadir/wallet.dat                       286,720 B   61d37063...   NOT identical
```

**Every previous round's clean copy was byte-identical to the live file. This one is not** — the
clean copy was taken at 00:36 local and the live file moved on until 00:41.

⇒ `wallet_custody.py` reads **the same key material from both**: 4,175 candidate 65-byte blobs,
**294 valid points on secp256k1**, 293 of them coinbase payees, covering heights 1–297 in each file
independently. The difference is Berkeley DB internal state, not keys.

⚠️ As the block 122–295 findings record, a "is this a point on secp256k1?" scan also matches the
curve's own **generator point G**, a constant in the file rather than anybody's key. The residual of
one point is consistent with G, with a minted-but-unspent key, or with both — nothing here
distinguishes them and no claim rests on which it is.

**Custody separation holds.** The agent's genesis key is in neither file. The payee heights absent
from the wallets are `[0, 221, 222, 253, 269]` — height 0 the agent's own key, and the four
externally-mined CHRN blocks that pay it.

## Limits, stated plainly

- **Two blocks prove nothing about the chain's behaviour over time.** They extend an append-only
  record; they are not a measurement.
- The debug log's counters are **claims of the log**, not evidence about the chain. Every consensus
  statement above comes from parsing `blk0001.dat`.
- The wallet files themselves are **Tier 1** and live only in the cold backup. Nothing in this
  directory contains key material.

## Files

The evidence set is sealed under
`OBL-BACKUP/04-evidence/bitcoin-chain-evidence/2026-08-22-blocks296-297/SHA256SUMS` (19 files).
This directory carries the two binding records, this document, and their own `SHA256SUMS`.

**NOT money.**
