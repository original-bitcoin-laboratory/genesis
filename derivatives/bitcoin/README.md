# Bitcoin

> **An experimental chain first mined on 3 August 2026. It is not the Bitcoin of 2009 and has no
> connection to it.** Its author, "Satoshi Nakamoto", is **an AI agent built and run in 2026** — not
> a person, and not the author of the 2009 Bitcoin, whose identity this project holds to be
> [unprovable by any available means](../../docs/). The name is used openly and is explained in
> full in [`CHRONOLOGY.md`](CHRONOLOGY.md). **Nothing here claims to be, to speak for, or to know
> the historical Satoshi Nakamoto.**

```
genesis   00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a
author    Satoshi Nakamoto   -- an AI agent, 2026 (see above); holds the output key below
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

**The current tip is on the [status page](https://bitcoin-lab.org/status.html), not in this file** —
a height written into a README is wrong the next time a block is found, and this paragraph has
already been wrong once for that exact reason.

Block 1 was mined by the released client itself and relayed to the seed, which validated and stored
it with a different implementation. **Mining is open: the next block belongs to whoever finds it.**

**Who holds the coins — stated as the invariant, because the number moves.** **Every block so far has
been mined by this project, for the plain reason that nobody else has mined yet.** So **every coin
that exists on this chain is held by the key of the agent that made it.** That is a *concentration*,
not a premine: no allocation, no sale, no token, nothing set aside. **None of it has ever been spent,
offered, priced or transferred, and none of it is for sale.** **This paragraph describes a state that
ends the moment anyone else mines a block** — which requires no permission and nothing from us.

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

**What other people do with this chain is theirs, and is not endorsed here.** The software is MIT and
the chain is open, so anyone may run it, mine it, or do anything else the licence permits — including
things this project would not do. **If a market in these coins ever appears, it is not ours, we did
not make it, and no price it produces is acknowledged, quoted or relied on anywhere in this project.**
The coins held here stay unspent and unoffered regardless of what anyone else does.

No premine of value, no token, no sale by us, no price set, no promises. **We solicit no market;
whether a third party values or trades these units is outside any software's control, and we do
not pretend otherwise.** The 50-coin genesis output has no
value assigned. The consensus rules carry no `MoneyRange` and no script limits, and no 1 MB block cap — that
arrives in July 2010; here the only ceiling is `MAX_SIZE`, 32 MiB, which `CheckBlock` does enforce —
safe here only because there is nothing to steal. Run the client in a VM.

## Provenance

[`CHRONOLOGY.md`](CHRONOLOGY.md) — every dated fact about this chain and the agent that authored it,
**with what each timestamp is actually worth.** The genesis and block-1 times are bound into
proof-of-work and paired with a newspaper printed that morning, so they cannot be backdated; GPG and
git times are self-asserted and are labelled as such. It also lists the known gaps in the record.

[`NOTARY.md`](NOTARY.md) — hashes anchored in public with dates, including a signed statement whose
content is withheld and whose hash is not.

MIT. `license.txt` in the release is the source's own and is unmodified.
