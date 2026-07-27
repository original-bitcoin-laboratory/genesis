# NOV08‑X and JAN09‑X — an invitation to run the earliest Bitcoin, faithfully

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

They are released as **candidates** — *a* Bitcoin, not *the* Bitcoin. That distinction is the whole
point, and it is made carefully in [`../../common/WHAT_IS_BITCOIN.md`](https://github.com/original-bitcoin-laboratory/common/blob/main/WHAT_IS_BITCOIN.md)
and [`../../common/RELEASE_AS_CANDIDATES.md`](https://github.com/original-bitcoin-laboratory/common/blob/main/RELEASE_AS_CANDIDATES.md).

## The honest claim (and the honest non‑claim)

- **We do not claim these are "the real Bitcoin."** "Which chain *is* Bitcoin" has **no factual
  answer** — BTC, BCH, BSV, and XEC all share one genesis and diverge by social convention, not by any
  measurable fact. Neither do we claim to settle it.
- **What we do claim is measurable:** NOV08‑X / JAN09‑X are **fidelity candidates** — new instances
  whose design sits at **distance 0** from the origin (see the interactive tracker at
  [`tracker.html`](https://original-bitcoin-laboratory.github.io/genesis/)). BTC and BSV are
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
  the full v0.1 script interpreter + transport, 25 tests).

An independent second implementation that agrees to the byte is extra evidence the byte formats,
hashing, sighash, and value rules are pinned down.

## How to take part

1. **Verify the genesis yourself** — the durable, permanent artifact. `scripts/verify_genesis.py`
   re‑derives both genesis blocks from source; `scripts/reproduce.py` runs the whole lab (21/21). No
   node required, no way to be misled. This is the part that lasts forever.
2. **Run a node** — [`../derivatives/netnode/RUN.md`](../derivatives/netnode/RUN.md) and the
   Docker/systemd templates in [`../derivatives/netnode/deploy/`](../derivatives/netnode/deploy/). Two
   people on two machines can sync a chain over the internet.
3. **Run a seed** — [`../derivatives/dnsseed/`](../derivatives/dnsseed/) hands fresh nodes a live set
   of peers. One resolvable name meshes a stranger in.
4. **Tell one other person.** A chain is "eternal" only once **independent** people keep nodes up. We
   can offer that; we can't manufacture it.

## Join the live network — peers you can connect to today

**Two** live, always‑on anchors run the two reconstructions side by side:

```
seed.bitcoin-lab.org:18009    JAN09‑X  (Jan 2009 v0.1.0 genesis client · magic f00ba709)
seed.bitcoin-lab.org:18008    NOV08‑X  (15 Nov 2008 pre‑release · magic f00ba708 · leading‑zero‑bits PoW)
```

Both experimental, both **NOT money**. Clone the repo and point a node at whichever you want to run:

```bash
git clone https://github.com/original-bitcoin-laboratory/genesis
cd genesis/derivatives

# the January 2009 v0.1.0 chain
python -m netnode --chain jan09x --datadir ./data-jan09 --connect seed.bitcoin-lab.org:18009

# the November 2008 pre-release chain (its own genesis, its own proof-of-work)
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

## The one rule that makes all of this safe

"**Nothing disabled**" is safe **only because** it is "**not money**." The reconstructions faithfully
carry the origin's *missing* guardrails (no value‑overflow check, no block‑size cap, no script
limits). On a **value‑bearing** chain those are exploitable; on a **valueless** one they are harmless
research curiosities — there is nothing to steal. Attach value and you are *forced* to add the 2010
guardrails, at which point it stops being the origin. **So these stay valueless. No premine, no sale,
no "token," no promises, ever.** (See [`PUBLIC_TESTNET_SCOPE.md`](PUBLIC_TESTNET_SCOPE.md) and each
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
