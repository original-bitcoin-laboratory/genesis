# Blocks 5–28 — twenty-four blocks, verified from the block file rather than from the client

**Captured 9–10 August 2026** from `bitcoin-node-1`, continuing
[`2026-08-09-block4`](../2026-08-09-block4/FINDINGS.md). **This run closes the gap between the
block-4 witness and the chain's current tip.**

## The chain, parsed independently

`blk0001.dat` was parsed byte-by-byte here — magic-delimited records, each header double-SHA'd —
rather than reading the client's own status line. **The client's opinion of its chain is not evidence
about its chain.**

```
file                6,522 B   sha256 f3d9e042565494aefc6da96d5863e87f058d2aadf868c89fbb4e069dcf36a353
blocks parsed       29        heights 0 - 28
genesis             00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a   MATCHES
block 1             000000007beb32b8380089595a91261a5ce4fbd4ece0cd661683cb1ce81e407c   MATCHES
tip (height 28)     000000009b6d2e544e07e799362bd62d4a83dfb6146aa7d3be43ee16d800a4a8
every prev-hash     links to its predecessor                                            PASS
every block         hash < the difficulty-1 target, nBits 0x1d00ffff                    PASS
```

**Twenty-four new blocks (5–28), each real difficulty-1 work of about 2³² hashes.** The tip was mined
**2026-08-09 20:27:01 UTC**.

## The binary that mined them, bound to the run

```
oracle_sha256                c3f15fc5b7bd80f4d08fe5ff356256214734eb1a3e4a7c953c9e8fc8453d2c7d
bitcoin_exe_matches_oracle   TRUE
binding_method               live-process-image
pre  captured                2026-08-08T23:13:06Z
post captured                2026-08-09T23:08:28Z
```

**That oracle is the CI-reproducible build of v0.1.3** — the same bytes the release workflow rebuilt
from the 2009 archive, and a copy already held in this repository. **So the binary that extended the
chain is the published one, bound to the running process at both ends of the window**, not merely
present on disk.

> **The `-Oracle` argument was passed.** `capture_binding.ps1` defaults to the JAN09 historical hash
> (`fbcac071…`), and a correct run without the flag reads `matches oracle: False`. That trap is
> recorded in the project's notes and was avoided here.

## The wallet — and the only question that mattered

**v0.1 has no keypool.** Each block mints a fresh key into `wallet.dat` at the moment it is found, so
**a backup taken before a block does not contain that block's coins.** Before this capture the newest
backup was block 4; the chain was at 28.

Both copies taken in this run were checked **against the secp256k1 curve equation**, not by counting
byte patterns:

```
wallet-clean-blk28-20260809.dat        29 on-curve keys
datadir/wallet.dat (live)              29 on-curve keys
identical key sets                     TRUE   (the byte difference is BDB page/log state)
29 keys for 29 blocks                  one per block, heights 0-28, exactly as v0.1 behaves
strict superset of ALL earlier backups TRUE   -- 0 keys would be lost
keys gained since the block-4 backup   24     -- exactly blocks 5 to 28
```

> **Every key for every block mined to date is now held.** *(Redundancy is not uniform: blocks 0–4
> exist across eight wallet copies, blocks 5–28 across two, both from this event. Worth knowing before
> the next long mining run.)*

## Where the bytes live

```
committed here          FINDINGS.md, the two binding JSONs, SHA256SUMS
raw evidence            OBL-BACKUP/04-evidence/bitcoin-chain-evidence/2026-08-10-blocks5-28/
                        (datadir, debug.log, capture script, 33 screenshots) -- 45 files, sealed
wallets  TIER-1         OBL-BACKUP/01-keys-SECRET/bitcoin-chain-wallets/
                        wallet-clean-blk28-20260809.dat, bitcoin-node-1-wallet-live-blk28-20260809.dat
binary                  not duplicated -- c3f15fc5... is already in derivatives/bitcoin/dist/
```

**Raw block and wallet bytes are never committed to this repository**; `.gitignore` excludes the
evidence trees, and the wallets are Tier-1 secret material held only in the local backup.

## What this does not establish

- **Nothing about who mined it beyond this project.** Every block here was mined by the project's own
  node, because nobody else has mined yet. That is a concentration, stated plainly in the chain's
  README, and it ends the moment anyone else finds a block.
- **No value.** These coins have never been spent, offered, priced or transferred.
- **Not an independent-validation claim for 5–28.** Block 1 was relayed to the seed and validated by a
  different implementation; **blocks 5–28 are recorded here from this node's own block file**, and a
  second implementation's confirmation of the current tip is a separate check.
