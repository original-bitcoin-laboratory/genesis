# Blocks 1182–1192 — the first round since August that one live process brackets

**Captured 23–24 September 2026** on `BITCOIN-NODE-1`. The chain is now **1,193 blocks, heights
0–1192**. Every number below was re-derived from the captured bytes by
[`verify/verify_capture.py`](../../verify/verify_capture.py), not read from the node's own
reporting.

✅ **14 checks passed, 0 failed.** The check that failed for the last three rounds — the same running
process bound at both ends of the run — passes here. That is the finding this round carries, and
§"The binding" says exactly how much it is worth.

---

## The chain, parsed independently

```
blocks in the file        1195
on the ACTIVE chain       1193        heights 0-1192
OFF the active chain         2        the same two retained since 19 August
height 0                  00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a
tip                       00000000909136422820d7987917f94364f6ceee9fc0268e67f76d15188bd5d3
tip time                  1790232140 = 2026-09-24T06:42:20Z
prev-hash linkage breaks     0
proof-of-work failures       0        every header hash below its own nBits target
merkle roots recomputed   1195/1195   from each block's own transactions
nBits                     0x1d00ffff at every height -- unchanged at every height so far
timestamps monotonic      yes         0 non-monotonic on the active chain
stray bytes outside a framed block    0
total coinbase            59,650 BTC over 1,193 blocks, 50.00 at every height
```

**The consensus side of this capture is intact.** Linkage, work, merkle roots, difficulty and
ordering all verify from the bytes.

## Append-only

```
previous capture      265605 B  sha256 5ee2102727c073ee7eceec28a3e45e4f6b290fe298ccb03fd755a58ca41330e6
this capture          268058 B
appended                2453 B
sha256(this[:265605]) 5ee2102727c073ee7eceec28a3e45e4f6b290fe298ccb03fd755a58ca41330e6
```

**The previous capture is a byte-exact prefix of this one.** Nothing earlier was rewritten.

## ✅ The binding — the check that has failed three rounds running, and passes here

```
pid                pre 8908                           post 8908
process started    pre 2026-09-23T16:52:37.4297210Z   post 2026-09-23T16:52:37.4297210Z
captured           pre 2026-09-23T16:53:17.7963409Z   post 2026-09-24T07:32:57.0302139Z
bitcoin.exe        pre  c3f15fc5b7bd80f4d08fe5ff356256214734eb1a3e4a7c953c9e8fc8453d2c7d
                   post c3f15fc5b7bd80f4d08fe5ff356256214734eb1a3e4a7c953c9e8fc8453d2c7d
on-disk exe        c3f15fc5b7bd80f4d08fe5ff356256214734eb1a3e4a7c953c9e8fc8453d2c7d
fields differing   captured_utc, phase
```

**One process, pid 8908, is bound at both ends**, and the round's blocks fall inside its lifetime:

```
process started   2026-09-23T16:52:37Z   1 h 11 min BEFORE the round's first block
first block       h=1182  2026-09-23T18:03:37Z
last block        h=1192  2026-09-24T06:42:20Z
post captured     2026-09-24T07:32:57Z   50 min AFTER the round's last block
```

⇒ **This is the first round since blocks 296–297 on 22 August whose run is bracketed by a single
live process with two genuine bindings.** Blocks 298–731 recorded the same process at both ends but
its `pre` was a byte-identical copy of an earlier run's, so that pass was not a reading; 732–861,
862–1167 and 1168–1181 each failed on a restart. **Here the two records are distinct files, the only
fields that differ are `captured_utc` and `phase`, and the process is the same one throughout.**

⚠️ **What this does and does not say.** It says the executable bound at the start of the run is the
one bound at the end, and that no restart intervened. It does **not** say the process mined any
particular block — that is what the chain file says — and it does not make the earlier rounds' data
weaker than it was. **The binary was established in every round; what was missing was the process,
and this round has it.**

✅ **All six binding records across the last three rounds are distinct files.** This round's `pre`
(`91cedd9e…`) is not the previous round's `post` (`81d0da88…`). The 298–731 copy defect has not
recurred, and it was checked rather than assumed.

## Cadence

```
this round       11 blocks    1181 tip 2026-09-23T15:01:27Z -> 1192 tip 2026-09-24T06:42:20Z
                              15.68 h, 85.5 min/block
previous round   14 blocks    101.1 min/block
whole chain    1192 blocks    1236.3 h, 62.2 min/block
```

⚠️ **Eleven blocks is a short round and the rate is quoted for what it is.** The four longest gaps
were 3.20 h (h1190), 3.04 h (h1182), 2.71 h (h1184) and 2.65 h (h1189); h1186 arrived **29 seconds**
after h1185. Over eleven blocks the figure is dominated by whether the mining host happened to
sleep, and it should not be read as a trend. What can be said is that two consecutive short rounds
have both run slower than the chain's lifetime average.

## The external miner produced nothing, for a third round

```
heights paying the AGENT genesis key   [0, 221, 222, 253, 269, 298, 322, 479, 530, 628, 732]
```

**That list is unchanged.** Its total stands at ten blocks, and this is the third consecutive round
in which the external miner produced none — **331 blocks across those three rounds, and 460 blocks
since its last one at height 732** on 6 September. Every one of the ten carries a `CHRN` marker in its coinbase scriptSig; height 0
carries the genesis headline instead; no other block on the chain carries a text marker.

⇒ Recorded as an observation. The same miner was silent between late August and early September and
then produced five blocks, so three silent rounds is not a statement about whether it returns.

## Custody

```
coinbase outputs with a 65-byte key   1193
distinct payees                       1183
payees appearing more than once          1   (the agent key, 11 times)
wallet: candidate 65-byte blobs      16619
        valid points on secp256k1     1183
        of those, coinbase payees     1182
        not yet used                     1   (the node's default receiving address)
        payee heights covered         1..1192
```

The run's wallet holds a key for **every coinbase payee from height 1 to 1192 except the agent's**.
**The agent's genesis key is not in it.** Separation holds, and it was checked against the wallet
bytes rather than against a policy document.

✅ **The two wallet copies in this capture are byte-identical** (`e704e8cf…`), and every page in both
carries the "not logged" log sequence number, so neither depends on a Berkeley DB log file to be
read. Last round's two copies differed in 96 bytes of page-header LSN and had to be reconciled page
by page before either could be trusted; that did not recur.

## Independent confirmation

Both public relays were probed **per host** over the chain's own P2P protocol on 29 September —
the name publishes two IPv4 addresses, and probing whichever one a resolver happens to return is a
reading of one host, not of the service:

```
both relays   advertised the same 1,230 block hashes, heights 0-1229
              heights 0-1192 identical to this capture -- SAME CHAIN, no fork
              ahead by 37 blocks, identical hashes on both hosts
```

**There is no fork, both relays hold every block in this capture, and the 37 blocks they hold beyond
it are the VM continuing to mine after the snapshot.** Two hosts answering identically is a stronger
statement than one host answering, which is why both were asked.

## The first retarget, from here

```
height 2016 is 824 blocks away
at this round's pace    (85.5 min/blk)   around 2026-11-12
at the chain's average  (62.2 min/blk)   around 2026-10-29
```

⚠️ **The round-pace projection has moved twice in two rounds** — around 20 October, then 21
November, now 12 November — because an 11- or 14-block round's rate is a fragile thing to project
from. **The chain-average projection has not moved at all across those same two rounds.** Where the
two disagree this far, the average is the one carrying information.

[`PREDICTION-first-retarget.md`](../PREDICTION-first-retarget.md), written at height 272 on
21 August, stays as written. **Its conclusion is untouched by any of these dates.** It rests on the
measured span exceeding four times the two-week target: `nActualTimespan` is clamped, the new target
is the old one multiplied by four, and the old one is already the proof-of-work limit — so the
computed value is discarded and `nBits` stays `0x1d00ffff`. Only a sustained rate **faster** than
10 min/block over 2,015 blocks would move it, and the chain has not been within a factor of four of
that at any point.

## The log

```
lines                      859954
ProcessBlock: ACCEPTED     1193     <- CUMULATIVE, and counts blocks RECEIVED too
exceptions                    0
REORGANIZE                    0
InvalidChainFound             0
error lines                 295     260 peer-dropped sockets, 26 dead-2009-host IP probes,
                                    9 dead-2009-host IRC bootstraps
```

These are **claims of the log**. Every consensus statement above comes from parsing the chain file.

## Limits, stated plainly

- **Eleven blocks is a short round.** Every rate quoted from it is fragile, and it is labelled so
  where it appears.
- **A single bracketing process is a statement about the client, not about the blocks.** The chain
  file is what establishes the blocks; the binding establishes which executable was running.
- The 260 peer-drop errors are the relay connections cycling, not a consensus event. No
  reorganisation and no invalid chain was found at any point.
- The debug log's counters are **claims of that surface**, not evidence about the chain.
- **The relay comparison confirms the blocks, not the process that made them.**
- **The external miner's silence is three rounds of data.** It is not a statement about whether it
  returns.
- Wallet files, the debug log and the run's screenshots are **Tier 1 / internal** and live only in
  the cold backup. Nothing in this directory contains key material, a host path or a capture image.

## Files

The evidence set is sealed under the cold backup's own `SHA256SUMS` for evidence set
"2026-09-24-blocks1182-1192" (31 files, seal `d8ae7faeda63cef7…`). This directory carries the two
binding records, this document, and their own `SHA256SUMS`.

**NOT money.**

The chain's author "Satoshi Nakamoto" is an AI agent built in 2026 — a program, not a person, and not
the historical Satoshi; see `derivatives/bitcoin/CHRONOLOGY.md`.
