# R3 run findings — `run1`

Evidence level: **JAN09-EXECUTED** for the genesis + wallet-key claims (the
unmodified v0.1.0 `bitcoin.exe` was run and its outputs captured). Raw artifacts are
hashed in `EVIDENCE_MANIFEST.json` (bytes stay under the gitignored
`r3-evidence/run1/`). Short hashes below; full values in `SHA256SUMS`.

This was a **single-node run on the operator's Windows 11 host** (not a VM). It was
enough to obtain the primary witness — the released binary reconstructs the exact
genesis — and to document the full original UI. Sustained mining and the two-node
network were **not** completed on the host (see Divergences) and remain for a VM run.

## Environment

| Field | Value |
|---|---|
| Date / operator | 2026-07-26 / repo operator (host run) |
| Host / "guest" OS | Windows 11 Home (ran `bitcoin.exe` directly, WOW64) |
| Isolation | Wi-Fi off for the genesis capture; later online (GUI stability) |
| Network peers | **0 connections** throughout (see Divergences — IRC discovery dead) |
| `bitcoin.exe` sha256 | `fbcac071d92e26d82ec917214e334bd43850c0691f113bab1d4741c9bdd30d2d` (verified pre-run) |
| Data dir | `C:\Users\…\AppData\Roaming\Bitcoin` (per `debug.log`) |

## Checklist results

| # | Observation | Result | Evidence → sha256 | Notes |
|---|---|:--:|---|---|
| 1 | Node starts; **constructs & recognises genesis** `…19d668…a8ce26f` | **PASS** | `host/debug.log` → `6810d66588861089…` | full header + coinbase logged |
| 2 | Genesis **on disk** independently re-parses to the canonical hash | **PASS** | `host/blk0001.dat` → `29961184…` (293 B) | re-hashed by the lab, matches |
| 3 | Wallet **generates a key/address** | **PASS** | `host/wallet.dat` → `3893f8ec…` | `mapKeys.size()=1`; addr `18YDsakgPomUc9ZZHyivxWmdTyke2L26j8` |
| 4 | Block index persists best chain | **PASS** | `host/blkindex.dat` → `295cee74…` | `LoadBlockIndex(): hashBestChain=…19d6 height=0` |
| 5 | Full original **GUI documented** | **PASS** | `host/screenshots/*.png` (6, hashed) | main + 5 dialogs; see below |
| 6 | `/gen` mining produces block 1+ (coinbase matures at 100) | **deferred** | — | miner started; no `proof-of-work found` at capture (difficulty-1 grind) |
| 7 | Two-node connect / relay / tx / reorg | **deferred** | — | needs 2 VMs; not attempted on host |

## What the binary logged (genesis, `debug.log` → `6810d665…`)

```
000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f      (block hash)
4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b      (merkle root)
CBlock(hash=…19d6, ver=1, hashPrevBlock=00…00, hashMerkleRoot=4a5e1e,
       nTime=1231006505, nBits=1d00ffff, nNonce=2083236893, vtx=1)
  CTxIn(coinbase 04ffff001d0104 45 "The Times 03/Jan/2009 Chancellor on brink
        of second bailout for banks")
  CTxOut(nValue=50.00000000, scriptPubKey=<65-byte pubkey> OP_CHECKSIG)
AddToBlockIndex: new best=000000000019d6  height=0
```

**Cross-agreement:** these values equal (a) our headless C++ port `node_port.cpp`
and (b) our Python model, and I re-parsed `blk0001.dat` independently → block hash
`000000000019d668…a8ce26f`, merkle `4a5e1e…deda33b`, coinbase = the Times headline.
Live binary = PORT = MODEL.

## GUI screenshots (full-screen, `host/screenshots/`, hashed in the manifest)

Bytes stay under the gitignored `r3-evidence/run1/host/screenshots/`; SHA-256 short
hashes below (full in `SHA256SUMS`). All six show `0 connections` and `1 blocks`.

| File | Shows | sha256 |
|---|---|---|
| `…193214.png` | main window — address `18YDsakg…`, Balance 0.00, `1 blocks` | `3bb525f143e485f5…` |
| `…193220.png` | **Send Coins** — pay-to-IP ("recipient's IP address … for online transfer") | `382688c615c23645…` |
| `…193228.png` | Address Book (empty) | `cf2a932e31a2a71e…` |
| `…193242.png` | Options — Transaction fee `0.00` | `dabb9b9fad1ea6bf…` |
| `…193254.png` | **About** — "Bitcoin version 0.1.1 Alpha, © 2009 Satoshi Nakamoto", MIT/X11 + OpenSSL | `7f071d27e3413a60…` |
| `…193302.png` | Options menu — **Generate Coins ✓** (miner enabled) | `312e53bc107a0d9b…` |

## Divergences / surprises (all source-consistent)

- **GUI stability on Win11.** Offline, the 2009 wxWidgets GUI crashes the process
  ~2 s after start (7 relaunches in `debug.log`); **online it is stable**. The
  consensus + Berkeley-DB layers ran flawlessly either way (genesis built, `blk*/`
  `blkindex/wallet.dat` written) — the instability is purely the old GUI. This is
  why the genesis witness was obtainable on the bare host with no VM.
- **Discovery is dead.** `GetMyExternalIP()` to `72.233.89.199:80` fails (defunct
  checkip host, tolerated); IRC connects to freenode but the modern server times out
  the 2009 registration (`IRC ERROR: Closing link … Registration timeout`) →
  **0 peers**, so the node stayed isolated even while online. Confirms the R3 plan's
  premise that a local `mini_ircd` is required for a real two-node run.
- **Version string.** The About box reads **"version 0.1.1 Alpha"** — the source
  computes `strprintf("version 0.%d.%d Alpha", VERSION/100, VERSION%100)` with
  `VERSION=101` (serialize.h:22). So the binary shipped in the *0.1.0* archive
  self-identifies as **0.1.1**, and `101` is exactly the `PROTOCOL_VERSION` our P2P
  port uses (`derivatives/p2p`).
- **Pay-to-IP.** The Send-Coins dialog offers payment to a *"recipient's IP address …
  for online transfer"* (or a bitcoin address if offline) — the early IP-to-IP
  payment mode Bitcoin later removed. Captured live.

## Conclusion

The core R3 claim is now supported at **JAN09-EXECUTED**: the unmodified v0.1.0
binary, run from the hash-verified archive, **reconstructs the exact genesis block**
(hash `000000000019d668…`, merkle `4a5e1e…`, nonce `2083236893`, the Times-headline
coinbase, 50-coin reward) and persists it — in three-way agreement with the lab's
headless **PORT** (`node_port.cpp`) and **MODEL**. Wallet key generation is likewise
executed. **Sustained mining (block 1+) and the two-node network (relay / tx / reorg)
remain at `MODEL`/`PORT` + `JAN09-SOURCE`**, deferred to a Windows-XP VM where the
GUI is stable; the headless ports (`derivatives/node`, `derivatives/p2p`) already
cover those behaviours. Net: the produce-and-validate genesis is now witnessed by the
original software itself.
