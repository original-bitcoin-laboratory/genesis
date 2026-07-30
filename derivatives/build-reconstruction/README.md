# build-reconstruction

How much of the **original, unmodified** January 2009 source compiles and runs on a modern
toolchain — the empirical answer to roadmap R2's "maximum executable reconstruction." **NOT money.**

- **[`BUILD_RECONSTRUCTION.md`](BUILD_RECONSTRUCTION.md)** — the findings: `sha.cpp` compiles
  *and executes* (SHA-256 KATs pass); everything else stops at two compiler-verified
  period-locks — a **32-bit-target** lock (`serialize.h:462`) and a hard **OpenSSL ≤ 1.0.2**
  lock (`bignum.h:49`, `class CBigNum : public BIGNUM`) — plus wxWidgets/Win32 in `util.h`.
- **[`PERIOD_BUILD.md`](PERIOD_BUILD.md)** — the period-toolchain recipe that pins the versions
  those locks require (i686 + OpenSSL 0.9.8–1.0.2 + wxWidgets 2.8 + BDB 4.7 + Boost 1.3x).
- **[`full_build_wsl.sh`](full_build_wsl.sh)** — builds the **entire client from source**: cross-builds
  all four period libraries (SHA-256-pinned) and links a self-contained 14.8 MB i686 `bitcoin.exe` from
  every original `.cpp`, by compiling in the era dialect (`-std=gnu++98`). Run the result only in an
  isolated VM (it's a live 2009 node).
- **[`period_build_wsl.sh`](period_build_wsl.sh)** — *runs* the period build (WSL i686 + a
  from-source OpenSSL 1.0.2): the original `serialize/uint256/bignum/key` **compile**;
  **[`period_exec_test.cpp`](period_exec_test.cpp)** executes the original `bignum.h` + `key.h`
  (CBigNum + secp256k1 ECDSA); and **[`script_exec_test.cpp`](script_exec_test.cpp)** compiles the
  original **`script.cpp`** (with the `compat/donor_*.h` tx/util scaffolding — no wx/BDB) and runs a
  real P2PK verify through `EvalScript + SignatureHash + CheckSig`. Both run byte-correct on Windows.
- **[`build.sh`](build.sh)** — reproducible probe: hash-verifies the originals against
  [`MANIFEST.sha256`](MANIFEST.sha256), compiles + runs `sha.cpp`, and reproduces both locks.
- **[`sha_selftest.cpp`](sha_selftest.cpp)** — driver that runs Satoshi's `SHA256::Transform`
  against known-answer vectors (adds only padding/word-packing, no algorithm changes).
- **[`compat/`](compat)** — a headless stand-in for `headers.h` (drops wx/winsock/BDB, keeps
  std + OpenSSL) and a 3-name Boost shim. These replace the *environment*, never the source.

## Run it

```bash
bash build.sh          # needs MSYS2 mingw64 g++ + OpenSSL, and ../../extracted/ (R0)
```

Expected: source hashes OK, `sha.cpp` compiles, SHA-256 vectors **ALL PASS**, and
`serialize.h` / `bignum.h` **BLOCK** at their documented lines. The `build/` output dir is
git-ignored. This module reads only the read-only `extracted/` tree; it modifies nothing.
