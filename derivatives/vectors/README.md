# Conformance vectors — the lab's differential corpus, exported as language-neutral JSON

**Evidence level: `MODEL`.** This directory consolidates test vectors the lab already computes in
Python and consumes in Rust source (`../validator-rs/tests/data/`) and a text DSL (`../port/vectors.txt`)
into one JSON corpus that carries no code. Each file states the rule it tests in prose, names the
oracle the expected values came from, and can be replayed in any language. NOT money.

```
python export_vectors.py            # regenerate *.json + MANIFEST.sha256 from the verified model
python export_vectors.py --check    # fail if the committed corpus differs from a fresh export
python verify_vectors.py            # replay: retarget/merkle/headers from hashlib alone, evalscript via ../model
python -m pytest -q                 # both of the above, as tests
```

## Why this exists

The January 2009 consensus rules have never been written down as a document; they exist as a C++
tree you have to run. The lab closes part of that gap with four implementations that agree — the
Python model, the C++/OpenSSL port, the Rust validator, and the unmodified 2009 binary in a VM — but
their agreement was recorded in language-specific containers. A stranger who wants to write a fifth
implementation from the rules should not need Python, Rust *or* the binary to check it. This corpus is
the shared target: pass it and you agree with all four on these surfaces.

`verify_vectors.py` is the proof that the prose is sufficient. It deliberately imports nothing from
the lab for the retarget, Merkle and header suites — only `hashlib` and integer arithmetic — and it
passes. The EvalScript suite needs a Script interpreter, so it is replayed through the model.

## Files

| file | rule tested | vectors | oracle |
|---|---|---|---|
| `evalscript.json` | v0.1 `EvalScript` on scriptSig-free scripts: completion (`ok`), `CastToBool(top)` (`valid`), top element, depth | the Rust generator's opcode-coverage cases + the C++ port's arithmetic DSL cases | `model/evalscript_model.py` == `port/port.cpp` (OpenSSL BN) == `validator-rs` |
| `retarget.json` | `GetNextWorkRequired` (`main.cpp:685-728`): 2015-interval measurement, 4× clamps, pow-limit cap; plus the `nBits` codec | integer-spacing windows, so no rounding is language-dependent; one forged-boundary (timewarp) window | `retarget/retarget.py` |
| `merkle.json` | `BuildMerkleTree` (`main.h:868-882`): odd levels pair the last node with itself | n = 1…8, plus `[A,B,C]` == `[A,B,C,C]` (CVE-2012-2459) | `p2p/p2p.py` == `validator-rs/src/lib.rs` == `node/node_port.cpp` |
| `headers.json` | 80-byte header serialization, `dsha256`, and `hash <= SetCompact(nBits)` | both genesis headers (2009 and this lab's 2026 chain), each with a nonce+1 negative control | the executed 2009 binary (`r3-findings/run1`); `derivatives/bitcoin/net.py` |
| `MANIFEST.sha256` | the four files above | — | — |

Every rule string inside the JSON is the complete statement needed to replay that file.

## What the vectors do not cover, said plainly

- **No `OP_CHECKSIG` / `OP_CHECKMULTISIG`.** Those need a transaction context and OpenSSL's exact
  pre-BIP66 DER leniency; they are exercised by `../model/test_checksig.py`, `../port/run_checksig.sh` and
  `../crypto_conformance/`, and are not yet exported here.
- **No full block validity** (`ConnectInputs`, `CheckTransaction`, `MoneyRange`'s absence). See
  `../ledger/`, `../overflow/`, `../validator-rs/tools/gen_state_vectors.py`.
- **Not replayed against the frozen `bitcoin.exe` directly.** The binary is the oracle only for the two
  genesis headers, which it reproduces (`JAN09-EXECUTED`). Everything else is `MODEL`-level, agreed
  across the reimplementations. Running the corpus through the 2009 binary itself would require driving
  it inside the archived VM image (the exported .ova, which is not published), which is possible and not done.

## A note for anyone building a timestamp proof on a chain like this

The Merkle suite's last vector is the point: two different transaction lists share a root, so a root
does not identify a list. A second ambiguity, the 64-byte transaction whose serialization equals two
concatenated interior hashes, is demonstrated in `../hash_structure/`. Neither reaches a proof that
**carries the leaf transaction's bytes** — as OpenTimestamps proofs do — because the verifier then
sees an actual transaction, not a bare branch. That format rule costs nothing and needs no consensus
change anywhere. Prefer it to any redesign of the tree.

MIT. Generated files are reproducible from `export_vectors.py`; edit the generator, never the JSON.
