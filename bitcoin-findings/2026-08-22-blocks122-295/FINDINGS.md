# Blocks 122–295 — 174 blocks, the first losing branch, and a verifier that cried fork

**Captured 14–22 August 2026** on `BITCOIN-NODE-1`. The chain is now **296 blocks, heights 0–295**.
Every number below was re-derived from the captured bytes by
[`verify/verify_capture.py`](../../verify/verify_capture.py), not read from the node's own
reporting.

---

## The chain, parsed independently

`blk0001.dat` parsed directly against this chain's magic `f0 0b a7 26`:

```
blocks in the file         298
on the ACTIVE chain        296        heights 0-295
OFF the active chain         2        <- new this round; see below
height 0                   00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a
tip                        000000009ac796005a0bb028edad243dee0ce6ff2fd6750b3170952668560d51
tip time                   1787411090 = 2026-08-22T15:04:50Z
prev-hash linkage breaks   0
proof-of-work failures     0          every header hash below its own nBits target
merkle roots recomputed    298/298    from each block's own transactions
nBits                      0x1d00ffff at every height -- the retarget has still never moved
timestamps monotonic       yes        0 non-monotonic on the active chain
```

### The append-only proof, fifth consecutive round

```
previous capture (blocks 64-121)  blk0001.dat   27,261 B
this capture                      blk0001.dat   67,152 B
appended                                        39,891 B

sha256(new file's first 27,261 bytes)  ebf447f0635338c0b0c645bd882853100ff7b424c14aae8662e8609c4fe24255
sha256(the previous file entire)       ebf447f0635338c0b0c645bd882853100ff7b424c14aae8662e8609c4fe24255
```

**The previous capture is a byte-exact prefix of this one.** Nothing before height 121 was
rewritten, reordered or re-signed — established by hashing, not by trusting the client.

---

## ★★ The first blocks this chain has ever discarded

Every prior round reported every block in the file as being on the chain. This one does not:

```
losing  00000000ccd47c6b542030a0609e7e2939dbac23ad9d1e50e23477ad9b9f450d   would-be height 219
        coinbase scriptSig  'L`CHRNrpKC$>H!}I+LjRdWG2-j]Jl66@Saic-'      pays the AGENT key
winner  00000000cd6121c17c3c0e1cd26e6ff40031b061b5aa30fae340dc4ffe013e83   height 219
        coinbase scriptSig  (empty)                                       fresh wallet key

losing  00000000eaa0fabf769b617429973096303bc282eddc47c5a12f3c8eede59b16   would-be height 220
        coinbase scriptSig  'L`CHRNrpKC$>H!}I+LjRdWG2-j]Jl66@Saic-'      pays the AGENT key
winner  000000004ccc5b55de9727622be0e2fb2ae17c4e994b504c1914e366a1ce6f7c   height 220
        coinbase scriptSig  (empty)                                       fresh wallet key
```

Both losers carry the **CHRN** marker of the Chronology Protocol's anchor toolchain — the second
miner that arrived on 19 August — and both pay the agent's genesis key. Both winners are the VM's,
with an empty scriptSig and a freshly minted wallet key. **So the external miner's first two
attempts on this chain lost, and its next four won** (heights 221, 222, 253 and 269).

⚠️ **What the timestamps do NOT say.** The losing blocks carry earlier `nTime` values than the
winners (10:05:41 vs 10:07:46; 10:36:30 vs 10:39:32). **A block's `nTime` is asserted by its miner,
not observed by anyone**, so this is not evidence about arrival order and no first-seen claim is
made from it.

⇒ **The client retained both losers as side branches and never reorganised.** That is correct v0.1
behaviour, and it is the rule choosing — not a defect.

### ★ Why `REORGANIZE 0` is true here even though this chain has had a reorganisation

[The 21 August round](../2026-08-21-first-reorganization/FINDINGS.md) documents a reorganisation at
height 264. This log reports `REORGANIZE 0`, and both are correct: **the VM's branch is the one that
won at 264, so the VM had nothing to reorganise — the public seed did.** The externally-mined 264
block is not in this capture at all; the VM never accepted it. A reorganisation is a fact about a
particular node's view, never about "the chain" in the abstract.

## ★ Two more agent-key blocks than were previously recorded

```
heights paying the agent's genesis key   0, 221, 222, 253, 269
previously documented                    0, 221, 222
new in this capture                      253, 269
```

The [external-blocks round](../2026-08-19-external-blocks221-222/FINDINGS.md) recorded 221 and 222.
The external miner has since taken two more, at 253 and 269. **The agent's key has now been paid by
four blocks it did not mine** — all four externally produced, none by this VM.

## Cadence

```
genesis -> height 121   121 blocks over 260.3 h  = 129.1 min/block
THIS round (122-295)    174 blocks over 192.4 h  =  66.3 min/block
overall since genesis   295 blocks over 452.7 h  =  92.1 min/block

blocks per day this round
  2026-08-15  21     2026-08-18  18     2026-08-21  24
  2026-08-16  22     2026-08-19  29     2026-08-22  11  (partial)
  2026-08-17  25     2026-08-20  23
```

**Difficulty is 1 and unchanged**, so the cadence is a statement about the VM's hash rate plus a
second miner's contribution — not about the retarget rule, which this chain has still never
exercised.

## The binary that mined them — the strongest binding form

```
pid                        1664                              IDENTICAL pre and post
create_time                2026-08-14T17:57:23.2765150Z      IDENTICAL pre and post
binding_method             live-process-image
bitcoin.exe sha256         c3f15fc5b7bd80f4d08fe5ff356256214734eb1a3e4a7c953c9e8fc8453d2c7d
matches oracle             true, at BOTH ends
captured pre               2026-08-14T17:57:49Z
captured post              2026-08-22T16:23:03Z
fields changed pre->post   phase, captured_utc -- and nothing else
```

★ **Both the process identifier and its creation time are identical at both ends, bracketing the
run.** This binds the *running process* to the image, not merely a file to a hash — the distinction
the obl-ledger correction turned on. The on-disk `bitcoin.exe` in this capture re-hashes to that
value.

## Network behaviour

```
log lines                  238,055
exceptions                 0
REORGANIZE                 0        (see above -- true of this node)
InvalidChainFound          0
ERROR lines                77
  62  "send error"                     peers dropping sockets, ordinary P2P churn
  15  "GetMyExternalIP() ... failed"   the dead 2009 IP-discovery hosts, as before
```

⚠️ **`ProcessBlock: ACCEPTED` appears 296 times and that is NOT this round's block count.** The log
is cumulative across sessions and `ACCEPTED` also counts blocks received from a peer. **The 174 is
derived from the file.** The log is a narrative; the chain is the record.

## Cross-check against the public seed — and a verifier that cried fork

`bitcoin.bitcoin-lab.org:18026` → `168.144.27.117`, v0.1 handshake then `getblocks` from the genesis
locator:

```
peer protocol version      101
inv returned               295 block hashes  (heights 1-295)
compared to this capture   heights 1-295 IDENTICAL
verdict                    same chain, no fork; the seed is EXACTLY level with the capture
the two losing blocks      NOT advertised by the seed -- they are not on its active chain either
```

> ### ★★ The probe reported a fork that did not exist
>
> On first run, `probe_seed_node.py` printed
> **`!! FORK: heights [220..224] differ. The seed is NOT on our chain.`**
>
> There was no fork. `local_chain()` walked `blk0001.dat` **in file order** and called the k-th
> block "height k". That was correct for every round through 64–121 because **every one of those
> captures had zero blocks off the active chain.** This capture has two, and from the first one
> onward every height was shifted by one — and a shifted comparison is indistinguishable from a
> fork.
>
> ⇒ **A tool that has only ever run on clean input has not been shown to handle the real case.** And
> the failure went in the dangerous direction: not a silent pass, but a **false alarm about the one
> property this chain most needs to be able to assert.** A verifier that cries fork will eventually
> be believed, or — worse — ignored.
>
> Fixed: the local chain is now assembled by prev-hash linkage from the fixed genesis, taking the
> deepest branch at a fork, and the count of off-chain blocks is reported rather than silently
> absorbed into the height numbering.

## The wallet — custody separation, re-verified

```
0x04-prefixed 65-byte blobs in the wallet    4,079   raw byte patterns
valid points on secp256k1                      292   the actual keys
coinbase payees on the chain                   296   one per block
wallet keys that ARE coinbase payees           291   heights 1-295, minus the four CHRN blocks
wallet keys not yet used                         1   v0.1 mints a key at find-time
```

⚠️ **This count was 293 until two tools were made to disagree.** A naive "is it a valid point on
secp256k1?" scan counts the curve's own **generator point G**, which sits in the wallet file as a
constant rather than as anybody's key. `verify/wallet_custody.py` said 293; the repository's
`generate_docs.py` said 292, because it already excluded G. **The disagreement is what found it —
a single tool would simply have been believed.** Both now exclude G and agree at 292.

> ### ★ The coinbase payees ABSENT from the miner's wallet are exactly the agent-key heights
> ```
> payee heights not present in the wallet :  0, 221, 222, 253, 269
> heights paying the agent's genesis key  :  0, 221, 222, 253, 269
> agent key present in the wallet         :  False   (both wallet files)
> ```
> **Two independent methods — a coinbase census over the chain, and a key census over the wallet
> bytes — produce the same set.** The key that speaks for the identity is held alone; the miner's
> wallet has never contained it.

`datadir/wallet.dat` and `wallet-clean-blk122onward-20260809.dat` are **byte-identical**
(`b42948fa0f349bb9…`), as are `datadir/blk0001.dat` and `blk0001-blk122onward-20260809.dat`
(`6b37b7fd8f7ec3d4…`).

**The wallet and the datadir are Tier 1 and are archived to the cold backup only.** Verified by
`git ls-files` across all ten repositories in this workspace: **zero** wallet, datadir, chain, log
or binary *data* files are tracked anywhere. (Six tracked paths match the word "wallet" — they are
`wallet.py`, `wallet.rs`, `nodewallet.py` and their tests: implementations, not data.)

## Limits, stated plainly

- **174 blocks at difficulty 1 prove liveness, append-only continuity and correct fork handling.
  They prove nothing about security margin**, which at difficulty 1 is negligible by construction.
- The seed agreeing is **one** independent witness, and it is one we operate. It is not a network.
- The two discarded blocks show the *rule* working on a two-block sample. They are not a study of
  fork behaviour.
- `ProcessBlock: ACCEPTED = 296` is a cumulative log figure and is deliberately not used as evidence.
- The 66.3 min/block cadence is a property of this VM plus a second miner. **It is not a protocol
  measurement.**
- Block `nTime` is miner-asserted. No arrival-order or first-seen claim is made anywhere above.

## Files

```
cold backup, evidence set "2026-08-22-blocks122-295"       81 files + SHA256SUMS, all re-hashed
  block122onward/datadir/          blk0001.dat, blkindex.dat, addr.dat, wallet.dat, database/
  block122onward/bitcoin-0.1.3/    bitcoin.exe, debug.log, db.log, capture_binding.ps1,
                                   the two binding JSONs
  block122onward/                  blk0001-blk122onward-*.dat, wallet-clean-*, pre/post JSON
  screenshots/                     66 PNGs, 2026-08-14 23:28 -> 2026-08-22 21:54
  SHA256SUMS                       generated after the copy, from the copies

this repository                    FINDINGS.md, SHA256SUMS, the two binding JSONs -- and nothing
                                   else. No chain data, no wallet, no logs.
```

**81 of 81 files re-hashed after the copy against their sources — 0 mismatches**, 57,207,176 bytes
in the evidence set. `sha256sum -c SHA256SUMS` verifies 81/81 from the manifest afterwards, and the
full verification was re-run **against the backup copy rather than the source**, passing 14/14.

Related: [previous round](../2026-08-14-blocks64-121/FINDINGS.md) ·
[external blocks 221–222](../2026-08-19-external-blocks221-222/FINDINGS.md) ·
[the first reorganization](../2026-08-21-first-reorganization/FINDINGS.md) ·
[`CORRECTIONS.md`](../CORRECTIONS.md) · `verify/verify_capture.py` · `verify/wallet_custody.py` ·
`verify/probe_seed_node.py`
