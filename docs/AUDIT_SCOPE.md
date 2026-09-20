# Audit scope — the experimental X‑chain node

**For an independent reviewer.** This scopes a security/correctness review of the NOV08‑X / JAN09‑X
node. It is deliberately blunt about what is and isn't defended, and about what a signoff would and
would not mean. **This is a valueless research node — the review is about correctness and robustness,
not about protecting anything of value, because nothing here is sold, offered, priced or traded.**

## The frame the review must keep

The single load‑bearing invariant is: **"nothing disabled" is safe only because it is "not money."**
The reconstructions faithfully carry the origin's *missing* guardrails (no `MoneyRange`/overflow
check, no 1 MB block‑size rule — the origin's own ceiling is 32 MiB, `MAX_SIZE` in `CheckBlock`, `OBL-F-0016` —
no script element/op/stack limits, unbounded arithmetic — see
[`common/conformance/CONSENSUS_SURFACE.md`](https://github.com/original-bitcoin-laboratory/common/blob/main/conformance/CONSENSUS_SURFACE.md)).
A review should **confirm the node stays valueless and un‑drifted**, not recommend adding the 2010
guardrails — adding them would make it no longer the origin. If value were attached (it must not
be), the review scope changes entirely.

**A third chain is in scope for that invariant.** Besides the two reconstruction networks, the
laboratory runs *Bitcoin (2026)*: the January 2009 client built from the archive with nine
chain-separation substitutions (its own genesis, magic and port), publicly reachable and mineable, its
author an agent named "Satoshi Nakamoto" that is a 2026 program (`START_HERE.md` explains the position).
It exists as the laboratory's own executed instance of the origin's rules and, since height 221, as an
anchor rail carrying commitments written by implementations other than this laboratory's
(`docs/WHY-THE-CHAIN-CONTINUES.md`). It is not a reconstruction. What has to stay true for it to remain
valueless is the same as for the X-chains and is stated in its charter: no premine, no sale, no price, no
solicited market, and no coin mined on it spent for value; every coin mined so far is held by one project
key and unspent, which the repository records as a concentration. A reviewer who finds any of those
statements false has found the drift this scope exists to catch.

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
- **The two implementations agree byte‑for‑byte on the shared vectors** — the Rust golden vectors are
  generated from the Python, so this is a port validated against the Python model, not two independent
  readings of the source; a reviewer should re‑derive and diff. The independent differential is the
  corpus replayed against a real binary over the wire (`r5-findings/`, and the unmodified 2009 binary
  when its replay is done).

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
- **Parser panic‑safety** — untrusted network bytes must not hang or panic the node. Both nodes now
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
  trivially rewritable. **Decided 20 September 2026: no floor is set on the seed.** Nothing is at stake on these chains by
  design, so a rewrite costs its author electricity and gains nothing; the floor applies to every
  block (`difficulty.py`, `_floor_bits`), so setting one now would invalidate the chain already
  built on the easy genesis and mean a restart; and a rewrite is visible rather than silent, because
  the anchors' tips are probed on a schedule and every probe is kept as a commit on the `status`
  branch. Joiners leave `--min-difficulty` unset. A floor stays a supported option for a network that
  chooses to restart with one.
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
- `scripts/reproduce.py` — the full lab (every step must pass; the count is printed, incl. both node suites and the DNS seed).
- `cd derivatives/validator-rs && cargo test` — the Rust node (**30** tests — covering NOV08's leading-zero-bits PoW + `==` coinbase rule, and the malformed‑block/tx flood DoS gates).

## What a signoff would — and would not — mean

A clean review would mean: *the valueless experimental node is correct and robust for what it is, and
faithful to the pre‑BIP66 origin.* It would **not** mean the chain is money, is safe to attach value
to, or is "the real Bitcoin" — nothing can mean that. Until an audit signs off **and** the framing
above holds, treat it strictly as a **valueless experiment**. **Not money.**

---

*Experimental laboratory research, in progress: what re-runnable methods find, and no conclusion beyond that. Not money — no premine, no sale, no value assigned, no token. Not financial advice. No warranty. [Rights, sourcing and corrections](https://github.com/original-bitcoin-laboratory/genesis/blob/main/RIGHTS.md).*
