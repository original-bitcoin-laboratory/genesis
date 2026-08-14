# Blocks 64–121 — fifty-eight blocks, the append-only proof again, and a second dead 2009 host

**Captured 12–14 August 2026** on `BITCOIN-NODE-1`. The chain is now **122 blocks, heights 0–121**.
Every number below was re-derived from the captured bytes, not read from the node's own reporting.

---

## The chain, parsed independently

`blk0001.dat` parsed directly against this chain's magic `f0 0b a7 26` — not by asking the client:

```
blocks parsed              122        heights 0-121
height 0                   00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a
tip                        00000000accf9b5da76fdd9f3aca1d20a7c4a931ed88f3afbb5af458f7a171c7
tip time                   1786718456 = 2026-08-14T14:40:56Z
prev-hash linkage breaks   0
timestamps monotonic       yes
```

### ★ The append-only proof, in its strongest form again

```
previous capture (blocks 61-63)   blk0001.dat   14,327 B
this capture                      blk0001.dat   27,261 B
appended                                        12,934 B

sha256(new file's first 14,327 bytes)  2a213629923f36a629d564a8ff3472976f359939c80c86609c8aaf4ef3c83f44
sha256(the previous file entire)       2a213629923f36a629d564a8ff3472976f359939c80c86609c8aaf4ef3c83f44
```

**The previous capture is a byte-exact prefix of this one.** Nothing before height 63 was rewritten,
reordered or re-signed — established by hashing, not by trusting the client. **This is the fourth
consecutive round in which the property holds.**

## Cadence

```
height 0     2026-08-03T18:22:55Z
height 63    2026-08-12T01:08:05Z
height 121   2026-08-14T14:40:56Z
this round   58 blocks over 61.5 h  =  63.7 min/block
```

**Difficulty is 1 and unchanged**, so the cadence is a statement about the VM's hash rate, not about
the retarget rule — which on this chain has not yet been exercised.

## The binary that mined them

```
pid                        4128       IDENTICAL in the pre- and post-run bindings
bitcoin.exe sha256         c3f15fc5b7bd80f4d08fe5ff356256214734eb1a3e4a7c953c9e8fc8453d2c7d
matches oracle             true, at BOTH ends
captured pre               2026-08-12T13:15:04Z
captured post              2026-08-14T17:41:05Z
fields changed pre->post   phase, captured_utc -- and nothing else
```

★ **The process identifier is the same at both ends**, so the binary that produced height 121 is the
same *running image* that was bound before height 64 — not merely a file with the same hash. The
on-disk `bitcoin.exe` in this capture re-hashes to that value.

## Network behaviour, and the 51 errors — all benign, and one of them is a finding

```
exceptions                 0
REORGANIZE                 0
InvalidChainFound          0
ERROR lines                51
  37  "send error" -- peers dropping sockets, ordinary P2P churn
  14  "GetMyExternalIP() : connection to <host>:80 failed"
```

> ### ★★ THE SECOND DEAD 2009 HOST, AND IT IS THE SAME SHAPE AS THE FIRST
>
> `GetMyExternalIP()` calls IP-discovery services **hardcoded in the 2009 source**. They are gone,
> exactly as `chat.freenode.net` is gone (F50). **Two of v0.1's outward-facing dependencies have now
> expired, and both failures are logged, harmless and self-limiting** — the client carries on and
> mines.
>
> ⇒ **Neither is a defect in the patch.** They are the parts of Satoshi's design that trusted a name
> somebody else controlled, and they are the only parts that have decayed in seventeen years. The
> consensus code, which trusts nothing, still runs.

⚠️ **`ProcessBlock: ACCEPTED` appears 120 times, and that is NOT this round's block count.** The
debug log is cumulative across sessions and ACCEPTED also counts blocks received from a peer. **The
58 is derived from the file, not from the log** — the log is a narrative, the chain is the record.

## Cross-check against the public seed, asked over the wire

`bitcoin.bitcoin-lab.org:18026` → `168.144.27.117`, v0.1 handshake then `getblocks` from the genesis
locator:

```
peer protocol version      101
inv returned               121 block hashes  (heights 1-121)
compared to this capture   heights 1-121 IDENTICAL
verdict                    same chain, no fork; the seed is EXACTLY level with the capture
```

★ **The seed is operated, not merely published**, so this is the one check that tests a running
service rather than a stored file. It has the blocks.

## The wallet — custody separation, re-verified

```
0x04-prefixed 65-byte blobs in the wallet    1,733   raw byte patterns
valid points on secp256k1                      123   the actual keys
coinbase payees on the chain                   122   one per block, all distinct
wallet keys that ARE coinbase payees           121   heights 1-121
wallet keys not yet used                         2   v0.1 mints a key at find-time
```

> ### ★ The one coinbase payee ABSENT from the miner wallet is height 0 — the agent's genesis key
> ```
> height 0 payee                     04c0414cfdcc009830708543b06e43a0...
> that key present in the wallet  :  False
> that key paid any of blocks 1-121: False
> ```
> **The custody separation holds, exactly as in every prior round.** The key that speaks for the
> identity is held alone; the miner's wallet has never contained it, and the chain shows it was
> used once, at height 0, and never again.

**The wallet is Tier 1 and is archived to the cold backup only.** Confirmed by `git ls-files`: zero
wallet, datadir or key files are tracked in any repository.

## Limits, stated plainly

- **58 blocks at difficulty 1 on one VM prove liveness and append-only continuity. They prove
  nothing about security margin**, which at difficulty 1 is negligible by construction.
- The seed agreeing is **one** independent witness, and it is one we operate. It is not a network.
- `ProcessBlock: ACCEPTED = 120` is a cumulative log figure and is deliberately not used as evidence.
- The 63.7 min/block cadence is a property of this VM. **It is not a protocol measurement.**

## Files

```
cold backup, evidence set "2026-08-14-blocks64-121"        50 files, all re-hashed
  block64onward/datadir/          blk0001.dat, blkindex.dat, addr.dat, wallet.dat, database/
  block64onward/bitcoin-0.1.3/    bitcoin.exe, debug.log, db.log, the two binding JSONs
  block64onward/                  blk0001-blk64onward-*.dat, wallet-clean-*, pre/post JSON
  screenshots/                    20 PNGs, 2026-08-12 18:45 -> 2026-08-14 23:10
  SHA256SUMS                      generated after the copy, from the copies
cold backup, key custody          the wallet, Tier 1, separate from the evidence set

this repository                   FINDINGS.md, SHA256SUMS, the two binding JSONs -- and nothing
                                  else. No chain data, no wallet, no logs.
```

**50 of 50 files re-hashed after the copy against their sources — 0 mismatches**, 40,011,301 bytes.

Related: [previous round](../2026-08-12-blocks61-63/FINDINGS.md) ·
[`CORRECTIONS.md`](../CORRECTIONS.md) · `verify/probe_seed_node.py`
