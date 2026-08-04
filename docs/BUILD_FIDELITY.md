# Which build did Satoshi ship?

**5 August 2026 · lab finding**

Running the reconstructed client for the first time produced two symptoms: no `debug.log` was ever
written, and wxWidgets logged *"Can't load bitmap 'send20' from resources!"* at startup. Both were
recorded as build defects. This note establishes what they actually are, because the obvious reading
of the makefile gives the wrong answer.

## The makefile does not settle it

`src/makefile` opens with a build selector:

```make
ifneq "$(BUILD)" "debug"
ifneq "$(BUILD)" "release"
BUILD=debug
endif
endif
ifeq "$(BUILD)" "debug"
D=d
DEBUGFLAGS=-g -D__WXDEBUG__
endif
```

Bare `make` yields a **debug** build. `make BUILD=release` yields no `__WXDEBUG__`, links the release
wxWidgets libraries, and — because the entire body of `OutputDebugStringF` sits inside
`#ifdef __WXDEBUG__` — produces a client that writes no log at all.

Both are legal builds of the same tree. The default is suggestive, not decisive: nothing stops a
maintainer from shipping `BUILD=release`, and plenty do. So "the makefile defaults to debug" is not
an argument about the artifact. It is an argument about the makefile.

## The binary settles it

We hold the artifact — `bitcoin.exe`, sha256 `fbcac071…`, the January 2009 release. It can be asked
directly. Three markers exist only under `__WXDEBUG__`, measured against our v0.1.1 build:

| marker | Satoshi's `fbcac071…` | our v0.1.1 `cfb59606…` |
|---|---|---|
| `debug.log` | **7** | 0 |
| `assert "%s" failed` | **1** | 0 |
| distinct `../../include/wx/*.h` paths | **24** | 0 |
| `.rsrc` PE section | **present** | **absent** |

Each row is load-bearing for a different reason:

**`debug.log`** occurs in exactly one place in the entire source — `util.h:236`,
`fopen("debug.log", "a")`, inside the `#ifdef`. There is no other way for that literal to enter a
binary built from this tree.

**The wx header paths** are `__FILE__` expansions from `wxASSERT` inside wxWidgets' *inline* code,
compiled into Bitcoin's own translation units. `wxASSERT` compiles to nothing when `__WXDEBUG__` is
undefined, so 24 distinct paths cannot appear in a release build.

**`.rsrc`** is the PE resource directory, the output of `windres ui.rc`. Its absence is the whole of
the bitmap failure.

One near-miss is worth recording, because it nearly produced a wrong conclusion. The *format strings*
passed to `OutputDebugStringF` — `"ThreadSocketHandler started"`, `"Loading addresses"` — appear in
**both** binaries, and an early count of them suggested our build had debug output and his had less
of it. They prove nothing. `util.h:30` reads:

```c
#ifdef _WINDOWS
#define printf OutputDebugStringF
#endif
```

`_WINDOWS` comes from `WXDEFS` and is always defined, so every call site compiles in regardless; only
the *function body* is gated. The strings are arguments, present either way. The distinction between
"a string that is gated" and "a string that merely looks gated" is the entire finding.

**Conclusion: the released client is a debug build.** Our v0.1.1 was not. That is a divergence from
the artifact being reconstructed, not a tidier way of building it.

## What changed

`full_build_wsl.sh` now takes `BUILD=debug|release` — the same variable Satoshi's makefile takes, with
the same default — and reproduces `CFLAGS` from `makefile:28`:

```
-mthreads -O0 -w -Wno-invalid-offsetof -Wformat $(DEBUGFLAGS) $(WXDEFS)
```

Four things follow that were previously absent:

- **`-D__WXDEBUG__`**, with wxWidgets rebuilt `--enable-debug` in a parallel tree. The define cannot
  be set on the application alone: wx 2.8 inline code compiled into our units must agree with the
  library it links. Satoshi linked the debug wx too — his include path ends `/lib/vc_lib/mswd`, the
  debug setup directory, and his `LIBS` read `-l wxmsw28$(D)_core` with `D=d`.
- **`windres ui.rc`**, producing the `.rsrc` section and the eleven bitmaps and icons.
- **`-mthreads`**, which on MinGW selects thread-safe C++ exception handling and the
  `_beginthreadex` runtime. This client runs five threads. It is not cosmetic.
- **`sha.cpp` at `-O3`**, overriding the `-O0` every other unit gets. It is the mining inner loop, and
  his makefile singles it out.

## The divergence that was not corrected

Satoshi linked OpenSSL and the MinGW runtime **dynamically** and shipped `libeay32.dll` and
`mingwm10.dll` beside the executable. We link statically: one file, 14.8 MB against his 6.4 MB, with
`.CRT`, `.tls` and `.reloc` sections his binary does not have.

This is left as it is, and disclosed rather than fixed. DLLs we shipped could not be *his* DLLs —
ours would come from Ubuntu's mingw-w64, not his MinGW — so matching the structure buys a resemblance
while adding two more files that must survive intact for the client to start at all. A single
self-contained executable is the more durable form, and nothing a peer can observe changes. It is
also why `capture_binding.ps1` reports both DLLs as *"absent — statically linked build"*.

## Method

Three days of hashing, string-scanning and cross-platform auditing did not surface either defect.
**Running the client surfaced both within an hour**, and the run was undertaken to mine a block, not
to test the build.

The correction then came from the reverse direction: the symptoms were explained by reading the
makefile, and reading the makefile alone would have justified the change on the wrong grounds — a
default, rather than evidence. Asking the shipped binary turned a plausible inference into a measured
fact, and along the way killed a false signal that pointed the other way.

Neither defect touches consensus. The genesis wrote correctly, the wire handshake is exact, both
implementations agree on every block, and block 1 was mined and relayed by the binary that has them.
They are divergences in the *build*, and they are now measured rather than assumed.
