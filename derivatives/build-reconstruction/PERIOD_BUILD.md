# Period-appropriate build recipe (documented; requires the period toolchain)

`BUILD_RECONSTRUCTION.md` shows a faithful build of the January 2009 client is bound to a
period toolchain on three axes. This file pins the versions. It is the **reproducible path**
for anyone with (or willing to stage) that toolchain; it is intentionally *not* run by
`build.sh`, which measures the modern host instead. The unmodified released `bitcoin.exe`
(sha256 `fbcac071…`) remains the JAN09-EXECUTED oracle — this recipe targets *rebuilding it
from source*, a strictly harder goal than running it (see `docs/R3_*`). **NOT money.**

## Pinned components (2009-era Windows i686)

| Component | Version | Forced by |
|---|---|---|
| Target arch | **i686 (32-bit)** | `serialize.h:462` (`size_t == unsigned int`) |
| Compiler | MinGW GCC 3.4.5 / 4.x (period) | original build; modern i686-mingw also works to the wx/db line |
| OpenSSL | **0.9.8 – 1.0.2** | `bignum.h:49` (`class CBigNum : public BIGNUM`, `BN_init`) |
| wxWidgets | **2.8.x** (`wx/wx.h`, `wx/clipbrd.h`, `wx/snglinst.h`) | `headers.h`, `ui.*`, `util.h` |
| Berkeley DB | **4.7.x** (C++ API) | `db.cpp` (`Db`, `DbTxn`, `DbEnv`) |
| Boost | **1.3x** (`foreach`, `lexical_cast`, `tuple`, `array`, `type_traits`) | `headers.h` |

## Recipe outline (cross-compile from Linux, gitian-style)

The lowest-friction faithful build is an **i686-w64-mingw32 cross-compile** with the four
period libraries cross-built to the same target. Sketch (fill in a container of choice):

```dockerfile
# Dockerfile.period  (outline — pins the axes above; not executed by build.sh)
FROM debian:bullseye
RUN apt-get update && apt-get install -y \
      g++-mingw-w64-i686 mingw-w64-tools make wget xz-utils
# --- OpenSSL 1.0.2 (public BIGNUM) ---
#   ./Configure mingw --cross-compile-prefix=i686-w64-mingw32- ; make
# --- wxWidgets 2.8.x  (--host=i686-w64-mingw32 --disable-shared) ---
# --- Berkeley DB 4.7  (--enable-cxx --host=i686-w64-mingw32) ---
# --- Boost 1.3x headers (header-only pieces headers.h uses) ---
# then, with the verified source at /src (extracted/bitcoin/src):
#   i686-w64-mingw32-g++ -m32 -O2 -DWIN32 -D__WXMSW__ -I<wx> -I<ssl> -I<bdb> -I<boost> \
#       /src/*.cpp -o bitcoin.exe  -l<wx> -lssl -lcrypto -l<db_cxx> -lws2_32 -lgdi32 ...
```

## Verification target

A successful period build should be compared to the released binary structurally
(entry points, consensus constants, the reproduced genesis `000000000019d668…`) rather than
by raw byte-equality — the original's exact compiler build id, section layout, and library
revisions are not all recoverable, so bit-identical reproduction is not claimed. The
`derivatives/node` headless consensus port constructs a genesis block and mines block-1 against
modern OpenSSL — this is the port's own **experimental** genesis, not the historical
`000000000019d668…`. The historical January genesis is witnessed **only** by the unmodified 2009
binary (block 0 of its `blk0001.dat`); neither this port nor the Python/Rust nodes is credited with
it, and the accompanying paper's evidence matrix records an em dash for them on that row. A period
build would additionally exercise the GUI/DB/net units this reconstruction marks as out of reach on
a modern host.

## Status

**Crypto/consensus core: DONE.** The i686 + OpenSSL 1.0.2 half of this recipe has been executed on
WSL Ubuntu 24.04 — the original `serialize.h / uint256.h / bignum.h / key.h` compile, and
`period_exec_test.cpp` (original `bignum.h` + `key.h`) builds to a static i686 PE and runs byte-correct
on Windows. Reproduce with [`period_build_wsl.sh`](period_build_wsl.sh); see the "Period build" section
of [`BUILD_RECONSTRUCTION.md`](BUILD_RECONSTRUCTION.md).

**Full GUI binary: DONE.** [`full_build_wsl.sh`](full_build_wsl.sh) cross-builds all four period
libraries — OpenSSL 1.0.2u, **wxWidgets 2.8.12**, **Berkeley DB 4.8.30.NC** (4.7-API-compatible), and
period **Boost 1.42.0** — then compiles **every** original `.cpp` against the real `headers.h` and
links a self-contained **14.8 MB i686 `bitcoin.exe`** that imports only system DLLs (no wx/openssl/bdb
DLLs), exactly like the 2009 release. The enabling insight: build wxWidgets and the Bitcoin source in
their era dialect (`-std=gnu++98`), which sidesteps the modern-compiler rejections (narrowing, and the
`std::array` vs `boost::array` ambiguity that C++11 introduces under `using namespace std` + `boost`).
Verified on WSL Ubuntu 24.04 + mingw i686 gcc 13. The released `bitcoin.exe` (sha256 `fbcac071…`)
remains the JAN09-EXECUTED oracle; this is a *from-source* rebuild of the same client. Run it only in
an isolated VM (`docs/R3_*`) — it is a live 2009 node.
