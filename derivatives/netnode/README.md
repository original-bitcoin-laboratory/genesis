# netnode — a hardened, joinable, validating, transacting node for the X‑chains (Path B)

**Evidence: MODEL / NEW‑EXP. Not money. Not production‑secure.** This is **Stages 1–4 + a full‑node
core + a wallet** from the plan in
[`../../docs/PUBLIC_TESTNET_SCOPE.md`](../../docs/PUBLIC_TESTNET_SCOPE.md): turning the MODEL's
localhost demo into something **two people on different machines can run, sync, pace, discover
peers on, validate, transact on, and *use*.** The **validated UTXO chainstate is the sole
authority** for what the node serves and mines, a validating **mempool** carries real transactions
between peers, and a **wallet + a localhost control interface** let a person mine to a self‑custodied
key, check a balance, and send a payment — without writing a line of Python.

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
| Wallet | — | a persistent **wallet** ([`nodewallet.py`](nodewallet.py), on the faithful v0.1 wallet MODEL) — a mining node **earns its coinbase** to it, and it **builds + signs payments** (SelectCoins / CreateTransaction), plus a localhost **control interface** ([`rpc.py`](rpc.py)) — `getinfo` / `getnewaddress` / `getbalance` / `send` via `python -m netnode ctl` |
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

## Use it (wallet + control)

Mine to your own wallet and open a **localhost** control interface:

```bash
python -m netnode --chain jan09x --datadir ./data --no-listen --mine --wallet --rpc 127.0.0.1:18332
```

Then drive it from another shell (loopback only — do **not** expose the RPC port):

```bash
python -m netnode ctl --rpc 18332 getinfo
python -m netnode ctl --rpc 18332 getnewaddress          # a fresh receive address (a pubkey)
python -m netnode ctl --rpc 18332 getbalance             # spendable (mature) balance
python -m netnode ctl --rpc 18332 send <ADDRESS> <AMOUNT> [FEE]
```

The wallet earns each block's coinbase; a coinbase is spendable after maturity. **Not money** — the
wallet stores experimental testnet keys for a valueless chain.

## Performance — where validation time goes ([`bench.py`](bench.py))

Before rewriting anything in C++/Rust you measure where the time goes. `python bench.py` builds a
chain of real **signed** transactions and times validating it from scratch:

```bash
python bench.py            # ~300 blocks; prints blocks/sec, tx/sec, sigs/sec + the dominant cost
```

The finding is consistent in **shape** (the ratio is machine‑independent even though the absolute
rate isn't): **~95% of validation time is ECDSA signature verification.** On a typical dev machine
that is on the order of ~1,000+ blocks/sec and a few thousand signature‑verifications/sec, at
~0.3–0.4 ms per `verify_spend`. So a faster node's real lever is a **native verifier (libsecp256k1)
/ batch verification**, *not* rewriting the Python bookkeeping — the pure‑Python node keeps up until
a chain is large or high‑throughput. (This session also made block‑connect avoid re‑serializing
every transaction to hash it — txids now come straight from the parsed bytes.)

## Tests (`test_netnode.py` + `test_chainstate.py` + `test_mempool.py` + `test_wallet.py`, 53)

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
which it leaves the pool, and a **tx relays over real TCP** into a second node's mempool. The wallet
**persists its keys** across restart, **earns its coinbase** (respecting maturity), **builds a
payment owned by the recipient**, and refuses an overspend; and the RPC control socket answers
`getinfo` / `getbalance` / `getnewaddress` and **builds + submits** a payment via `send`.

```bash
python -m pytest        # 53 passed
python -m netnode --chain jan09x --datadir ./d --no-listen --mine   # watch it mine
```

## Honest boundary — what this is *not*

The X‑chains are now **joinable, self‑pacing, self‑discovering, resource‑bounded, fully‑validating,
transacting, and usable**: a validated UTXO chainstate (the **sole authority** for what the node
serves and mines) rejects double‑spends / bad scripts / inflation / over‑claimed coinbases and
reorgs safely, a validating **mempool** relays real transactions into assembled blocks, and a
**wallet + localhost RPC** let a person mine, check a balance, and send — but this is *not* safe as
money or "eternal." The difficulty *floor* exists (`--min-difficulty`) but **defaults to easy** (a
real one is an operator job); the RPC is **loopback‑only and unauthenticated**; the wallet holds
**experimental keys for a valueless chain.** Still ahead (see the scope doc): running at a **real
difficulty**, GPG‑**signed** builds, a **security review**, a **faster node** if Python can't keep
up (and [`bench.py`](bench.py) says the lever is a native signature verifier, not a rewrite of the
bookkeeping), and — the part no code delivers — **other operators.** A chain is only "eternal" once
independent people choose to keep running it. **Not money.**

Provenance: consensus is `chainsync.Chain` (faithful to v0.1); the transport, persistence, and CLI
are **NEW‑EXP**. A tool, never authority (`../../../common/AUTHORITY.md`).
