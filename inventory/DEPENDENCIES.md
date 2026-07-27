# External dependencies of Bitcoin as a system (NOV08 + JAN09)

What early Bitcoin depended on **outside its own code** — read from the `#include`
graph (`headers.h`) and the linked libraries (`makefile` `LIBS`) of each hash‑verified
tree. (Bitcoin's own units — `main`, `script`, `net`, `db`, `key`, … — are *not*
dependencies; they are the system.)

## Bitcoin v0.1.0 (JAN09) — the complete external stack

| # | Dependency | What Bitcoin uses it for | Evidence |
|---|---|---|---|
| 1 | **OpenSSL** (`libeay32` / `libeay32.dll`) | the entire cryptographic base — **ECDSA on secp256k1** (`EC_KEY`, curve `secp256k1`), **big‑number math** (`BN_*`/`BIGNUM`, wrapped by `bignum.h`→`CBigNum` for Script arithmetic + the compact difficulty target), **SHA‑256** (`openssl/sha.h`), **RIPEMD‑160** (addresses, `Hash160`), **RNG** (`openssl/rand.h`), EVP | `openssl/{ecdsa,evp,rand,ripemd,sha}.h`; `-l eay32`; `EC_KEY`/`BN_*`/`secp256k1` in `key.h`,`bignum.h` |
| 2 | **wxWidgets 2.8** (`wxmsw28_*`) | the wallet **GUI** — windows, controls, clipboard, single‑instance. Pulls in its bundled **zlib** (compress), **libpng/libjpeg/libtiff** (images), **regex**, **expat** (XML) | `wx/wx.h`, `wx/clipbrd.h`, `wx/snglinst.h`; `-l wxmsw28*_richtext/html/core -l wxbase28 -l wxtiff/jpeg/png/zlib/regex/expat` |
| 3 | **Berkeley DB** (`db_cxx`) | the embedded **key/value database** — block index, wallet, address book (`blkindex.dat`, `wallet.dat`, `addr.dat`), wrapped by `db.h`/`db.cpp` (`CDB`) | `-l db_cxx`; `-I"/DB/build_unix"`; `CDB`/`CTxDB`/`CWalletDB` |
| 4 | **Boost** (header‑only) | small C++ conveniences — `foreach` (`boost/foreach.hpp`), tuples, `lexical_cast`, `array` | `boost/{array,foreach,lexical_cast,tuple/*}.hpp`; `-I"/boost"` |
| 5 | **Win32 API + Winsock 2** | the **operating‑system layer** — **TCP sockets** for the P2P network (`winsock2.h`/`mswsock.h`/`ws2_32`), windowing (`user32`,`gdi32`,`comctl32`,`comdlg32`), COM (`ole32`,`oleaut32`,`uuid`), shell (`shell32`), timing/multimedia (`winmm`), registry/security (`advapi32`), RPC (`rpcrt4`), core (`kernel32`) | `windows.h`,`winsock2.h`,`mswsock.h`; the Win32 `-l` list |
| 6 | **C runtime threading** | `_beginthread` (via `process.h`) spawns the miner / socket / message‑handler threads — **not** boost::thread or pthreads | `process.h`; 16× `_beginthread` |
| 7 | **C / C++ Standard Library** | STL containers + algorithms (`vector`,`map`,`set`,`list`,`deque`,`algorithm`,`numeric`,`string`,`sstream`,`memory`) and the C runtime (`stdio`,`stdlib`,`math`,`limits`,`assert`,`malloc`) | the `<...>` includes in `headers.h` |
| 8 | **MinGW C++ runtime** (`mingwm10.dll`) | the compiler runtime, **shipped alongside `bitcoin.exe`** | the two DLLs bundled with the release: `libeay32.dll`, `mingwm10.dll` |

**In one breath:** OpenSSL (crypto) + wxWidgets (GUI) + Berkeley DB (storage) + Boost
(utilities) + Win32/Winsock (OS + networking) + the C/C++ standard library + the MinGW
runtime. Everything else is Bitcoin's own 26 source units.

## What v0.1 did *not* depend on (each is a notable absence)

- **No `libsecp256k1`.** v0.1's ECDSA is OpenSSL's *general* elliptic‑curve code on the
  `secp256k1` curve — the purpose‑built, consensus‑critical `libsecp256k1` is a **2013+**
  Bitcoin Core creation. Early Bitcoin's signature security rested entirely on OpenSSL.
- **No separate networking library** — raw Winsock, no boost::asio.
- **No JSON / serialization library** — its own `serialize.h`.
- **No separate threading library** — the C runtime's `_beginthread`.
- **No build system beyond a hand‑written makefile** that hard‑codes `/boost`,
  `/DB/build_unix`, `/OpenSSL`, `/wxWidgets` — no autotools, no package manager.

## NOV08 (pre‑release) — a smaller external surface

The surviving 5‑file November witness shows a **headless‑ish ledger + network** node:

- **Winsock 2** (`winsock2.h`, `WSAStartup`) — networking, the one external dep it
  states directly.
- **References** to OpenSSL `BN_*` (big numbers), `SHA256`, and Berkeley DB (`CDB`) — but
  their wrapper headers (`headers.h`, `sha.h`) are **absent** from the package (it is a
  partial snapshot).
- **No wxWidgets** — *zero* files reference `wx/`; November has no GUI dependency at all.

So the external stack, like the monetary constitution and the Script engine, **grows at
the genesis:** November needs networking + crypto + a database + the C++ stdlib; **the GUI
(wxWidgets) and its media libraries, Boost, and the full OpenSSL surface are January‑born.**

## Why this matters

Bitcoin v0.1 is a **thin application over a few heavyweight libraries** — its novelty is
the *protocol* (the `main`/`script`/`net` logic), not the plumbing. The single most
consequential external dependency is **OpenSSL**, which carried *all* of the crypto; its
later replacement (by `libsecp256k1`, and the removal of `OP_*` that stressed OpenSSL's
BIGNUM) is a direct thread from the origin the descendant matrix maps — told in full in
[`THE_OPENSSL_THREAD.md`](THE_OPENSSL_THREAD.md). And the **Win32/wxWidgets binding is what
makes the release Windows‑only** — the fact that shapes R2 (see `docs/R2_BUILD_STEPS.md`).
