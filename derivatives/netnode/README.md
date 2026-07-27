# netnode — a hardened, joinable node for the X‑chains (Path B, Stage 1)

**Evidence: MODEL / NEW‑EXP. Not money. Not production‑secure.** This is **Stage 1** of the plan
in [`../../docs/PUBLIC_TESTNET_SCOPE.md`](../../docs/PUBLIC_TESTNET_SCOPE.md): turning the MODEL's
localhost demo into something **two people on different machines can actually run and sync.**

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

B handshakes, pulls the chain over real TCP, and stays in sync as A mines. Swap `jan09x` for
`nov08x` (magic `f00ba708`, port `18008`, leading‑zero‑bits PoW) for the November constitution.
Each chain has its **own identity** (magic / port / genesis) and **cannot** connect to any
historical or live chain.

## Tests (`test_netnode.py`, 8)

The wire rejects a tampered checksum / bad magic / oversize; the store ignores a crash‑truncated
tail; **two nodes sync a chain over real TCP sockets**; a node **reloads its chain from disk** on
restart.

```bash
python -m pytest        # 8 passed
python -m netnode --chain jan09x --datadir ./d --no-listen --mine   # watch it mine
```

## Honest boundary — what Stage 1 is *not*

This makes the X‑chains **joinable**; it does **not** make them safe as money or "eternal." Still
ahead (see the scope doc): **Stage 2** a real difficulty retarget (this mines at regtest‑easy
difficulty — trivially rewritable, which is fine *only* because it is not money); **Stage 3**
peer discovery / seed nodes / `addr` gossip (today discovery is manual `--connect`); **Stage 4** a
packaged, signed release; a **security review** before any real public liveness; **Stage 6** a
faster node if Python can't keep up; and — the part that can't be engineered — **other operators.**
A chain is only "eternal" once independent people choose to keep running it. **Not money.**

Provenance: consensus is `chainsync.Chain` (faithful to v0.1); the transport, persistence, and CLI
are **NEW‑EXP**. A tool, never authority (`../../../common/AUTHORITY.md`).
