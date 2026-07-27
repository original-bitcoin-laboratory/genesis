# validator-rs — a standalone native Rust node for the X-chains (NOT money)

**Evidence: NEW-EXP. Not money.** A **consensus-complete, standalone** native Rust node: it validates
every consensus rule *and* runs — a hardened wire, a crash-safe block store, and a real TCP
block-sync. Two Rust nodes sync a signed chain over TCP (each block re-validated by the native
consensus) and reload from disk on restart. Everything is cross-checked byte-for-byte against the
verified Python node. (`bench.py` showed the dominant cost is signature verification — already
handled on the live Python node by the [libsecp256k1 fast path](../netnode/fastverify.py) — so a
native node matters only at extreme scale; this is that node, built and tested.)

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
- **the full v0.1 script interpreter** (`eval`) — a faithful `EvalScript` port over raw CScript
  bytes: the `bignum.h` **unbounded** sign-magnitude number codec, push / control-flow (`vfExec`) /
  stack / alt-stack / splice / bitwise / numeric / hash opcodes, `OP_CODESEPARATOR`, and
  `OP_CHECKSIG(VERIFY)` / `OP_CHECKMULTISIG(VERIFY)` (with v0.1's off-by-one). Spends are verified by
  **running `scriptSig · OP_CODESEPARATOR · scriptPubKey`** through it (`script::verify_spend`),
  exactly as `VerifySignature` does — so **P2PK, P2PKH, multisig, and arbitrary scripts** all work,
  not templates;
- **real ECDSA** (`script`) via the pure-Rust `k256` crate, **byte-faithful to v0.1's lenient
  (pre-BIP66) OpenSSL semantics** — the signature is normalized to low-S before verifying, so
  high-S (malleated) signatures verify the same, exactly as OpenSSL accepts them;
- **reorg + difficulty** (`reorg::NodeState` over a `BlockIndex`, `difficulty`, `rules`) — an active
  validated chain with per-block undo and `activate_best`, which moves toward the index's best
  (height-selected) chain, **gating every step on full validity** (value/script rules *and* the
  difficulty retarget) and **rolling back to the prior chain** if a branch fails to validate.

**Transport** (mirrors the core of `netnode/`):

- **hardened wire** (`wire`) — `[magic·command·length·checksum·payload]`, first-4-of-double-SHA-256
  checksum, size cap; rejects tampering / bad magic;
- **crash-safe store** (`store`) — length-prefixed, fsync'd append; `read_all` ignores a truncated tail;
- **a runnable node** (`net::Node`) — persistence + a real **TCP block-sync**: a peer sends its height,
  the server replies with the main-chain blocks above it, and the client **re-validates each into its
  own `NodeState`** and persists it. Two nodes end in sync;
- **transacting** — key generation + transaction **signing** (`script::sign_input`, via `k256`), a
  validating **mempool** (`mempool`) that accepts/rejects spends against the UTXO + pooled parents
  (fees, no double-spend, maturity, script via the full interpreter), and **block assembly + mining**
  (`miner`) — so a Rust node mines coins, pools a spend, and mines it into a block.

This is a whole, transacting node. The **richer transport** the Python `netnode` also has — `addr`
gossip, tx relay over the wire, DoS scoring, the wallet/RPC — is not re-ported here (it exists and is
tested in Python; a second copy adds no capability). Hashes use pure-Rust RustCrypto crates (`ripemd`,
`sha1`); arithmetic uses `num-bigint`; ECDSA uses `k256`; networking + persistence use only `std` — no
C / OpenSSL / async runtime anywhere.

```bash
cargo run --bin obl-validate -- <HEX_BLOCK>     # context-free verdict for one block (or stdin)
cargo test                                       # cross-checks everything against the Python node
```

## How it's verified

`cargo test` cross-checks the Rust against the **verified Python node** — **21 tests** (covering
70+ opcode scripts + reorg + difficulty + a live two-node TCP sync + mine-and-spend):

- `tests/golden.rs` (3): the standard SHA-256 `"abc"`/empty vectors; golden blocks' hash / merkle /
  PoW / tx-count; and a tamper-rejection case.
- `tests/txparse.rs` (3): the structured parser (txids, inputs, output sums) and the coinbase-value
  rule for both chains.
- `tests/state.rs` (2): a **real signed chain connects** (now through the full interpreter) while
  tracking the exact UTXO count + balance — which only passes if the Rust sighash + interpreter +
  ECDSA match the Python — and **rule-violating blocks are rejected with the Python's exact reasons**
  (double-spend → *input missing or already spent*; inflation; immature-coinbase spend; bad signature
  → *input script does not satisfy output*).
- `tests/eval.rs` (1, **73 scripts**): the interpreter reproduces the Python model's `(ok, valid)` on
  arithmetic (incl. big numbers), stack/alt-stack, splice, bitwise, comparisons, hashes, flow
  control, VERIFY/RETURN, and structural errors.
- `tests/multisig.rs` (1): a real **2-of-2 CHECKMULTISIG** spend validates, and one with a wrong
  signature is rejected.
- `tests/reorg.rs` (5): the reorg-safe chainstate **reorgs to a taller valid branch**, **aborts and
  restores** the prior chain when a taller branch is invalid, and **rejects a forged-difficulty
  block** — all matching the Python `ChainState`; plus the **retarget math** and **compact-target
  round-trip**.
- `tests/net.rs` (5): the wire round-trips and **rejects a tampered checksum / bad magic**; the store
  survives a **crash-truncated tail**; and **two nodes sync a signed chain over real TCP** (re-validated
  by the native consensus) and **reload it from disk** on restart.
- `tests/mempool.rs` (1): self-contained — a Rust node **mines coins to a key**, accepts a real signed
  spend into the **mempool** (rejecting a **double-spend** and a **bad signature**), and **mines the
  spend into a block**, which connects; the coinbase is consumed and the payee output confirmed.

The golden vectors come from the verified Python — the block vectors from `netnode/bench.py`'s chain
builder, and the rest from the regenerable generators in [`tools/`](tools/) (`gen_state_vectors.py`,
`gen_eval_vectors.py`, `gen_multisig_vectors.py`, `gen_reorg_vectors.py`). **Verified:** compiled +
tested with **rustc 1.97.1** (`x86_64-pc-windows-gnu`), all **21 pass**; `obl-validate` on a golden
block reproduces the Python's block hash. The novel 256-bit compact-target/PoW math was additionally
cross-checked against the Python reference across easy / hard / edge `nBits`.

## Provenance

The consensus meaning is the lab's (faithful to v0.1); this is a **NEW-EXP** re-implementation in a
second language, useful precisely because an independent port that agrees byte-for-byte — down to
the pre-BIP66 lenient signature semantics — is extra evidence the byte formats, hashing, sighash, and
value rules are pinned down. A tool, never authority (`../../../common/AUTHORITY.md`). **Not money.**
