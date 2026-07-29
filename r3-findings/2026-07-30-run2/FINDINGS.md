# R3 run findings — `2026-07-30-run2`

Evidence level: **JAN09-EXECUTED** (the unmodified v0.1.0 `bitcoin.exe` executed
directly). Raw artifacts are hashed in `EVIDENCE_MANIFEST.json` (bytes stay under the
gitignored `r3-evidence/2026-07-30-run2/`); each claim below cites a supporting file.

> This run is a **single-node host execution**, not the two-VM network run the template
> envisions. Its principal result is a *finding about the origin's miner* rather than a
> mined block; the two-node mined-block setup is in `docs/R3_HISTORICAL_NODE.md`.

## Environment

| Field | Value |
|---|---|
| Date / operator | 2026-07-30, ~00:06–02:11 local; host operator |
| Host | Windows 11 (the released Win32 GUI binary runs on the modern host) |
| Network | Wi-Fi interface up, but the exe blocked outbound by a Windows Firewall rule `obl-block-bitcoin-v01`; **0 peers** throughout |
| `bitcoin.exe` sha256 | `fbcac071d92e26d82ec917214e334bd43850c0691f113bab1d4741c9bdd30d2d` (verified live — `screenshots/Screenshot 2026-07-29 235124.png` → `3888a73a…`) |

## What executed (JAN09-EXECUTED)

| # | Observation | Result | Evidence |
|---|---|:--:|---|
| 1 | Binary starts and **validates the real genesis** `000000000019d668…a8ce26f` | ✓ | `debug.log` → `247acc0d…`: `LoadBlockIndex(): hashBestChain=000000000019d6  height=0` |
| 2 | **Miner thread starts** (`fGenerateBitcoins = 1`, `BitcoinMiner started`) | ✓ | `debug.log` |
| 3 | Runs the **real 2009 IRC discovery** (`chat.freenode.net` → `JOIN #bitcoin`) | ✓ | `debug.log`: freenode NOTICE + `Registration timeout` (the bootstrap is long dead) |
| 4 | Sustained run: **1 block, 0 connections** at start (00:06) and unchanged after 2 h (02:11) | ✓ | `screenshots/…000630.png` → `82f3c092…`; `…021143.png` → `f93fae64…` |
| 5 | **No block mined** (the miner never hashed) | — (expected) | `blk0001.dat` = 293 B, genesis only → `29961184…`; no hashmeter in `debug.log` |

## ★ Finding — the origin's miner is peer-gated (a lone node cannot mine)

`BitcoinMiner()` parks in `while (vNodes.empty())` (`main.cpp:2195`) until at least one
peer connects, so a single isolated node **starts the miner thread but never hashes**.
Confirmed independently: over the 2-hour run the process used **~13 CPU-seconds** (idle),
emitted **no hashmeter line** (v0.1 logs `khash/s` every 30 min *only while hashing*), and
produced no block. Discovery is **IRC-only** (`irc.cpp:148`), there is **no
`-connect`/`-addnode`**, and the freenode `#bitcoin` bootstrap is long dead — so the node
has 0 peers and the miner stays parked indefinitely.

**This is a behaviour of the earliest client, not a defect:** it could not mine in
isolation — it needed the IRC rendezvous to find a peer before the miner would hash.
(Contrast: the lab's `netnode` reconstruction has no such gate and mines standalone — a
NEW-EXP operational choice, not a consensus rule; see `docs/R3_HISTORICAL_NODE.md`.)

## Conclusion

At **JAN09-EXECUTED** level this run supports: the unmodified 2009 binary boots on the
modern host, **validates the real genesis** `000000000019d668…`, starts its miner, and
runs its original IRC peer-discovery — a direct, hash-anchored execution witness of the
released client's startup, consensus-genesis check, and networking path, with the binary
hash matching the archived `fbcac071…`. It does **not** support sustained mining or block
production, which the origin's peer-gated miner precludes for a lone node; those remain at
**MODEL/PORT** (the headless C++ port re-derives the genesis and mines block 1; the live
Python/Rust networks mine and relay) pending the two-node IRC run
(`docs/R3_HISTORICAL_NODE.md`).
