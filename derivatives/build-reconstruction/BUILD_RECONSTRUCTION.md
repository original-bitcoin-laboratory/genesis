# Build reconstruction — how much of the original v0.1.0 source builds today

**Evidence level: PORT/NEW-EXP (host-toolchain build attempt of unmodified source).**
**NOT money.** This is a laboratory measurement, not a release.

Roadmap R2 asks for "the maximum executable reconstruction possible." This module
answers it empirically: it compiles Satoshi's **unmodified, hash-verified** January
2009 source (`../../extracted/bitcoin/src`, pinned in [`MANIFEST.sha256`](MANIFEST.sha256))
on the modern host toolchain and records, per translation unit, exactly where the
portable subset ends. Nothing here edits the original files — [`compat/prelude.h`](compat/prelude.h)
only replaces the *environment* the original `headers.h` assumed (see Method).

Reproduce: `bash build.sh` (needs MSYS2 mingw64 `g++` + OpenSSL, and the R0-verified
archive extracted at `../../extracted/`). Current host: `g++ 16.1.0`, `OpenSSL 3.6.3`.

## Result

| Unit | Modern host (64-bit, OpenSSL 3.x, no wx) | Why |
|---|---|---|
| `sha.cpp` / `sha.h` | **Compiles *and* executes** (SHA-256 KATs pass) | Self-contained Crypto++-derived code; no platform deps |
| `serialize.h` | **Blocked** @ `serialize.h:462` | 32-bit-target lock (see below) |
| `uint256.h`, `base58.h` | Blocked (transitively) | need `serialize.h` (`VERSION`, `IMPLEMENT_SERIALIZE`) |
| `bignum.h` | **Blocked** @ `bignum.h:49` | OpenSSL ≤ 1.0.2 lock (see below) |
| `key.h` | Blocked (transitively) | needs `secure_allocator` (serialize.h) + EC_KEY |
| `script.h` / `script.cpp` | Blocked | use `CBigNum` → inherit the OpenSSL lock |
| `util.h` / `util.cpp` | Blocked | Windows API + wxWidgets (see below) |
| `main.*`, `net.*`, `irc.*`, `db.*`, `market.*`, `ui.*`, `uibase.*` | Blocked | wxWidgets / winsock / Berkeley DB / GUI |

The one genuinely portable, consensus-relevant unit is **`sha.cpp`**, and it does not
merely compile — the harness links the original `SHA256::Transform` and reproduces the
standard SHA-256 known-answer vectors (empty, `"abc"`, the pangram). Satoshi's original
hash code runs, byte-correct, on a 2026 compiler.

## The two period-locks (each captured from the compiler)

**1. 32-bit target — `serialize.h:462`.**
```cpp
unsigned int blk = min(nSize - i, 1 + 4999999 / sizeof(T));
```
`nSize - i` is `unsigned int`; `1 + 4999999 / sizeof(T)` is `size_t`. On the 32-bit
platform v0.1 shipped for, `size_t == unsigned int`, so `std::min` deduces one type and
compiles. On a 64-bit target the two operands differ and template deduction fails. The
released binary (`bitcoin.exe`, sha256 `fbcac071…`) is a 32-bit PE; this line is a direct
fingerprint of that target. A faithful build must target **i686 (32-bit)**.

**2. Public-struct OpenSSL (≤ 1.0.2) — `bignum.h:49`.**
```cpp
class CBigNum : public BIGNUM { ... BN_init(this); ... }
```
This inherits from `BIGNUM` and calls `BN_init`, both of which require `BIGNUM` to be a
**public struct**. OpenSSL made `BIGNUM` opaque and removed `BN_init` in **1.1.0 (2016)**;
against the host's OpenSSL 3.6.3 the compiler reports *"invalid use of incomplete type
'BIGNUM' {aka 'struct bignum_st'}"*. Everything that touches `CBigNum` — `script.cpp`,
`main.cpp`, key handling — inherits this wall. A faithful build needs **OpenSSL 0.9.8–1.0.2**.
(`key.h`'s `EC_KEY` API, by contrast, is merely *deprecated* in 3.x and still present — the
EC axis is soft; the BIGNUM axis is hard.)

**3. Platform GUI/OS — `util.h`.** `CRITICAL_SECTION` / `EnterCriticalSection` /
`wxTheApp` bind the utility layer to the Win32 API and **wxWidgets 2.8**, which then flows
into every unit that includes `util.h`.

## Why it is coupled, not modular

The source is a single-header monolith: every `.cpp` does `#include "headers.h"`, which
includes the project headers in a fixed order and defines shared names the leaf headers
rely on — `VERSION` (`serialize.h:22`, value `101`) and `secure_allocator`
(`serialize.h:664`). Individual translation units therefore cannot be peeled off and built
in isolation except `sha.*`, which stands alone by design. This is why the reconstruction
is all-or-nothing at the toolchain level.

## Conclusion — what a faithful full build requires

A byte-faithful build of the January 2009 client is **not** a matter of a few shims; it is
structurally bound to a period toolchain on three independent axes:

- **i686 / 32-bit** (from `serialize.h:462`),
- **OpenSSL 0.9.8–1.0.2** (from `bignum.h:49`, the hard one),
- **wxWidgets 2.8 + Win32** (from `util.h` and the GUI/net/db units),

plus **Boost 1.3x** and **Berkeley DB 4.7**. That is exactly the "period-appropriate build
environment" R2 names. See [`PERIOD_BUILD.md`](PERIOD_BUILD.md) for a recipe that pins
those versions; it is the documented reproducible path for anyone with the period toolchain
(the released `bitcoin.exe` itself is the JAN09-EXECUTED oracle — see `docs/R3_*`).

**What the lab already provides as the modern-toolchain substitute:** rather than depend on
period libraries, the lab's `derivatives/node` and `derivatives/port` recompile the v0.1
*consensus logic* against modern OpenSSL by porting `CBigNum` to an opaque-`BIGNUM` member
(the exact change this report shows to be necessary), and `derivatives/nov08x` /
`derivatives/jan09x` run new experimental genesis chains on that substrate. This module is
the honest boundary marker between "the original source, unmodified" (which reaches `sha.cpp`
+ the two documented walls) and "the original *behaviour*, re-derived" (which the rest of
`derivatives/` covers, differential-tested against the released binary).

For the November 2008 preview, standalone build is impossible for a stronger reason than any
lock above — see `BUILD_RECONSTRUCTION.md` in the **pre-genesis** repo: its snapshot
`#include "headers.h"` while shipping no `headers.h` and none of the script/key/bignum units
it references, so it cannot even begin to compile.
