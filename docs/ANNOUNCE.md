# An invitation to run the earliest Bitcoin — and the chain built from it

**Experimental. Educational. Not money.** This is an invitation to *operators*, not an offering. There
is nothing here to buy, sell, or hold, and there never will be. Read [why](#the-one-rule-that-makes-all-of-this-safe) before deciding it's worth your time.

## What these are

**NOV08‑X** and **JAN09‑X** are faithful, executable reconstructions of the earliest Bitcoin:

- **JAN09‑X** — the released reference client, **v0.1.0** (3 January 2009): its full opcode
  vocabulary, its value/consensus rules, its genesis‑born choices — with **nothing disabled** (none
  of the guardrails added from 2010 onward).
- **NOV08‑X** — the **pre‑release** of 15 November 2008: the design *before* the genesis block, where
  it differs from January (a 100‑coin subsidy, `COIN = 1e6`, ~15‑minute blocks, a leading‑zero‑bits
  proof‑of‑work).

A third chain runs alongside them and is **not** a reconstruction:

- **Bitcoin** — the same v0.1.0 client on a genesis of its own, mined at the original difficulty‑1,
  its coinbase carrying the front page of the day it was mined. Its own network, its own signed
  release (`Bitcoin-v0.1.3`). It does **not** interoperate with the two above, and it has its own
  seed rather than sharing the crawler.

The reconstructions are released as **candidates** — *a* Bitcoin, not *the* Bitcoin. That
distinction is the whole point, and it is made carefully in [`../../common/WHAT_IS_BITCOIN.md`](https://github.com/original-bitcoin-laboratory/common/blob/main/WHAT_IS_BITCOIN.md)
and [`../../common/RELEASE_AS_CANDIDATES.md`](https://github.com/original-bitcoin-laboratory/common/blob/main/RELEASE_AS_CANDIDATES.md).

## The honest claim (and the honest non‑claim)

- **We do not claim these are "the real Bitcoin."** "Which chain *is* Bitcoin" has **no factual
  answer** — BTC, BCH, BSV, and XEC all share one genesis and diverge by social convention, not by any
  measurable fact. Neither do we claim to settle it.
- **What we do claim is measurable:** NOV08‑X / JAN09‑X are **fidelity candidates** — new instances
  whose design sits at **distance 0** from the origin (see the interactive tracker at
  [`tracker.html`](https://bitcoin-lab.org/)). BTC and BSV are
  **continuity candidates** — branches of the launched chain. Both *kinds* are candidates; which lens
  counts (continuity vs fidelity) is itself a choice. So these stand as **equal contenders**, not
  lesser ones — they just haven't been *run by anyone but us yet.* That is what this invitation is for.
- **Distance is not identity, and not probability.** The tracker measures conformance to a chosen
  origin, nothing more.

## Two independent implementations

The consensus and the node exist **twice**, cross‑checked byte‑for‑byte:

- a Python node — [`../derivatives/netnode/`](../derivatives/netnode/) (validation, mempool, wallet,
  RPC, a ~7× libsecp256k1 verifier, the DNS seed);
- a Rust node — [`../derivatives/validator-rs/`](../derivatives/validator-rs/) (every consensus rule +
  the full v0.1 script interpreter + transport, 30 tests — validating **both** chains' consensus).

An independent second implementation that agrees to the byte is extra evidence the byte formats,
hashing, sighash, and value rules are pinned down.

## How to take part

1. **Verify the genesis yourself** — the durable, permanent artifact. `scripts/verify_genesis.py`
   re‑derives both genesis blocks from source; `scripts/reproduce.py` runs the whole lab (25/25). No
   node required, no way to be misled. This is the part that lasts forever.
2. **Run a node** — one command with the prebuilt image
   (`docker run --rm -v xnode-data:/data ghcr.io/original-bitcoin-laboratory/xnode`), or from source
   via [`../derivatives/netnode/RUN.md`](../derivatives/netnode/RUN.md) and the Docker/systemd
   templates in [`../derivatives/netnode/deploy/`](../derivatives/netnode/deploy/). Two people on two
   machines can sync a chain over the internet.
3. **Run a seed** — [`../derivatives/dnsseed/`](../derivatives/dnsseed/) hands fresh nodes a live set
   of peers. One resolvable name meshes a stranger in.
4. **Tell one other person.** A chain is "eternal" only once **independent** people keep nodes up. We
   can offer that; we can't manufacture it.

**Watch it live:** the [status page](https://bitcoin-lab.org/status.html) and
[block explorer](https://bitcoin-lab.org/explorer.html) show each chain's tip height, anchor uptime,
and recent blocks. **Verify what you run:** every release is GPG‑signed — check it against the
[published key](https://github.com/original-bitcoin-laboratory/genesis/blob/main/docs/VERIFY_RELEASES.md).

## Join the live network — peers you can connect to today

**Two** live, always‑on anchors run the two reconstructions side by side, and a third node serves
the Bitcoin chain:

```
seed.bitcoin-lab.org:18009      JAN09‑X  (Jan 2009 v0.1.0 genesis client · magic f00ba709)
seed.bitcoin-lab.org:18008      NOV08‑X  (15 Nov 2008 pre‑release · magic f00ba708 · leading‑zero‑bits PoW)
bitcoin.bitcoin-lab.org:18026   Bitcoin  (its own genesis 00000000ad12f3ec… · magic f00ba726 · difficulty‑1)
```

All three experimental, all **NOT money**. Join in **one command** with the prebuilt image — or clone and
run from source:

```bash
# Docker — one command, no setup (JAN09-X):
docker run --rm -v xnode-data:/data ghcr.io/original-bitcoin-laboratory/xnode
# NOV08-X (its own genesis + proof-of-work):
docker run --rm -v xnode-data:/data ghcr.io/original-bitcoin-laboratory/xnode \
    --chain nov08x --datadir /data --connect seed.bitcoin-lab.org:18008

# or from source (needs Python 3 + cryptography):
git clone https://github.com/original-bitcoin-laboratory/genesis
cd genesis/derivatives
python -m netnode --chain jan09x --datadir ./data-jan09 --connect seed.bitcoin-lab.org:18009
python -m netnode --chain bitcoin --datadir ./data-bitcoin --connect bitcoin.bitcoin-lab.org:18026
python -m netnode --chain nov08x --datadir ./data-nov08 --connect seed.bitcoin-lab.org:18008
```

Your node mints the matching genesis (JAN09‑X `51eec236…` / NOV08‑X `00000f08…`), dials the anchor,
and downloads **and independently re‑validates** every block until it reaches the tip. (Needs Python 3
+ `cryptography`; on Debian/Ubuntu install it in a `venv`. `bitcoinx` is optional — it enables the ~7×
verifier. Full steps: [`../derivatives/netnode/RUN.md`](../derivatives/netnode/RUN.md).)

This anchor is a **convenience, not an authority**: it can disappear tomorrow and nothing is lost —
the genesis is reproducible forever from `scripts/verify_genesis.py`, and any node you run is an equal
peer. The name `seed.bitcoin-lab.org` resolves to the anchor (`143.110.255.205` today); if the anchor
ever moves, the name follows it — so prefer the name, and the reproducible recipe over both. **Not money.**

### Or join Bitcoin with the released 2009 client

`bitcoin-0.1.3.tar.gz` ships the actual client, and it will find the network on its own — but read this
first, because it behaves like software from 2009, which is the point.

It has **no `-connect` and no `-addnode`**. Reading `mapArgs` in `ui.cpp`, the switches it honours are
`/datadir /proxy /debug /dropmessages /loadblockindextest /printblockindex /gen /randsendtest`. But it
learns peer addresses from **four** places, not three, and the fourth is the one that matters if you
are reading this long after 2026:

| source | `main.cpp` / `db.cpp` | works on a fresh install? |
|---|---|---|
| `addr.txt` — a plain text file you write | `CAddrDB::LoadAddresses`, "Load user provided addresses" | **yes** |
| IRC channel names | `irc.cpp:225` | yes |
| `addr` messages from a peer you already have | `main.cpp:1759` | no |
| `addr.dat` from a previous run | `db.cpp:419` | no |

So on startup it resolves `chat.freenode.net`, joins `#bitcoin26`, and reads the channel for names it
can decode into addresses — which is how it finds our seed by default, and how any other node finds
you.

**If IRC is unavailable — blocked, or Freenode simply gone — put a file called `addr.txt` next to
`bitcoin.exe`** containing one address per line:

```
168.144.27.117
```

`CAddrDB::LoadAddresses` reads it before anything else, and `CAddress`'s string constructor defaults
the port to `DEFAULT_PORT`, which this build has already patched to 18026 — so the bare IP is enough.
No switch, no eleventh line, no dependency on a third party outliving the chain.

*(**Executed 5 August 2026.** A fresh Windows guest was firewalled to allow outbound TCP to the seed
and nothing else — `Test-NetConnection 1.1.1.1 -Port 53` failed, so `chat.freenode.net` was
unreachable by construction and no IRC bootstrap was possible. With a 16-byte `addr.txt` containing
the bare address beside `bitcoin.exe`, the client opened and held a session to the seed, observed
from the seed side as an established connection to `168.144.27.117:18026`. `addr.txt` is therefore
the only path by which it could have learned that address.)*

**It announces itself the same way.** Its nickname is `EncodeAddress(addrLocalHost)`: your own routable
address, base58‑encoded, published into a public channel on infrastructure nobody here operates, where
anyone present can read it and the servers keep logs. `ThreadIRCSeed` starts unconditionally and there
is no `-noirc`; the only lever is the client's own `/proxy`, which leaves the local address unroutable
so the nickname falls back to a random value. There is no transport encryption, no authentication, and
`wallet.dat` is written in the clear. **Run it in an isolated VM.**

```
verify first:  sha256  d24469a4894ad40554fab111b823faf2aa57a42d901f38089a1bb87753c93c9b
then:          bitcoin.exe          # add /gen to mine
```

## The one rule that makes all of this safe

"**Nothing disabled**" is safe **only because** it is "**not money**." The reconstructions faithfully
carry the origin's *missing* guardrails (no value‑overflow check, no block‑size cap, no script
limits). On a **value‑bearing** chain those are exploitable; on a **valueless** one they are harmless
research curiosities — there is nothing to steal. Attach value and you are *forced* to add the 2010
guardrails, at which point it stops being the origin. **So these stay valueless. No premine, no sale,
no "token," no promises, ever — the maintainers assign the units no value and solicit no market;
whether anyone else values them is outside any software's control, but nothing here invites it.** (See
[`PUBLIC_TESTNET_SCOPE.md`](PUBLIC_TESTNET_SCOPE.md) and each
node's `SECURITY.md`.)

## What we are asking, and not asking

- **Asking:** inspect the code, verify the genesis, run a node or a seed, and — if it interests you —
  keep it up and invite someone else.
- **Not asking:** money, speculation, belief, or that you call it "the real Bitcoin." Logic and
  science care about definition and truth, not popularity.

A tool, never authority ([`../../common/AUTHORITY.md`](https://github.com/original-bitcoin-laboratory/common/blob/main/AUTHORITY.md)).
**Not money.**

---
*Repos: <https://github.com/original-bitcoin-laboratory> · seed the network with the DNS seed +
deploy templates · report issues on the genesis repo.*
