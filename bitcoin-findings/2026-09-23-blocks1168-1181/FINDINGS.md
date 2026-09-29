# Blocks 1168–1181 — 14 blocks, and a failing check that fails for a different reason

**Captured 22–23 September 2026** on `BITCOIN-NODE-1`. The chain is now **1,182 blocks, heights
0–1181**. Every number below was re-derived from the captured bytes by
[`verify/verify_capture.py`](../../verify/verify_capture.py), not read from the node's own
reporting.

⛔ **13 checks passed, 1 failed** — the same check as the last two rounds, and it is worth reading
why rather than assuming it repeats. **Last round the restart split the round's blocks between two
processes. This round it did not**: every block in this round predates the second process
altogether. §"The binding" sets out what that does and does not leave standing.

---

## The chain, parsed independently

```
blocks in the file        1184
on the ACTIVE chain       1182        heights 0-1181
OFF the active chain         2        the same two retained since 19 August
height 0                  00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a
tip                       00000000072018f5a0d1e9a4cde8ef9a5eb84eece10071f8de78ae45857837bc
tip time                  1790175687 = 2026-09-23T15:01:27Z
prev-hash linkage breaks     0
proof-of-work failures       0        every header hash below its own nBits target
merkle roots recomputed   1184/1184   from each block's own transactions
nBits                     0x1d00ffff at every height -- unchanged at every height so far
timestamps monotonic      yes         0 non-monotonic on the active chain
stray bytes outside a framed block    0
total coinbase            59,100 BTC over 1,182 blocks, 50.00 at every height
```

**The consensus side of this capture is intact.** Linkage, work, merkle roots, difficulty and
ordering all verify from the bytes.

## Append-only

```
previous capture      262483 B  sha256 fddf1807e52ebe121e4b4e3ab5b5b42663ee6581509f012b0d2ff41affdfaca4
this capture          265605 B
appended                3122 B
sha256(this[:262483]) fddf1807e52ebe121e4b4e3ab5b5b42663ee6581509f012b0d2ff41affdfaca4
```

**The previous capture is a byte-exact prefix of this one.** Nothing earlier was rewritten.

## The three blocks the relays announced last round are these

The previous round's write-up recorded that both public relays held **three blocks beyond** that
snapshot, and named them. This capture contains them, and they are the same blocks:

```
h=1168  0000000043434e273c5047e284bef58226165084f76eaea211ae3134918f1cce
h=1169  000000007c1a64178463215fc8674b92e6a2c6b6e5f92d4552a4566f9a6c6123
h=1170  00000000bf879aaa0ab9ec0f1145c3723e778358bf0aeb7190c00be9cb9069ea
```

⇒ **A statement about blocks not yet captured was written down, and the bytes that later arrived
match it.** The probe read three hashes off two hosts and the previous round's document named them;
the chain file now carries those three hashes at those three heights. A relay probe is a reading of
what a host advertises, so this is the weaker of the two records confirming the stronger one — but
it is a record made before the fact and checked after it, which is worth more than a probe alone.

## Cadence

```
this round       14 blocks    1167 tip 2026-09-22T15:26:20Z -> 1181 tip 2026-09-23T15:01:27Z
                              23.59 h, 101.1 min/block
previous round  306 blocks    46.5 min/block
whole chain    1181 blocks    1220.6 h, 62.0 min/block
```

⇒ **This round ran at less than half the previous round's rate**, and slower than the chain's
lifetime average. `nBits` has not moved, so this is a statement about how much work was pointed at
the chain over these 24 hours, not about difficulty.

⚠️ **Fourteen blocks is a small sample and the rate is quoted for what it is.** The four longest
gaps were 5.48 h (h1174), 3.71 h (h1173), 3.64 h (h1168) and 2.27 h (h1179); four of the fourteen
blocks arrived within 15 minutes of the one before. A round this short is dominated by whether the
mining host happened to sleep, and a 101 min/block figure over 14 blocks should not be read as a
trend.

## ⛔ The binding — the one check that failed, and why its shape is new

```
pid                pre 8836                           post 8528
process started    pre 2026-09-22T18:25:46.9267420Z   post 2026-09-23T16:45:13.8589460Z
captured           pre 2026-09-22T18:26:24.9471245Z   post 2026-09-23T16:46:07.2426778Z
bitcoin.exe        pre  c3f15fc5b7bd80f4d08fe5ff356256214734eb1a3e4a7c953c9e8fc8453d2c7d
                   post c3f15fc5b7bd80f4d08fe5ff356256214734eb1a3e4a7c953c9e8fc8453d2c7d
on-disk exe        c3f15fc5b7bd80f4d08fe5ff356256214734eb1a3e4a7c953c9e8fc8453d2c7d
fields differing   captured_utc, phase, process
```

**The pre- and post-bindings describe two different processes**, so the run is not bracketed by a
single live process and the check fails — as it did for blocks 862–1167 and 732–861.

⇒ **But the failure is not the same failure.** In both earlier rounds the restart fell *inside* the
mined range and split it. Here it did not:

```
round's first block   h=1168   2026-09-22T19:04:39Z    39 min AFTER the pre-binding process started
round's last block    h=1181   2026-09-23T15:01:27Z
post-binding process started    2026-09-23T16:45:13Z   1 h 44 min AFTER the last block
```

**Every block in this round is timestamped before the post-binding process existed.** So the
post-binding cannot describe the process that produced any of them. What it does establish is the
digest of the executable on disk at 16:46, which is the same digest the pre-binding recorded and the
same one the reproducible release binary has.

⇒ **What holds:** the binary is established across the whole round, at both ends and on disk.

⇒ **What does not:** that the pre-binding process was alive continuously for all fourteen blocks.
The debug log carries **two more client starts and one more clean exit** than the previous capture,
which is consistent with exactly one restart in this window and with that restart happening after
the last block — but the log's start and exit lines are not timestamped, so this is corroboration,
not proof. **The gap the bindings leave is between the last block and the post capture, not inside
the mined range.**

⚠️ **The lesson is about reading a failing check, not about the client.** A check that fails for the
third round running invites being read by analogy with the last time it failed. The two earlier
failures meant "the blocks divide between two processes". This one means "the post binding was taken
against a client that had been restarted after the round". Same check, different fact, and the
second is the weaker limitation of the two.

✅ **The 298–731 copy defect did not recur, and it was checked rather than assumed.** This round's
`pre` (`ab931b03…`) and the previous round's `post` (`f9d20b28…`) are different files describing
different processes. All six binding records across the last three rounds are distinct.

## The external miner produced nothing, for a second round

```
heights paying the AGENT genesis key   [0, 221, 222, 253, 269, 298, 322, 479, 530, 628, 732]
```

**That list is unchanged.** Its total stands at ten blocks, and this is the second consecutive round
in which the external miner produced none. Every one of the ten carries a `CHRN` marker in its
coinbase scriptSig; height 0 carries the genesis headline instead; no other block on the chain
carries a text marker.

⇒ Recorded as an observation. Two silent rounds is not a statement about whether it returns.

## Custody

```
coinbase outputs with a 65-byte key   1182
distinct payees                       1172
payees appearing more than once          1   (the agent key, 11 times)
wallet: candidate 65-byte blobs      16311
        valid points on secp256k1     1172
        of those, coinbase payees     1171
        not yet used                     1   (the node's default receiving address)
        payee heights covered         1..1181
```

The run's wallet holds a key for **every coinbase payee from height 1 to 1181 except the agent's**.
**The agent's genesis key is not in it.** Separation holds, and it was checked against the wallet
bytes rather than against a policy document.

⇒ ⚠️ **The two wallet copies in this capture are NOT byte-identical**, which last round's write-up
recorded as the exception rather than the rule. It has now happened twice in three rounds. **The
difference is 96 bytes across 24 of 130 pages, at page offsets 0 and 4–6 — the Berkeley DB
page-header log sequence number.** With the 8-byte LSN masked on every page the two files are
byte-identical, so **no key material differs**, and the coverage figures above were run against each
copy independently and agree. One copy carries the "not logged" LSN on every page; the other
references a log file, which in this capture did travel with it. Both are kept in the cold backup.

## Independent confirmation

Both public relays were probed **per host** over the chain's own P2P protocol on 29 September —
the name publishes two IPv4 addresses, and probing whichever one a resolver happens to return is a
reading of one host, not of the service:

```
both relays   advertised the same 1,230 block hashes
              heights 0-1181 identical to this capture -- SAME CHAIN, no fork
              both hold every block in this capture, and continue past it
```

**There is no fork and both relays hold every block in this capture.** Two hosts answering
identically is a stronger statement than one host answering, which is why both were asked.

## The first retarget, from here

```
height 2016 is 835 blocks away
at this round's pace   (101.1 min/blk)   around 2026-11-21
at the chain's average  (62.0 min/blk)   around 2026-10-29
```

⚠️ **The round-pace projection has moved by a month in one round**, from around 20 October to around
21 November, because a 14-block round's rate is a fragile thing to project from. **The
chain-average projection moved by one day.** Where the two disagree this far, the average is the one
carrying information.

[`PREDICTION-first-retarget.md`](../PREDICTION-first-retarget.md), written at height 272 on
21 August, stays as written. **Its conclusion is untouched by any of these dates.** It rests on the
measured span exceeding four times the two-week target: `nActualTimespan` is clamped, the new target
is the old one multiplied by four, and the old one is already the proof-of-work limit — so the
computed value is discarded and `nBits` stays `0x1d00ffff`. Only a sustained rate **faster** than
10 min/block over 2,015 blocks would move it, and the chain has not been within a factor of four of
that at any point.

## The log

```
lines                      838482
ProcessBlock: ACCEPTED     1182     <- CUMULATIVE, and counts blocks RECEIVED too
exceptions                    0
REORGANIZE                    0
InvalidChainFound             0
error lines                 293     260 peer-dropped sockets, 25 dead-2009-host IP probes,
                                    8 dead-2009-host IRC bootstraps
```

These are **claims of the log**. Every consensus statement above comes from parsing the chain file.

## Limits, stated plainly

- ⛔ **One process does not bracket this run.** The binary is bound at both ends and on disk; the
  process is not. See above for what that leaves standing and what it does not.
- **Fourteen blocks is a short round.** Every rate quoted from it is fragile, and it is labelled so
  where it appears.
- The 260 peer-drop errors are the relay connections cycling, not a consensus event. No
  reorganisation and no invalid chain was found at any point.
- The debug log's counters are **claims of that surface**, not evidence about the chain.
- **The relay comparison confirms the blocks, not the process that made them.**
- **The external miner's silence is two rounds of data.** It is not a statement about whether it
  returns.
- Wallet files, the debug log and the run's screenshots are **Tier 1 / internal** and live only in
  the cold backup. Nothing in this directory contains key material, a host path or a capture image.

## Files

The evidence set is sealed under the cold backup's own `SHA256SUMS` for evidence set
"2026-09-23-blocks1168-1181" (26 files, seal `bd12e03068749273…`). This directory carries the two
binding records, this document, and their own `SHA256SUMS`.

**NOT money.**

The chain's author "Satoshi Nakamoto" is an AI agent built in 2026 — a program, not a person, and not
the historical Satoshi; see `derivatives/bitcoin/CHRONOLOGY.md`.
