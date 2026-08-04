# Bitcoin

```
genesis   00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a
author    Satoshi Nakamoto   (holds the output key below)
coinbase  The Times 03/Aug/2026 Toll of schooling 'straitjacket'
output    50.00000000 -> P2PK 04c0414c…   (no value assigned)
nTime     1785781375 = 2026-08-03 18:22:55 UTC
nBits     0x1d00ffff        nNonce 33394338
magic     f00ba726          port 18026
```

## Run a node

```bash
# join
python3 -m netnode --chain bitcoin --datadir ./data --connect bitcoin.bitcoin-lab.org:18026

# be reachable
python3 -m netnode --chain bitcoin --datadir ./data \
        --listen [::]:18026 --advertise YOUR_PUBLIC_IP
```

A public node in one command: [`deploy/provision.sh`](deploy/provision.sh) (Ubuntu, systemd, ufw).

## Mine

    height 0  00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a   3 Aug 2026
    height 1  000000007beb32b8380089595a91261a5ce4fbd4ece0cd661683cb1ce81e407c   4 Aug 2026

Block 1 was mined by the released client itself and relayed to the seed, which validated and stored
it with a different implementation. Block 2 onward are unmined and anyone may take them.

Blocks cost difficulty-1 work — about 2³² hashes — so the client's own miner takes roughly an hour
per block on one core. There is nothing to buy, nothing to claim, and nothing owed to whoever mines
next.

## Build

```bash
python make_chain.py                      # derive the client source
SRC=$PWD/src bash ../build-reconstruction/full_build_wsl.sh
bash make_release.sh                      # -> dist/bitcoin-0.1.2.tar.gz
```

`make_chain.py` composes the client source from two inputs: the v0.1.0 source tree, SHA256
`8b17eb9a5707f2519defda4cdf8d14fa1b8dee630e11e6ef85ff9f5547555b56`, and
[`bitcoin-v0.1.0.patch`](bitcoin-v0.1.0.patch) — this chain's genesis, network magic and port, and
bootstrap channel. It refuses to run unless every substitution matches exactly once, so the build
either reproduces or fails loudly.

## Verify

```bash
python make_chain.py --check   # the source is that tree plus exactly those nine substitutions
python net.py                  # re-derives the genesis hash; checks it meets difficulty-1
```

The client asserts the genesis hash on startup, so a wrong build does not run.

## Not money

No premine of value, no token, no sale, no market, no promises. The 50-coin genesis output has no
value assigned. The consensus rules carry no `MoneyRange` and no script limits, and no 1 MB block cap — that
arrives in July 2010; here the only ceiling is `MAX_SIZE`, 32 MiB, which `CheckBlock` does enforce —
safe here only because there is nothing to steal. Run the client in a VM.

MIT. `license.txt` in the release is the source's own and is unmodified.
