# dnsseed — a bootstrap DNS seed for the X‑chains (operator infrastructure)

**Evidence: NEW‑EXP. Not money.** A chain becomes reachable to strangers only if a fresh node can
**find its first peers**. The netnode already meshes via `addr` gossip once you have *one* peer —
this provides that one peer, the standard Bitcoin way: an **authoritative DNS name** that resolves
to a live set of node IPs.

It has two halves:

- **[`crawler.py`](crawler.py)** connects to candidate nodes over the real netnode wire (magic +
  checksum framing), does the `version` handshake — proving a node is *reachable and on the right
  chain* — and harvests the peers it gossips, expanding the known set. Only nodes that answer are
  marked **healthy**.
- **[`server.py`](server.py)** is an authoritative UDP DNS server ([`dnsmsg.py`](dnsmsg.py) is the
  RFC‑1035 codec) that answers `A` queries for your zone with a shuffled batch of those healthy IPs.

## Run it

```bash
python -m dnsseed --chain jan09x --zone seed.example.test \
                  --seed A_KNOWN_NODE:18009 --listen 0.0.0.0:5354
```

A fresh node then bootstraps by resolving the name (in practice you delegate `seed.example.test` to
this server with an `NS` record so port‑53 resolvers reach it; binding `:53` directly needs
privileges). Swap `jan09x`↔`nov08x` — each chain has its own magic/port, so the seed only reports
nodes actually on that chain.

## Why this is the "operators" piece

Everything else in the lab is code you can finish; a live chain's last mile is **other people
running nodes**, and they need to find each other. A DNS seed is the smallest durable thing that
turns "I know one node's IP" into "anyone can join": publish the zone, keep the seed + at least one
node up, and newcomers mesh in automatically. It is offered, not authoritative — anyone can run
their own seed, or hard‑code peers instead. See [`../netnode/RUN.md`](../netnode/RUN.md) ("Running a
public seed") and [`../../docs/PUBLIC_TESTNET_SCOPE.md`](../../docs/PUBLIC_TESTNET_SCOPE.md).

## Tests (`test_dnsseed.py`, 3)

The DNS codec round‑trips a query + A‑record response; the UDP server answers a real query with the
healthy IPs; and the crawler, over the real netnode wire, marks a live node reachable on the right
magic, **rejects a wrong‑magic node**, harvests its gossiped address, and reports it healthy.

```bash
python -m pytest        # 3 passed
```

**Not money.** A tool, never authority (`../../../common/AUTHORITY.md`).
