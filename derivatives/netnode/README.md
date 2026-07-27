# netnode — a hardened, joinable, validating node for the X‑chains (Path B)

**Evidence: MODEL / NEW‑EXP. Not money. Not production‑secure.** This is **Stages 1–4 + the start
of full‑node validation** from the plan in
[`../../docs/PUBLIC_TESTNET_SCOPE.md`](../../docs/PUBLIC_TESTNET_SCOPE.md): turning the MODEL's
localhost demo into something **two people on different machines can run, sync, pace, discover
peers on, and validate.**

It keeps the lab's **faithful consensus** ([`../p2p/chainsync.py`](../p2p/chainsync.py) `Chain`:
validation, height‑based reorg, orphans, block‑locator) and wraps it in the **adversarial‑conditions
transport** a public node needs — the "rewrite for adversarial conditions," not a wrapper.

## What's hardened (vs the faithful MODEL wire)

| | MODEL (`../p2p`) | netnode (Stage 1) |
|---|---|---|
| Framing | magic + command + size, **no checksum** | + **checksum** + **4 MiB size cap** ([`wire.py`](wire.py)) |
| Stalls | trusting, blocks forever | **read timeouts** → drop the peer |
| Bad peers | — | **misbehavior scoring** → ban/disconnect |
| Persistence | in‑memory | **crash‑safe on‑disk store** + restart recovery ([`store.py`](store.py)) |
| Connections | one shot | **outbound reconnection** with backoff |
| Blocks | — | **relay** (`inv`) to other peers + optional **miner** |
| Difficulty | fixed genesis (easy) | **retarget** — mine at the target, **reject** peers' wrong‑nBits blocks ([`difficulty.py`](difficulty.py)) |
| Validation | PoW only | **beyond PoW** — structure, merkle, difficulty, coinbase value ([`fullnode.py`](fullnode.py)) + a **validated UTXO chainstate** — no double‑spends / bad scripts / inflation, reorg‑safe with abort‑on‑invalid ([`chainstate.py`](chainstate.py)) |
| Discovery | manual only | **`addr` gossip + auto‑connect** — one seed address meshes you in |
| Run it | a pytest scenario | a **CLI** anyone can run (`python -m netnode`) |

## Run it (two machines)

Machine **A** — seed + miner:

```bash
python -m netnode --chain jan09x --datadir ./data-a --listen 0.0.0.0:18009 --mine
```

Machine **B** — join and sync (use A's LAN/public IP):

```bash
python -m netnode --chain jan09x --datadir ./data-b --connect A_HOST:18009
```

B handshakes, pulls the chain over real TCP, stays in sync as A mines, and — via **`addr`
gossip** — discovers the rest of the network from that one seed address (no manual `--connect`
chain). Set `--advertise YOUR_PUBLIC_IP` so peers can dial you back. Swap `jan09x` for `nov08x`
(magic `f00ba708`, port `18008`, leading‑zero‑bits PoW) for the November constitution. Each chain
has its **own identity** (magic / port / genesis) and **cannot** connect to any historical or
live chain.

**Operator guide → [`RUN.md`](RUN.md)** (seeds, ports, NAT, troubleshooting).
**Security posture + known gaps → [`SECURITY.md`](SECURITY.md)** — read it before exposing a node.

## Tests (`test_netnode.py` + `test_chainstate.py`, 30)

The wire rejects a tampered checksum / bad magic / oversize; the store ignores a crash‑truncated
tail; **two nodes sync over real TCP**; a node **reloads its chain from disk**; the retarget
math nudges/floors correctly and the compact target round‑trips; a node **rejects a block with a
forged nBits**; **three nodes mesh** (C discovers A purely through B's `addr` gossip and syncs A's
chain); the resource bounds hold — a **bounded peer table**, an **inbound‑connection cap**, and a
**rate limit that drops a flooding peer**; full block validation works — the parser round‑trips
and an **over‑claimed coinbase** / **tampered merkle root** is rejected; and the UTXO chainstate
accepts a valid spend while rejecting a **double‑spend / inflation / immature‑coinbase spend / bad
signature**, and **aborts a reorg to an invalid branch, restoring the prior chain.**

```bash
python -m pytest        # 30 passed
python -m netnode --chain jan09x --datadir ./d --no-listen --mine   # watch it mine
```

## Honest boundary — what this is *not*

The X‑chains are now **joinable, self‑pacing, self‑discovering, resource‑bounded, and
fully‑validating** (a UTXO chainstate rejects double‑spends / bad scripts / inflation and reorgs
safely) — but *not* safe as money or "eternal." The validated chainstate runs alongside the index
but the node still **serves/mines on the PoW‑selected tip** (they coincide on today's
coinbase‑only network); making the validated chain the sole authority + adding a **mempool + tx
relay** is the next increment, and the retarget still starts at an easy floor (fine *only* because
it is not money). Still ahead (see the scope doc): that authoritative wiring, GPG‑**signed**
builds, a **security review**, a **faster node** (C++/Rust) if Python can't keep up, and — the part
no code delivers — **other operators.** A chain is only "eternal" once independent people choose to
keep running it. **Not money.**

Provenance: consensus is `chainsync.Chain` (faithful to v0.1); the transport, persistence, and CLI
are **NEW‑EXP**. A tool, never authority (`../../../common/AUTHORITY.md`).
