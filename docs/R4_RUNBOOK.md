# R4 runbook — sustained mining, reorg (and optional tx relay) between two real 2009 nodes

**Goal.** Lift three behaviours from *modeled* to *witnessed on the unmodified 2009 `bitcoin.exe`*:
**R4a** sustained multi-block mining + relay; **R4b** a reorganisation; **R4c** (optional, overnight) a
relayed spend. Evidence level target: **JAN09-EXECUTED**. **NOT money.**

This is a solo re-run of the R3 setup with new capture goals. The R3 VMs were deleted, so it starts with a
rebuild. Do it on a machine with spare disk (~60 GB) and CPU. All the tooling is in this repo.

---

## What you need

- **VirtualBox** 7.x (+ Extension Pack optional).
- The **v0.1.0 archive** — `bitcoin.exe` + `libeay32.dll` + `mingwm10.dll`. Get it from
  `https://cdn.nakamotoinstitute.org/code/bitcoin-0.1.0.rar` (also in this repo at
  `artifacts/jan09/bitcoin-0.1.0.rar`). The exe **must** hash to the oracle
  `fbcac071d92e26d82ec917214e334bd43850c0691f113bab1d4741c9bdd30d2d`.
- From this repo, copy onto each VM's `C:\obl`: `derivatives/r3/mini_ircd.py` (the discovery daemon, with
  the bare-`\r` fix) and `scripts/capture-evidence.py`.
- On the **host** (any OS with Python 3): `derivatives/r4/verify_r4.py` (the chain/reorg verifier).

## Gotchas carried over from R3 (read before you start)

1. `bitcoin.exe` needs **`libeay32.dll` + `mingwm10.dll` shipped beside it** — copy all three into `C:\obl`.
2. `mini_ircd.py` already has the fix: v0.1 ends IRC lines with a **bare `\r`**, so it reads `readuntil(b"\r")`.
   Use the repo copy; don't retype it.
3. v0.1 stores the chain in **`%APPDATA%\Bitcoin\blk0001.dat`**, but writes **`debug.log` to the current
   directory** (`C:\obl` if you launch from there). Launch `bitcoin.exe` from `C:\obl`.
4. **`IsRoutable`** rejects `10.x` and `192.168.x` — the isolated net must be **`172.16–31.x`** (we use
   `172.20.0.0/24`).
5. The miner is **peer-gated** (`while(vNodes.empty())`): a node mines **only while it has ≥1 connected peer**.
6. Both nodes mining continuously **saturates CPU and starves relay** — that's a bug for R4a (use one miner)
   but the *mechanism* we exploit for R4b.
7. After editing the `hosts` file, run **`ipconfig /flushdns`** and restart `bitcoin.exe`.

---

## Part 0 — Rebuild the two VMs

**0.1 Guest OS (pick one).**
- **Path A (fastest):** import Microsoft's free pre-built Windows dev VM (VirtualBox appliance) — no ISO, no
  install: download, **File → Import Appliance**, boot. It's Windows 11; the 32-bit `bitcoin.exe` runs under
  WOW64 with the shipped DLLs (small unknown — if it won't launch, fall back to Path B).
- **Path B (matches R3):** install **Windows 10** from ISO (Rufus). Slower but validated. See
  `R3_LAYMAN_RUNBOOK.md` for the granular install screenshots.

**0.2 Base node (do this on ONE VM, then clone).**
1. Create `C:\obl`. Extract the v0.1.0 archive into it so `C:\obl` has `bitcoin.exe`, `libeay32.dll`,
   `mingwm10.dll`. Verify the exe's SHA-256 = `fbcac071…`.
2. Copy `mini_ircd.py`, `capture-evidence.py` into `C:\obl`. Install Python 3 (for `mini_ircd.py`).
3. Edit `C:\Windows\System32\drivers\etc\hosts`, add:  `172.20.0.1   chat.freenode.net`
4. Turn **Windows Firewall off** (or allow TCP 8333 + 6667) for this isolated lab.
5. Shut down. In VirtualBox: **Settings → Network → Adapter 1 → Internal Network**, name `obl-r4`.

**0.3 Clone for the second node.** Right-click the VM → **Clone → Full clone** → name it node B.

**0.4 Static IPs (inside each guest).** Set Adapter 1 to a static IPv4:
- **node A:** `172.20.0.1` / `255.255.255.0` (no gateway)
- **node B:** `172.20.0.2` / `255.255.255.0`

Confirm `ping 172.20.0.2` (from A) and `ping 172.20.0.1` (from B) both reply.

**0.5 Discovery.** On **node A** only, open a terminal in `C:\obl` and run:
`python mini_ircd.py`  → it prints `mini_ircd listening on … (channel #bitcoin)`. Leave it running.

**0.6 Boot both nodes.** Launch `bitcoin.exe` from `C:\obl` on both. Within a minute, `debug.log` on each
should show the IRC handshake, then a P2P connect (node A learns `…ff ff ac 14 00 02` = `172.20.0.2`). If
discovery stalls, re-check step 2 (bare-`\r`) and step 7 (flushdns). This reproduces R3 up to block 1.

---

## Part 1 — R4a: sustained multi-block mining + relay (~1 hr, deterministic)

1. On **node B only**: **Options → Generate Coins** (or launch `bitcoin.exe /gen`). **Leave node A NOT
   mining** — it stays a pure receiver so the CPU isn't split and blocks relay cleanly.
2. Node B mines blocks **2 → ~6** on top of block 1 (difficulty-1 ≈ 10–15 min/block average, high variance).
   Watch **node A's** block count climb in lockstep; `nodeA\debug.log` shows, per block:
   `got inventory: block <hash> → askfor → received block → ProcessBlock: ACCEPTED`.
3. When node A shows ~6 blocks, turn **Generate Coins off** on node B.
4. Capture: copy each node's `%APPDATA%\Bitcoin\blk0001.dat` and `C:\obl\debug.log` to the host.
5. Verify on the host:
   `python verify_r4.py nodeA/blk0001.dat nodeB/blk0001.dat`
   **Expect:** best-chain height ~6, *every* block valid PoW, genesis = the real historical genesis,
   **0 orphans**, and **both nodes converged on the same tip**. That's sustained production + relay witnessed.

---

## Part 2 — R4b: a reorganisation (stochastic; run until it happens)

The miner is peer-gated, so you can't cleanly partition two nodes and keep mining. Instead exploit relay
latency: **run BOTH miners at once.** Under CPU saturation, relay lags mining, so the two nodes occasionally
mine the *same height* independently → a fork → the taller branch wins → the other node **reorgs**, orphaning
its block(s). This is a real reorg on the real binary; it's just not deep or scheduled.

1. Note the current agreed tip/height (end of R4a).
2. Turn **Generate Coins ON on BOTH** node A and node B. Let them run.
3. Watch for a reorg on either node's `debug.log` — lines like `REORGANIZE` / a new best block whose prev is
   *not* the previous tip / a block count that steps back then jumps forward.
4. Let it run until at least one reorg has occurred (could be minutes or a couple of hours — the more blocks
   mined, the likelier). Turn both miners **off**.
5. Capture both `blk0001.dat` + `debug.log` again.
6. Verify:
   `python verify_r4.py nodeA/blk0001.dat nodeB/blk0001.dat`
   **Expect:** on the node that reorged, **≥1 orphan off the best chain** (its abandoned block), and **both
   nodes converged on the same (taller) tip**. `verify_r4.py` prints `reorg witnessed (>=1 orphan …): True`.

*(Advanced, optional deterministic variant: run two isolated node-pairs — {A,A2} and {B,B2} — each pair
mining in isolation so each has a peer, build a short branch on one pair and a taller branch on the other,
then bridge A↔B and watch the shorter side reorg. Needs 4 VMs; only do this if the stochastic reorg won't
converge for you.)*

---

## Part 3 — R4c: a relayed spend (OPTIONAL, overnight)

Hard constraint: coinbase outputs are spendable only after **100 confirmations**, and there's no premine, so
the first spendable coin appears at **block ~101** ≈ ~a day of difficulty-1 mining. Only do this if you want
the tx-relay cell witnessed on the real binary.

1. On node B, mine **≥101 blocks** (leave it running overnight; node A receiver).
2. Once block 1's coinbase has matured, on node B: **Send Coins** → pay node A (v0.1 supports pay-to-IP
   `172.20.0.1`, or send to a node-A address).
3. Confirm the tx **relays** (`nodeA\debug.log`: `received tx …`) and is **mined into a block** (appears in a
   subsequent block; recipient balance updates on node A).
4. Capture `blk0001.dat` + `debug.log` + wallet screenshots.

---

## Evidence capture & write-up

- Mirror the R3 layout. Create `r4-findings/<YYYY-MM-DD>-sustained-and-reorg/` for the committed write-up +
  hashed manifest, and keep raw bytes under the gitignored `r4-evidence/<same>/`.
- Run `python scripts/capture-evidence.py --run <YYYY-MM-DD>-sustained-and-reorg` (same tool as R3) to hash
  everything into `EVIDENCE_MANIFEST.json`.
- Write `FINDINGS.md` like `r3-findings/2026-07-31-twonode-mined-block/FINDINGS.md`: environment, the
  `verify_r4.py` output (heights, PoW, orphans, convergence), both `bitcoin.exe` = `fbcac071…`, and the
  divergences (peer-gated miner, stochastic reorg, maturity constraint for R4c).
- Then update `docs/STATUS.md` + the paper §8: move sustained mining + reorg from "modeled/deferred" to
  **witnessed (r4-findings/…)**; if you skip R4c, keep tx-relay explicitly headless-only.

**NOT money.** Isolated networks, real genesis, valueless by design.
