# The first chain reorganization — height 264, 21 August 2026

**The chain replaced an accepted tip for the first time in its history.** Every prior
round reported `REORGANIZE 0`; that number is no longer zero. The cause is not a defect
— it is the arithmetic of a second miner finally arriving.

---

## What happened

```
06:17:47Z   an external miner submits a block for height 264
              0000000032580c2f20211b668bb643965dda2dff3a7621bf9797599d75de710c
              valid difficulty-1 work, nNonce 1780533975, CHRN epoch-3 coinbase
06:18:0xZ   the public seed advertises that block as its tip at height 264
              (getblocks from the genesis locator returns 264 hashes ending in it)
~later      BITCOIN-NODE-1 produces its OWN height-264 block
              00000000cda96f0eeff6d3202f446f5bb1fbcd02a46c45242a29a500419e7518
              and extends it to height 265
              000000003506989e31b94426d9aff5fc304290f21b33787affc01276cc5568d4
08:28-08:41Z the seed serves the VM's branch. Two blocks beat one; the external
              block is orphaned and off the active chain
```

Re-derived from the captured bytes at **08:41Z**, not from any node's reporting: the
active chain was 266 blocks, heights 0–265, linkage unbroken from the fixed genesis,
`nBits` still `0x1d00ffff` at every height. (The chain kept moving during this write-up
— by 09:19Z the VM had produced 266, 267 and 268 in roughly fifteen minutes, a burst
well above its long-run ~64 min average. A height stated in a document is a claim about
a capture time, never about now.)

## Why it happened, stated plainly

**Since 19 August 2026 this chain has had two independent miners.** The laboratory VM
mines continuously; the Chronology Protocol's anchor toolchain
(a separate implementation, on a separate machine) mines whenever it anchors a
checkpoint — that is how heights 221, 222 and 253 were produced. Two uncoordinated
miners at difficulty 1 with ~1-hour spacing will collide, and on 21 August they did.

Nothing about this is a failure of either implementation. Both blocks carry valid
proof-of-work for the same height; the network resolved it by the longest-chain rule,
exactly as the 2009 consensus code specifies. **The first reorganization on this chain
is therefore evidence that the consensus rule works, not that anything broke.**

## What it cost, and what it did not

```
lost      one block of difficulty-1 work by the external miner
          (its 50-coin coinbase, which paid the agent's genesis key, is void —
          orphaned coinbases pay nobody)
intact    every prior height. Heights 0-263 are untouched; the reorganization
          was one block deep and replaced only the contested tip
intact    the external miner's evidence: the checkpoint it was anchoring is
          unchanged, and was re-anchored onto the new tip. Its own record
          carries the correction rather than deleting the claim
```

⚠️ **The append-only property is not violated by a one-block reorganization at the
tip.** The property this laboratory has tested five rounds running is that *captured*
history is a byte-exact prefix of later captures. A block that was tip for two hours and
then lost a race was never part of a sealed capture. Nothing that any capture recorded
has been rewritten. **But the distinction now matters and did not before**, and any
future capture must be taken as a claim about a branch, not about the only branch.

## Limits

- We observed the seed advertising the orphaned block as its tip. **Whether
  `BITCOIN-NODE-1` ever accepted that block is not established here** — no log from
  the VM was captured for this event, and the honest reading is that the VM continued
  mining its own candidate, which is ordinary behaviour, not evidence of rejection.
- Depth 1. Nothing here measures reorganization risk at any greater depth, and at
  difficulty 1 with two miners deeper reorganizations are entirely possible.
- Both miners are operated by the same person. This is competition between two
  *implementations*, not between two parties.

## Files

```
orphaned-block-264.hex   the external miner's losing block, raw
                         sha256 44c9aa533af678fbfa17aadc05dee39dbeb2d5fc04c0779278002168e358ad1c
winning-block-264.hex    BITCOIN-NODE-1's block that took height 264
block-265.hex            the block that settled the race by extending it
SHA256SUMS               generated from the files in this directory
```

Related: [previous round](../2026-08-19-external-blocks221-222/FINDINGS.md) ·
[`CORRECTIONS.md`](../CORRECTIONS.md)
