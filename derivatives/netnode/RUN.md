# Running an experimental X‑chain node

> **This is not money.** `NOV08‑X` / `JAN09‑X` are experimental research networks carrying the
> original Bitcoin vocabulary with **nothing disabled** — released as *candidates*, not "the real
> Bitcoin," and explicitly valueless. There is no coin to buy, sell, or hold. Read
> [`SECURITY.md`](SECURITY.md) before exposing a node to the internet.

## Requirements

- **Python 3.10+.** No external packages — the node uses only the standard library plus this
  repository's own modules. Just clone the repo and run from `genesis/derivatives/`.

```bash
git clone https://github.com/original-bitcoin-laboratory/genesis
cd genesis/derivatives
python -m netnode --version
```

## Quick start (two machines)

**Machine A** — the first node, mining and listening:

```bash
python -m netnode --chain jan09x --datadir ./data-a --listen 0.0.0.0:18009 \
                  --advertise <A_PUBLIC_IP> --mine
```

**Machine B** — join with A's address; discovery does the rest:

```bash
python -m netnode --chain jan09x --datadir ./data-b --connect <A_PUBLIC_IP>:18009 \
                  --advertise <B_PUBLIC_IP>
```

B handshakes, pulls the chain over TCP, stays in sync as A mines, and learns any other peers A
knows through `addr` gossip — you only ever need **one** reachable address to mesh in.

## The two chains

| Chain | `--chain` | Default port | Proof‑of‑work |
|---|---|---|---|
| November constitution | `nov08x` | 18008 | leading‑zero‑bits |
| January (v0.1.0) constitution | `jan09x` | 18009 | compact target |

Each has its own genesis, magic, and port; they cannot connect to each other or to any historical
or live Bitcoin chain.

## Options

| Flag | Meaning |
|---|---|
| `--chain {nov08x,jan09x}` | which experimental chain |
| `--datadir DIR` | where the block store lives (survives restarts) |
| `--listen HOST:PORT` | bind address (default `0.0.0.0:<chain port>`) |
| `--no-listen` | outbound‑only (won't accept inbound peers) |
| `--connect HOST:PORT` | a peer/seed to dial (repeatable; discovery finds the rest) |
| `--advertise HOST` | your **reachable** IP, gossiped so peers can dial you back |
| `--mine` | produce blocks |
| `--version` | print version and exit |

## Running a public seed

A "seed" is just a normal node with a **stable, reachable address** that others `--connect` to
first. Run it with `--listen 0.0.0.0:18009 --advertise <STABLE_IP>`, open that port in your
firewall, and keep the process up (e.g. under `systemd` / `tmux`). Publish the `IP:PORT` so others
can bootstrap; from there `addr` gossip meshes newcomers automatically.

## Data & restarts

Blocks are written to `<datadir>/blocks.dat` (fsync'd). On restart the node **reloads its chain
from disk** and resumes — no re‑sync from genesis. Deleting the datadir resets the node.

## Transactions

The node carries **real transactions**, not just coinbases. A received `tx` is validated against
the node's UTXO (no double‑spend, script satisfied, no inflation, coinbase maturity), pooled, and
relayed onward (`inv`→`getdata`→`tx`); a mining node **assembles pooled transactions** into its
next block after the coinbase, which then claims the block subsidy **plus** the transactions' fees.
Building and signing a spend is a **programmatic** step today — construct a signed transaction with
the lab's `tx_sighash` / `spend` helpers and hand its raw bytes to `Node.submit_tx(raw)`, which
validates it into the mempool and broadcasts it. (A wallet CLI is deliberately out of scope while
this is valueless; see [`../wallet/`](../wallet/) for the SelectCoins / CreateTransaction model.)

## Troubleshooting

- **Peers can't reach you** → you're likely behind NAT/firewall. Forward the port and set
  `--advertise` to your public IP. Without a reachable address you can still *connect out* and
  sync, you just won't accept inbound peers.
- **"bad magic" / instant disconnects** → the peer is on a different chain (or a different
  network entirely). Both sides must use the same `--chain`.
- **Nothing is syncing** → confirm the seed is actually listening and the port is open
  (`--listen 0.0.0.0:PORT`), and that you passed the seed via `--connect`.

## Remember

It's a research microscope, not a currency. If it ever gets treated as money on unaudited,
easy‑difficulty experimental code, people get hurt — don't let that happen. See
[`SECURITY.md`](SECURITY.md) and [`../../docs/PUBLIC_TESTNET_SCOPE.md`](../../docs/PUBLIC_TESTNET_SCOPE.md).
