#!/usr/bin/env bash
# Build the C++/OpenSSL end-to-end (secp256k1) OP_CHECKSIG / OP_CHECKMULTISIG:
# it generates keys, signs the demo tx, self-checks, and writes scenario.txt; then
# the Python MODEL interpreter independently verifies those signed scenarios.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
GXX="${GXX:-g++}"

"$GXX" -std=c++17 -O2 -Wno-deprecated-declarations checksig_e2e.cpp -o checksig_e2e.exe -lcrypto
./checksig_e2e.exe
echo "--- Python MODEL interpreter verifies the C++-signed scenarios ---"
python verify_scenario.py scenario.txt
