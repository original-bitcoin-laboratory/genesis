# Blocks 61–63 — three blocks, the append-only proof repeated, and two apparent gaps that closed

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

**The pre and post captures are DIFFERENT processes** — pid 1040 then pid 7720, seventeen hours
apart. That looked at first like a weaker binding than the previous round's. **The log settles it,
and the answer is better than the appearance.**

```
line 45405   Bitcoin exiting          <- previous session ends
line 45428   Loading addresses...     <- SESSION S begins (pid 1040, created 19:43:22,
                                          pre-binding captured 19:43:56, 34 s later)
line 47056   proof-of-work found
line 47448   proof-of-work found      <- THREE blocks, and NO "Bitcoin exiting" between them
line 49709   proof-of-work found
line 50619   Loading addresses...     <- SESSION T begins (pid 7720, created 12:42:45,
                                          post-binding captured 12:43:19, 34 s later)
             proof-of-work found in session T: 0
```

> ### ⇒ **All three blocks were mined inside ONE continuous session, and the pre-binding bound it.**
> **Session T mined nothing** — it is a later restart that happened to be running when the post
> capture was taken.
>
> ⚠️ **So the defect is in the POST-BINDING PROCEDURE, not in the blocks' provenance.** The
> post capture is supposed to close the same process the pre capture opened; here it bound a
> different one. **The fix is procedural: take the post capture BEFORE restarting the client**, as
> the previous round did.
>
> *(Cross-check: 62 cumulative `proof-of-work found` minus the previous round's 59 = 3, and session
> S contains exactly 3. Two independent countings agree.)*

## Network behaviour

`debug.log` is cumulative across sessions, so the counters are totals rather than per-round:

```
proof-of-work found    62      previous round reported 59  ->  62 - 59 = 3 = this round's blocks
ProcessBlock: ACCEPTED 62      every one of them accepted
received block          0      NONE arrived from a peer
```

**Every block on this chain was mined locally.** The delta matching the block count exactly is the
check that the cumulative reading is being interpreted correctly.

## ★★ Cross-implementation validation — obtained after the fact, from the seed

The capture arrived without a `netnode-crossvalidation/` directory, which every round since
`blocks5-28` had carried. **It did not need the VM to close: the independent Python implementation
can sync from the public seed.**

```
python -m netnode --chain bitcoin --datadir <empty> --no-listen --connect 168.144.27.117:18026
```

**It minted the genesis ITSELF from the chain parameters before connecting to anything**, arriving
at `00000000ad12f3ec…` independently, then validated every block it received.

```
netnode (Python, host)      66 blocks   blocks.dat    14,509 B
2009 C++ client (in the VM) 64 blocks   blk0001.dat   14,327 B

compared heights 0-63       64 / 64 identical, 0 mismatches
heights 61-63, this round   3 / 3 VALIDATED
  height 61  000000008a6bb267f77a2d2a53426d62d895edc5e0543e40faf441b9c0e7df15  match
  height 62  000000003b21ac6cac30594480183e4c950e41403a875e0ee8566e31b91a2839  match
  height 63  000000001b3089823e7f7cf60a5f61167e2636a97443a219d24ea04da29d06eb  match
```

**The size difference is FRAMING, not content**, and it is exact:

```
over the 64 blocks both hold:
  netnode   length+block        (4 B/block)  = 14,071 B
  C++       magic+length+block  (8 B/block)  = 14,327 B  == blk0001.dat exactly
  difference 256 B = 4 x 64                              EXACT
```

**netnode also holds heights 64 and 65**, which the VM had mined after the snapshot — independently
confirming the two blocks the seed advertised.

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
inventory advertised      65 block hashes              heights 1-65 (re-probed after ingest)
```

⚠️ **v0.1's `version` message carries NO block height** — `nBestHeight` was added to the protocol
later — so the height cannot come from a handshake. It is obtained the way a 2009 client obtains it:
ask for an inventory and count it.

**The seed's height-1 hash matches ours exactly, so it is on this chain and not a fork.** It
advertised 65 hashes where our capture holds 63 above genesis, **so the seed is two blocks ahead:
the VM kept mining after the snapshot was taken.** Expected — a capture is behind by construction —
and the netnode sync above independently confirms heights 64 and 65 as real blocks on this chain.

## Limits, stated plainly

```
CLOSED  cross-validation  64/64 by the independent Python implementation, 61-63 at 3/3
CLOSED  one process       the three blocks are all inside one session; the POST-BINDING
                          procedure is what needs fixing, not the provenance
seed is ahead by two      heights 64-65 exist on the seed and are not in this capture
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
  netnode-crossvalidation/          blocks.dat (66 blocks), peers.json -- added after ingest
  screenshots/                      19 PNGs
OBL-BACKUP/01-keys-SECRET/bitcoin-chain-wallets/wallet-clean-blk63-20260812.dat
```

**34 of 34 files re-hashed after the copy, 0 mismatches** (plus the 2 cross-validation files added here).

Related: [previous round](../2026-08-12-blocks51-60/FINDINGS.md) ·
[`CORRECTIONS.md`](../CORRECTIONS.md) · `verify/probe_seed_node.py`
