#!/usr/bin/env bash
# Build the C++/OpenSSL SignatureHash port, run it and the Python MODEL over the
# same fixed transaction, and diff the 32-byte digests for every nIn x SIGHASH type.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
GXX="${GXX:-g++}"

"$GXX" -std=c++17 -O2 sighash.cpp -o sighash.exe -lcrypto
./sighash.exe > cxx_sighash_out.txt
python ../model/tx_sighash.py > py_sighash_out.txt

if diff -u cxx_sighash_out.txt py_sighash_out.txt; then
  echo "IDENTICAL SignatureHash on $(grep -c . cxx_sighash_out.txt) (nIn x SIGHASH) cases -- MODEL == OpenSSL port"
else
  echo "DIFFERENCES"; exit 1
fi
