# Public experimental testnet — honest scope (not a coin launch)

If you want NOV08‑X / JAN09‑X to be *live and joinable* rather than only a
reproducible recipe (`scripts/verify_genesis.py`), this is the honest gap between
what exists (a MODEL) and a network others can run. It is a **sustained
engineering + community effort**, not a switch — and it stays **experimental and
non‑monetary** throughout. Read this before deciding it's worth it.

## The hard truth about "eternal"

A chain persists only because **independent people choose to keep running it**. One
machine broadcasting is not a network; it lasts exactly as long as that process. So
the real deliverable isn't code — it's *other operators*. Everything below is
necessary but **not sufficient**; adoption is the sufficient part, and it can't be
engineered, only earned.

## Gap: MODEL → joinable node

| Area | Have (MODEL) | Need for a public testnet |
|---|---|---|
| Wire / P2P | localhost asyncio, no checksum, trusting | real sockets over the internet, message checksums, timeouts, reconnection, `addr` gossip |
| DoS resistance | none | rate limits, ban scoring, message‑size caps, orphan/mempool limits, misbehavior disconnects |
| Persistence | in‑memory + a KV‑file model | crash‑safe on‑disk block/UTXO store, reorg‑safe writes, restart recovery |
| Difficulty | regtest‑easy (instant) | a real retarget so blocks pace ~evenly and the chain can't be trivially rewritten |
| Mining | brute‑force in a test | a miner others can run; enough distributed hashpower that no single party dominates |
| Discovery | none | seed nodes / a DNS‑seed equivalent so a fresh node finds peers |
| Wallet | minimal SelectCoins model | key backup, address book, resync, fee handling — safe enough for others to use |
| Build/dist | Python, run from repo | a packaged node + reproducible builds + signed releases |
| Perf | Python, seconds‑scale | fast enough to validate a growing chain (likely a C++/Rust node, or heavy optimization) |

## A staged plan (each stage independently useful)

1. **Harden the wire.** Add checksums, real TCP over the internet, timeouts,
   reconnection, `addr` gossip, and the DoS caps. Two nodes on *different machines*
   sync reliably.
2. **Real difficulty + persistence.** Wire the chain's actual retarget (NOV08's
   ±1‑bit / JAN09's proportional) and a crash‑safe store; a node survives restart and
   reorgs.
3. **Discovery + a public seed.** Stand up one or two seed nodes with fixed
   addresses; document how a stranger points a node at them and syncs from genesis.
4. **A runnable release.** Package the node, write install/run docs, publish signed
   builds. This is the "docs so others can join" step.
5. **Invite operators.** The chain is only "eternal" once **other people** run
   nodes 3 and 4 without you. This is community work, not code.
6. *(Only if ever justified)* a faster node (C++/Rust) if the Python one can't keep up.

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
