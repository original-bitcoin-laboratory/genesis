# Audit scope — the experimental X‑chain node

**For an independent reviewer.** This scopes a security/correctness review of the NOV08‑X / JAN09‑X
node. It is deliberately blunt about what is and isn't defended, and about what a signoff would and
would not mean. **This is a valueless research node — the review is about correctness and robustness,
not about protecting anything of value, because there is nothing of value here (and never will be).**

## The frame the review must keep

The single load‑bearing invariant is: **"nothing disabled" is safe only because it is "not money."**
The reconstructions faithfully carry the origin's *missing* guardrails (no `MoneyRange`/overflow
check, no block‑size cap, no script element/op/stack limits, unbounded arithmetic — see
[`../derivatives/conformance/CONSENSUS_SURFACE.md`](https://github.com/original-bitcoin-laboratory/common/blob/main/conformance/CONSENSUS_SURFACE.md)).
A review should **confirm the node stays valueless and un‑drifted**, not recommend adding the 2010
guardrails — adding them would make it no longer the origin. If value were ever attached (it must not
be), the review scope changes entirely.

## In scope

### 1. Consensus validation (the heart)
Two independent implementations; a reviewer should check them **against each other** and against the
v0.1 source.
- **Value/UTXO rules** — `netnode/chainstate.py` `ChainState._connect` and `validator-rs/src/{chainstate,reorg}.rs`:
  no double‑spend, coinbase maturity, no inflation, the coinbase‑value rule with fees, atomic
  rollback, reorg‑safe `activate_best` with abort‑and‑restore on an invalid branch.
- **Script interpreter** — `netnode`'s `model/evalscript_model.py` and `validator-rs/src/eval.rs`: the
  full opcode set, the unbounded `bignum.h` number codec, `OP_CHECKSIG` / `OP_CHECKMULTISIG` (incl.
  v0.1's off‑by‑one), and the sighash (`tx_sighash.py` / `sighash.rs`).
- **Difficulty** — the retarget + the authoritative on‑connect check (covers the orphan path);
  `difficulty.py` / `validator-rs/src/difficulty.rs`.
- **The two implementations agree byte‑for‑byte** — the Rust golden vectors are generated from the
  Python; a reviewer should re‑derive and diff.

### 2. Cryptography — the pre‑BIP66 fidelity axis
The most subtle area. v0.1 verifies with **OpenSSL**, which is *lenient* (accepts high‑S / malleable
signatures); modern **libsecp256k1** is *strict*. The X‑chains are faithful **pre‑BIP66**
reconstructions, so their consensus rule is the lenient one.
- Confirm the **accelerated verifier** (`netnode/fastverify.py`, and `validator-rs`'s `k256` path)
  stays consistent with v0.1's lenient acceptance **on the tested canonical‑DER paths**: it normalizes
  to low‑S and falls back to OpenSSL, so it accepts high‑S signatures rather than adopting modern
  low‑S/strict rules. It does **not** claim exhaustive emulation of historical non‑strict‑DER parsing.
  The differential tests are `test_fastverify.py`.
- Confirm the crypto‑conformance thread (`derivatives/crypto_conformance/`) — v0.1 OpenSSL vs
  libsecp256k1 (via `bitcoinx`) — is the true statement it claims.
- The quantum exposure (bare‑P2PK coinbases) is documented, shared by *all* descendants, and out of
  scope to "fix" (it would be a drift): [`QUANTUM_EXPOSURE.md`](https://github.com/original-bitcoin-laboratory/common/blob/main/conformance/QUANTUM_EXPOSURE.md).

### 3. Transport robustness (adversarial input)
- **Parser panic‑safety** — untrusted network bytes must never hang or panic the node. Both nodes now
  gate every untrusted path: the Rust sync has bounds‑safe `well_formed_block` **and** `well_formed_tx`
  gates before the indexing parsers (`validator-rs/src/net.rs`); the Python `netnode` parsers bound
  every wire count to the actual payload length before looping/allocating. An internal robustness pass
  ([`AUDIT.md`](AUDIT.md)) closed a set of parser‑bounds findings (unbounded‑count DoS in
  `parse_inv`/`parse_getblocks`; an ungated tx‑parse panic); an independent reviewer should re‑fuzz
  both and confirm.
- **Wire** — checksum, size cap, timeouts (`wire.py` / `wire.rs`).
- **DoS bounds** — misbehavior scoring, rate limits, connection/table caps, mempool bounds
  (`livenode.py`, `mempool.py`; `validator-rs` misbehavior scoring).

## Known gaps (already documented — confirm, don't rediscover)

From each node's `SECURITY.md`. These are **acceptable for a valueless research node** and are listed
so a reviewer can confirm the boundary, not treat them as surprises:

- **Difficulty defaults to easy.** Without an operator‑set `--min-difficulty` floor, the chain is
  trivially rewritable. Choosing/coordinating a real floor is an operator action.
- **No peer authentication or encryption** — plaintext P2P; no strong eclipse/Sybil resistance.
- **RPC is loopback‑only and unauthenticated**; the **wallet stores plaintext keys** (no encryption,
  HD, or backup discipline) — experimental keys for a valueless chain.
- **Mempool policy is minimal** — no RBF/fee‑bump/package relay; leaf‑only eviction; basic orphan
  handling. (Cannot admit an invalid tx — consensus is re‑checked on connect.)
- **Python resource accounting** is not rigorous; the datadir is not integrity‑signed.
- **Difficulty starts at a floor, orphan‑path difficulty is now validated on connect** (a previously
  open gap, closed — confirm it).

## Out of scope / non‑goals

- It is **not** a money system, a wallet you should trust with value, or a production node. Do not
  scope it as one.
- Recommending the 2010 guardrails (overflow/size/script limits): out of scope — that is a *drift*,
  not a fix. The whole point is the undrifted origin, kept safe by being valueless.

## Reproducing the claims

- `scripts/verify_genesis.py` — re‑derive both genesis blocks from source.
- `scripts/reproduce.py` — the full lab (**25/25** steps, incl. both node suites and the DNS seed).
- `cd derivatives/validator-rs && cargo test` — the Rust node (**30** tests — covering NOV08's leading-zero-bits PoW + `==` coinbase rule, and the malformed‑block/tx flood DoS gates).

## What a signoff would — and would not — mean

A clean review would mean: *the valueless experimental node is correct and robust for what it is, and
faithful to the pre‑BIP66 origin.* It would **not** mean the chain is money, is safe to attach value
to, or is "the real Bitcoin" — nothing can mean that. Until an audit signs off **and** the framing
above holds, treat it strictly as a **valueless experiment**. **Not money.**
