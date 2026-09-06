# Blocks 298–731 — 434 blocks, five more external blocks, and a pre-binding that is not this run's

**Captured 22 August – 6 September 2026** on `BITCOIN-NODE-1`. The chain is now **732 blocks,
heights 0–731**. Every number below was re-derived from the captured bytes by
[`verify/verify_capture.py`](../../verify/verify_capture.py), not read from the node's own reporting.

⛔ **This is the first capture in the series that does not pass every check. Read §"The binding"
before relying on it.** 12 checks passed, 1 failed.

---

## The chain, parsed independently

```
blocks in the file         734
on the ACTIVE chain        732        heights 0-731
OFF the active chain         2        the same two retained since 19 August
height 0                   00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a
tip                        00000000604d43ff9e21d18dd8732f7218615ee08c8de25905df12aba3cb437a
tip time                   1788706267 = 2026-09-06T14:51:07Z
prev-hash linkage breaks   0
proof-of-work failures     0          every header hash below its own nBits target
merkle roots recomputed    734/734    from each block's own transactions
nBits                      0x1d00ffff at every height -- the retarget has still never moved
timestamps monotonic       yes        0 non-monotonic on the active chain
stray bytes outside a framed block    0
```

**The consensus side of this capture is intact.** Everything the chain itself asserts — linkage,
work, merkle roots, difficulty, ordering — verifies from the bytes.

## Cadence

```
this round      434 blocks     297 tip 2026-08-22T18:50:38Z -> 731 tip 2026-09-06T14:51:07Z
                               356.0 h, 49.2 min/block
whole chain     731 blocks     812.5 h, 66.7 min/block
```

⇒ The round ran roughly **1.9× faster than the chain's lifetime average** and faster than any
previous round. `nBits` has never moved, so this is a statement about how much work was pointed at
the chain over those fifteen days, not about difficulty.

## ⛔ The binding — the one check that failed, and what it costs

```
pid                pre 7508                        post 7508
process started    pre 2026-08-22T17:39:18.3974910Z   post 2026-08-22T19:15:13.8880450Z
run label          pre 2026-08-22-blk296onward        post 2026-09-06-blk298onward
fields differing   captured_utc, phase, process, run
```

**The `pre` record in this capture is a byte-identical copy of the block-297 run's** (sha256
`36dfcdbaa6baefa661892a231d756d1a…` in both directories). It describes a process created at
17:39:18; the post record describes one created at 19:15:13. **They are different processes that
happen to share a pid**, because the operating system reuses pids.

⇒ **What this capture still establishes.** The post-binding is intact: `bitcoin.exe` hashes to
`c3f15fc5…`, matching both the oracle and the on-disk binary. The chain parses, links and verifies
from genesis to tip. Heights 1–731 are identical to the public seed.

⇒ ⛔ **What it does NOT establish.** That the binary was unchanged *across* this run — which is the
single thing a pre/post pair exists to show. **That claim must not be made for heights 298–731.**

⚠️ **Nothing can repair this after the fact.** A pre-binding cannot be back-fitted to a run that has
already finished; the same rule this project applied to block 4 in August applies here. The next
run must capture its own `pre` before the node starts.

### ★★ The verifier passed this, and the defect was in the check

`verify_capture.py` reported **`ok  the SAME running process is bound at both ends`** — while
printing `fields differing pre->post: … process, run` four lines above. It contradicted itself on
one screen and scored the run 13/13. The check compared **pid alone**:

```python
chk("the SAME running process is bound at both ends", pid_a is not None and pid_a == pid_b, ...)
```

A pid is a *proxy* for process identity, not process identity. `create_time` does not move for a
given process and was sitting unread in the same JSON. **Corrected 7 September to compare pid AND
create_time.**

⚠️ **The correction was checked against all fourteen captures before it was believed**, because a
fix that fails everything is a broken checker rather than a finding: **10 pass, 3 fail, 1 has no
binding pair.** And two of those three (`29-50`, `61-63`) were *already* failing on differing pids —
the node was restarted mid-run. **So the correction found one case, not three.** Overstating it
would be the same error as the check itself.

## ★ Who mined what — the external miner is now a recurring participant

```
heights paying the AGENT genesis key
  [0, 221, 222, 253, 269, 298, 322, 479, 530, 628]
                          ^^^^^^^^^^^^^^^^^^^^^^^  new this round
coinbase outputs with a 65-byte key    732
distinct payees                        723
```

All five new heights carry a `CHRN` scriptSig marker, the same external miner recorded in August.
**It has now produced nine blocks rather than four**, spread across the round rather than clustered.

⇒ This is a fact about the chain, not a defect — the chain is open and the rule chose these blocks
like any others. It is recorded because the previous rounds' documentation described the external
miner as a small August episode, and that description is no longer accurate.

## Network behaviour

```
debug.log lines            519,444
ProcessBlock: ACCEPTED     732        cumulative, and counts blocks RECEIVED too
exceptions                 0
REORGANIZE                 0
InvalidChainFound          0
error lines                258        241 send error (peer dropped socket)
                                       17 GetMyExternalIP (dead 2009 host)
```

## Cross-check against the public seed

The DigitalOcean seed `bitcoin.bitcoin-lab.org:18026` was asked for its inventory over the wire. It
advertised **734 block hashes, heights 1–734**:

```
heights 1-731 identical      SAME CHAIN, no fork
seed ahead by 3 blocks       heights 732-734, mined after this capture was taken
```

⇒ The operated node and the captured file agree on every block they both hold.

## The wallet

688,128 B, sha256 `fbff522dc958127b…`, **byte-identical** to the live `datadir/wallet.dat`.

`wallet_custody.py`: 10,220 candidate blobs, **723 valid points on secp256k1**, 722 of them coinbase
payees covering heights 1–731. **The agent's genesis key is not in it.** Separation holds.

⚠️ **The 723rd point is not necessarily an unused key.** As the block 122–295 findings record, a
"is this a point on secp256k1?" scan also matches the curve's own **generator point G**, which sits
in a wallet file as a constant rather than as anybody's key. The residual of one is consistent with
G, with a minted-but-unspent key, or with both offsetting — this capture does not distinguish them,
and no claim rests on which it is.

## Limits, stated plainly

- ⛔ **The binary is not bound across this run.** See above. This is the capture's real limitation
  and it is not recoverable.
- The debug log's counters are **claims of the log**. Every consensus statement above comes from
  parsing `blk0001.dat`.
- **434 blocks over fifteen days is one node's record of one chain.** The seed comparison is the
  only independent confirmation here, and it confirms the blocks, not the process that made them.
- Wallet files are **Tier 1** and live only in the cold backup. Nothing in this directory contains
  key material.

## Files

The evidence set is sealed under
`OBL-BACKUP/04-evidence/bitcoin-chain-evidence/2026-09-06-blocks298-731/SHA256SUMS` (137 files).
This directory carries the two binding records — **including the mis-copied `pre`, kept exactly as
it shipped so the defect stays visible** — this document, and their own `SHA256SUMS`.

**NOT money.**
