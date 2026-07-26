#!/usr/bin/env bash
# Build and run the headless v0.1 consensus port. Requires a C++17 compiler +
# OpenSSL (libcrypto). MSYS2/MinGW: export GXX=/c/msys64/mingw64/bin/g++ and put
# mingw64/bin on PATH.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; cd "$HERE"
GXX="${GXX:-g++}"
"$GXX" -std=c++17 -O2 -Wno-deprecated-declarations node_port.cpp -o node_port.exe -lcrypto
./node_port.exe
