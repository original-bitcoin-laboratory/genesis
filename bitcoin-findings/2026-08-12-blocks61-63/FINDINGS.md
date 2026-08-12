# Blocks 61–63 — three blocks, the append-only proof repeated, and one round with no cross-validation

**12 August 2026.** The fourth capture after
[`2026-08-12-blocks51-60`](../2026-08-12-blocks51-60/FINDINGS.md). **The chain is now 64 blocks deep.**

---

## The chain, parsed independently

Parsed from the raw `blk0001.dat` by our own walker — magic, length, block — with no client involved.

```
blocks                64          heights 0-63
blk0001.dat           14,327 B    sha256 2a213629923f36a629d564a8ff3472976f359939c80c86609c8aaf4ef3c83f44
magic                 f00ba726    unchanged
links verified        63 of 63    each block's prev == the previous block's double-SHA256
proof-of-work         64 of 64    every hash below the 0x1d00ffff target
coinbase pubkeys      64 distinct one key per block -- v0.1 has NO keypool
supply                3,200 BTC   50 x 64, no halving before 210,000
tip (height 63)       000000001b3089823e7f7cf60a5f61167e2636a97443a219d24ea04da29d06eb
```

**The three new blocks:**

```
height 61   000000008a6bb267f77a2d2a53426d62d895edc5e0543e40faf441b9c0e7df15   2026-08-11 21:47:36 UTC
height 62   000000003b21ac6cac30594480183e4c950e41403a875e0ee8566e31b91a2839   2026-08-11 22:19:23 UTC
height 63   000000001b3089823e7f7cf60a5f61167e2636a97443a219d24ea04da29d06eb   2026-08-12 01:08:05 UTC
```

### ★ The append-only proof, repeated in its strongest form

```
previous file, whole-file sha256      9d7de18d69e8805572dee802241a690b0b6f19fc6f71143dcc6ff3b817c47324
new file, first 13,658 B sha256       9d7de18d69e8805572dee802241a690b0b6f19fc6f71143dcc6ff3b817c47324
                                      IDENTICAL
```

**Nothing before height 61 was rewritten.** The store is checkably append-only, not merely
consistent — the whole of the previous capture is a byte-exact prefix of this one.

## The binary that mined them

```
bitcoin.exe            c3f15fc5b7bd80f4d08fe5ff356256214734eb1a3e4a7c953c9e8fc8453d2c7d
matches the oracle     true, in BOTH the pre and post captures
pre  capture           2026-08-11 19:43:56 UTC   pid 1040, created 19:43:22 UTC
post capture           2026-08-12 12:43:19 UTC   pid 7720, created 12:42:45 UTC
same binary as the previous round (51-60)        yes -- identical sha256
```

⚠️ **The pre and post captures are DIFFERENT processes** — pid 1040 then pid 7720, with a
`create_time` seventeen hours apart. **This is not the single continuous process the previous round
demonstrated.** The client was restarted between the two bindings. The binary is identical in both,
so what is bound is *which executable ran*, not *that one uninterrupted run produced these blocks*.
**Stated because the previous round could claim the stronger form and this one cannot.**

## Network behaviour

`debug.log` is cumulative across sessions, so the counters are totals rather than per-round:

```
proof-of-work found    62      previous round reported 59  ->  62 - 59 = 3 = this round's blocks
ProcessBlock: ACCEPTED 62      every one of them accepted
received block          0      NONE arrived from a peer
```

**Every block on this chain was mined locally.** The delta matching the block count exactly is the
check that the cumulative reading is being interpreted correctly.

## ⚠️ This round has NO cross-implementation validation

Every previous round from `blocks5-28` onward carried a `netnode-crossvalidation/` directory — the
independent Python implementation's `blocks.dat`, re-derived from the same chain, compared block by
block. **This capture does not contain one.**

```
2026-08-12-blocks51-60     netnode-crossvalidation/  present    61/61, 0 mismatches
2026-08-12-blocks61-63     netnode-crossvalidation/  ABSENT
```

**So heights 61–63 are verified by our parser and by proof-of-work, but not yet by a second
implementation.** That is a real gap in this round's evidence, not a formatting difference. It closes
whenever a netnode capture over the current chain is taken; nothing about the blocks needs redoing.

## The wallet — and the custody separation, re-verified

Archived to `01-keys-SECRET/bitcoin-chain-wallets/wallet-clean-blk63-20260812.dat` (90,112 B,
sha256 `7d477243cbd127fccab59bf828dfec5b41e133f980efcb6c35a84f3e82959bf9`). **Tier 1 — it stays in
the backup and never enters a repository.** *(Confirmed by `git ls-files`: zero wallet or datadir
files are tracked in either repo.)*

```
0x04-prefixed 65-byte blobs in the wallet     222   raw byte patterns
valid points on secp256k1                      64   the actual keys
coinbase payees on the chain                   64
wallet keys that ARE coinbase payees           63   heights 1-63
wallet keys not yet used                        1   v0.1 mints a key at find-time
```

> ### ★ The one coinbase payee ABSENT from the miner wallet is height 0 — the agent's genesis key
> ```
> 04c0414cfdcc009830708543b06e43a03570dc1f...   is the agent's genesis key: TRUE
> agent key present in the miner wallet    :   False
> ```
> **The custody separation holds, exactly as in every prior round.** The key that speaks for the
> identity is held alone; the miner's wallet has never contained it.

## The public seed, asked over the wire

The DigitalOcean seed is the one component this project *operates* rather than publishes, so it is
queried rather than assumed — `verify/probe_seed_node.py`, a v0.1 handshake plus `getblocks`.

```
bitcoin.bitcoin-lab.org  ->  168.144.27.117:18026     connected
version reply             protocol 101, services 1     on magic f00ba726 -- our network
inventory advertised      64 block hashes              heights 1-64
```

⚠️ **v0.1's `version` message carries NO block height** — `nBestHeight` was added to the protocol
later — so the height cannot come from a handshake. It is obtained the way a 2009 client obtains it:
ask for an inventory and count it.

**The seed's height-1 hash matches ours exactly, so it is on this chain and not a fork.** It
advertised 64 hashes where our capture holds 63 above genesis, **so the seed is one block ahead: the
VM kept mining after the snapshot was taken.** Expected, and it resolves itself at the next capture.

## Limits, stated plainly

```
NOT cross-validated       heights 61-63 have no second-implementation check this round
NOT one process           pre and post bindings are different pids; the binary is bound, the
                          continuity of the run is not
seed is ahead by one      height 64 exists on the seed and is not in this capture
cadence                   NOT reported. Three inter-block gaps carry far too much variance to
                          say anything about hashrate, and the previous round already recorded
                          why 10 samples were not enough either
```

## Files

```
OBL-BACKUP/04-evidence/bitcoin-chain-evidence/2026-08-12-blocks61-63/    34 files, all re-hashed
  block61onward/datadir/            blk0001.dat, blkindex.dat, addr.dat, wallet.dat, database/
  block61onward/bitcoin-0.1.3/      bitcoin.exe, debug.log, db.log, the two binding JSONs
  block61onward/                    blk0001-blk61onward-*.dat, wallet-clean-*, pre/post JSON
  screenshots/                      19 PNGs
OBL-BACKUP/01-keys-SECRET/bitcoin-chain-wallets/wallet-clean-blk63-20260812.dat
```

**34 of 34 files re-hashed after the copy, 0 mismatches.**

Related: [previous round](../2026-08-12-blocks51-60/FINDINGS.md) ·
[`CORRECTIONS.md`](../CORRECTIONS.md) · `verify/probe_seed_node.py`
