#!/usr/bin/env bash
# Reproducible PERIOD build of the original v0.1.0 consensus-crypto core.
#
# Where build.sh measures the modern host and finds two period-locks, THIS script
# supplies the period toolchain and shows the same original source compiling and
# running: an i686 cross-compile (kills serialize.h:462) against a from-source
# OpenSSL 1.0.2 (kills bignum.h:49, the public-BIGNUM lock). It then builds and
# runs period_exec_test.cpp, exercising the ORIGINAL bignum.h + key.h.
#
# Verified on WSL Ubuntu 24.04 with the mingw i686 cross-toolchain:
#   sudo apt-get install -y gcc-mingw-w64-i686 g++-mingw-w64-i686 make perl
# Needs the R0-verified archive extracted at ../../extracted/. NOT money.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$HERE/../../extracted/bitcoin/src"
WORK="${WORK:-$HOME/obl-period-build}"
XPREFIX=i686-w64-mingw32
GXX="$XPREFIX-g++"
OSSL_VER=1.0.2u
OSSL_SHA=ecd0c6ffb493dd06707d38b14bb4d8c2288bb7033735606569d8f90f89669d16   # openssl.org
OSSL_URL="https://www.openssl.org/source/old/1.0.2/openssl-$OSSL_VER.tar.gz"

echo "== period build (i686 + OpenSSL $OSSL_VER) =="
command -v "$GXX" >/dev/null || { echo "!! missing $GXX -- sudo apt-get install -y gcc-mingw-w64-i686 g++-mingw-w64-i686"; exit 2; }
[ -d "$SRC" ] || { echo "!! extract the R0-verified bitcoin-0.1.0 archive at extracted/ first"; exit 2; }
echo "toolchain: $($GXX -dumpmachine), $($GXX --version | head -1)"
mkdir -p "$WORK"; cd "$WORK"

echo; echo "-- [1/4] OpenSSL $OSSL_VER (last public-BIGNUM release), verified + cross-built --"
if [ ! -f "openssl-$OSSL_VER.tar.gz" ]; then
  wget -q "$OSSL_URL" || curl -fsSLO "$OSSL_URL"
fi
echo "$OSSL_SHA  openssl-$OSSL_VER.tar.gz" | sha256sum -c -
OSSL="$WORK/openssl-$OSSL_VER"
[ -d "$OSSL" ] || tar xzf "openssl-$OSSL_VER.tar.gz"
if [ ! -f "$OSSL/libcrypto.a" ]; then
  ( cd "$OSSL"
    ./Configure mingw no-shared no-asm no-dso --cross-compile-prefix="$XPREFIX-" >/dev/null
    make links >/dev/null 2>&1 || true
    make build_crypto >/dev/null 2>&1 )
fi
[ -f "$OSSL/libcrypto.a" ] && echo "   libcrypto.a: $(stat -c%s "$OSSL/libcrypto.a") bytes" || { echo "!! OpenSSL build failed"; exit 1; }

INC="-I$OSSL/include -I$HERE -I$HERE/compat -I$SRC"
STD="-std=gnu++11 -w -DOPENSSL_SUPPRESS_DEPRECATED"

echo; echo "-- [2/5] compile the ORIGINAL core (both locks now lifted) --"
probe() { # $1 label  $2 headers
  { echo '#include "compat/prelude.h"'; for h in $2; do echo "#include \"$h\""; done; echo 'int main(){return 0;}'; } > "$WORK/p.cpp"
  if $GXX $STD $INC -c "$WORK/p.cpp" -o "$WORK/p.o" 2>"$WORK/p.err"; then echo "   COMPILES: $1"
  else echo "   BLOCKED:  $1 -> $(grep -m1 error: "$WORK/p.err" | grep -oE '[a-z0-9_]+\.h:[0-9]+' | head -1) (coupling, not a lock)"; fi
}
probe "serialize.h"                         "serialize.h"
probe "uint256.h"                           "serialize.h uint256.h"
probe "bignum.h  (was the OpenSSL lock)"    "serialize.h uint256.h bignum.h"
probe "key.h     (secp256k1 EC_KEY)"        "serialize.h uint256.h bignum.h key.h"

LIBS="-lcrypto -lws2_32 -lgdi32 -lcrypt32 -ladvapi32 -luser32 -static -static-libgcc -static-libstdc++"

echo; echo "-- [3/5] build the crypto exec test (original bignum.h + key.h) --"
$GXX $STD $INC "$HERE/period_exec_test.cpp" -L"$OSSL" $LIBS -o "$WORK/period_exec_test.exe"
echo "   built: $WORK/period_exec_test.exe ($(stat -c%s "$WORK/period_exec_test.exe") bytes)"

echo; echo "-- [4/5] build the INTERPRETER test (original script.cpp, donor-assisted) --"
# verbatim copy of script.cpp + a one-line headers.h shim next to it, so its
# #include "headers.h" resolves to our headless one (donor tx/util surfaces, no wx/BDB).
SB="$WORK/script-build"; mkdir -p "$SB"
cp "$SRC/script.cpp" "$SB/script.cpp"
echo "#include \"$HERE/compat/headers_headless.h\"" > "$SB/headers.h"
# NB: -I"$SB" must precede -I"$SRC" so our headers.h shadows the original wx-laden one.
$GXX $STD -I"$SB" $INC "$SB/script.cpp" "$HERE/script_exec_test.cpp" -L"$OSSL" $LIBS \
  -o "$WORK/script_exec_test.exe"
echo "   built: $WORK/script_exec_test.exe ($(stat -c%s "$WORK/script_exec_test.exe") bytes)"

echo; echo "-- [5/5] run them --"
for exe in "$WORK/period_exec_test.exe" "$WORK/script_exec_test.exe"; do
  echo "   >> $(basename "$exe")"
  if command -v wine >/dev/null 2>&1; then wine "$exe" 2>/dev/null || true
  else echo "      (run on Windows/WOW64): $(wslpath -w "$exe" 2>/dev/null || echo "$exe")"; fi
done
echo; echo "done."
