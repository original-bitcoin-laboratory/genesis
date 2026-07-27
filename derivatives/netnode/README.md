# netnode — a hardened, joinable, validating, transacting node for the X‑chains (Path B)

**Evidence: MODEL / NEW‑EXP. Not money. Not production‑secure.** This is **Stages 1–4 + a full‑node
core** from the plan in
[`../../docs/PUBLIC_TESTNET_SCOPE.md`](../../docs/PUBLIC_TESTNET_SCOPE.md): turning the MODEL's
localhost demo into something **two people on different machines can run, sync, pace, discover
peers on, validate, and transact on.** The **validated UTXO chainstate is the sole authority** for
what the node serves and mines, and a validating **mempool** carries real transactions between
peers — not just coinbases.

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
| Difficulty | fixed genesis (easy) | **retarget** — mine at the target, **reject** wrong‑nBits blocks on the direct path *and* authoritatively **on connect** (covers the orphan path); optional **`--min-difficulty` floor** for real work above the easy genesis ([`difficulty.py`](difficulty.py)) |
| Validation | PoW only | **beyond PoW** — structure/merkle/difficulty ([`fullnode.py`](fullnode.py)) + a **validated UTXO chainstate** that is the **sole authority** for serving/mining — no double‑spends / bad scripts / inflation / immature‑coinbase / over‑claimed coinbase / wrong‑difficulty, reorg‑safe with abort‑on‑invalid ([`chainstate.py`](chainstate.py)) |
| Transactions | — | a validating **mempool** ([`mempool.py`](mempool.py)) — `tx` messages validated, pooled, and **relayed** (`inv`→`getdata`→`tx`), with an **orphan buffer** (retried when the parent arrives) and **fee‑rate eviction** when full; the miner assembles pooled txs after the coinbase (claiming subsidy + fees) and drops them once mined |
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

## Tests (`test_netnode.py` + `test_chainstate.py` + `test_mempool.py`, 45)

The wire rejects a tampered checksum / bad magic / oversize; the store ignores a crash‑truncated
tail; **two nodes sync over real TCP**; a node **reloads its chain from disk**; the retarget
math nudges/floors correctly and the compact target round‑trips; a node **rejects a block with a
forged nBits**; **three nodes mesh** (C discovers A purely through B's `addr` gossip and syncs A's
chain); the resource bounds hold — a **bounded peer table**, an **inbound‑connection cap**, and a
**rate limit that drops a flooding peer**; block validation works — the parser round‑trips, a
**tampered merkle root** is rejected, and an **over‑claimed coinbase** is accepted by the index but
**rejected by the validated chainstate**; the UTXO chainstate accepts a valid spend while rejecting
a **double‑spend / inflation / immature‑coinbase spend / bad signature**, and **aborts a reorg to
an invalid branch, restoring the prior chain**; a **min‑difficulty floor** raises the required work
above the easy genesis and is enforced on connect, and a **forged‑difficulty orphan** that
reconnects into the PoW index is **rejected by the authoritative connect gate**; and the mempool
accepts a valid spend (recording its **fee**), rejects a **double‑spend / inflation / bad signature
/ immature‑coinbase spend**, allows and **orders a chained unconfirmed spend** (parent before
child), **holds an orphan tx and promotes it when the parent arrives**, **evicts by fee rate** when
full, **drops a mined tx** on reconcile, the miner **assembles a pooled tx into a block** after
which it leaves the pool, and a **tx relays over real TCP** into a second node's mempool.

```bash
python -m pytest        # 45 passed
python -m netnode --chain jan09x --datadir ./d --no-listen --mine   # watch it mine
```

## Honest boundary — what this is *not*

The X‑chains are now **joinable, self‑pacing, self‑discovering, resource‑bounded, fully‑validating,
and transacting**: a validated UTXO chainstate (the **sole authority** for what the node serves and
mines) rejects double‑spends / bad scripts / inflation / over‑claimed coinbases and reorgs safely,
and a validating **mempool** relays real transactions and feeds them into assembled blocks — but
this is *not* safe as money or "eternal." The difficulty *floor* now exists (`--min-difficulty`),
but it **defaults to easy** and choosing/coordinating a real one is an operator job. Still ahead
(see the scope doc): running at a **real difficulty**, GPG‑**signed** builds, a **security review**,
a **faster node** (C++/Rust) if Python can't keep up, and — the part no code delivers — **other
operators.** A chain is only "eternal" once independent people choose to keep running it. **Not
money.**

Provenance: consensus is `chainsync.Chain` (faithful to v0.1); the transport, persistence, and CLI
are **NEW‑EXP**. A tool, never authority (`../../../common/AUTHORITY.md`).
