# Block 4 — the Bitcoin chain (genesis 00000000ad12f3ec…)

Mined **2026-08-08 22:19:22 UTC**. Verified from the raw `blk0001.dat`.

```
height 0  00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a  nonce   33394338  270 B
height 1  000000007beb32b8380089595a91261a5ce4fbd4ece0cd661683cb1ce81e407c  nonce  895691393  215 B
height 2  000000001690a604f122ddf97c77d2580535fde2b2d700dc8a4478aea7ed75d5  nonce 1510572694  215 B
height 3  00000000428303928c985745792c7ad7644cb5f310b417263a66108fa7f49dcf  nonce  612491648  215 B
height 4  0000000097b1298a990e8f872e4acda48ace5274e99d2a5f9a483f183c1bd20c  nonce 2045882594  215 B
          nBits 0x1d00ffff throughout; magic f00ba726; 1,170 bytes total
```

**All five link, and all five satisfy their proof-of-work target** — checked against the difficulty
arithmetic, not by eye. Block 4's `prev` is block 3's hash exactly.

## Binding — and this one is tighter than any before it

```
process started   2026-08-08 21:56:08 UTC   pid 2272
PRE  binding      2026-08-08 21:56:16 UTC
block 4 nTime     2026-08-08 22:19:22 UTC   <-- inside the bracket
POST binding      2026-08-08 22:35:05 UTC
bitcoin.exe       c3f15fc5b7bd80f4d08fe5ff356256214734eb1a3e4a7c953c9e8fc8453d2c7d
path              C:\bitcoin\bitcoin-0.1.3\bitcoin.exe
                  bitcoin_exe_matches_oracle = true, both phases; identical pid and start time
```

**The whole session is 39 minutes and the block sits in the middle of it.** Same PID, same process
start time in both captures — so the bracket holds one uninterrupted process, and the block was
produced *inside* it.

> **Worth stating because the R4c capture could not claim it:** there, the binding pair spanned ~65
> hours and the blocks were scattered through it. Here the window is minutes wide. **A narrow bracket
> is a stronger statement than a wide one** — it leaves less room between "this binary was running"
> and "this binary made this block."

The exact executable is retained beside this file at `client/bitcoin.exe-c3f15fc5`.

## ★ The released client mined it

Blocks 2, 3 and 4 were all produced by **`bitcoin-0.1.3`** — the client published as
`Bitcoin-v0.1.3`, hash `c3f15fc5…`, matching its own release oracle.

**So the release is not merely a package: it is an executed artifact.** That is the same claim the
laboratory makes about Satoshi's `fbcac071…`, now made about our own.

*(Block 1 was mined by `bitcoin-0.1.1`, `cfb59606…`, and its evidence records say so. Do not
retro-fit v0.1.3 onto it.)*

## Interval — and what it does NOT measure

```
genesis -> 1   28.2 h
1 -> 2         23.9 h
2 -> 3          1.3 h
3 -> 4         68.6 h
```

**These are wall-clock gaps between sessions, not block times.** The miner is not left running; the
guest is started when there is time for it. **A 68-hour gap means the machine was off, not that the
work got harder** — difficulty never moved from 1 (`nBits 0x1d00ffff` on every block), and at
difficulty 1 a 2-vCPU guest finds a block in roughly 50–90 minutes of actual mining.

**Nothing here measures hashrate, difficulty, or network behaviour.** A single node mining alone on
an isolated chain measures only that the client works.

## Corrections carried

**`NEXT-SESSION_block4_pre.json` in the block-3 directory is not a block-4 binding**, despite what
that directory's `FINDINGS.md` says. It was captured 2026-08-04T23:11:41Z from PID 5072 running
`C:\bitcoin\bitcoin-0.1.1\bitcoin.exe` — a process that had already exited. **This block-4 session
took a fresh `pre` (PID 2272, 21:56:16Z), which is the one that counts.** The misdescription is
recorded in `../CORRECTIONS.md` §1 and the sealed block-3 set is left untouched.

> **A `pre` capture from a dead process binds nothing.** That is the whole reason a fresh one was
> taken rather than reusing the file that was sitting there labelled for this purpose.

## What this establishes

```
ESTABLISHED   block 4 exists, links to block 3, and meets its PoW target
              the released v0.1.3 client produced it, bound before and after by
              pid + process start time across a 39-minute window
              the chain is 5 blocks, all valid, all at difficulty 1

NOT           anything about value. 50.00 of nothing, no market, no sale. NOT money.
ESTABLISHED   anything about network behaviour -- one node, isolated, no peers.
              anything about difficulty dynamics -- nBits never changed.
```

## Reproduce

```bash
python original-bitcoin-laboratory/lab/genesis/derivatives/bitcoin/net.py   # re-derives the genesis
sha256sum client/bitcoin.exe-c3f15fc5     # c3f15fc5...2c7d, the v0.1.3 release binary
sha256sum -c SHA256SUMS
```

**Raw bytes are internal.** This directory carries the datadir, both wallets and the client; the
published findings in the repo carry the hashes and the reasoning, never the bytes.
