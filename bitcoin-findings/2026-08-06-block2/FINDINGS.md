# Block 2 — the Bitcoin chain (genesis 00000000ad12f3ec…)

Mined **2026-08-06 00:23:51 UTC** (05:53:51 IST) by `bitcoin-node-1`, after an unclean shutdown on
5 August interrupted the first attempt. Verified here from the raw `blk0001.dat`, not from the
client's display.

## The chain, parsed from the bytes

```
height 0  00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a   nonce      33394338
height 1  000000007beb32b8380089595a91261a5ce4fbd4ece0cd661683cb1ce81e407c   nonce     895691393
height 2  000000001690a604f122ddf97c77d2580535fde2b2d700dc8a4478aea7ed75d5   nonce    1510572694
          merkle 3f076b52f91c94c9e5c997832961cb282895e7b71b9fe5492107c1824faecb4b
          nTime  1785975831        nBits 0x1d00ffff        magic f00ba726
```

Every block's `prevblock` matches its predecessor's hash, and **every block satisfies its
proof-of-work target** — checked against the difficulty arithmetic, not merely by eye.

## What binds this block to a verifiable binary

```
process started      2026-08-06 00:05:14 UTC   pid 2268
PRE  binding         2026-08-06 00:18:12 UTC
block 2 nTime        2026-08-06 00:23:51 UTC   <-- inside the bracket
POST binding         2026-08-06 00:34:13 UTC
bitcoin.exe (both)   c3f15fc5b7bd80f4d08fe5ff356256214734eb1a3e4a7c953c9e8fc8453d2c7d
```

The block was minted **between two captures of the same live process**, both binding it to the
v0.1.3 binary. That binary is **reproducible**: rebuild it from the published 2009 archive and the
bytes hash to the same value. So "which program mined this block" is answerable by anyone, without
trusting us.

Blocks 0 and 1 were mined by v0.1.1, which is consensus-identical but not reproducible. **Block 2 is
the first block on this chain minted by a binary a stranger can rebuild.**

## Why the client reads "version 0.1.1 Alpha"

That is the 2009 source's own `VERSION = 101` (`serialize.h:22`), unchanged deliberately so nodes
built from any release interoperate. It is not our release number. See
`machine-satoshi/LICENCE-AND-ATTRIBUTION.md` (local).

## Files

| file | what it is |
|---|---|
| `blk0001.dat` | the chain at height 2, 724 bytes |
| `EXECUTED_BINARY_BINDING_…_pre.json` / `_post.json` | the live-process bindings bracketing the block |
| `screenshots/` | 11 captures, 06:04–06:16 IST: the post binding, clean exit, capture, relaunch, and the block-3 pre binding |
| *(wallet held separately)* | `01-keys-SECRET/bitcoin-chain-wallets/wallet-clean-blk2-20260806.dat` — **Tier 1, never publish** |

The earlier phase of the same day — the crash, the cold copy, the 0.1.1→0.1.3 switch, and block 2
being found at 05:53 — is in the sibling folder `2026-08-06-crash-recovery/` (44 screenshots).

Wallet copied from a **cleanly exited** client. v0.1 has no keypool: each block mints a new key
written at the moment it is found, so a backup predating a block does not contain its coins.

**NOT money.**
