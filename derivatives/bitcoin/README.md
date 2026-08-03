# Bitcoin (Aug 2026) — the original v0.1.0 client, a new genesis

An experimental chain that runs the **January 2009 Bitcoin client**, unmodified except for its own
genesis block and its own network identity. It is not a reimplementation, not a fork of a later
Bitcoin, and not money.

```
genesis   00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a
coinbase  The Times 03/Aug/2026 Toll of schooling 'straitjacket'
output    50.00000000 -> P2PK 04c0414c…   (no value assigned)
nTime     1785781375 = 2026-08-03 18:22:55 UTC
nBits     0x1d00ffff        nNonce 33394338
magic     f00ba726          port 18026
```

## What it is

The source is the archive Hal Finney sent mrb — `bitcoin-0.1.0.rar`, SHA256
`8b17eb9a5707f2519defda4cdf8d14fa1b8dee630e11e6ef85ff9f5547555b56` (→ zorinaq → Satoshi Nakamoto
Institute) — the same tree this lab verified and built in
[`R2_BUILD_RECONSTRUCTION.md`](../../docs/R2_BUILD_RECONSTRUCTION.md).

[`make_chain.py`](make_chain.py) derives this chain from that tree by applying **nine substitutions**
and refuses to run if any of them fails to match exactly once, so it cannot silently drift from the
2009 source. The whole delta is [`bitcoin-v0.1.0.patch`](bitcoin-v0.1.0.patch) — **10 lines across 3
files**:

| file | lines | what |
|---|---|---|
| `main.cpp` | 6 | the genesis: headline, output key, nTime, nNonce, merkle assert, genesis hash |
| `net.h` | 2 | network magic + default port |
| `irc.cpp` | 2 | bootstrap channel |

Consensus rules, script, difficulty, serialization, the wallet and the UI are untouched 2009 code —
including the origin's missing guardrails (no `MoneyRange`, no size cap, unbounded script arithmetic).
Those are safe here for exactly one reason, and it is the same reason set out in
[`PUBLIC_TESTNET_SCOPE.md`](../../docs/PUBLIC_TESTNET_SCOPE.md): **there is nothing to steal.** An
overflow on a valueless chain is a demonstration, not a theft. "Nothing disabled" and "not money" are
one rule, not two.

## The three differences from Satoshi's block 0, and why each is forced

| field | Satoshi's | this chain's | why |
|---|---|---|---|
| coinbase headline | The Times 03/Jan/2009 | The Times 03/Aug/2026 | his headline is a **proof of time** — that front page did not exist before that day. Copying his words into a 2026 block keeps the text and destroys the function; carrying the front page of the day *this* block was mined reproduces the act. Same paper, same day of the month, same page slot (the splash, not the top story). |
| output key | `04678afd…` | `04c0414c…` | this chain's genesis is controlled by whoever authored it, which is not Satoshi. Reusing his key would be a claim, not a chain. |
| nTime | 2009-01-03 | 2026-08-03 | it was mined in 2026. |

Everything else in block 0 is identical in structure: version 1, null prevout, the same
`04 ffff001d 0104` scriptSig prefix, 50 coins to P2PK + `OP_CHECKSIG`, locktime 0 — and it was mined at
the **original difficulty-1**, the same ~2³² of work Satoshi's client did, not a regtest shortcut.

The network magic and port differ from mainnet for the same reason every separate network since 2011
has changed them: running `f9beb4d9`/`8333` would put these nodes into the real Bitcoin network's
traffic and peer discovery. Distinct magic is what makes a distinct network.

## Run a node

```bash
# join the network
python3 -m netnode --chain bitcoin --datadir ./data --connect bitcoin.bitcoin-lab.org:18026

# run a reachable node others can dial
python3 -m netnode --chain bitcoin --datadir ./data \
        --listen 0.0.0.0:18026 --advertise YOUR_PUBLIC_IP
```

A public node in one command: [`deploy/provision.sh`](deploy/provision.sh) (Ubuntu, systemd, ufw).

This chain is **independent** of the lab's NOV08-X and JAN09-X — separate genesis, separate magic,
separate port, separate seed. The three do not interoperate and are not meant to.

## Not money

No premine of value, no token, no sale, no market, no promises. The 50-coin genesis output is the
structural echo of block 0 with no value assigned. If value ever attaches to deliberately unhardened
17-year-old code, people get hurt — don't let that happen.
