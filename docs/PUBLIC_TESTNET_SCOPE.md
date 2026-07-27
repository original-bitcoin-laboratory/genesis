# Public experimental testnet — honest scope (not a coin launch)

If you want NOV08‑X / JAN09‑X to be *live and joinable* rather than only a
reproducible recipe (`scripts/verify_genesis.py`), this is the honest gap between
what exists (a MODEL) and a network others can run. It is a **sustained
engineering + community effort**, not a switch — and it stays **experimental and
non‑monetary** throughout. Read this before deciding it's worth it.

## Why do this? — accessibility parity, not a coin

The point of a live network is narrow and honest: to give NOV08‑X / JAN09‑X the **same kind of
open accessibility a BTC or a BSV has** — a node a stranger can download, run, and sync — so they
stand as *equally accessible* candidates, not only reproducible artifacts. It closes the
**"network‑parity" rung** of
[`RELEASE_AS_CANDIDATES.md`](https://github.com/original-bitcoin-laboratory/common/blob/main/RELEASE_AS_CANDIDATES.md).
It does **not** make them money, and it does **not** make them "the real Bitcoin" — it makes them
*reachable on the same footing.*

## The hard truth about "eternal"

A chain persists only because **independent people choose to keep running it**. One
machine broadcasting is not a network; it lasts exactly as long as that process. So
the real deliverable isn't code — it's *other operators*. Everything below is
necessary but **not sufficient**; adoption is the sufficient part, and it can't be
engineered, only earned.

## The crux: "nothing disabled" is only safe *because* it isn't money

The reconstructions are faithful to the origin — which means they **carry the origin's missing
guardrails**: no `MoneyRange` (the value‑overflow surface), no block‑size cap, no script
element/op/stack limits, unbounded arithmetic (see
[`CONSENSUS_SURFACE.md`](https://github.com/original-bitcoin-laboratory/common/blob/main/conformance/CONSENSUS_SURFACE.md)).
On a **value‑bearing** chain those absences are exploitable — an overflow mints coins, unbounded
scripts/blocks are denial‑of‑service. On a **non‑monetary** chain they are **harmless research
curiosities**: there is nothing to steal, so an overflow is a *demonstration*, and a DoS costs a
restart, not money.

So *"nothing disabled"* and *"not money"* are **not two rules — they are the same rule.** The only
way to run the *undrifted* origin design in the open, safely, is to keep it valueless. Attach
value and you are **forced** to add the 2010 guardrails — at which point it is no longer the
origin (it has drifted), and you have simply re‑derived why those guardrails were added. That is
the real reason path C (money) is off: it would force the reconstruction to **stop being the
reconstruction.**

## Gap: MODEL → joinable node

| Area | Have (MODEL) | Need for a public testnet |
|---|---|---|
| Wire / P2P | localhost asyncio, no checksum, trusting | real sockets over the internet, message checksums, timeouts, reconnection, `addr` gossip |
| DoS resistance | none | rate limits, ban scoring, message‑size caps, orphan/mempool limits, misbehavior disconnects |
| Persistence | in‑memory + a KV‑file model | crash‑safe on‑disk block/UTXO store, reorg‑safe writes, restart recovery |
| Difficulty | regtest‑easy (instant) | a real retarget so blocks pace ~evenly and the chain can't be trivially rewritten |
| Mining | brute‑force in a test | a miner others can run; enough distributed hashpower that no single party dominates |
| Discovery | none | seed nodes / a DNS‑seed equivalent so a fresh node finds peers. **Delivered** a bootstrap **DNS seed** (`derivatives/dnsseed/`): crawls the network over the real wire, verifies reachable nodes on the right magic, and answers `A` queries with their IPs — one resolvable name meshes a stranger in |
| Wallet | minimal SelectCoins model | key backup, address book, resync, fee handling — safe enough for others to use. **Delivered** a persistent node wallet + loopback RPC (`netnode/nodewallet.py`, `rpc.py`); key encryption / backup discipline still absent (fine while valueless) |
| Build/dist | Python, run from repo | a packaged node + reproducible builds + signed releases. **Delivered** Docker + systemd **deploy templates** (`netnode/deploy/`); GPG‑signed releases still need the operator's key |
| Perf | Python, seconds‑scale | fast enough to validate a growing chain. **Measured** (`netnode/bench.py`): ~95% of validation time was ECDSA signature verification → **delivered** an optional **libsecp256k1 verifier** (`netnode/fastverify.py`, ~7× per signature, ~4–5× end‑to‑end), wired **byte‑faithfully** to the origin's pre‑BIP66 OpenSSL semantics (differential‑tested; normalize + fall back, so no BIP66 drift). A full native node remains only for extreme scale |

## A staged plan (each stage independently useful)

> **Status (27 Jul 2026): Stages 1–4 built + tested, and the production‑node core is done**
> in [`../derivatives/netnode/`](../derivatives/netnode/) (**45 tests**): hardened wire, crash‑safe
> store, real‑TCP sync, difficulty retarget, `addr`‑gossip discovery, DoS resource bounds, a tagged
> pre‑release, **block validation beyond PoW** (`fullnode.py`), a **validated UTXO chainstate**
> (`chainstate.py`) that is the **sole authority** for what the node serves and mines —
> double‑spends / bad scripts / inflation / immature‑coinbase / over‑claimed‑coinbase / **wrong‑
> difficulty** rejected (the difficulty check is authoritative **on connect**, so it also covers the
> **orphan reconnection** path), with reorg‑safe connect/disconnect that **aborts a reorg to an
> invalid branch** — a validating **mempool** (`mempool.py`): `tx` messages validated (fees
> recorded), pooled, and **relayed** (`inv`→`getdata`→`tx`), with an **orphan buffer** (retried when
> the parent arrives) and **fee‑rate eviction** when full, and the miner **assembles pooled
> transactions** after the coinbase (subsidy + fees), dropping them once mined — and an optional
> **`--min-difficulty` floor** so a live network can require real work above the deliberately‑easy
> (faithful) genesis; and a **wallet + localhost control interface** (`nodewallet.py`, `rpc.py`) — a
> mining node **earns its coinbase** to a persistent wallet and a person can `getbalance` /
> `getnewaddress` / `send` over a loopback RPC (`python -m netnode ctl`), all on the faithful v0.1
> SelectCoins / CreateTransaction path. The network now carries **real transactions**, and a person
> can **use** it without writing Python. A **performance harness** (`netnode/bench.py`) found **~95% of
> validation time is ECDSA signature verification**, so this session **delivered** that lever — an
> optional **libsecp256k1 verifier** (`netnode/fastverify.py`, ~7× per signature / ~4–5× end‑to‑end)
> wired **byte‑faithfully** to the origin's pre‑BIP66 OpenSSL semantics (it normalizes + falls back
> so it does **not** drift to the BIP66 strict rule; differential‑tested). Finally, the **operator
> rung** now has real infrastructure: a bootstrap **DNS seed** (`derivatives/dnsseed/`) that crawls
> the network and hands fresh nodes a resolvable set of live peers, **Docker + systemd deploy
> templates** (`netnode/deploy/`), and a **standalone Rust node** (`derivatives/validator-rs/`) —
> consensus‑complete (context‑free checks, stateful UTXO/value validation, the full v0.1 `EvalScript`
> interpreter with unbounded bignum + all opcodes + `OP_CHECKSIG`/`OP_CHECKMULTISIG` via real `k256`
> ECDSA byte‑faithful to pre‑BIP66 OpenSSL, and reorg + difficulty) **plus a runnable transport**
> (hardened wire, crash‑safe store, a real TCP **block‑sync + transaction relay** [`inv`→`getdata`→
> `tx`], **and transacting** — tx signing via `k256`, a validating mempool, and block assembly/mining,
> so a Rust node mines coins, pools a spend, mines it into a block, relays it to a peer, and
> **discovers peers via `addr` gossip**, and is **DoS‑hardened** — a bounds‑safe gate rejects
> malformed blocks with no panic, and misbehavior scoring drops flooding peers). Compiled + tested
> (24 tests) byte‑for‑byte against the Python node; the only remaining transport (a wallet/RPC control
> interface) exists + is tested in the Python `netnode`. Remaining toward a hardened public launch
> is no longer node‑core code: **choosing/running a real difficulty floor** on a live launch,
> GPG‑signed builds, a security review, the rest of a native node **only for extreme scale** — and,
> above all, **other people choosing to run it.**

1. **Harden the wire.** ✅ Checksums, real TCP, timeouts, reconnection, DoS size caps, misbehavior
   scoring — two nodes on *different machines* sync reliably (`netnode/wire.py`, `livenode.py`).
2. **Real difficulty + persistence.** ✅ A retarget following each chain's algorithm shape at the
   network's own spacing, floored at genesis, validated on receipt; a crash‑safe on‑disk store
   with restart recovery (`netnode/difficulty.py`, `store.py`).
3. **Discovery + a public seed.** ✅ `addr` gossip + auto‑connect *plus* a bootstrap **DNS seed**
   (`derivatives/dnsseed/`) that crawls + verifies reachable nodes and answers `A` queries with a
   live peer set. *(Standing up a seed with a fixed address + hostname is still the operator's part.)*
4. **A runnable release.** ✅ operator guide (`netnode/RUN.md`), threat model (`netnode/SECURITY.md`),
   versioning + a tagged GitHub release, and **Docker + systemd deploy templates** (`netnode/deploy/`);
   **GPG‑signed builds remain an operator step** (needs a signing key).
5. **Invite operators.** The chain is only "eternal" once **other people** run nodes 3 and 4 without
   you. The code lowers the bar (DNS seed + deploy templates); the *choosing to run it* can't be
   engineered, only earned.
6. *(Only if ever justified)* a faster node. ✅ *started* — the dominant cost (signature
   verification) is handled by the optional libsecp256k1 verifier, and a **standalone Rust node**
   (`derivatives/validator-rs/`) ports every consensus check — context‑free, stateful UTXO/value, the
   full v0.1 `EvalScript` interpreter, and reorg + difficulty — **plus a runnable transport** (hardened
   wire, crash‑safe store, real TCP block‑sync), compiled + tested byte‑for‑byte vs the Python. Only
   the richer transport features (gossip/mempool‑relay/DoS/RPC), already in the Python node, are not
   re‑ported — a second copy adds no capability.

## Non‑negotiable framing

- **Experimental / educational, never money.** The coinbase already says so. No
  premine, no sale, no "value," no promises. If value ever attaches to insecure
  experimental code, people get hurt — don't let that happen.
- **Security review before any public liveness.** MODEL code is not safe to expose;
  stage 1 is a rewrite for adversarial conditions, not a wrapper.
- **Provenance discipline stays.** New network code is `NEW‑EXP`; N‑ORIG consensus
  rules (NOV08's constitution) still win where November specifies.

## The honest recommendation

The **reproducible recipe** (`verify_genesis.py`) already gives you a durable, honest
kind of permanence — anyone can re‑derive the exact genesis forever, with no node to
maintain and no way to mislead. A live testnet adds *liveness* but also real
obligations (security, maintenance, and the framing above) and only becomes "eternal"
if strangers adopt it. Do stage 1–2 if you want the technical satisfaction of two
machines syncing a full‑capability chain over the real internet; go past stage 3 only
with eyes open about the community + responsibility it entails.
