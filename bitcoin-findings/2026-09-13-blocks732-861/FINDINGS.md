# Blocks 732–861 — 130 blocks, a tenth external block, and a client restarted mid-run

**Captured 6–12 September 2026** on `BITCOIN-NODE-1`. The chain is now **862 blocks, heights
0–861**. Every number below was re-derived from the captured bytes by
[`verify/verify_capture.py`](../../verify/verify_capture.py), not read from the node's own
reporting.

⛔ **13 checks passed, 1 failed.** The failure is a different one from last round's and is described
in §"The binding". Read it before relying on the binary claim.

---

## The chain, parsed independently

```
blocks in the file         864
on the ACTIVE chain        862        heights 0-861
OFF the active chain         2        the same two retained since 19 August
height 0                   00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a
tip                        00000000d2f58d7b022499f07fb6c4c8cb507912412bf0c0052abcdcbcfae8de
tip time                   1789237865 = 2026-09-12T18:31:05Z
prev-hash linkage breaks   0
proof-of-work failures     0          every header hash below its own nBits target
merkle roots recomputed    864/864    from each block's own transactions
nBits                      0x1d00ffff at every height -- the retarget has still never moved
timestamps monotonic       yes        0 non-monotonic on the active chain
stray bytes outside a framed block    0
```

**The consensus side of this capture is intact.** Linkage, work, merkle roots, difficulty and
ordering all verify from the bytes.

## Append-only

```
previous capture      164995 B  sha256 41cc2bb9ae4f0acbab4061453bb6c0f8df7e6c4d1a6f6694d071be1a3a1abaf3
this capture          194101 B
appended               29106 B
sha256(this[:164995]) 41cc2bb9ae4f0acbab4061453bb6c0f8df7e6c4d1a6f6694d071be1a3a1abaf3
```

**The previous capture is a byte-exact prefix of this one.** Nothing earlier was rewritten.

## Cadence

```
this round      130 blocks     731 tip 2026-09-06T14:51:07Z -> 861 tip 2026-09-12T18:31:05Z
                               147.7 h, 68.2 min/block
whole chain     861 blocks     960.1 h, 66.9 min/block
```

⇒ This round ran at **essentially the chain's lifetime average**, and materially slower than the
previous round's 49.2 min/block. `nBits` has never moved, so this says how much work was pointed at
the chain over these six days, not anything about difficulty.

## ⛔ The binding — the one check that failed

```
pid                pre 8188                           post 9988
process started    pre 2026-09-06T16:43:30.7278350Z   post 2026-09-09T07:51:50.0487660Z
bitcoin.exe        pre c3f15fc5b7bd80f4d08fe5ff356256214734eb1a3e4a7c953c9e8fc8453d2c7d
                   post c3f15fc5b7bd80f4d08fe5ff356256214734eb1a3e4a7c953c9e8fc8453d2c7d
on-disk exe        c3f15fc5b7bd80f4d08fe5ff356256214734eb1a3e4a7c953c9e8fc8453d2c7d
fields differing   captured_utc, phase, process
```

**The client was restarted on 9 September.** The pre-binding describes one process and the
post-binding another, so the run is not bracketed by a single live process.

⇒ **What still holds:** both captures, and the executable on disk, carry the *same* digest and it
matches the reproducible release binary. **The binary is established for the whole run.**

⇒ **What does not:** that one process produced every block. The blocks divide at the restart, and
there is a 13.6-hour gap across it with no block in it:

```
h=732        arrived over the network -- see below; predates both processes
h=733..752   first process     last block before the restart  2026-09-08T19:38:43Z
h=753..861   second process    first block after it           2026-09-09T09:14:36Z
```

⚠️ **This is a different defect from last round's.** Round 298–731 shipped a `pre` binding that was
a byte-identical copy of an earlier run's. **That did not recur** — both bindings here are distinct
captures of distinct processes. The limitation this time is a real restart, recorded rather than
smoothed over.

## The external miner produced a tenth block

```
heights paying the AGENT genesis key   [0, 221, 222, 253, 269, 298, 322, 479, 530, 628, 732]
```

**Block 732 is new to that list**, so the external miner has now produced **ten** blocks. Every one
of the ten carries a `CHRN` marker in its coinbase scriptSig; height 0 carries the genesis headline
instead; no other block on the chain carries a text marker at all.

⇒ **Block 732's own timestamp is 2026-09-06T16:09:38Z — 34 minutes before this run's first client
process started.** It was received over the network, not mined here. That is what an external miner
looks like from inside one node, and it is why the block count of a round and the number of blocks
a node *mined* are different quantities.

## Custody

```
coinbase outputs with a 65-byte key   862
distinct payees                       852
payees appearing more than once         1   (the agent key, 11 times)
```

The run's wallet holds a key for **every coinbase payee from height 1 to 861 except the agent's**.
**The agent's genesis key is not in it.** Separation holds, and it was checked rather than assumed:
the backed-up key multiplies to exactly the pubkey those eleven coinbases pay, and to the agent's
published address.

## Independent confirmation

The public relay — reachable at the chain's DNS name — was probed over the chain's own P2P protocol
on 13 September. **Its genesis matches, its block locator resolves entirely onto this chain, and its
active chain height is 861 with the identical tip hash.** There is no fork, and the relay holds
every block in this capture.

⚠️ **A mid-sync reading is not a state.** An earlier probe the same day put the relay's tip at
height 757 and that was reported internally as "104 blocks behind". It was catching up at the time.
**A point-in-time measurement of a converging process says nothing about where it settles**, and the
second probe is the one that means anything.

## The log

```
lines                      566699
ProcessBlock: ACCEPTED     862     <- CUMULATIVE, and counts blocks RECEIVED too
exceptions                   0
REORGANIZE                   0
InvalidChainFound            0
error lines                271     246 peer-dropped sockets, 21 dead-2009-host IP probes,
                                   4 dead-2009-host IRC bootstraps
```

These are **claims of the log**. Every consensus statement above comes from parsing the chain file.

## Limits, stated plainly

- ⛔ **One process does not bracket this run.** See above. The binary is bound; the process is not.
- The 246 peer-drop errors are the relay connection cycling, not a consensus event. No
  reorganisation and no invalid chain was found at any point.
- The debug log's counters are **claims of the log**.
- **130 blocks over six days is one node's record of one chain.** The relay comparison confirms the
  blocks, not the process that made them.
- Wallet files are **Tier 1** and live only in the cold backup. Nothing in this directory contains
  key material.

## Files

The evidence set is sealed under the cold backup's own `SHA256SUMS` for evidence set
"2026-09-13-blocks732-861" (61 files). This directory carries the two binding records, this
document, and their own `SHA256SUMS`.

**NOT money.**

The chain's author "Satoshi Nakamoto" is an AI agent built in 2026 — a program, not a person, and not
the historical Satoshi; see `derivatives/bitcoin/CHRONOLOGY.md`.
