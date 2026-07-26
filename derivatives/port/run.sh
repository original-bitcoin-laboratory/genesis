#!/usr/bin/env bash
# Build the C++/OpenSSL port, run it and the Python MODEL over the shared vector
# corpus, and diff the two. Requires a C++17 compiler + OpenSSL (libcrypto).
# On MSYS2/MinGW: export GXX=/c/msys64/mingw64/bin/g++ and put mingw64/bin on PATH.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
GXX="${GXX:-g++}"

"$GXX" -std=c++17 -O2 -Wno-misleading-indentation port.cpp -o port.exe -lcrypto
./port.exe < vectors.txt > cxx_out.txt
python diff_runner.py vectors.txt > py_out.txt

if diff -u cxx_out.txt py_out.txt; then
  echo "IDENTICAL on $(grep -cvE '^#|^[[:space:]]*$' vectors.txt) vectors — Python MODEL == real OpenSSL BN port"
else
  echo "DIFFERENCES (OpenSSL is authoritative)"; exit 1
fi
