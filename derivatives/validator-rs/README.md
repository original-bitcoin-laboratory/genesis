# validator-rs — a Rust port of the X-chain block validator (NOT money)

**Evidence: NEW-EXP. Not money.** A native Rust port of the X-chain validator: the context-free
checks *and* the stateful UTXO/value/signature validation, cross-checked byte-for-byte against the
verified Python node. (`bench.py` showed the dominant cost is signature verification — already
handled on the live node by the [libsecp256k1 fast path](../netnode/fastverify.py) — so a full
native node matters only at extreme scale; this is that native validator, built and tested.)

## What it does

**Context-free** (only the block bytes — mirrors [`netnode/fullnode.py`](../netnode/fullnode.py)):

- **SHA-256 / double-SHA-256** — implemented in-crate (FIPS 180-4), no dependencies;
- **block hash** + **merkle root** recomputation;
- **structure** — ≥1 transaction, the first is a coinbase, no other is;
- **proof-of-work** — the 256-bit target from compact `nBits`, header-hash ≤ target.

**Stateful** (mirrors [`netnode/chainstate.py`](../netnode/chainstate.py) `ChainState._connect`):

- **structured transactions** — `parse_tx` / `parse_block_txs` (inputs, outputs, scripts, txids);
- **UTXO connect** (`chainstate::ChainState`) — every input exists and is unspent, **coinbase
  maturity**, **no inflation**, and the **coinbase-value rule** with fees (NOV08 `==` / JAN09 `<=`),
  applied atomically (a rejected block leaves the UTXO unchanged);
- **the v0.1 signature hash** (`sighash`) — ported to match `tx_sighash.signature_hash` exactly;
- **real ECDSA** (`script`) via the pure-Rust `k256` crate, **byte-faithful to v0.1's lenient
  (pre-BIP66) OpenSSL semantics** — the signature is normalized to low-S before verifying, so
  high-S (malleated) signatures verify the same, exactly as OpenSSL accepts them.

What is **not** here (the remaining native-node slice): a full **`EvalScript`** interpreter for
arbitrary scripts (this verifies the templates the chains actually use — bare **P2PK** and the
anyone-can-spend `OP_1` coinbase output; a non-template script returns `Err("unsupported script")`),
**P2PKH** (needs RIPEMD-160), and **reorg/disconnect + the difficulty retarget** (need the chain
index). Those stay in the Python node.

```bash
cargo run --bin obl-validate -- <HEX_BLOCK>     # context-free verdict for one block (or stdin)
cargo test                                       # cross-checks everything against the Python node
```

## How it's verified

`cargo test` cross-checks the Rust against the **verified Python node** — **8 tests**:

- `tests/golden.rs` (3): the standard SHA-256 `"abc"`/empty vectors; golden blocks' hash / merkle /
  PoW / tx-count; and a tamper-rejection case.
- `tests/txparse.rs` (3): the structured parser (txids, inputs, output sums) and the coinbase-value
  rule for both chains.
- `tests/state.rs` (2): a **real signed chain connects** while tracking the exact UTXO count +
  balance — which only passes if the Rust sighash + ECDSA match the Python (a wrong sighash makes the
  real signature fail) — and **rule-violating blocks are rejected with the Python's exact reasons**
  (double-spend → *input missing or already spent*; inflation; immature-coinbase spend; bad signature
  → *input script does not satisfy output*).

The golden vectors come from the verified Python node — `tests/golden.rs` from `netnode/bench.py`'s
chain builder, and `tests/data/state_data.rs` from [`tools/gen_state_vectors.py`](tools/gen_state_vectors.py)
(rerun it to regenerate). **Verified:** compiled + tested with **rustc 1.97.1**
(`x86_64-pc-windows-gnu`), all **8 pass**; `obl-validate` on a golden block reproduces the Python's
block hash. The novel 256-bit compact-target/PoW math was additionally cross-checked against the
Python reference across easy / hard / edge `nBits`.

## Provenance

The consensus meaning is the lab's (faithful to v0.1); this is a **NEW-EXP** re-implementation in a
second language, useful precisely because an independent port that agrees byte-for-byte — down to
the pre-BIP66 lenient signature semantics — is extra evidence the byte formats, hashing, sighash, and
value rules are pinned down. A tool, never authority (`../../../common/AUTHORITY.md`). **Not money.**
