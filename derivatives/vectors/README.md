# Conformance vectors — the lab's differential corpus, exported as language-neutral JSON

**Evidence level: `MODEL`** (two headers `JAN09-EXECUTED`; the rest awaits `replay/`). This directory
consolidates test vectors the lab computes in Python and consumes in Rust source
(`../validator-rs/tests/data/`) and a text DSL (`../port/vectors.txt`) into one JSON corpus that carries
no code, and adds the surfaces those containers never held: SignatureHash, CHECKSIG and CHECKMULTISIG
spends, and whole-block validity. Each file states the rule it tests in prose, names the oracle the
expected values came from, and can be replayed in any language. NOT money.

```
python export_vectors.py            # regenerate *.json + MANIFEST.sha256 from the verified model
python export_vectors.py --check    # fail if the committed corpus differs from a fresh export
python verify_vectors.py            # replay every suite from the rules; evalscript via ../model
python -m pytest -q                 # the above, plus the replay harness end-to-end against a stand-in node
```

## Why this exists

The January 2009 consensus rules have never been written down as a document; they exist as a C++
tree you have to run. The lab closes part of that gap with four implementations that agree — the
Python model, the C++/OpenSSL port, the Rust validator, and the unmodified 2009 binary in a VM — but
their agreement was recorded in language-specific containers. A stranger who wants to write a fifth
implementation from the rules should not need Python, Rust *or* the binary to check it. This corpus is
the shared target: pass it and you agree with all four on these surfaces.

`verify_vectors.py` is the proof that the prose is sufficient. For every suite but one it imports
nothing from the lab — only `hashlib`, `hmac` and integer arithmetic: its own secp256k1, DER parser,
SignatureHash, the EvalScript subset that P2PK and multisig spends need, and a 2009 block validator
written from `main.cpp` in `main.cpp`'s order with `main.cpp`'s error strings — and it passes. The
full-vocabulary EvalScript suite needs a complete Script interpreter, so it is replayed through the model.

## Files

| file | rule tested | vectors | oracle |
|---|---|---|---|
| `evalscript.json` | v0.1 `EvalScript` on scriptSig-free scripts: completion (`ok`), `CastToBool(top)` (`valid`), top element, depth | 136: the Rust generator's opcode-coverage cases + the C++ port's arithmetic DSL cases | `model/evalscript_model.py` == `port/port.cpp` (OpenSSL BN) == `validator-rs` |
| `retarget.json` | `GetNextWorkRequired` (`main.cpp:685-728`): 2015-interval measurement, 4× clamps, pow-limit cap; the `nBits` codec | 15: integer-spacing windows (no language-dependent rounding), one forged-boundary (timewarp) window | `retarget/retarget.py` |
| `merkle.json` | `BuildMerkleTree` (`main.h:868-882`): odd levels pair the last node with itself | 9: n = 1…8, plus `[A,B,C]` == `[A,B,C,C]` (CVE-2012-2459) | `p2p/p2p.py` == `validator-rs/src/lib.rs` == `node/node_port.cpp` |
| `headers.json` | 80-byte header serialization, `dsha256`, `hash <= SetCompact(nBits)` | 4: both genesis headers (2009 and this lab's 2026 chain), each with a nonce+1 negative control | the executed 2009 binary (`r3-findings/run1`); `derivatives/bitcoin/net.py` |
| `sighash.json` | `SignatureHash` (`script.cpp:818`): every hash type on both inputs, the two `return 1` cases, `OP_CODESEPARATOR` removal | 15 | `model/tx_sighash.py` == `port/sighash.cpp` (OpenSSL) |
| `checksig.json` | `VerifySignature` / `CheckSig` / `OP_CHECKMULTISIG` (`script.cpp:881, 727, 1126`): canonical, high-S, wrong key, hash-type byte cases, compressed key, empty sig, three non-strict DER probes, three multisig layouts | 17, three verdict columns each | strict-DER rule; `model/spend.py`; the 2009 binary (via `replay/`) |
| `blocks.json` | `CheckBlock` → orphan → `AcceptBlock` → `ConnectBlock` (`main.cpp:1154-1260, 772-870, 934-953`), in order, with `main.cpp`'s strings | 121: genesis, a funding block, 100 maturity blocks, 3 valid cases, 16 rejected cases | `verify_vectors.Chain2009`; agrees with `ledger/`, `netnode/chainstate.py`, `validator-rs` on the shared cases |
| `MANIFEST.sha256` | the seven files above | — | — |

Every rule string inside the JSON is the complete statement needed to replay that file. Test keys are
derived from labels, published inside the files, and worthless by construction.

### The three columns in `checksig.json`

`expected_strict_der` is what the stated rule gives with a strict DER parser that accepts high-S.
`expected_model` is the lab's Python model (OpenSSL 3 through `cryptography`). `expected_binary` is the
frozen 2009 `bitcoin.exe` (OpenSSL 0.9.8): stated where no parser leniency can change the answer, `null`
for the three non-strict DER encodings, which only the binary can settle. Keeping the columns apart is
the point: a verdict that depends on which OpenSSL you link is a consensus fact, and it is recorded as
one instead of being averaged away.

### `blocks.json` is mined at an easy target

Its chain uses proof-of-work limit `0x207fffff` so it can be built at export time (a NEW-EXP parameter,
stated in the file). The 2009 binary would reject every one of those headers at *nBits below minimum
work* — which is itself one of the vectors. `replay/` rebuilds the same cases at `0x1d00ffff` on the live
chain; the cases are constructions (`recipes.py`), not byte strings, so both chains test the same thing.

## `replay/` — the same corpus against the frozen binary

The 2009 client has no test interface, so the replay speaks its wire protocol: it mines a funding block
whose coinbase carries one output per vector, matures it, spends each output, and reads the node's
verdict from the node itself (`getdata` from its relay pool for transactions; `getdata` + `getblocks` for
blocks). `replay/RUNBOOK.md` is the human procedure on the machine that holds the appliance.
`replay/fake2009.py` puts the from-spec validator behind the same wire so `test_replay.py` exercises the
whole harness here; **that proves the plumbing, not the binary**. The native miner in `replay/miner-rs`
is dependency-free Rust with SHA-NI when the CPU has it (~55 MH/s on the workspace laptop, about a
minute per difficulty-1 block); `replay/miner.py` falls back to multiprocessing `hashlib`.

## What the corpus found while being built

Building `checksig.json` exposed a defect in the lab's own model: `tx_sighash.py` removed
`OP_CODESEPARATOR` from the scriptCode by stripping every `0xab` byte, including bytes inside pushed
public keys. A key containing `0xab` then hashed to the wrong digest, and CHECKMULTISIG spends against
it verified as invalid while the from-spec interpreter, following `script.cpp:829`'s opcode-boundary
`FindAndDelete`, verified them as valid. Fixed 12 September 2026; the model's 146 tests still pass.
This is what a second implementation written from the text is for.

## What the vectors do not cover, said plainly

- **Not yet replayed against the frozen `bitcoin.exe`.** The binary is the oracle only for the two genesis
  headers, which it reproduces (`JAN09-EXECUTED`). Everything else is `MODEL`-level, agreed across the
  reimplementations. `replay/` is built and tested against a stand-in; the VM run is the remaining human step.
- **The wall-clock rules** (`nTime <= now + 2h`) are not replayed from data.
- **Retarget boundaries inside a block chain**, reorganisations, and the `nLockTime`/`IsFinal` rules are not
  in `blocks.json`; the retarget arithmetic has its own suite.
- **Full Script inside blocks.** `blocks.json` spends only `OP_TRUE` and P2PK outputs; the full vocabulary is
  `evalscript.json`'s job, and the replay spends every one of those scripts on the live chain.

## A note for anyone building a timestamp proof on a chain like this

The Merkle suite's last vector is the point: two different transaction lists share a root, so a root
does not identify a list. A second ambiguity, the 64-byte transaction whose serialization equals two
concatenated interior hashes, is demonstrated in `../hash_structure/`. Neither reaches a proof that
**carries the leaf transaction's bytes** — as OpenTimestamps proofs do — because the verifier then
sees an actual transaction, not a bare branch. That format rule costs nothing and needs no consensus
change anywhere. Prefer it to any redesign of the tree.

MIT. Generated files are reproducible from `export_vectors.py`; edit the generator, never the JSON.
