# R2 — Historical Build Reconstruction (status, honestly)

Roadmap R2 asks to reconstruct a period build environment and attempt a **reproducible
build of the JAN09 source**, plus determine the maximum executable reconstruction for
NOV08. This records where that stands — including what is deliberately **not** done, so
the record is honest rather than padded.

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
period Docker/VM image, then patching the source for compat — at which point a *verbatim*
build is compromised by the patches. This is genuinely hard and is **not attempted here**
as a byte‑reproducing period build. Claiming otherwise would be dishonest.

## What the lab already achieves toward R2

R2's deeper intent — *an executable reconstruction whose behaviour matches the released
binary* — is met by two artifacts that do not require the period toolchain:

1. **The consensus/script PORT** (`derivatives/port/`, `derivatives/node/`) — the v0.1
   Script engine, SignatureHash, `OP_CHECKSIG` on real secp256k1, `GetBlockValue`,
   difficulty, `ConnectInputs`/`ConnectBlock`, and the **exact genesis reproduction**
   (`000000000019d668…`), in modern C++/OpenSSL 3, **differential‑tested** against the
   Python MODEL. This is an executable reconstruction of the *consensus* — the part R2
   most wants — just not a verbatim compile of the GUI app.
2. **The released binary was actually run** — `r3-findings/run1/` (JAN09‑EXECUTED): the
   unmodified 2009 `bitcoin.exe` built the exact genesis on a live host, triple‑agreeing
   with the PORT and MODEL. So the *behavioural* oracle is confirmed directly, without a
   rebuild.

## Maximum executable reconstruction for NOV08

Determined and delivered: the surviving NOV08 archive is **5 files** with **no Script,
keys, db, or build system** (R1 / the NOV08→JAN09 diff), so it **cannot be compiled
standalone**. Its maximum executable reconstruction is therefore not a verbatim build
but a **provenance‑controlled completion** — which is exactly `NOV08‑Minimal`
(`derivatives/nov08x/`, and the interpretive `common/nov08x/NOV08_FULL.md`). That is the
honest answer R2 asks for on the NOV08 side.

## If someone wants the verbatim period build

The reproducible path (left as future work, requires sourcing period components):

1. A pinned Docker/VM image: Debian‑era with MinGW GCC 3.4, wxWidgets 2.8, OpenSSL
   0.9.8, Berkeley DB 4.7, Boost 1.34.
2. Build from the extracted `src/` with the original `makefile` / `makefile.vc`.
3. Record every source patch needed for the image to compile (each classified, like the
   NOV08‑X provenance ledger), and diff the resulting binary against the hash‑verified
   `bitcoin.exe` (sha256 `fbcac071…`).

Until that image exists, R2's byte‑reproducing build is **open**; its behavioural intent
is **met** (PORT + the live JAN09‑EXECUTED witness), and the NOV08 ceiling is
**established**.
