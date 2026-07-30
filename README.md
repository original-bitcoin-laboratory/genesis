# Original Bitcoin Laboratory — Genesis (`OBL-JAN09`)

Self-contained reconstruction of the **January 2009 Bitcoin v0.1.0** release — the
first publicly announced Bitcoin implementation (node + wallet + miner + validator
+ Script interpreter + P2P networking + database + a commerce/market subsystem). This is the
principal **behavioral oracle** for "original Bitcoin", and its runnable `derivatives/`
contain **both** reconstructions — the January 2009 `JAN09-X` and the 15 November 2008
pre-release `NOV08-X`. (The sibling `pre-genesis` repo holds the November 2008 source
edition and its differential.)

## Quick start

```bash
./scripts/fetch-artifacts.sh          # pull the 2 canonical v0.1.0 archives (Nakamoto Institute CDN)
python scripts/verify-artifacts.py    # hash-check against manifests/EXPECTED_CHECKSUMS.json
```

Archives land in `artifacts/jan09/` (gitignored) and are never edited. Verified
values: MD5/SHA-1 (SNI catalogue) plus SHA-256 matching the 2012 Hal Finney
recovery thread — `bitcoin-0.1.0.rar` = `8b17eb9a…`, `bitcoin-0.1.0.tgz` =
`ce9da465…`.

## Reproduce the executable reconstruction

`derivatives/` is a faithful reconstruction of v0.1.0's rules, made to **run** in two declared postures —
faithfully as written (`OP_NOTEQUAL` disabled), and, for the isolated experimental networks, with
**"nothing disabled"** (both are declared and verified in `derivatives/profiles/`, below): the full Script
engine (Python MODEL + C++ PORT), sighash, `OP_CHECKSIG`/`CHECKMULTISIG` on real secp256k1,
lab-executed constructions (escrow / hash‑lock / assurance), a UTXO `ConnectInputs`/`ConnectBlock`
ledger, a wallet, the P2P wire + chain sync, persistence, the neutral descendant matrix
(BTC + BSV **executed**), a model of v0.1's commerce subsystem (signed listings + atoms reputation), a
script **debugger**, a **full‑stack console**, and two live counterfactual networks —
**NOV08‑X** and **JAN09‑X**.

Which rule posture a run uses — the **faithful** reconstruction (v0.1 as written, its one disabled opcode
`OP_NOTEQUAL` preserved) or the experimental **"nothing disabled"** posture, which rewrites the
`OP_NOTEQUAL` *token* to `OP_EQUAL OP_NOT` as a model-level macro (v0.1 has no such enum value or wire
byte, so this is not a reopened on-wire opcode) — is declared
and machine‑verified in [`derivatives/profiles/`](derivatives/profiles/): each profile's vocabulary is
checked against the source opcode inventory and the live engine, so the distinction can never silently
drift.

**Requirements.** Python 3.10+ with `cryptography` and `pytest` (the faithful crypto + test runner); `bitcoinx` is optional and
only enables the ~7× `libsecp256k1` verifier. The Rust node needs a stable Rust toolchain (`cargo`);
the optional C++ port differentials need `g++`. Install the pinned Python environment in one step with
`python -m venv .venv && pip install -e ".[test]"` (see `pyproject.toml`).

```bash
python scripts/reproduce.py        # every Python suite + regenerated artifacts (add --rust for the Rust node)
python scripts/verify_genesis.py   # both experimental genesis blocks re-derive from source
```

The unmodified 2009 `bitcoin.exe` was also run and hash‑verified against these
reconstructions — the **historical** genesis is reconstructed from source by the C++/OpenSSL port and
reproduced by the unmodified 2009 binary (`r3-findings/run1/`, level `JAN09-EXECUTED`); the Python and Rust
nodes regenerate the *experimental-network* genesis blocks, which they check differ from the historical
hash. Findings, the honest claim, and scope live in the umbrella:
[`common/README.md`](https://github.com/original-bitcoin-laboratory/common/blob/main/README.md) · [`common/CLAIMS.md`](https://github.com/original-bitcoin-laboratory/common/blob/main/CLAIMS.md).
These chains are **not money**: no premine, no sale, and **no value assigned** (stamped in the
coinbase) — a research microscope, not a coin. The maintainers solicit no market; whether third
parties value the units is outside any software's control, but nothing here invites it.

## Run a node — and join the live experimental network

The consensus and node exist **twice**, cross‑checked byte‑for‑byte on shared vectors (a differential
check, not full independence — one author, Python‑generated vectors): a Python node
([`derivatives/netnode/`](derivatives/netnode/) — validation, mempool, wallet, RPC, a ~7×
libsecp256k1 verifier, a DNS seed) and a standalone Rust node
([`derivatives/validator-rs/`](derivatives/validator-rs/), 30 tests — **both** chains).

Two live, always‑on anchors run both reconstructions — **JAN09‑X** (`seed.bitcoin-lab.org:18009`) and
**NOV08‑X** (`seed.bitcoin-lab.org:18008`, its own genesis + leading‑zero‑bits PoW). Join either and
watch your node sync + independently re‑validate every block:

```bash
git clone https://github.com/original-bitcoin-laboratory/genesis
cd genesis/derivatives
python -m netnode --chain jan09x --datadir ./data-jan09 --connect seed.bitcoin-lab.org:18009   # JAN09-X (Jan 2009 edition)
python -m netnode --chain nov08x --datadir ./data-nov08 --connect seed.bitcoin-lab.org:18008   # Nov 2008
```

Full invitation + how to run your own node or seed: [`docs/ANNOUNCE.md`](docs/ANNOUNCE.md). For an
independent reviewer: [`docs/AUDIT_SCOPE.md`](docs/AUDIT_SCOPE.md). **Not money.**

## Verify the signed release

Releases are **GPG‑signed** (key `B0145F74B78CF1DA`, fingerprint
`B128 526A F85A E4A8 F22B 949F B014 5F74 B78C F1DA`; public key at
[`docs/parthod0x-signing-key.asc`](docs/parthod0x-signing-key.asc)). See the latest under
[**Releases**](https://github.com/original-bitcoin-laboratory/genesis/releases) and the checklist in
[`docs/RELEASE_SIGNING.md`](docs/RELEASE_SIGNING.md). A signature authenticates *a distribution*;
the reproducible recipe (`scripts/verify_genesis.py`) *regenerates* the artifact from a stated input —
inspectability rather than authentication, and the guarantee that lasts, with no key and no node to trust.

## Layout

```text
docs/         charter, evidence policy, status
provenance/   whitepaper + provenance sources
manifests/    expected checksums + generated manifests
profiles/     frozen OBL-JAN09 profile
scripts/      acquisition / verification / inventory tooling
artifacts/    acquired archive bytes (gitignored)
derivatives/  all modified / instrumented / modernized code
```

## Boundaries

- `artifacts/` holds acquired historical bytes and is never edited.
- `derivatives/` holds every patch, port, harness, UI, or experiment; a
  derivative is never described as canonical original code.
- The program-wide roadmap lives in the lab umbrella (`common/ROADMAP.md`);
  see `docs/PROJECT_CHARTER.md` for method and evidence rules.

## License

MIT © 2026 Parth Mauria Saxena (new laboratory material only). Original Bitcoin
source retains Satoshi Nakamoto's original notices. See `LICENSE`.
