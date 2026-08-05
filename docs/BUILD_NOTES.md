# Build notes — v0.1.2

**5 August 2026**

The client was run for the first time on 4 August, to mine block 1. It mined it, and it showed two
things that three days of hashing and string-scanning had not: it wrote no `debug.log`, and
wxWidgets logged *"Can't load bitmap 'send20' from resources!"* at startup.

Both were failures to follow `src/makefile` — the makefile in this source tree, which ships inside
the release tarball. Neither touches consensus. This note records what they were, how the one
genuine ambiguity was settled, and one place where the makefile is not followed on purpose.

## What the makefile specifies, and what the build was doing

```make
DEBUGFLAGS=-g -D__WXDEBUG__
CFLAGS=-mthreads -O0 -w -Wno-invalid-offsetof -Wformat $(DEBUGFLAGS) $(WXDEFS) $(INCLUDEPATHS)

obj/ui_res.o: ui.rc  rc/bitcoin.ico rc/check.ico rc/send16.bmp … rc/addressbook20mask.bmp
	windres $(WXDEFS) $(INCLUDEPATHS) -o $@ -i $<
```

Four things in there were not happening:

- **`-D__WXDEBUG__`.** The whole body of `OutputDebugStringF` sits inside `#ifdef __WXDEBUG__`
  (`util.h:232`). Without the define the function is a no-op, so the client emits no diagnostic
  output at all — not to file, not to `OutputDebugString`. That is the missing `debug.log`.
- **`windres ui.rc`.** The rule was never run, so the binary had no `.rsrc` section and none of the
  eleven bitmaps and icons. That is the missing toolbar.
- **`-mthreads`.** On MinGW this selects thread-safe C++ exception handling and the
  `_beginthreadex` runtime. This client runs five threads: socket handler, IRC seed, message
  handler, miner, UI.
- **`sha.cpp` at `-O3`**, overriding the `-O0` every other unit gets. It is the mining inner loop.

`full_build_wsl.sh` now does all four, and takes `BUILD=debug|release` the way the makefile does.

## The one real ambiguity: debug or release

The makefile can build either way:

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

Bare `make` gives debug. `make BUILD=release` gives no `__WXDEBUG__`, links the release wxWidgets,
and produces a client that writes no log. Both are legal builds of this tree, so the default is
suggestive and not conclusive — plenty of projects ship the non-default mode.

The lab holds a 2009-era binary of the same source, `fbcac071…`, in `extracted/`. It works as a
**control sample**: whatever mode it was built in, its markers show which of the two the makefile's
author had in mind. Reading it as data, not as a standard:

| marker | 2009 control `fbcac071…` | our v0.1.1 `cfb59606…` |
|---|---|---|
| `debug.log` | 7 | 0 |
| `assert "%s" failed` | 1 | 0 |
| distinct `include/wx/*.h` paths | 24 | 0 |
| `.rsrc` section | present | absent |

Each row carries different weight. **`debug.log`** occurs in exactly one place in the entire source
— `util.h:236`, `fopen("debug.log", "a")`, inside the `#ifdef` — so there is no other route for that
literal into a binary built from this tree. **The wx header paths** are `__FILE__` expansions from
`wxASSERT` inside wxWidgets' inline code; `wxASSERT` compiles to nothing without `__WXDEBUG__`, so
24 distinct paths cannot appear in a release build.

Debug, then. `BUILD` defaults to debug here for the same reason it does there.

One near-miss is worth recording, because it briefly pointed the other way. The *format strings*
passed to `OutputDebugStringF` — `"ThreadSocketHandler started"`, `"Loading addresses"` — appear in
**both** binaries, and counting them suggested our build had more debug output rather than none.
They prove nothing. `util.h:30` reads:

```c
#ifdef _WINDOWS
#define printf              OutputDebugStringF
#endif
```

`_WINDOWS` comes from `WXDEFS` and is always defined, so every call site compiles in regardless;
only the function *body* is gated. The strings are arguments, present either way. Distinguishing a
string that is gated from one that merely looks gated is the whole of it.

## Where the makefile is not followed, on purpose

**`-g` is dropped.** Building with it produced a **54.8 MB** binary carrying eight `.debug_*`
sections, against 15.5 MB without. DWARF is debugger metadata: it changes no instruction, and this
is a client meant to be run, copied and kept, not stepped through. It is also where absolute build
paths live — with `-g` on, the build refused to link because `/home/xyoga` had been embedded via
DWARF arriving from wxWidgets' own `--enable-debug` compilation, which `-ffile-prefix-map` did not
reach. `__WXDEBUG__` is the half of `DEBUGFLAGS` with observable behaviour and it stays; `-g` has
none and goes.

Worth noting the 2009 control has no `.debug_*` sections either, so nothing is lost by the
comparison this decision does not depend on.

**Static linking.** OpenSSL, Berkeley DB, wxWidgets and the C++ runtime are all inside the
executable, which ships no DLLs. One file that either runs or does not, with nothing beside it that
has to survive intact for it to start. This is also why `capture_binding.ps1` reports
`libeay32.dll` and `mingwm10.dll` as *"absent — statically linked build"*.

**Debug sections are stripped at link.** OpenSSL, Berkeley DB and wxWidgets all default their
`configure` to `-g`, so their DWARF rode in through static linking even when nothing here asked for
it — v0.1.1 shipped eight `.debug_*` sections for that reason alone. The link now strips them.

## Result

`bitcoin-0.1.2.tar.gz` sha256 `099c011d…`, shipping `bitcoin.exe` sha256 `d148996b…`.

| | v0.1.1 `cfb59606…` | v0.1.2 `d148996b…` |
|---|---|---|
| `debug.log` written | no | **yes** |
| toolbar bitmaps | absent | **present** |
| `.rsrc` section | absent | **present** |
| `.debug_*` sections | 8 | **0** |
| `-mthreads` | no | **yes** |
| `sha.cpp` optimisation | `-O0` | **`-O3`** |
| build-machine paths | 0 | **0** |

## Method

Three days of hashing, string-scanning and cross-platform auditing did not surface either defect.
**Running the client surfaced both within an hour**, and the run was undertaken to mine a block, not
to test the build.

The correction then nearly went in on the wrong basis. The symptoms were explained by reading the
makefile, and the makefile's default would have justified the change without establishing anything —
a default is not evidence. Consulting a control sample turned an inference into a measurement, and
along the way killed a false signal that pointed the other way.

Neither defect touched consensus. The genesis wrote correctly, the wire handshake is exact, both
implementations agree on every block, and block 1 was mined and relayed by the v0.1.1 binary that
had them.

---

# Reproducible builds

**5 August 2026**

`bitcoin.exe` is byte-reproducible. Two machines that share a toolchain now produce the same
15,529,604 bytes:

```
c3f15fc5b7bd80f4d08fe5ff356256214734eb1a3e4a7c953c9e8fc8453d2c7d
```

A GitHub-hosted runner built it from the published 2009 archive and arrived at exactly that, with
zero differing bytes against the local build. The job is `.github/workflows/reproducible.yml`; it
fails loudly if the hash ever moves.

This was the one objection in `00-DECISIONS-AND-REASONING.md` §11 conceded without a rebuttal.

## What it took: two flags

Nobody had ever built this twice and compared. Doing so cost minutes and found everything.

**First comparison — same machine.** Two builds of identical inputs differed in **4 bytes of
15,529,604**: two in the PE `TimeDateStamp` at `0x88`, and two in the `CheckSum` at `0xd8` that
derives from it. `ld` writes the build clock into the header. `-Wl,--no-insert-timestamp` zeroes it.

**Second comparison — a different machine.** With an identical toolchain, the runner still differed,
now in **8 bytes**. Six were in `.rdata` and every one was an ASCII digit. Read as a string:

```
local   '23:28:12'   'Aug  4 2026'
CI      '01:20:56'   'Aug  5 2026'
```

wxWidgets stamping its own build clock through `wxGetLibraryVersionInfo`, plus the PE checksum
following it. gcc honours `SOURCE_DATE_EPOCH` for `__DATE__` and `__TIME__` from version 7 on, so
the build exports it.

Worth stating plainly, because it is the substance of the finding: **not one instruction ever
differed.** Not a symbol, not a section, not an offset, not a byte of any of the four statically
linked period libraries. Two machines hours apart emitted identical machine code and disagreed only
about what time it was. The build was never chaotic — it was two clocks, and nobody had looked.

## The epoch

`SOURCE_DATE_EPOCH=1785781375` — 2026-08-03 18:22:55 UTC, **this chain's own genesis**. Any fixed
number would work. Using the genesis means the binary carries the instant the chain starts from, and
it is a figure already published and independently checkable rather than one invented for the
purpose. The string inside the binary reads `Aug  3 2026` / `18:22:55`.

## What reproducibility here does and does not mean

**Does:** anyone with the same toolchain can rebuild the shipped bytes from the published 2009
archive and check them against the signature. The signature stops attesting only that *we* built
something; it attests to a binary anyone can regenerate.

**Does not:** free the result from the toolchain. gcc 13.2.0 with the **win32** thread model,
binutils 2.41.90, mingw-w64 11.0.1, on Ubuntu 24.04. A different compiler emits different code, and
Ubuntu ships the posix thread variant alongside the win32 one — they are not interchangeable and do
not produce the same binary. The CI job asserts the alternative rather than hoping, and prints the
full package set on every run.

That limit is not removable by trying harder; it is what "reproducible build" means everywhere,
including Bitcoin Core, which pins its toolchain with Guix for the same reason.

## The order of operations mattered

The first CI run failed, and the failure was worth more than a pass would have been. It failed
because neither `extracted/` nor `derivatives/bitcoin/src/` is in the repository — correctly, since
the first is a third party's archive and the second is derived from it — which meant the job had
been about to build from files that only exist on a machine that already did the work by hand.

It now starts where a stranger starts: fetch `bitcoin-0.1.0.tgz`, check it against `ce9da465…`,
extract, run `make_chain.py` (which refuses unless each of the ten edits matches exactly once), then
build and compare. The whole chain, on a machine nobody here controls.
