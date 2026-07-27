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
| Validation | PoW only | **beyond PoW** — structure, merkle commitment, difficulty, coinbase‑value rule ([`fullnode.py`](fullnode.py)) |
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

## Tests (`test_netnode.py`, 20)

The wire rejects a tampered checksum / bad magic / oversize; the store ignores a crash‑truncated
tail; **two nodes sync over real TCP**; a node **reloads its chain from disk**; the retarget
math nudges/floors correctly and the compact target round‑trips; a node **rejects a block with a
forged nBits**; **three nodes mesh** (C discovers A purely through B's `addr` gossip and syncs A's
chain); the resource bounds hold — a **bounded peer table**, an **inbound‑connection cap**, and a
**rate limit that drops a flooding peer**; and full block validation works — the block/tx parser
round‑trips, and a block with an **over‑claimed coinbase** or a **tampered merkle root** is
rejected.

```bash
python -m pytest        # 20 passed
python -m netnode --chain jan09x --datadir ./d --no-listen --mine   # watch it mine
```

## Honest boundary — what this is *not*

Stages 1–4 make the X‑chains **joinable, self‑pacing, self‑discovering, resource‑bounded, and
block‑validating** — but *not* safe as money or "eternal." Block validation is now beyond PoW
(structure/merkle/difficulty/coinbase), but **full transaction/UTXO validation** (double‑spends,
scripts, no‑inflation, with reorg‑safe connect/disconnect) is the active next increment; the
retarget still starts at an easy floor (fine *only* because it is not money). Still ahead (see the
scope doc): the full‑node validation program, GPG‑**signed** builds, a **security review**, a
**faster node** (C++/Rust) if Python can't keep up, and — the part no code delivers — **other
operators.** A chain is only "eternal" once independent people choose to keep running it. **Not
money.**

Provenance: consensus is `chainsync.Chain` (faithful to v0.1); the transport, persistence, and CLI
are **NEW‑EXP**. A tool, never authority (`../../../common/AUTHORITY.md`).
