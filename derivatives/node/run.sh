#!/usr/bin/env bash
# Build and run the headless v0.1 consensus ports. Requires C++17 + OpenSSL.
# MSYS2/MinGW: export GXX=/c/msys64/mingw64/bin/g++ and put mingw64/bin on PATH.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; cd "$HERE"
GXX="${GXX:-g++}"
echo "=== node_port (genesis reproduction, subsidy, PoW, difficulty) ==="
"$GXX" -std=c++17 -O2 -Wno-deprecated-declarations node_port.cpp -o node_port.exe -lcrypto
./node_port.exe
echo
echo "=== chain_port (UTXO block-connect: spends, double-spend, inflation, maturity) ==="
"$GXX" -std=c++17 -O2 -Wno-deprecated-declarations chain_port.cpp -o chain_port.exe -lcrypto
./chain_port.exe
