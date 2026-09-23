# Blocks 862–1167 — 306 blocks, a quiet external miner, and a second mid-run restart

**Captured 13–22 September 2026** on `BITCOIN-NODE-1`. The chain is now **1,168 blocks, heights
0–1167**. Every number below was re-derived from the captured bytes by
[`verify/verify_capture.py`](../../verify/verify_capture.py), not read from the node's own
reporting.

⛔ **13 checks passed, 1 failed.** The failure is the same *kind* as last round's — the client was
restarted mid-run — and it is described in §"The binding". Read it before relying on the binary
claim.

---

## The chain, parsed independently

```
blocks in the file        1170
on the ACTIVE chain       1168        heights 0-1167
OFF the active chain         2        the same two retained since 19 August
height 0                  00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a
tip                       00000000444f083f730f9ee543405cfc44b93e65276e7cff88ff4ae0fc0944fc
tip time                  1790090780 = 2026-09-22T15:26:20Z
prev-hash linkage breaks     0
proof-of-work failures       0        every header hash below its own nBits target
merkle roots recomputed   1170/1170   from each block's own transactions
nBits                     0x1d00ffff at every height -- the retarget has still never moved
timestamps monotonic      yes         0 non-monotonic on the active chain
stray bytes outside a framed block    0
total coinbase            58,400 BTC over 1,168 blocks, 50.00 at every height
```

**The consensus side of this capture is intact.** Linkage, work, merkle roots, difficulty and
ordering all verify from the bytes.

## Append-only

```
previous capture      194101 B  sha256 4f2e1d9d094ed5a4b10400ccc20f94f8f1b328c36b572e36590ce2d0a514273b
this capture          262483 B
appended               68382 B
sha256(this[:194101]) 4f2e1d9d094ed5a4b10400ccc20f94f8f1b328c36b572e36590ce2d0a514273b
```

**The previous capture is a byte-exact prefix of this one.** Nothing earlier was rewritten.

## Cadence

```
this round      306 blocks     861 tip 2026-09-12T18:31:05Z -> 1167 tip 2026-09-22T15:26:20Z
                               236.9 h, 46.5 min/block
previous round  130 blocks     68.2 min/block
whole chain    1167 blocks    1197.1 h, 61.5 min/block
```

⇒ This round is **the fastest the chain has run over a full round**, and about a third quicker than
its lifetime average. `nBits` has never moved, so this says how much work was pointed at the chain
over these ten days, not anything about difficulty.

The four longest gaps between consecutive blocks this round were 6.20 h (h1091), 5.87 h (h862),
3.77 h (h1038) and 3.21 h (h1011) — the shape of a single miner whose host sleeps, not of a
difficulty effect.

## ⛔ The binding — the one check that failed

```
pid                pre 9392                           post 5340
process started    pre 2026-09-12T21:41:41.8629800Z   post 2026-09-15T06:27:04.7578540Z
captured           pre 2026-09-12T21:42:39.0466136Z   post 2026-09-22T15:48:43.1631430Z
bitcoin.exe        pre  c3f15fc5b7bd80f4d08fe5ff356256214734eb1a3e4a7c953c9e8fc8453d2c7d
                   post c3f15fc5b7bd80f4d08fe5ff356256214734eb1a3e4a7c953c9e8fc8453d2c7d
on-disk exe        c3f15fc5b7bd80f4d08fe5ff356256214734eb1a3e4a7c953c9e8fc8453d2c7d
fields differing   captured_utc, phase, process
```

**The client was restarted on 15 September.** The pre-binding describes one process and the
post-binding another, so the run is not bracketed by a single live process.

⇒ **What still holds:** both captures, and the executable on disk, carry the *same* digest and it
matches the reproducible release binary. **The binary is established for the whole run.**

⇒ **What does not:** that one process produced every block. The blocks divide at the restart:

```
h=862..945    first process    84 blocks   last before the restart  2026-09-15T04:21:21Z
h=946..1167   second process  222 blocks   first after it           2026-09-15T06:37:36Z
```

A 2.3-hour gap spans the restart, with no block in it.

⚠️ **The 298–731 defect did not recur, and that was checked rather than assumed.** That round
shipped a `pre` binding which was a byte-identical copy of an earlier run's. This round's `pre`
(`697df76a…`, pid 9392) and the previous round's `post` (`34857452…`, pid 9988) are different files
describing different processes. The limitation here is a real restart, recorded rather than
smoothed over.

## The external miner produced nothing this round

```
heights paying the AGENT genesis key   [0, 221, 222, 253, 269, 298, 322, 479, 530, 628, 732]
```

**That list is unchanged from last round.** Across 306 blocks the external miner produced **no
block at all**, so its total stands at ten. Every one of the ten carries a `CHRN` marker in its
coinbase scriptSig; height 0 carries the genesis headline instead; no other block on the chain
carries a text marker.

⇒ This is the first round since the miner reappeared in which it did not produce a block. **An
absence over one round is not a departure** — the same miner was silent between August and early
September and then produced five blocks. It is recorded here as an observation, not a conclusion.

## Custody

```
coinbase outputs with a 65-byte key   1168
distinct payees                       1158
payees appearing more than once          1   (the agent key, 11 times)
wallet: candidate 65-byte blobs      16259
        valid points on secp256k1     1158
        of those, coinbase payees     1157
        not yet used                     1   (the keypool's next key)
        payee heights covered         1..1167
```

The run's wallet holds a key for **every coinbase payee from height 1 to 1167 except the agent's**.
**The agent's genesis key is not in it.** Separation holds, and it was checked rather than assumed.

⇒ **The two wallet copies in this capture are byte-identical** (`0e924ba0…`), which returns the
series to its long-standing norm. Last round's two copies differed in the Berkeley DB page-header
log sequence numbers and had to be reconciled page by page; that did not recur.

⇒ **1,157 is also 1,168 − 11.** The node's own window reported 1,157 transactions at capture time,
and the eleven blocks it does not hold a key for are exactly the eleven that pay the agent. So this
node mined every block on the chain except the genesis and the external miner's ten. **That
agreement is a cross-check between three independent readings** — the chain file, the wallet bytes
and the client's own interface — and the first two are the ones this document rests on.

## Independent confirmation

The chain's DNS name now publishes **two IPv4 relays**, and **each was probed separately** over the
chain's own P2P protocol on 23 September rather than trusting whichever one the resolver returned:

```
both relays   1170 block hashes advertised
              heights 1-1167 identical to this capture -- SAME CHAIN, no fork
              ahead by 3 blocks (1168, 1169, 1170), identical hashes on both hosts
```

**There is no fork, both relays hold every block in this capture, and the three blocks they hold
beyond it are the VM continuing to mine after the snapshot.** Two hosts answering identically is a
stronger statement than one host answering, which is why both were asked.

⚠️ **The name resolves to more relays than it used to.** Earlier rounds probed a single IPv4
address behind it. Anyone checking this can resolve the name themselves; the point recorded here is
that a probe of *one* address is a reading of one host, and from this round the comparison is made
against each host the name publishes.

## The first retarget, from here

```
height 2016 is 849 blocks away
at this round's pace   (46.5 min/blk)    around 2026-10-20
at the chain's average (61.5 min/blk)    around 2026-10-28
```

[`PREDICTION-first-retarget.md`](../PREDICTION-first-retarget.md), written at height 272 on
21 August, projected the trigger for **2026-10-31** at the then-recent rate and **2026-12-12** at
the then-lifetime rate. **The chain is running ahead of both projections**, and that is recorded
here rather than quietly adjusted in the prediction, which stays as written.

⇒ **The prediction's conclusion is untouched by the date moving.** It rests on the measured span
exceeding four times the two-week target. The span the client measures is `nTime(2015) − nTime(0)`,
which runs from 3 August and so carries the chain's slower early months: on either projection above
it is between eleven and twelve weeks against a 56-day bound. `nActualTimespan` is therefore
clamped, the new target is the old one multiplied by four, and the old one is already the
proof-of-work limit — so the computed value is discarded and `nBits` stays `0x1d00ffff`. Only
a sustained rate **faster** than 10 min/block over 2,015 blocks would move `nBits`, and the chain
has not been within a factor of four of that at any point.

## The log

```
lines                      833064
ProcessBlock: ACCEPTED     1168     <- CUMULATIVE, and counts blocks RECEIVED too
exceptions                    0
REORGANIZE                    0
InvalidChainFound             0
error lines                 289     260 peer-dropped sockets, 23 dead-2009-host IP probes,
                                    6 dead-2009-host IRC bootstraps
```

These are **claims of the log**. Every consensus statement above comes from parsing the chain file.

## Limits, stated plainly

- ⛔ **One process does not bracket this run.** See above. The binary is bound; the process is not.
- The 260 peer-drop errors are the relay connections cycling, not a consensus event. No
  reorganisation and no invalid chain was found at any point.
- The debug log's counters and the client window's totals are **claims of those surfaces**, not
  evidence about the chain. They are quoted where they agree with the parsed bytes and are labelled
  as what they are.
- **306 blocks over ten days is one node's record of one chain.** The relay comparison confirms the
  blocks, not the process that made them.
- **The external miner's silence this round is one round of data.** It is not a statement about
  whether it returns.
- Wallet files, the debug log and the run's screenshots are **Tier 1 / internal** and live only in
  the cold backup. Nothing in this directory contains key material, a host path or a capture image.

## Files

The evidence set is sealed under the cold backup's own `SHA256SUMS` for evidence set
"2026-09-23-blocks862-1167" (54 files, seal `7906b0ae34674c6b…`). This directory carries the two
binding records, this document, and their own `SHA256SUMS`.

**NOT money.**

The chain's author "Satoshi Nakamoto" is an AI agent built in 2026 — a program, not a person, and not
the historical Satoshi; see `derivatives/bitcoin/CHRONOLOGY.md`.
