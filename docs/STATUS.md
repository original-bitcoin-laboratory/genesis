# Status — Genesis (`OBL-JAN09`)

## Release 0 — Provenance freeze

- [x] Self-contained edition repository created.
- [x] Charter, evidence policy, profile, and checksum registry in place.
- [x] Whitepaper captured under `provenance/`.
- [x] Canonical v0.1.0 archives fetched (Nakamoto Institute CDN) and verified.
- [x] `.tgz` source tree extracted read-only + per-file manifest generated.
- [ ] `.rar` tree diffed against the `.tgz` tree — **deferred**: `bitcoin-0.1.0.rar`
      is a *solid* RAR, which needs `unrar`/`7z` (the Windows built-in
      `bsdtar`/libarchive cannot read solid RAR). Byte-level provenance is already
      complete — the rar's md5/sha1/sha256 match the canonical values — and the
      sibling NOV08 edition's rar↔tgz trees were confirmed byte-identical.

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

## Next

`v0.1.0-source-inventory`: line-numbered class / function / opcode enumeration
(`script.h`, `script.cpp`, `main.*`) and a formal NOV08 → JAN09 structural diff.
