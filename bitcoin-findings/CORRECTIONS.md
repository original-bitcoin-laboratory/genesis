# Corrections to the block findings

**Each findings directory is sealed** — its `SHA256SUMS` covers its own contents, including its
`FINDINGS.md`. **Nothing in them is edited.** Where something in a sealed set turns out to be wrong,
the correction is recorded here instead, so the seal keeps verifying and the error stays visible.

> **Editing a sealed record to make it right destroys the only thing that made it worth sealing.**

---

## 1. `2026-08-06-block3/` — `NEXT-SESSION_block4_pre.json` is misdescribed

**That directory's `FINDINGS.md` says:**

> *"`NEXT-SESSION_block4_pre.json` is the binding taken after relaunching — it belongs to the block-4
> session and is kept here only so it is not lost to the next overwrite."*

**It is not a block-4 binding.**

```
its captured_utc      2026-08-04T23:11:41Z
its executable_path   C:\bitcoin\bitcoin-0.1.1\bitcoin.exe
its bitcoin.exe       cfb59606…  (v0.1.1)
its pid               5072 — a process that had already exited
```

**Block 4 was mined on 2026-08-08 by a different client and a different process** — v0.1.3
(`c3f15fc5…`), PID 2272 — and took its own fresh `pre` capture at 21:56:16Z. **That is the binding
that counts**, and it is in `2026-08-09-block4/`.

> **A `pre` capture from a dead process binds nothing.** The point of the pair is that one
> *uninterrupted* process spans it; a record from a PID that has already exited proves only that the
> file exists. This is why a fresh capture was taken rather than reusing the file that was sitting
> there labelled for the purpose.

## 2. Which client mined which block

Recorded because it is easy to flatten, and flattening it would be a false claim.

```
block 1    bitcoin-0.1.1   cfb59606c032faa933d5007e85d36f4cfd02737fc4bc485ec2d8699aeacba5ac
blocks 2-4 bitcoin-0.1.3   c3f15fc5b7bd80f4d08fe5ff356256214734eb1a3e4a7c953c9e8fc8453d2c7d
```

**Do not retro-fit v0.1.3 onto block 1.** Its evidence records say v0.1.1 and they are right.

## 3. What the block bindings do and do not establish

**They establish** that a process running a binary of a known hash was alive before and after the
block's own timestamp, with the same PID and process start time in both captures.

**They do not establish** that this specific process mined this specific block — no artifact can tie
a nonce to a PID. The binding narrows the gap between *"this binary was running"* and *"this binary
made this block"*; it does not close it.

**The narrower the bracket, the stronger the statement.** Block 4's is 39 minutes wide with the block
in the middle. Earlier brackets are wider. **A wide bracket is weaker evidence, not equal evidence.**

## 4. What these numbers are not

The gaps between blocks — 28.2 h, 23.9 h, 1.3 h, 68.6 h — are **wall-clock intervals between
sessions, not block times.** The miner is not left running; the guest is started when there is time.
**A 68-hour gap means the machine was off**, not that anything got harder: `nBits` is `0x1d00ffff` on
every block and difficulty has never moved.

**Nothing here measures hashrate, difficulty, or network behaviour.** One node, isolated, no peers.

## 5. Where the raw bytes live

These published directories carry **findings, hashes and binding records**. The `SHA256SUMS` in each
covers the full sealed set — including files that are **deliberately not published**: `blk0001.dat`,
`blkindex.dat`, `addr.dat`, `wallet.dat`, `debug.log`, the client binary and the screenshots.

**That is not an inconsistency.** The manifest is the sealed set's manifest; the repository publishes
the part that can be published. **A hash is not a reproduction** — you can verify our claims against
these digests without us shipping a wallet.

**NOT money.** The chain has no value assigned, no market, no sale.
