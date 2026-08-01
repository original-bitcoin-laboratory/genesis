# R4 run findings — `2026-08-02-reorg-partition` (R4b)

Evidence level: **JAN09-EXECUTED** (unmodified v0.1.0 `bitcoin.exe` in isolated VMs).
Raw artifacts are hashed in `EVIDENCE_MANIFEST.json` (bytes stay under the gitignored
`r4-evidence/2026-08-02-reorg-partition/`). **NOT money.**

This is **R4b** from `docs/R4_RUNBOOK.md`: a **witnessed chain reorganisation** on the unmodified 2009
client. R4a (`r4-findings/2026-08-01-sustained-relay/`) showed sustained mining and relay but recorded
**0 reorgs** — on a fast 2-node net each block propagates before the next is found, so no competing fork
forms. As that write-up concluded, a reorg on this topology therefore requires a **deliberate network
partition**. This run does exactly that: the two chains are made to diverge by unequal depth while
partitioned, then reconnected, and node A's released binary orphans its own block and adopts the longer
chain — the live `*** REORGANIZE ***` path in `main.cpp`, executed. R4c (a relayed spend, needs a matured
coinbase ~101 blocks) remains deferred.

## Environment

| Field | Value |
|---|---|
| Date / operator | 2 Aug 2026 (host clock; VM block timestamps ~same day) |
| Hypervisor | Oracle VirtualBox (VMs `obl-r4-node-a`, `obl-r4-node-b`, carried over from R4a) |
| Network | `172.20.0.0/24` VirtualBox **Internal Network** `obl-r4`, no gateway/DNS, firewall off |
| Partition control | node B's virtual **cable** (Devices → Network → *Connect Network Adapter*) toggled off/on |
| VM-A / VM-B IP | `172.20.0.1` (node A) / `172.20.0.2` (node B, the isolated miner) |
| `bitcoin.exe` sha256 | `fbcac071d92e26d82ec917214e334bd43850c0691f113bab1d4741c9bdd30d2d` (+ shipped `libeay32.dll`, `mingwm10.dll`) |
| Guest OS | Windows 10 (64-bit), two VMs |
| Continuity | resumes the R4a `run-b-14` chain: its tip `00000000464529…` (height 13) is the **fork point** here |

## What executed (JAN09-EXECUTED)

The chain climbed (bidirectionally, as in R4a) to a shared tip at **height 13**,
`00000000464529357196408a…` (block `464529` below), then:

| # | Step | Result | Evidence |
|---|---|:--:|---|
| 1 | Node A mines its **own** height-14 block `000000000234ed…c81188fc` on top of `464529` (valid PoW, difficulty 1) | ✓ | `nodeA_debug.log:453-464` (`proof-of-work found`, `new best=000000000234ed height=14`) |
| 2 | **Partition:** node B's cable is disconnected (`recv failed: 10054` → `disconnecting node 172.20.0.2`); node A left at height 14 not mining, node B isolated and mining | ✓ | `nodeA_debug.log:472-492` (`recv failed`, repeated `trying 172.20.0.2:8333`) |
| 3 | In isolation node B mines a **competing** height-14 `00000000c0383b…` (also on `464529`) then extends to height-15 `000000004e442b…` — its chain is now **one block longer** than node A's | ✓ | `nodeB_debug.log:490-561` (`new best=00000000c0383b height=14`, `…4e442b height=15`) |
| 4 | **Reconnect:** node A links to B, is advertised B's tip `4e442b`, takes it as `ORPHAN BLOCK` (parent missing), and back-fills B's `c0383b` via `getblocks`/`getdata` | ✓ | `nodeA_debug.log:493-536` (`ORPHAN BLOCK, prev=00000000c0383b` → back-fill `00000000c0383b`) |
| 5 | Node A's binary fires **`*** REORGANIZE ***`**: it orphans its self-mined `000000000234ed`, adopts B's chain, and sets `new best=000000004e442b height=15` → `ProcessBlock: ACCEPTED` | ✓ | `nodeA_debug.log:538-542` |
| 6 | Node B never reorganised (its chain won): **0** `REORGANIZE`, **0** orphans in `nodeB_debug.log` | ✓ | `nodeB_debug.log` (linear `new best` 0→15) |
| 7 | Both nodes end on the **same** tip `000000004e442b…` at height 15 | ✓ | `verify_r4.py` two-node agreement |

### The reorg, verified from the raw `blk0001.dat` bytes

`verify_r4.py` (committed alongside this file, the R4b copy that additionally **names** off-best blocks)
decodes both nodes' `blk0001.dat`, rebuilds the index, follows the height-based best chain, verifies
every proof-of-work and prev-linkage, and reports the orphan and the two-node agreement:

```
== nodeA_blk0001.dat ==
  blocks in file: 17   best-chain height: 15   orphans (off-best): 1
  [OK ] h0   000000000019d6689c085ae1...  nonce=2083236893  <- genesis (real)
  [OK ] h14  00000000c0383ba9b20b1a80...  nonce=3486865427
  [OK ] h15  000000004e442bf67f2abcaa...  nonce=3386467329
  [ORPHAN] 000000000234edf2e743a6b0...  nonce=2750869646  pow_ok=True  prev=0000000046452935... (forked off best chain at height 13)
  reorg witnessed (>=1 orphan off the best chain): True

== nodeB_blk0001.dat ==
  blocks in file: 16   best-chain height: 15   orphans (off-best): 0
  reorg witnessed (>=1 orphan off the best chain): False

== two-node agreement ==
  BOTH NODES converged on the same best tip: True   (tip 000000004e442bf67f2abcaa..., height 15)
```

The blocks at the fork, from the raw bytes:

| Height | Hash | prev | nonce | coinbase scriptSig | role |
|:--:|---|---|--:|---|---|
| 13 | `00000000464529357196408a…` | block 12 | 1850206216 | `04ffff001d0109` | **fork point** (shared) |
| 14A | `000000000234edf2e743…c81188fc` | `464529` | 2750869646 | `04ffff001d010b` | **node A's block → ORPHANED** |
| 14B | `00000000c0383ba9b20b1a80…` | `464529` | 3486865427 | `04ffff001d010a` | node B's competing block (won) |
| 15B | `000000004e442bf67f2abcaa…` | `c0383b` | 3386467329 | `04ffff001d010d` | node B's tip (new best) |

All four are real **difficulty 1** (`nBits=1d00ffff`), each a valid PoW below the target
`00000000ffff0000…` — including the **orphan `234ed` (`pow_ok=True`)**: it is a perfectly valid block
that lost only because a **longer** chain existed, which is exactly the reorg rule (`v0.1` selects the
chain by **height**, `main.cpp`), not because it was malformed.

## An on-disk fingerprint of the reorg (independent of the logs)

The two nodes' `blk0001.dat` are **not** byte-identical here (contrast R4a's runs, which were):

```
nodeA_blk0001.dat  3861 bytes  sha256 909852b71c2ec1aa5d3ee1a11c8349196f47ddcdfb7b8c174d1c633cd4d8daf0
nodeB_blk0001.dat  3638 bytes  sha256 48a84ce77864f1896da2f0501f18cdb482bc7bb51ac6222b809bb859560bdcd9
                   -----------
delta              +223 bytes  ==  exactly one v0.1 block (215-byte block record + 8-byte magic/len frame)
```

`blk0001.dat` is append-only in receive/mine order and **retains orphaned blocks** (they are removed from
the best chain, not from the file). Node A therefore carries **one extra block on disk** — its orphaned
`234ed` — and node B, which never saw it, does not. The `+223`-byte delta *is* the orphan, and it equals
exactly one v0.1 block record. So even without reading a single log line, the file sizes alone testify that
one node reorganised and the other did not, while `verify_r4.py` confirms both nonetheless agree on the
**best** tip.

## Divergences / surprises

- **The orphan is a valid block, not a reject.** In node A's wallet GUI it appears as
  `0/unconfirmed — Generated (not accepted)`: node A really mined it (50-coin coinbase, valid PoW), then
  lost it in the reorg. "Not accepted" here means *not on the best chain*, not *invalid*.
- **Reorg needs a partition, as predicted.** R4a explicitly reasoned that two miners on a fast net produce
  0 reorgs and that a reorg "requires a deliberate network partition." R4b confirms that prediction by
  construction: the reorg only appeared once the cable was pulled long enough for node B to get a
  full block ahead.
- **Height, not chainwork, decides.** All blocks share `nBits=1d00ffff` (equal difficulty), so the tie is
  broken purely by chain **length** — B's height 15 beats A's height 14 — matching the v0.1 source, which
  selects on height (see `common/…VALIDATION_PATH`, R1).
- **`GetMyExternalIP()` fails** (harmless): it dials a public IP-echo host, unreachable in isolation.
- **One reorg, depth 1.** Node A orphaned a single block (`234ed`); the fork point is height 13
  (`464529`). A deeper reorg would just mean a longer isolated run for node B.

## Captured artifacts

Preserved and hashed in `EVIDENCE_MANIFEST.json` (bytes gitignored under `r4-evidence/`): both nodes'
**full `debug.log`** and both nodes' **`blk0001.dat`** (node A `909852b7…`, node B `48a84ce7…`; the
`Get-FileHash` values shown in the capture screenshots match these byte-for-byte). Both files re-parse
under `verify_r4.py`: node A → 17 blocks, 1 orphan, reorg = True; node B → 16 blocks, 0 orphans; both →
the same height-15 tip `000000004e442b…`.

## Conclusion

At **JAN09-EXECUTED** level this run lifts a **chain reorganisation** from MODEL
(`derivatives/validator-rs`, `derivatives/node`) to the **released binary**: two unmodified v0.1.0 nodes
were partitioned until their equal-difficulty chains diverged by one block in depth, and on reconnect the
shorter node executed Satoshi's `*** REORGANIZE ***` path — orphaning its own valid, self-mined block and
adopting the longer chain — with both nodes then agreeing on the identical height-15 tip, verified from the
raw block bytes (and corroborated by the exact `+223`-byte one-block on-disk delta). Together with R3
(single-block production + relay) and R4a (sustained bidirectional mining + relay), this closes **R4b** and
leaves only **R4c** (a relayed spend of a matured coinbase). **NOT money** — isolated network, real
genesis, valueless by design.
