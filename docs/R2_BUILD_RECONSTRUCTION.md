# R2 — Historical Build Reconstruction (status, honestly)

Roadmap R2 asks to reconstruct a period build environment and attempt a **reproducible
build of the JAN09 source**, plus determine the maximum executable reconstruction for
NOV08. This records where that stands: the from‑source build is **done** on a pinned period
toolchain, with the honest boundary that a *byte‑exact* reproduction of the released binary is
**not** claimed — so the record stays honest rather than padded.

## The goal, and why it is toolchain‑hard

A verbatim rebuild of `bitcoin.exe` from the 2009 `src/` needs the **period toolchain**:

| Dependency | Period version | Why modern systems can't just build it |
|---|---|---|
| compiler | MinGW GCC ~3.4.5 | the source predates C++11; modern GCC rejects/repairs constructs and changes ABI |
| GUI | **wxWidgets 2.8** | does not compile cleanly on modern MinGW/GCC; the app is GUI‑bound (`ui.cpp`/`uibase.cpp`) |
| crypto | **OpenSSL 0.9.8** | EOL; `CBigNum` uses the 0.9.8 `BN_*` API and struct layout; OpenSSL 3 changed `BIGNUM` to opaque |
| storage | **Berkeley DB 4.x** | old license/ABI; `CDB` binds its C++ API |
| misc | Boost 1.3x, Windows APIs | `QueryPerformanceCounter`, `_beginthread`, wx event loop |

Reproducing this on a current host means either sourcing 15‑year‑old binaries or a
period Docker/VM image, then building the source against it. This **has now been done**
(see *The period build, executed* below) on a pinned period toolchain — the original source
compiles, links, and runs as `bitcoin.exe`. What is **not** claimed is a *byte‑identical*
reproduction of the released `fbcac071…` binary: the 2009 compiler build id, section layout,
and exact library revisions are not all recoverable, so the comparison is **structural, not
byte‑for‑byte**. Claiming bit‑equality would be dishonest.

## Attempt log (2026‑07‑26 — modern g++, honest first wall)

Attempted a modern‑toolchain compile of the extracted `src/` (MSYS2 g++ 16.1.0,
`-std=c++03 -fpermissive`), to see how far it gets before the period deps bite:

- Every core unit `#include "headers.h"`, which pulls in **`wx/wx.h`** (wxWidgets 2.8),
  **`openssl/ecdsa.h` … (0.9.8 API)**, **`windows.h` / `winsock2.h` / `mswsock.h`** — the
  GUI/OS/crypto wall named above.
- Even the most self‑contained header, `uint256.h`, **does not compile verbatim**: it
  refers to `vector<string>` unqualified (`uint256.h:19`), because in 2009 it relied on
  `headers.h` having already done `using namespace std;` (and provided the 2009 API
  context) *before* including it. Modern g++ (stricter scoping) rejects it outright.

**Finding:** the original source is **not modularly compilable on a modern toolchain** —
it assumes the `headers.h` precompiled‑header world (global `using namespace std`, wx 2.8,
OpenSSL ≤1.0.2, Win32). A verbatim build therefore genuinely needs the period image. Rather
than patch the source into modern shape, the lab **staged the period toolchain** and built the
unmodified source against it — see next section. The two hard walls turned out to be exactly
two compiler‑enforced *period locks*: a 32‑bit target (`serialize.h:462`) and OpenSSL ≤1.0.2's
public `BIGNUM` (`bignum.h:49`), both cleared by the cross‑build below.

## The period build, executed

The full recipe is pinned and reproducible in
[`derivatives/build-reconstruction/`](../derivatives/build-reconstruction/)
(`PERIOD_BUILD.md`, `BUILD_RECONSTRUCTION.md`), and it has been **run**:

1. **Crypto/consensus core — DONE** (`period_build_wsl.sh`). On WSL Ubuntu 24.04, OpenSSL
   1.0.2u is cross‑built for i686, and the original `serialize.h / uint256.h / bignum.h /
   key.h` compile; `period_exec_test.cpp` links to a static i686 PE and runs **byte‑correct**
   on Windows (CBigNum arithmetic, Script sign‑magnitude `vch`, secp256k1 sign/verify).
2. **Full `bitcoin.exe` from source — DONE** (`full_build_wsl.sh`). All four period libraries
   (OpenSSL 1.0.2u · wxWidgets 2.8.12 · Berkeley DB 4.8.30.NC · Boost 1.42.0, all sha256‑pinned)
   are cross‑built, then **every** original `.cpp` is compiled against the real `headers.h` and
   linked into a self‑contained **14.8 MB i686 `bitcoin.exe`** that imports only system DLLs —
   just like the 2009 release. The enabling move: build in the era dialect `-std=gnu++98`, which
   clears the modern‑compiler rejections (narrowing, and the `std::array` vs `boost::array`
   ambiguity under `using namespace std` + `boost`).

Both period locks are cleared; the only source changes are logged compat shims (e.g.
`<direct.h>` for `_mkdir`, a BDB `atomic_init` rename), not behavioural edits.

R2's deeper intent — *an executable reconstruction whose behaviour matches the released binary* —
is independently corroborated by the consensus/script **PORT** (`derivatives/port/`,
`derivatives/node/`): the v0.1 Script engine, `SignatureHash`, `OP_CHECKSIG` on real secp256k1,
`GetBlockValue`, difficulty, `ConnectInputs`/`ConnectBlock`, and the **exact genesis**
(`000000000019d668…`), in modern C++/OpenSSL 3, differential‑tested against the Python MODEL — and
by the unmodified 2009 `bitcoin.exe` being **run** (`r3-findings/run1/`, and the two‑node
mined‑block witness `r3-findings/2026-07-31-twonode-mined-block/`), triple‑agreeing with PORT and
MODEL.

## Maximum executable reconstruction for NOV08

Determined and delivered: the surviving NOV08 archive is **5 files** with **no Script,
keys, db, or build system** (R1 / the NOV08→JAN09 diff), so it **cannot be compiled
standalone**. Its maximum executable reconstruction is therefore not a verbatim build
but a **provenance‑controlled completion** — which is exactly `NOV08‑Minimal`
(`derivatives/nov08x/`, and the interpretive `common/nov08x/NOV08_FULL.md`). That is the
honest answer R2 asks for on the NOV08 side.

## Reproduce it, and the honest boundary

To rebuild from source yourself: stage the pinned toolchain and run the scripts in
`derivatives/build-reconstruction/` — `period_build_wsl.sh` (crypto core) and
`full_build_wsl.sh` (full `bitcoin.exe`); `MANIFEST.sha256` pins the library tarballs. The
result is compared to the released binary **structurally** (entry points, consensus constants,
the reproduced genesis `000000000019d668…`), not by raw byte‑equality: the original's exact
compiler build id, section layout, and library point‑revisions are not all recoverable, so a
bit‑identical reproduction of `fbcac071…` is **not claimed**.

So R2's build is **done** as a period‑faithful *source → `bitcoin.exe`* rebuild; a *byte‑exact*
reproduction of the historical binary stays out of reach (and out of scope). The behavioural
oracle is confirmed directly (the unmodified binary was run), and the NOV08 ceiling is
**established**.
