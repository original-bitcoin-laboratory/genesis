#pragma once
// SPDX-License-Identifier: MIT
// Reproduces logic from Bitcoin v0.1, Copyright (c) 2009 Satoshi Nakamoto, MIT.
// Their notice travels with their logic; the surrounding scaffolding is this laboratory's, 2026.
// Donor scaffolding (NEW-EXP): the hash helpers script.cpp / base58.h expect from
// util.h -- double-SHA256 and SHA256+RIPEMD160 -- so the ORIGINAL interpreter compiles
// headless without pulling in util.h's wxWidgets/Win32 half. Same algorithm and same
// OpenSSL calls as v0.1 util.h; requires uint256.h + OpenSSL + serialize.h in scope.
// This is build scaffolding, not a reimplementation of consensus logic. NOT money.

template <typename T1>
inline uint256 Hash(const T1 pbegin, const T1 pend) {
    uint256 hash1, hash2;
    SHA256((unsigned char*)&pbegin[0], (pend - pbegin) * sizeof(pbegin[0]), (unsigned char*)&hash1);
    SHA256((unsigned char*)&hash1, sizeof(hash1), (unsigned char*)&hash2);
    return hash2;
}

template <typename T1, typename T2>
inline uint256 Hash(const T1 p1begin, const T1 p1end, const T2 p2begin, const T2 p2end) {
    uint256 hash1, hash2;
    SHA256_CTX ctx;
    SHA256_Init(&ctx);
    SHA256_Update(&ctx, (unsigned char*)&p1begin[0], (p1end - p1begin) * sizeof(p1begin[0]));
    SHA256_Update(&ctx, (unsigned char*)&p2begin[0], (p2end - p2begin) * sizeof(p2begin[0]));
    SHA256_Final((unsigned char*)&hash1, &ctx);
    SHA256((unsigned char*)&hash1, sizeof(hash1), (unsigned char*)&hash2);
    return hash2;
}

inline uint160 Hash160(const vector<unsigned char>& vch) {
    uint256 hash1;
    uint160 hash2;
    SHA256(&vch[0], vch.size(), (unsigned char*)&hash1);
    RIPEMD160((unsigned char*)&hash1, sizeof(hash1), (unsigned char*)&hash2);
    return hash2;
}

template <typename T>
uint256 SerializeHash(const T& obj, int nType = SER_GETHASH, int nVersion = VERSION) {
    CDataStream ss(nType, nVersion);
    ss.reserve(10000);
    ss << obj;
    return Hash(ss.begin(), ss.end());
}
