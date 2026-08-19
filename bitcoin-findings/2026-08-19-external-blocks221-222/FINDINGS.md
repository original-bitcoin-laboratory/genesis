# Blocks 221–222 — the first blocks mined outside the client, and the append-only proof extended through an external store

**Observed 19 August 2026, over the wire and through an external node** — not a
`BITCOIN-NODE-1` capture round. The chain was downloaded raw from the public seed
(`bitcoin.bitcoin-lab.org:18026`, v0.1 handshake, `getblocks` from the genesis locator,
`getdata` for every block) and independently re-parsed; two datadir captures from an
unmodified released client run *outside* the laboratory VM corroborate it. Every number
below was re-derived from raw bytes, not read from any node's reporting.

---

## The chain, parsed independently

```
blocks parsed              225        heights 0-224 (222 at first observation; 224 by close)
height 221                 00000000fc80fe4f27b59cafbf782f029f586151bd144115b3d5f1ee360d088b
height 222                 0000000055cddf6e969747b574d17435af0799c839a3f149e020745b69419fa0
prev-hash linkage breaks   0
nBits                      0x1d00ffff at every height -- the retarget has still never moved
```

## ★ The payee table — one repeated payee in 224 blocks, and it is the finding

Coinbase output keys across heights 1–224, extracted from the raw transactions:

```
distinct coinbase payees        223
payees appearing exactly once   222      the client mints a key per block, as v0.1 does
payees appearing twice          1        04c0414cfdcc0098...  -- the agent's genesis key
  at heights                    221, 222
```

**Every laboratory-mined block pays a freshly minted wallet key. Heights 221 and 222 pay
the genesis key** — the key that speaks for the chain's author-agent, used once at height 0
and never since. The miner of these two blocks paid its entire subsidy to the agent's key
and kept nothing. That payee anomaly is the chain-visible signature of what happened, and
it is readable by anyone straight off the bytes.

## The two blocks, in full

```
height 221   nTime 1787136965 = 2026-08-19T10:56:05Z   nNonce 2757362010
height 222   nTime 1787138996 = 2026-08-19T11:29:56Z   nNonce 2885682098
```

Both coinbase scriptSigs are exactly 98 bytes: `4c 60` (OP_PUSHDATA1, 96) followed by a
96-byte payload beginning `CHRN` — an anchor commitment of the Chronology Protocol
(github.com/machine-native/chronology-protocol), parsed here from the raw bytes:

```
height 221   CHRN v1  flags 0x0003  epoch 0  sha256 7270814b43cb2404...
height 222   CHRN v1  flags 0x0003  epoch 1  sha256 4dc9b6343f7ebd08...
```

Under the Jan09 rules these are ordinary coinbases (scriptSig between 2 and 100 bytes,
content unconstrained); the client validated and relayed them like any others. **Bitcoin
was not patched for chronology semantics** — the anchoring project is a wire client of
this chain, nothing more. Two earlier candidates with valid proof-of-work lost their
height races to `BITCOIN-NODE-1` and are disclosed in that project's own acceptance
record, not hidden.

## ★ The append-only proof — fifth consecutive round, first through an external store

Three `blk0001.dat` stores now exist from two operators' machines: this laboratory's
2026-08-14 cold capture, and two captures from an unmodified v0.1.5 client
(`bitcoin.exe` sha256 `c3f15fc5b7bd80f4...`, the published release binary) run outside
the VM and fed the chain over the wire:

```
lab capture 2026-08-14 (h0-121)      27,261 B   sha256 ebf447f0635338c0...
external capture A     (h0-221)      49,678 B   sha256 5a19fc5677acd328...
external capture B     (h0-224)      50,440 B   sha256 c7e2b521a57eee1a...

sha256(A's first 27,261 bytes)  ==  sha256(lab capture entire)     PREFIX HOLDS
sha256(B's first 49,678 bytes)  ==  sha256(A entire)               PREFIX HOLDS
```

**Nothing before height 121 was rewritten between the laboratory's own capture and an
independently synced external store, and nothing before 221 was rewritten as the chain
grew past it.** The property has now held five consecutive rounds, and for the first time
it is established across stores produced by different runs of the client on a machine the
mining VM has never touched.

## Attribution, stated exactly

What the bytes show: two blocks with valid difficulty-1 work, CHRN anchor coinbases, and
the genesis-key payee, accepted and buried by this chain (heights 223–224 are ordinary
`BITCOIN-NODE-1` blocks with fresh payees again — the VM built on the external blocks
without ceremony, which is the whole protocol working).

What rests on disclosure: the miner was the Chronology Protocol's anchor toolchain,
**operated by the same person who operates this laboratory** (parthod0x). These are the
first blocks mined outside the laboratory's own client — a first external
*implementation*, **not** yet a first external *party*. The distinction is the finding's
honest edge and it is stated rather than implied away. Operator diversity remains zero;
implementation diversity on the mining side is now real (netnode seed, 2009-derived
client, and an independent Python/C toolchain have all now produced or validated blocks
on this chain).

## Limits

- Difficulty-1 work is real but small; nothing here claims security margin.
- This is a wire-observation round: no pre/post binary bindings exist for the external
  miner, and none are claimed. The chronology project's own evidence (PQ-signed
  checkpoints, offline-verifiable bundles, OpenTimestamps sidecars) carries that side.
- The seed and the VM are still operated by the same person as the external miner. The
  first genuinely third-party block remains unmined, and remains open to anyone.

## Files

```
block-221.hex   raw block, height 221, as received over the wire
block-222.hex   raw block, height 222, as received over the wire
SHA256SUMS      generated from the files in this directory
```

Related: [previous round](../2026-08-14-blocks64-121/FINDINGS.md) ·
[`CORRECTIONS.md`](../CORRECTIONS.md) ·
the anchoring project's own evidence: github.com/machine-native/chronology-protocol
(`live/anchor-evidence/ACCEPTANCE.md`, `live/anchor-evidence/SANDWICH-ACCEPTANCE.md`)
