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
- [ ] Executable per-opcode reachability / block-acceptance witnesses (→ R3–R4).
