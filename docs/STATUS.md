# Status — Genesis (`OBL-JAN09`)

## Release 0 — Provenance freeze

- [x] Self-contained edition repository created.
- [x] Charter, evidence policy, profile, and checksum registry in place.
- [x] Whitepaper captured under `provenance/`.
- [x] Canonical v0.1.0 archives fetched (Nakamoto Institute CDN) and verified.
- [x] `.tgz` source tree extracted read-only + per-file manifest generated.
- [x] `.rar` tree extracted (7-Zip 26.02) and diffed against the `.tgz` tree.

### Verified archives (2026-07-26)

| Artifact | md5 | sha1 | sha256 |
|---|:--:|:--:|:--:|
| `bitcoin-0.1.0.rar` | OK | OK | OK (`8b17eb9a…`) |
| `bitcoin-0.1.0.tgz` | OK | OK | OK (`ce9da465…`) |

SHA-256 values match the 2012 Hal Finney recovery thread. Whitepaper matches
`manifests/PROVENANCE_SHA256SUMS`. Verified bytes live under `artifacts/jan09/`
(gitignored, never edited). Per-file hashes of the extracted tree — including the
binary — are recorded in `manifests/SOURCE_MANIFEST.json` (bytes stay local under
`extracted/`).

The `.rar` and `.tgz` source trees are **byte-identical**: all 48 files match by
SHA-256 — including `bitcoin.exe`, `script.cpp`, `script.h`, `market.cpp`, and
`key.h` — independent confirmation that both canonical archives carry the same
tree. (`bitcoin-0.1.0.rar` is a *solid* RAR, extracted with 7-Zip 26.02.)

## First finding — source inventory

The v0.1.0 `.tgz` is the **runnable release**, not just source (48 files):

- **`bitcoin.exe`** (6,440,960 B) + `libeay32.dll` (OpenSSL) + `mingwm10.dll`,
  `readme.txt`, `license.txt`.
- **`src/` — 21 source files**: `main.*`, `net.*`, `script.*` (interpreter),
  `key.h`, `db.*`, `market.*` (commerce subsystem), `irc.*`, `ui.*`/`uibase.*`,
  `sha.*`, `base58.h`, `bignum.h`, `serialize.h`, `uint256.h`, `util.*`,
  `headers.h`, plus `makefile` / `makefile.vc` and UI resources
  (`rc/`, `ui.rc`, `uiproject.fbp`).

The complete original financial machine — Script interpreter (`script.cpp`,
35,279 B), keys, and the `market.*` commerce experiments — plus a runnable
`BITCOIN.EXE` are all present, corroborating that this edition is the intended
behavioral oracle. (Contrast: the NOV08 pre-release is 5 files.)

## Release 1 — source inventory (started)

- [x] Full opcode & SIGHASH inventory, **reproducible** via
  `scripts/inventory-symbols.py` → `inventory/OPCODES.md` + `OPCODES.json`:
  **106 opcodes (+2 aliases), 94 implemented in `EvalScript`**, 4 SIGHASH modes,
  only `OP_NOTEQUAL` disabled. The later-BTC-disabled family (`OP_CAT`, `OP_MUL`,
  `OP_DIV`, `OP_LSHIFT`, `OP_INVERT`, …) is **live** in v0.1.
- [x] File/class map for all 26 `src/` units → `inventory/SOURCE_INVENTORY.md`
  (noted `market.*` commerce + a dormant poker UI in `uibase`).
- [x] NOV08 → JAN09 structural diff → `../../common/conformance/NOV08_JAN09_DIFF.md`.
- [x] Line-numbered consensus validation-path catalog →
  `inventory/VALIDATION_PATH.md`: `ProcessBlock → CheckBlock → AcceptBlock →
  AddToBlockIndex → ConnectBlock → ConnectInputs → VerifySignature → EvalScript`
  with `src:line` anchors + consensus-constants table; flags height-based chain
  selection (`main.cpp:1097`) and global-`nBestHeight` subsidy (`main.cpp:680`).
- [x] Executable **MODEL** (`derivatives/model/`, Python) and **PORT**
  (`derivatives/port/`, C++/OpenSSL) interpreters — differential-tested against
  each other. Built with MSYS2 g++ 16.1.0 + OpenSSL 3.6.3. Coverage:
  - Numeric/splice/bitwise vocabulary (incl. the disabled-in-BTC `OP_CAT`/`OP_MUL`/
    `OP_DIV`/`OP_LSHIFT`/`OP_INVERT`/…) — PORT uses the **real OpenSSL `BN_*`**
    engine + `bignum.h` codec (`CBigNum` ported to OpenSSL 3.x opaque `BIGNUM`).
  - Control flow (`OP_IF/NOTIF/ELSE/ENDIF/VERIFY/RETURN`), alt-stack, full stack
    ops. `run.sh` differential over **63 vectors → IDENTICAL**.
  - `CTransaction` + **`SignatureHash`** (pre-BIP143) — `run_sighash.sh`
    differential over **12 (nIn × SIGHASH) digests → IDENTICAL** (pinned).
  - **`OP_CHECKSIG` / `OP_CHECKMULTISIG` on real secp256k1** — `run_checksig.sh`:
    C++ signs + self-checks (8/8: P2PK + 2-of-3 escrow/arbitration; tamper /
    wrong-key / wrong-order rejected) and the **Python interpreter independently
    verifies the C++-signed scenarios** (4/4). Model pytest: 44.
  - Byte-level `CScript` (`cscript.py`, opcode bytes from our own `OPCODES.json`):
    `scriptCode` is now the **real subscript** (`scriptSig + OP_CODESEPARATOR +
    scriptPubKey`, script.cpp:1126), not a configured constant.
  - Executed native **instrument corpus** (`INSTRUMENTS.md`): buyer–seller–arbiter
    2-of-3 escrow, hash-lock (preimage) claim, hash-lock/refund `OP_IF` branch, and
    an assurance/crowdfund contract via `SIGHASH_ANYONECANPAY`. Model pytest: 51.
  - Evidence level **MODEL** (Python) / **PORT** (C++ + real OpenSSL EC/BN).
- [x] Headless **consensus PORT** → `derivatives/node/`:
  - `node_port` (12/12): reproduces the **exact genesis block** from the original
    construction — Merkle `4a5e1e…` **and** hash `000000000019d668…` (the live-chain
    anchor, the same startup assertion) — plus subsidy/halving, a real PoW mine, and
    difficulty retarget.
  - `chain_port` (8/8): faithful `ConnectInputs`/`ConnectBlock` over an in-memory
    UTXO index — builds a 121-block chain and **validates a real spend of a matured
    coinbase**, rejecting double-spend, inflation, tampered sig, immature-coinbase
    spend, and coinbase over-claim. Covers the ledger's core guarantees headlessly.
    Remaining boundary: Berkeley-DB persistence, P2P (`net.*`), the unmodified binary.
- [ ] True JAN09-EXECUTED — **plan + binary staging ready**
  (`docs/R3_HISTORICAL_NODE.md`, `scripts/stage-jan09-binary.sh`; staged
  `bitcoin.exe` sha256 `fbcac071…` matches the manifest). Awaits an isolated-VM
  run (user-driven VirtualBox/Hyper-V; IRC-discovery two-node net). + block-
  acceptance witnesses.
