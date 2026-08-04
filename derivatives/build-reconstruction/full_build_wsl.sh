#!/usr/bin/env bash
# Reproducible FULL build of the January 2009 client from Satoshi's original source.
#
# Where period_build_wsl.sh builds the consensus/crypto/script core with donor scaffolding,
# THIS script builds the entire runnable GUI binary the faithful way: it cross-compiles all four
# period libraries and then compiles EVERY original .cpp against the real headers.h, linking a
# self-contained i686 bitcoin.exe. It is the executed form of PERIOD_BUILD.md.
#
# The one insight that makes it work on a modern host: compile in each component's era dialect --
# wxWidgets 2.8 and the Bitcoin source are C++98 (-std=gnu++98/-std=gnu89), which sidesteps the
# whole class of modern-compiler rejections (narrowing, std::array vs boost::array under the dual
# `using namespace std/boost`, removed keywords). Verified on WSL Ubuntu 24.04 + mingw i686 (gcc 13).
#
#   sudo apt-get install -y gcc-mingw-w64-i686 g++-mingw-w64-i686 make perl
#   bash full_build_wsl.sh          # ~15-30 min the first time (builds wx/bdb/openssl)
#
# Needs the R0-verified archive extracted at ../../extracted/. NOT money. This rebuilds the client
# FROM SOURCE; the released bitcoin.exe (sha256 fbcac071...) remains the JAN09-EXECUTED oracle.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Defaults to the R0-verified January 2009 tree. Override SRC to build a derived chain from the
# same period toolchain (e.g. derivatives/bitcoin/src, produced by bitcoin/make_chain.py).
SRC="${SRC:-$HERE/../../extracted/bitcoin/src}"
W="${WORK:-$HOME/obl-period}"; mkdir -p "$W"
X=i686-w64-mingw32; GXX="$X-g++"; NP="$(nproc)"

# Satoshi's src/makefile takes BUILD=debug|release and DEFAULTS TO DEBUG:
#   ifneq "$(BUILD)" "debug" / ifneq "$(BUILD)" "release" / BUILD=debug
#   ifeq "$(BUILD)" "debug"  ->  D=d ; DEBUGFLAGS=-g -D__WXDEBUG__
# We take the same variable with the same default, because the released bitcoin.exe
# (fbcac071...) is demonstrably a DEBUG build. Three markers, measured from his binary
# against ours:
#   * "debug.log"                  7 occurrences vs 0 -- and that literal exists in exactly
#                                  one place in the whole source, util.h:236, inside #ifdef __WXDEBUG__
#   * 'assert "%s" failed'         1 vs 0
#   * ../../include/wx/*.h paths   24 distinct vs 0 -- __FILE__ expansions from wxASSERT in
#                                  wx inline headers, which vanish unless __WXDEBUG__ is set
# Reading the makefile alone would suggest the opposite conclusion is arguable, since
# `make BUILD=release` is a legal build of the same tree. It is not arguable: the shipped
# artifact settles it. A release build here is a divergence, not a tidier binary.
BUILD="${BUILD:-debug}"
case "$BUILD" in debug|release) ;; *) BUILD=debug ;; esac
# NOTE on -g. His DEBUGFLAGS are "-g -D__WXDEBUG__" and we take only the second, because on this
# point the makefile and the shipped artifact disagree and the artifact is what we reconstruct:
#   his bitcoin.exe   6,440,960 bytes   sections .text .data .rdata .bss .idata .rsrc   0 debug
#   with -g here     54,860,743 bytes   + 8 .debug_* sections
# gcc 3.x-era -g did not survive into what he published. Carrying DWARF we know his binary does
# not have would be matching the flag and missing the artifact -- and DWARF is precisely where
# absolute build paths live, which is why the leak gate below fires on /home/xyoga when -g is on.
# __WXDEBUG__ is kept: it is the half that has observable behaviour (debug.log, wxASSERT).
if [ "$BUILD" = debug ]; then DEBUGFLAGS="-D__WXDEBUG__"; WXDBG="--enable-debug"
else DEBUGFLAGS=""; WXDBG="--disable-debug"; fi
echo "== BUILD=$BUILD (DEBUGFLAGS='${DEBUGFLAGS:-none}') =="
command -v "$GXX" >/dev/null || { echo "!! install: sudo apt-get install -y gcc-mingw-w64-i686 g++-mingw-w64-i686"; exit 2; }
[ -d "$SRC" ] || { echo "!! extract the R0-verified bitcoin-0.1.0 archive at extracted/ first"; exit 2; }

get() { # url  file  sha256
  [ -f "$W/$2" ] || curl -fSL --max-time 300 -o "$W/$2" "$1"
  echo "$3  $W/$2" | sha256sum -c - >/dev/null || { echo "!! sha256 mismatch: $2"; exit 1; }
}

echo "== full period build of bitcoin.exe (i686; $($GXX --version | head -1)) =="

echo "-- [1/5] OpenSSL 1.0.2u --"
get "https://www.openssl.org/source/old/1.0.2/openssl-1.0.2u.tar.gz" openssl-1.0.2u.tar.gz \
    ecd0c6ffb493dd06707d38b14bb4d8c2288bb7033735606569d8f90f89669d16
OSSL="$W/openssl-1.0.2u"; [ -d "$OSSL" ] || tar xzf "$W/openssl-1.0.2u.tar.gz" -C "$W"
if [ ! -f "$OSSL/libcrypto.a" ]; then ( cd "$OSSL"
  ./Configure mingw no-shared no-asm no-dso --cross-compile-prefix="$X-" >/dev/null
  make links >/dev/null 2>&1 || true; make build_crypto >/dev/null 2>&1 ); fi
echo "   libcrypto.a OK"

echo "-- [2/5] wxWidgets 2.8.12 (built in its native C++98 dialect) --"
get "https://github.com/wxWidgets/wxWidgets/releases/download/v2.8.12/wxWidgets-2.8.12.tar.gz" \
    wxWidgets-2.8.12.tar.gz 197c94f7d46269a7fc261a3c8c943f03a9807acf65381944489a538fd8b5dd21
WX="$W/wxWidgets-2.8.12"; [ -d "$WX" ] || tar xzf "$W/wxWidgets-2.8.12.tar.gz" -C "$W"
grep -q obl-direct-fix "$WX/include/wx/filefn.h" || sed -i "1i // obl-direct-fix\n#include <direct.h>" "$WX/include/wx/filefn.h"
# __WXDEBUG__ cannot be set on the application alone: wx 2.8 inline code compiled into our
# translation units must agree with the library it links, or the two disagree about asserts
# and layout. Each BUILD therefore gets its own wx, built out-of-tree side by side -- which is
# also what Satoshi linked: -I"/wxWidgets/lib/vc_lib/mswd" is the DEBUG setup directory, and
# his LIBS read -l wxmsw28$(D)_core with D=d.
WXB="$WX/bld-$BUILD"
if [ ! -f "$WXB/lib/libwx_base-2.8-$X.a" ]; then mkdir -p "$WXB"; ( cd "$WXB"
  ../configure --host=$X --build=x86_64-pc-linux-gnu --disable-shared --disable-unicode $WXDBG     --without-opengl --disable-mediactrl CXXFLAGS="-std=gnu++98 -include direct.h -w" CFLAGS="-std=gnu89 -w" >/dev/null 2>&1
  make -j"$NP" >/dev/null 2>&1 ); fi
echo "   $(ls "$WXB"/lib/libwx*.a 2>/dev/null | wc -l) wx libs OK ($BUILD)"

echo "-- [3/5] Berkeley DB 4.8.30.NC (4.7-API-compatible; modern-gcc atomic patches) --"
get "https://download.oracle.com/berkeley-db/db-4.8.30.NC.tar.gz" db-4.8.30.NC.tar.gz \
    12edc0df75bf9abd7f82f821795bcee50f42cb2e5f76a6a281b85732798364ef
BDB="$W/db-4.8.30.NC"; if [ ! -d "$BDB" ]; then tar xzf "$W/db-4.8.30.NC.tar.gz" -C "$W"
  sed -i "s/__atomic_compare_exchange\b/__db_atomic_compare_exchange/g" "$BDB/dbinc/atomic.h"
  sed -i "s/\batomic_init\b/__db_atomic_init/g" "$BDB/dbinc/atomic.h" "$BDB"/mp/mp_*.c; fi
if [ ! -f "$BDB/build_unix/libdb_cxx-4.8.a" ]; then ( cd "$BDB/build_unix"
  CC=$X-gcc CXX=$X-g++ ../dist/configure --host=$X --enable-mingw --enable-cxx \
    --disable-replication --disable-shared CFLAGS="-w -std=gnu89" CXXFLAGS="-w -std=gnu++98" >/dev/null 2>&1
  make -j"$NP" libdb_cxx-4.8.a >/dev/null 2>&1 ); fi
echo "   libdb_cxx-4.8.a OK"

echo "-- [4/5] Boost 1.42.0 (period, C++98 -- matches v0.1's boost 1.3x) --"
get "https://archives.boost.io/release/1.42.0/source/boost_1_42_0.tar.gz" boost_1_42_0.tar.gz \
    ac571be9223dfe2ef77d35351ab0e7cbb245ce3fa9e6eb7e0c1b7ce0504b165d
BOOST="$W/boost_1_42_0"; [ -d "$BOOST/boost" ] || tar xzf "$W/boost_1_42_0.tar.gz" -C "$W"
echo "   boost headers OK"

echo "-- [5/5] compile ALL original units + link bitcoin.exe --"
OB="$W/bitcoin-build"; mkdir -p "$OB"
CXX="$GXX -std=gnu++98 -w -fpermissive"

# Satoshi's makefile compiles `g++ -c $(CFLAGS) -o $@ $<` from inside src/ -- a RELATIVE filename --
# with its dependencies at short root paths (-I"/boost" -I"/OpenSSL/include" ...). That is why his
# bitcoin.exe embeds no build-machine paths at all: every path assert() and BOOST_ASSERT bake into
# .rodata via __FILE__ is either a bare filename or a rooted one. Compiling an ABSOLUTE source path
# instead writes the builder's home directory into the shipped binary.
#
# We reproduce both properties. Sources are compiled by relative name from within $SRC, and every
# dependency root is rewritten to the name his makefile used, so __FILE__ resolves the period way
# regardless of where this actually builds. -ffile-prefix-map implies -fmacro-prefix-map, which is
# what rewrites the __FILE__ string literals.
#
# Order matters and is the opposite of the intuition: when several maps match a path gcc applies the
# LAST one given, so these run least-specific -> most-specific. The two catch-alls come first purely
# as a backstop; the named roots that follow are what actually land, and they are deliberately the
# same names Satoshi's makefile used (-I"/boost" -I"/OpenSSL/include" -I"/wxWidgets/include" ...),
# so the rebuilt binary quotes its headers exactly as his does: /boost/boost/array.hpp.
MAP="-ffile-prefix-map=$HOME=/obl-home"
MAP="$MAP -ffile-prefix-map=$W=/obl"
MAP="$MAP -ffile-prefix-map=$SRC=/bitcoin/src"
MAP="$MAP -ffile-prefix-map=$BDB=/DB"
MAP="$MAP -ffile-prefix-map=$OSSL=/OpenSSL"
MAP="$MAP -ffile-prefix-map=$WX=/wxWidgets"
MAP="$MAP -ffile-prefix-map=$BOOST=/boost"

# Satoshi's CFLAGS, verbatim from src/makefile line 28:
#   CFLAGS=-mthreads -O0 -w -Wno-invalid-offsetof -Wformat $(DEBUGFLAGS) $(WXDEFS) $(INCLUDEPATHS)
# -mthreads is not cosmetic on MinGW -- it selects thread-safe C++ exception handling and the
# _beginthreadex-based runtime, and this client runs five threads (socket handler, IRC seed,
# message handler, miner, UI). Building a threaded app without it is a real divergence.
WXDEFS="-DWIN32 -D__WXMSW__ -D_WINDOWS -DNOPCH"
CFLAGS="-mthreads -O0 -w -Wno-invalid-offsetof -Wformat $DEBUGFLAGS $WXDEFS"
INC="$($WXB/wx-config --cxxflags) -I$OSSL/include -I$BDB/build_unix -I$BOOST -I."
( cd "$SRC"
  for f in util script net irc db market main uibase ui; do
    $CXX $CFLAGS $MAP $INC -c "$f.cpp" -o "$OB/$f.o"; echo "   compiled $f.cpp"
  done
  # sha.cpp alone is compiled -O3 in his makefile, overriding the -O0 that applies to every
  # other unit. It is the mining inner loop; leaving it at -O0 would be faithful to the flag
  # list and unfaithful to the artifact.
  $CXX $CFLAGS -O3 $MAP $INC -c sha.cpp -o "$OB/sha.o"; echo "   compiled sha.cpp (-O3)"
  # obj/ui_res.o: windres ui.rc -- the toolbar bitmaps, the icons, the cursor. Omitting this
  # is why the client logged "Can't load bitmap 'send20' from resources" on first execution
  # and why our binary had no .rsrc section at all where his has one.
  # windres takes preprocessor options only. His rule passes exactly $(WXDEFS) $(INCLUDEPATHS)
  # -- defines and include paths, nothing else -- so wx-config --cxxflags cannot be handed over
  # whole: it also emits -mthreads, and windres exits 1 with "invalid option -- 'm'".
  WXRC=""
  for t in $($WXB/wx-config --cxxflags); do case "$t" in -I*|-D*) WXRC="$WXRC $t";; esac; done
  $X-windres $WXDEFS $WXRC -I. -o "$OB/ui_res.o" -i ui.rc
  echo "   windres ui.rc -> ui_res.o" )
cd "$OB"
OUT="${OUTDIR:-$OB}"; mkdir -p "$OUT"   # OUTDIR is caller-supplied; ld will not create it
# His link line: g++ $(CFLAGS) -mwindows -Wl,--subsystem,windows -o $@ $(LIBPATHS) $(OBJS) $(LIBS)
# The GUI subsystem was already correct here -- wx-config --libs supplies -mwindows, and both
# binaries measure subsystem=2 -- but it is now stated rather than inherited, and -mthreads is
# carried to the link as his CFLAGS do.
#
# -static is a DELIBERATE and DISCLOSED divergence. He linked OpenSSL and the MinGW runtime
# dynamically and shipped libeay32.dll + mingwm10.dll beside the exe; we link everything in.
# Not corrected, for a reason about the artifact outliving us: DLLs we ship could not be his
# DLLs anyway -- ours would come from Ubuntu's mingw-w64, not his MinGW -- so matching the
# structure buys a resemblance while adding two more files that must survive intact for the
# client to start at all. One self-contained executable is the more durable form and changes
# nothing a peer can observe. Recorded in RELEASE.txt, and it is why capture_binding.ps1
# reports libeay32.dll / mingwm10.dll as "absent - statically linked build".
# --strip-debug: OpenSSL/BDB/wx configure scripts default to -g, so their DWARF rides in through
# static linking even when we compile without it -- our v0.1.1 shipped 8 .debug_* sections for
# exactly that reason. His binary has none. Stripping them matches his section list and removes
# the only place an absolute build path can survive.
$GXX -std=gnu++98 -mthreads -mwindows -Wl,--subsystem,windows *.o $($WXB/wx-config --libs) -L"$OSSL" -lcrypto -L"$BDB/build_unix" -ldb_cxx-4.8 -lws2_32 -lmswsock -lole32 -loleaut32 -luuid -static -static-libgcc -static-libstdc++ -o "$OUT/bitcoin-0.1.0-reconstructed.exe" -Wl,--strip-debug
echo
echo "BUILT: $OUT/bitcoin-0.1.0-reconstructed.exe ($(stat -c%s "$OUT/bitcoin-0.1.0-reconstructed.exe") bytes)"
# Hard gate: the shipped binary must carry no trace of the machine that built it. Satoshi's
# bitcoin.exe (fbcac071...) contains zero absolute paths -- only relative ones like
# ../../include/wx/arrstr.h -- so a build that leaks the builder's home directory is a divergence
# from the artifact we are reconstructing, not merely an untidy one. Fail loudly rather than ship.
LEAKS="$(grep -aoE '(/home/[A-Za-z0-9_.-]+|/mnt/[a-z]/[A-Za-z0-9_.-]+|[A-Za-z]:\+Users)' \
        "$OUT/bitcoin-0.1.0-reconstructed.exe" | sort -u || true)"
if [ -n "$LEAKS" ]; then
  echo "!! build-machine paths embedded in the binary -- refusing to ship:"; echo "$LEAKS" | sed 's/^/     /'
  exit 1
fi
echo "paths: no build-machine paths embedded (matches the original's property)."

$X-objdump -p "$OUT/bitcoin-0.1.0-reconstructed.exe" | grep -q "DLL Name" && \
  echo "imports: system DLLs only (statically linked wx/openssl/bdb) -- a self-contained GUI client."
echo "Run it ONLY in an isolated VM (see docs/R3_*): it is a live 2009 node (creates a wallet,"
echo "attempts IRC peer discovery, mines). Building it here is FROM SOURCE; not money."