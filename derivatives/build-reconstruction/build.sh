#!/usr/bin/env bash
# Reproducible build-reconstruction probe for the ORIGINAL v0.1.0 source.
#
# It compiles Satoshi's unmodified, hash-verified source on the modern host
# toolchain and reports, per translation unit, exactly where the portable subset
# ends -- distinguishing the two period-locks (32-bit target; OpenSSL <= 1.0.2)
# from a genuinely portable unit (sha.cpp, which also executes correctly).
#
# Requires: a C++ compiler + OpenSSL headers (MSYS2 mingw64 g++ + openssl here),
# and the R0-verified archive extracted at ../../extracted/ (that tree is
# .gitignored; regenerate it from the verified .tgz if absent). NOT money.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$HERE/../../extracted/bitcoin/src"
OUT="$HERE/build"; mkdir -p "$OUT"
GXX="${GXX:-}"
[ -z "$GXX" ] && [ -x /c/msys64/mingw64/bin/g++.exe ] && export PATH="/c/msys64/mingw64/bin:$PATH"
GXX="${GXX:-g++}"
STD="-std=gnu++11 -w -DOPENSSL_SUPPRESS_DEPRECATED"
rc=0

echo "== build-reconstruction =="
echo "g++: $("$GXX" --version 2>/dev/null | head -1 || echo 'NOT FOUND')"
if [ ! -d "$SRC" ]; then
  echo "!! original source not found at extracted/bitcoin/src"
  echo "   extract the R0-verified bitcoin-0.1.0 archive first (see ../../scripts)."
  exit 2
fi

echo; echo "-- [1/5] verify we are compiling the UNMODIFIED originals --"
if sed "s|  src/|  $SRC/|" "$HERE/MANIFEST.sha256" | sha256sum -c --quiet; then
  echo "   OK: all referenced source files match MANIFEST.sha256"
else
  echo "!! source hash mismatch -- extracted tree is not the verified v0.1.0"; rc=1
fi

echo; echo "-- [2/5] sha.cpp: compile UNMODIFIED (expect OK) --"
if "$GXX" $STD -I"$SRC" -c "$SRC/sha.cpp" -o "$OUT/sha.o" 2>"$OUT/sha.err"; then
  echo "   COMPILES: sha.cpp -> sha.o"
else
  echo "!! sha.cpp failed unexpectedly:"; sed 's/^/     /' "$OUT/sha.err" | head; rc=1
fi

echo; echo "-- [3/5] sha.cpp: EXECUTE against known-answer vectors (expect ALL PASS) --"
if "$GXX" $STD -I"$SRC" "$HERE/sha_selftest.cpp" "$SRC/sha.cpp" -o "$OUT/sha_selftest.exe" 2>"$OUT/sha_st.err"; then
  if "$OUT/sha_selftest.exe"; then :; else echo "!! sha vectors FAILED"; rc=1; fi
else
  echo "!! sha_selftest build failed:"; sed 's/^/     /' "$OUT/sha_st.err" | head; rc=1
fi

# probe: compile prelude + a header; classify PASS / expected-BLOCK(at wall)
probe() { # $1 label  $2 "headers"  $3 expect-substring-in-error ("" => expect COMPILE)
  local lbl="$1" hdrs="$2" want="$3" f="$OUT/probe_${1}.cpp"
  { echo '#include "compat/prelude.h"'; for h in $hdrs; do echo "#include \"$h\""; done
    echo 'int main(){return 0;}'; } > "$f"
  if "$GXX" $STD -I"$HERE" -I"$HERE/compat" -I"$SRC" -c "$f" -o "$f.o" 2>"$f.err"; then
    if [ -z "$want" ]; then echo "   COMPILES: $lbl"; else
      echo "!! $lbl compiled but a period-lock was expected ($want)"; rc=1; fi
  else
    local line; line="$(grep -m1 -E ':[0-9]+:[0-9]+: error:' "$f.err" | grep -oE '[a-z0-9_]+\.h:[0-9]+' | head -1)"
    if [ -n "$want" ] && grep -q "$want" "$f.err"; then
      echo "   BLOCKED (expected): $lbl  @ $line"
    else
      echo "!! $lbl blocked for an UNEXPECTED reason @ $line"; sed 's/^/     /' "$f.err" | grep -m1 error:; rc=1
    fi
  fi
}

echo; echo "-- [4/5] serialize.h: 32-bit-target lock (expect BLOCK @ serialize.h:462) --"
probe serialize "serialize.h" "no matching function for call to 'min"

echo; echo "-- [5/5] bignum.h: OpenSSL<=1.0.2 lock (expect BLOCK: incomplete type BIGNUM) --"
probe bignum "bignum.h" "incomplete type 'BIGNUM'"

echo
[ $rc -eq 0 ] && echo "RESULT: all expectations held (sha executes; both period-locks reproduced)." \
             || echo "RESULT: one or more expectations VIOLATED (see !! above)."
exit $rc
