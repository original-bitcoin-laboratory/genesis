// SPDX-License-Identifier: MIT
// A test DRIVER, original to this laboratory, 2026. It reproduces no Satoshi-authored code: it
// links against the UNMODIFIED src/sha.cpp and src/sha.h, which are Crypto++ by Wei Dai (public
// domain, from Steve Reid's sha1.c) and carry no Satoshi notice in the 2009 release either.
// Executes Satoshi's ORIGINAL sha.cpp (the Crypto++-derived SHA-256) on a modern
// 64-bit toolchain and checks it against NIST/known-answer vectors.
//
// This file is a DRIVER only: it links against the unmodified src/sha.cpp and
// src/sha.h (see MANIFEST.sha256) and adds nothing to the algorithm -- just the
// standard SHA-256 message padding and the big-endian word packing that v0.1's
// IteratedHash framework performed before calling SHA256::Transform. The point is
// to show the original consensus-hash code both COMPILES and RUNS correctly today.
// NOT money.
//
//   build:  see build.sh (target: sha)
//   pass:   exit 0 and "ALL PASS"

#include <cassert>          // headers.h provided <assert.h> before sha.h; replicate that
#include "sha.h"            // ORIGINAL (namespace CryptoPP): word32, SHA256
#include <cstdio>
#include <cstdint>
#include <string>
#include <vector>
using namespace std;
using namespace CryptoPP;

static uint32_t be32(const unsigned char* p) {
    return (uint32_t(p[0]) << 24) | (uint32_t(p[1]) << 16)
         | (uint32_t(p[2]) <<  8) |  uint32_t(p[3]);
}

// Full SHA-256 over `msg`, driving the ORIGINAL SHA256::Transform block function.
static string sha256_hex(const string& msg) {
    vector<unsigned char> m(msg.begin(), msg.end());
    uint64_t bitlen = (uint64_t)msg.size() * 8;
    m.push_back(0x80);                       // 1-bit, then pad
    while (m.size() % 64 != 56) m.push_back(0);
    for (int i = 7; i >= 0; --i)             // 64-bit big-endian length
        m.push_back((unsigned char)((bitlen >> (i * 8)) & 0xff));

    word32 state[8];
    SHA256::InitState(state);
    for (size_t off = 0; off < m.size(); off += 64) {
        word32 data[16];                     // blk0(i) is (W[i]=data[i]) -> big-endian words
        for (int i = 0; i < 16; ++i) data[i] = be32(&m[off + i * 4]);
        SHA256::Transform(state, data);      // <-- Satoshi's sha.cpp, unmodified
    }
    char out[65];
    for (int i = 0; i < 8; ++i) sprintf(out + i * 8, "%08x", (unsigned)state[i]);
    return string(out, 64);
}

int main() {
    struct { const char* in; const char* want; } v[] = {
        { "",    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" },
        { "abc", "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad" },
        { "The quick brown fox jumps over the lazy dog",
                 "d7a8fbb307d7809469ca9abcb0082e4f8d5651e46d3cdb762d02d0bf37c9e592" },
    };
    int fail = 0;
    for (auto& t : v) {
        string got = sha256_hex(t.in);
        bool ok = (got == t.want);
        printf("%-4s  \"%s\"\n      %s\n", ok ? "PASS" : "FAIL", t.in, got.c_str());
        if (!ok) { printf("      want %s\n", t.want); ++fail; }
    }
    printf("\n%s\n", fail ? "SOME FAILED" : "ALL PASS -- original sha.cpp executes correctly");
    return fail;
}
