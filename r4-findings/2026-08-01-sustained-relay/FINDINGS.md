# R4 run findings — `2026-08-01-sustained-relay` (R4a)

Evidence level: **JAN09-EXECUTED** (unmodified v0.1.0 `bitcoin.exe` in isolated VMs).
Raw artifacts are hashed in `EVIDENCE_MANIFEST.json` (bytes stay under the gitignored
`r4-evidence/2026-08-01-sustained-relay/`). **NOT money.**

This is **R4a** from `docs/R4_RUNBOOK.md`: **sustained multi-block mining + relay** on the unmodified
2009 client. It extends the R3 result (`r3-findings/2026-07-31-twonode-mined-block/`, a single mined and
relayed block) to a **run of blocks**: one node mines several blocks in succession and the other node
receives and accepts every one, both ending on the identical chain. R4b (reorg) and R4c (a relayed
spend) remain deferred.

## Environment

| Field | Value |
|---|---|
| Date / operator | 1 Aug 2026 (host clock; VM block timestamps ~same day) |
| Hypervisor | Oracle VirtualBox (fresh VMs `obl-r4-node-a`, `obl-r4-node-b`) |
| Network | `172.20.0.0/24` VirtualBox **Internal Network** `obl-r4`, no gateway/DNS, firewall off |
| mini_ircd | on **node A** `172.20.0.1:6667`; both VMs' `hosts` → `chat.freenode.net = 172.20.0.1` |
| VM-A / VM-B IP | `172.20.0.1` (node A, receiver, nick `uAfj1myhx8niewh`) / `172.20.0.2` (node B, miner, nick `uAfj1n1uS3p71jp`) |
| `bitcoin.exe` sha256 | `fbcac071d92e26d82ec917214e334bd43850c0691f113bab1d4741c9bdd30d2d` (+ shipped `libeay32.dll`, `mingwm10.dll`) |
| Guest OS | Windows 10 (64-bit), two VMs |

## What executed (JAN09-EXECUTED)

Two unmodified 2009 `bitcoin.exe` nodes, air-gapped, discovered each other over the original IRC path,
connected on port 8333, and — with **only node B mining** (node A a pure receiver, so relay isn't
starved by CPU contention):

| # | Observation | Result | Evidence |
|---|---|:--:|---|
| 1 | Both nodes recognise the historical genesis `000000000019d668…0a8ce26f` (Chancellor coinbase) | ✓ | `*/blk0001.dat` block 0 |
| 2 | Node A discovers node B via IRC (`GOT JOIN … CAddress(172.20.0.2:8333)`) and connects | ✓ | `nodeA/debug-excerpt.txt` |
| 3 | Node B's **peer-gated miner starts only after the peer connects** (`accepted connection from 172.20.0.1` → `BitcoinMiner started`) | ✓ | `nodeB/debug-excerpt.txt` |
| 4 | Node B **mines 3 blocks in succession** (`proof-of-work found` → `ProcessBlock: ACCEPTED`, heights 1→2→3), each below the difficulty-1 target `00000000ffff0000…` | ✓ | `nodeB/debug-excerpt.txt` |
| 5 | Node A **receives and accepts every block** (`inv` → `getdata` → `received block` → `AddToBlockIndex: new best` → `ProcessBlock: ACCEPTED`), climbing 1→2→3 in lockstep | ✓ | `nodeA/debug-excerpt.txt` |
| 6 | Both nodes end holding the **byte-identical** 4-block chain | ✓ | `nodeA/blk0001.dat` == `nodeB/blk0001.dat` (sha256 `aaf08aa3…6dbebc4c`) |

### The chain, verified from the raw `blk0001.dat` bytes

`verify_r4.py` (committed alongside this file) decodes **both** nodes' `blk0001.dat`, rebuilds the block
index, follows the height-based best chain, verifies every block's proof-of-work and prev-linkage, and
confirms both nodes converged on the same tip:

```
blocks in file: 4   best-chain height: 3   orphans (off-best): 0
[OK] h0  000000000019d668…  nonce=2083236893   <- genesis (real)
[OK] h1  000000005df5e9a1…  nonce=2048796966
[OK] h2  00000000092b5374…  nonce=1227982862
[OK] h3  00000000b719a917…  nonce=309381835
genesis is the real historical genesis: True
every best-chain block has valid PoW: True
BOTH NODES converged on the same best tip: True   (tip 00000000b719a917…, height 3)
```

The four blocks, from the raw bytes:

| Height | Hash | prev | nonce | nTime (VM) | merkle | coinbase scriptSig |
|:--:|---|---|--:|--:|---|---|
| 0 | `000000000019d668…0a8ce26f` | `0000…0000` | 2083236893 | 1231006505 | `4a5e1e…` | *Times 03/Jan/2009 …* |
| 1 | `000000005df5e9a1…5e04e039` | genesis | 2048796966 | 1785520070 | `aca421…` | `04ffff001d0101` |
| 2 | `00000000092b5374…c1b67a00` | block 1 | 1227982862 | 1785530882 | `9d1829…` | `04ffff001d0104` |
| 3 | `00000000b719a917…08965473` | block 2 | 309381835 | 1785531222 | `dee112…` | `04ffff001d0105` |

All three mined blocks are at real **difficulty 1** (`nBits=1d00ffff`), properly chained (each
`hashPrevBlock` = the previous block), each a valid PoW below `00000000ffff0000…`, all 50-coin coinbases.
The two independent nodes' 962-byte `blk0001.dat` hash identically (`aaf08aa3…`), so they agree byte for
byte that node B produced this run and node A accepted all of it.

## Divergences / surprises

- **Peer-gated miner confirmed again:** `BitcoinMiner started` appears in `nodeB/debug.log` immediately
  after `accepted connection from 172.20.0.1` — the released miner (`while(vNodes.empty())`, `main.cpp`)
  begins only with a connected peer, exactly as the source reads.
- **One miner keeps relay clean:** node A was left **not** mining, so CPU wasn't split and each block's
  `inv → getdata → block → ProcessBlock: ACCEPTED` completed without the CPU-starvation seen when both
  nodes mine (the mechanism R4b will instead exploit). Node A's log contains no `BitcoinMiner` lines.
- **`GetMyExternalIP()` fails** (harmless): it dials a public IP-echo host, unreachable in isolation.
- **Capture is a consistent snapshot** at height 3 — both nodes' `blk0001.dat` are byte-identical at the
  moment of copy. (Node B's miner continued afterward; immaterial to this witnessed snapshot.)

## Captured artifacts

Preserved and hashed in `EVIDENCE_MANIFEST.json` (bytes gitignored under `r4-evidence/`): both nodes'
**full `debug.log`**, both nodes' **`blk0001.dat`** (byte-identical, `aaf08aa3…`), and per-node annotated
`debug-excerpt.txt` (the discovery, mining, and relay lines). Both nodes' `blk0001.dat` re-parse to the
same height-3 chain and the same tip under `verify_r4.py`.

## Follow-up (run B, 1 Aug 2026): bidirectional production + relay, across a reboot

A second capture (`r4-evidence/.../run-b/`) strengthens R4a from one-directional to **bidirectional**.
With **both** nodes generating, the chain grew to **7 blocks (height 6)** and the two nodes still hold a
**byte-identical** `blk0001.dat` (sha256 `c8ff1c6cabf6897bff13eca7a2096a77592f31a3491674dca7f5cd32cfb113ea`),
same tip `000000001fad15d9…`, **0 orphans** (`verify_r4.py`). From the logs:

| node | mined (`proof-of-work found`) | received from peer | accepted (`ProcessBlock: ACCEPTED`) |
|---|:--:|:--:|:--:|
| A | **2** | 4 | 6 |
| B | **4** | 2 | 6 |

So each node both **produced** blocks and **validated and accepted the other's** — bidirectional
production and relay, converging on one chain (R4a only showed B→A). Two incidental robustness facts:
the extended chain shares R4a's `h1`/`h2` (`000000005df5e9…`/`00000000092b53…`), and it **survived an
unplanned guest reboot** — on restart both `bitcoin.exe` reloaded the persisted `blk0001.dat`,
re-discovered over IRC, and resumed on the same chain. No reorg occurred (0 `REORGANIZE`), consistent
with fast relay on a 2-node net; R4b remains open.

## Conclusion

At **JAN09-EXECUTED** level this run lifts **sustained multi-block mining and relay** from MODEL
(`derivatives/node`, `derivatives/p2p`) to the **released binary**: an unmodified v0.1.0 node mined
**three** valid difficulty-1 blocks in succession on top of the real genesis, and a second unmodified
node received, validated, and accepted **every** one, both ending on the identical four-block chain —
verified from the raw block bytes, not just the GUI. Together with R3 (single-block production + relay)
this closes **R4a**. Still deferred: **R4b** a reorganisation, and **R4c** a relayed spend (needs a
matured coinbase, ~101 blocks). **NOT money** — isolated network, real genesis, valueless by design.
