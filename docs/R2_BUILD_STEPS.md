# R2 — build steps you can actually run (with WSL / Docker)

Honest, staged instructions to attempt a period build of the January‑2009 source.
Read the "which goal" section first — it decides everything.

## First, the finding that shapes this

`src/makefile` is **Windows‑only**: target `all: bitcoin.exe`, `-D__WXMSW__ -DWIN32`,
and it links Win32 (`kernel32 … ws2_32`), `eay32` (OpenSSL‑for‑Windows), and `wxmsw28`
(wxWidgets *MSW*). `makefile.vc` is the Visual C++ variant. **There is no Linux
makefile.** So:

| Goal | What it takes | Difficulty |
|---|---|---|
| **A. Byte‑reproduce `bitcoin.exe`** (sha256 `fbcac071…`) | a *period Windows* toolchain: MinGW GCC ~3.4 + wxWidgets 2.8 (MSW) + OpenSSL 0.9.8 (Win) + Berkeley DB 4.x + Boost, laid out as `/boost /DB /OpenSSL /wxWidgets` | hardest; WSL/Linux does **not** directly help |
| **B. Get the source to build + run at all** | a **Linux port** on a *period* distro (small patch set) | doable, iterative — recommended first |

Do **B** first. It proves the source compiles and runs (R2's core intent) even though
the resulting Linux binary is *not* byte‑identical to the Windows `bitcoin.exe` (wrong
platform — that's expected).

## Goal B — period‑Linux build in Docker (start here)

Idea: use a **period distro** (Ubuntu 10.04) so the *dependencies already match the era*
(wxWidgets 2.8, OpenSSL 0.9.8, Berkeley DB 4.8, Boost 1.40). Then the only real work is
the **Windows→Linux port** (wxMSW→wxGTK, drop Win32 libs, replace a few Win32 calls) —
not fighting modern OpenSSL 3 / wx 3 API changes.

### 1. Prereqs (on either Windows machine, in WSL)
```bash
# in WSL (Ubuntu):
sudo apt-get update && sudo apt-get install -y docker.io   # or install Docker Desktop
sudo service docker start
```

### 2. Get the verified source into WSL
Copy the extracted, hash‑verified tree out of the repo (it's gitignored, stays local):
```bash
# adjust the Windows path; /mnt/c is your C: drive inside WSL
cp -r "/mnt/c/Users/<you>/Desktop/workspace/vscode_workspace_bitcoin-proton/original-bitcoin-laboratory/lab/genesis/extracted/bitcoin/src" ~/btc01-src
```

### 3. A period build container (`Dockerfile`)
```dockerfile
FROM ubuntu:10.04
# 10.04 is EOL; point apt at the archive
RUN sed -i 's|archive.ubuntu.com|old-releases.ubuntu.com|g; s|security.ubuntu.com|old-releases.ubuntu.com|g' /etc/apt/sources.list
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential g++ make \
      libwxgtk2.8-dev libssl-dev libdb4.8++-dev libboost-all-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
```
```bash
cd ~/btc01-src && docker build -t btc01 -f Dockerfile .   # put the Dockerfile in ~/btc01-src
docker run -it -v ~/btc01-src:/src btc01 bash
```

### 4. Port the makefile (inside the container)
Write a `makefile.linux` (start from the original, minus Windows):
```make
INCLUDEPATHS = $(shell wx-config --cxxflags) -I/usr/include
LIBS = -ldb_cxx -lssl -lcrypto -lboost_system -lboost_filesystem -lboost_thread \
       $(shell wx-config --libs core,base,html,richtext)
CFLAGS = -O0 -w -Wno-invalid-offsetof -D__WXGTK__ -DNOPCH $(INCLUDEPATHS)
OBJS = obj/util.o obj/script.o obj/db.o obj/net.o obj/irc.o obj/main.o \
       obj/market.o obj/uibase.o obj/ui.o obj/sha.o
bitcoin: $(OBJS)
	g++ $(CFLAGS) -o bitcoin $(OBJS) $(LIBS)
obj/%.o: %.cpp
	@mkdir -p obj && g++ -c $(CFLAGS) -o $@ $<
```
```bash
make -f makefile.linux 2>&1 | tee /src/build.log
```

### 5. Patch the Windows‑isms it complains about — and **log every patch**
Expect errors in this order; fix, re‑run, repeat:
- `headers.h`: comment out `#include <windows.h> / <winsock2.h> / <mswsock.h> / <io.h>`,
  keep `<sys/*>` equivalents; make sure `using namespace std;` stays before other headers.
- `QueryPerformanceCounter`, `_beginthread`, `Sleep`, `GetTickCount`: replace with
  `clock_gettime`, `pthread_create`, `usleep`, etc.
- wx: `__WXMSW__`→`__WXGTK__` code paths; tray‑icon / clipboard bits may need stubbing.
- Berkeley DB: `libdb4.8` header/version pin (`DB_CXX_HEADER`).

**Discipline:** keep every edit as a patch with a one‑line reason (a `patches/` dir),
classed like the NOV08‑X ledger (`ORIGINAL` / `PORT‑COMPAT` / `PLATFORM`). A build that
needed 30 logged patches is honest; a silently‑edited tree is not.

### 6. Report back
Paste me `build.log` (or the first error block) and I'll give you the exact next patch.
This is genuinely iterative — early Bitcoin is finicky — but each error has a known fix,
and we converge.

## Goal A — reproducing the exact `bitcoin.exe` (later, harder)

Only attempt after B works. You need a **Windows** MinGW period environment (or a
`mingw‑w64` cross‑compiler in WSL) plus **Windows** builds of wx 2.8 / OpenSSL 0.9.8 /
BDB 4.x, arranged as the makefile expects (`/boost /DB/build_unix /OpenSSL /wxWidgets`).
Build with the original `makefile`, then `sha256sum bitcoin.exe` and compare to
`fbcac071d92e26d82ec917214e334bd43850c0691f113bab1d4741c9bdd30d2d`. A match is a genuine
reproducible‑build result; a mismatch tells us which component/version differs. Sourcing
the exact period Windows libraries is the hard part and may not be fully attainable — which
is why byte‑repro stays "open" while build‑and‑run (B) is the achievable win.

## Shortcut worth knowing

The lab's **C++ PORT** (`derivatives/port/`, `derivatives/node/`) already compiles the
v0.1 *consensus + script* on a modern toolchain (OpenSSL 3), reproduces the exact genesis,
and is differential‑tested. So the *consensus* is already an executable reconstruction;
Goal B adds the rest of the original program (GUI, market, db) as a period build.
