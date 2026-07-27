# The OpenSSL thread — Bitcoin's load‑bearing dependency and how it was unwound

A synthesis essay: the single most consequential external dependency of the origin
(`inventory/DEPENDENCIES.md`) was **OpenSSL**, and it sat *inside consensus* in two
places. Removing it from consensus is one of Bitcoin's longest de‑risking arcs — and it
is exactly the arc this lab's dependency inventory, C++ PORT, and descendant matrix map.

> **Tier note.** The *source facts* (v0.1's `EC_KEY`/`BIGNUM` usage) are Tier 0, read from
> the hash‑verified tree. The *historical arc* (dates, versions) is Tier‑4 context,
> sourced below and dated — verify before quoting.

## 1. Where OpenSSL lived in v0.1 (from our source reading)

Two consensus‑critical things ran through OpenSSL's **general‑purpose** code:

- **Signatures / keys** — `key.h`: OpenSSL `EC_KEY` on the `secp256k1` curve, with
  `ECDSA_sign` / `ECDSA_verify`. Signature **verification** is a consensus rule.
- **Script arithmetic** — `bignum.h`: `CBigNum` wraps OpenSSL's arbitrary‑precision
  `BIGNUM`; every numeric/splice opcode (`OP_ADD`, `OP_MUL`, `OP_LSHIFT`, `OP_CAT`, …)
  computed on it.

Consensus needs **every node to agree, byte‑for‑byte, forever**. A library optimized for
general correctness/speed is the wrong thing to place there. That mismatch produced two
distinct hazards, and two distinct fixes.

## 2. Thread A — signature validity → BIP66 → libsecp256k1

**The hazard.** ECDSA signatures are DER‑encoded, and OpenSSL's parser was **lenient** —
accepting non‑canonical encodings. Two effects:
- **Malleability** — re‑encode a signature, keep validity, change the txid.
- **Consensus divergence (the dangerous one)** — whether a borderline signature was
  "valid" could depend on the **OpenSSL version/platform**. Different builds → different
  verdicts → **chain split**. A consensus rule was outsourced to "whichever OpenSSL you
  linked."

**The near‑miss (concrete).** **BIP66 (Strict DER)** made nodes parse signatures with
their own strict, deterministic parser instead of trusting OpenSSL. It activated at the
95% threshold on **4 July 2015, block 363,725** (enforced by Bitcoin Core 0.10+). Within
hours a non‑upgraded miner produced an invalid block, and because ~half the hashrate was
**SPV‑mining** (building on headers without full validation), the invalid chain reached
**six blocks deep** — costing miners **>$50,000** and prompting a "wait 30 confirmations"
advisory. A live demonstration of exactly the outsourced‑consensus risk.

**The replacement.** **`libsecp256k1`** — a from‑scratch, Bitcoin‑only C library for the
secp256k1 curve, started by **Pieter Wuille (initial commit 5 March 2013)**. Its reasons
are the three failures above:
- **Determinism** — small, specified, auditable; identical behavior everywhere (removes
  "which OpenSSL version" from consensus);
- **Constant‑time** — no secret‑dependent branches/timing (side‑channel resistance);
- **Performance** — specialized field/group arithmetic; verification **2.5–5.5× faster**.

Migration was staged: **signing** in Bitcoin Core **v0.10 (2015)**, then the
consensus‑critical **ECDSA verification** in **v0.12 (2016)** — the moment OpenSSL left
consensus. OpenSSL was **finally removed entirely from Bitcoin Core in 2019**.

## 3. Thread B — arbitrary‑precision arithmetic → disable, then bound

**The hazard.** Script numbers were unbounded OpenSSL `BIGNUM`. A *tiny* script could
force enormous work on every validator — `OP_LSHIFT`/`OP_MUL` producing astronomically
large integers, `OP_CAT` building giant blobs — a network‑wide **DoS** from a few bytes,
on unhardened opcodes.

**The fix — the event this lab's matrix maps.** In **2010 Satoshi disabled** the broad
vocabulary — precisely the opcodes that computed on unbounded `CBigNum`/`BIGNUM`
(`OP_CAT`, `OP_MUL`, `OP_LSHIFT`, `OP_INVERT`, …). Later Bitcoin replaced arbitrary‑
precision Script numbers with **`CScriptNum`** (bounded to 4 bytes, explicit size checks) —
killing the DoS *and* removing OpenSSL `BIGNUM` from the interpreter. "Disabled vocabulary"
and "bounded script numbers" are the **same** move: pull arbitrary‑precision arithmetic out
of consensus‑critical execution.

**What "restore original Script" therefore means.** When **BCH (2018)** and **BSV (2020)**
re‑enabled these opcodes, they re‑implemented them with **size limits / their own big‑int
code**, not the naive OpenSSL‑BIGNUM version (the dangerous one). Our matrix shows the
*enable/disable map*; this is the *why* under it — and why BSV still leaves `OP_2MUL`/
`OP_2DIV` off.

## 4. How this lab makes the thread executable

- **C++ PORT** (`derivatives/port`, `derivatives/node`) had to port `CBigNum` from v0.1's
  **OpenSSL 0.9.8 `BN_*` API** to **OpenSSL 3.x's opaque `BIGNUM`** — living the exact API
  drift that made OpenSSL a moving target.
- **MODEL + conformance matrix** execute the full broad vocabulary (the BIGNUM‑stressing
  ops) that v0.1 had, and show it **disabled across the Bitcoin Core lineage (BTC/LTC/DOGE)**
  and **restored in the Cash lineage / BSV** — Thread B, watchable.
- **CHECKSIG** signs/verifies on **real secp256k1** (OpenSSL‑backed EC), mirroring v0.1's
  `EC_KEY` — the origin of Thread A.

So "OpenSSL is the load‑bearing dependency" is the spine connecting
`DEPENDENCIES.md` → the disabled‑opcode matrix (`conformance/`) → the crypto layer.

## 5. The lesson

**A consensus system cannot safely delegate consensus‑critical behavior — signature
validity, arithmetic bounds — to a general‑purpose library whose behavior varies by
version and platform.** Bitcoin's maturation from the origin is largely the story of
pulling that behavior *in‑house* — strict‑DER parsing, `libsecp256k1`, bounded
`CScriptNum` — to guarantee the determinism a global monetary ledger requires. v0.1's
reliance on OpenSSL was the expedient choice that got Bitcoin *working*, and a latent
consensus risk that took ~10 years (2009 → 2019) to fully unwind.

## Neutrality note — why this reads Core‑centric, and the neutral reframing

This essay names **Bitcoin Core** a lot (BIP66, v0.10/v0.12, `libsecp256k1`). That is a
*sourcing* fact, not a privileging one: `libsecp256k1` **is** a Bitcoin Core project
(`bitcoin-core/secp256k1`), and the migration happened there **first and best‑documented**,
because Bitcoin Core is the continuous code lineage of v0.1. But telling only that story
would quietly privilege BTC, against this lab's rule (measure everyone *from the origin*,
none privileged). The neutral — and more interesting — framing:

- **Thread A (crypto) CONVERGED across the whole lineage.** `libsecp256k1` was integrated
  into the shared codebase (verification, v0.12 / 2016) **before** the Cash split
  (BCH 2017 → BSV 2018), so BCH and BSV **inherited** it; LTC/DOGE (Bitcoin Core forks)
  synced it from upstream. **BTC, BCH, BSV, LTC, DOGE all run `libsecp256k1`.** Getting
  OpenSSL out of *signature* consensus is common ground — nobody kept OpenSSL there.
- **Thread B (Script) DIVERGED — and *that* is what our matrix maps.** The Bitcoin Core
  lineage kept the broad vocabulary disabled; the Cash lineage / BSV re‑enabled a hardened
  subset. This is the real fork in philosophy, and it's neutral to state because it's the
  executed evidence.

So: OpenSSL was **the origin's** dependency; every descendant unwound Thread A the same way
and split on Thread B. The Core‑centric dates are just where the primary sources live.

## Sources (Tier‑4 context; dates verified 2026‑07‑27)

- BIP66 text + activation — [bips/bip-0066](https://github.com/bitcoin/bips/blob/master/bip-0066.mediawiki), [Bitcoin Optech: soft-fork activation](https://bitcoinops.org/en/topics/soft-fork-activation/)
- The 4 July 2015 SPV‑mining fork — [NewsBTC](https://www.newsbtc.com/2015/07/04/implementation-of-bip66-der-signature-affects-bitcoin-network/)
- libsecp256k1 history (2013 commit; signing v0.10/2015, verification v0.12/2016; OpenSSL removed 2019) — [Bitcoin Magazine: The Core Issue](https://bitcoinmagazine.com/print/the-core-issue-libsecp256k1-bitcoins-cryptographic-heart), [bitcoin-core/secp256k1](https://github.com/bitcoin-core/secp256k1)
- v0.1 source facts (`EC_KEY`, `BIGNUM`) — this repo's hash‑verified tree (`key.h`, `bignum.h`); see `inventory/DEPENDENCIES.md`.
