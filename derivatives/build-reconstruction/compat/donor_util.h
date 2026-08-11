#pragma once
// SPDX-License-Identifier: MIT
// Reproduces logic from Bitcoin v0.1, Copyright (c) 2009 Satoshi Nakamoto, MIT.
// Their notice travels with their logic; the surrounding scaffolding is this laboratory's, 2026.
// Donor scaffolding (NEW-EXP): the small PORTABLE utilities from util.h that the original
// serialize.h / base58.h / script.h use (a few macros + REF + the hex/format helpers) --
// reimplemented without util.h's wxWidgets/Win32/threading half, so the original interpreter
// compiles headless. Same names and semantics as v0.1 util.h. NOT money.

#include <cstdarg>
#include <cstdio>
#include <string>
#include <vector>

#define foreach(decl, coll)  for (decl : (coll))    // v0.1: #define foreach BOOST_FOREACH
#define loop                 for (;;)
#define UBEGIN(a)            ((unsigned char*)&(a))
#define UEND(a)              ((unsigned char*)&((&(a))[1]))
#define PAIRTYPE(t1, t2)     std::pair<t1, t2>
// v0.1 CRITICAL_BLOCK(cs) takes a scoped lock; this donor is single-threaded, so it drops the
// lock and just runs the guarded block. (The wallet-side Solver/SignSignature paths that use it
// are not exercised by the consensus verify path this build targets.)
#define CRITICAL_BLOCK(cs)

template <typename T> inline T& REF(const T& val) { return const_cast<T&>(val); }

inline std::string strprintf(const char* format, ...) {
    char buf[4096];
    va_list a; va_start(a, format);
    int n = vsnprintf(buf, sizeof(buf), format, a);
    va_end(a);
    if (n < 0) return std::string();
    if ((size_t)n < sizeof(buf)) return std::string(buf, (size_t)n);
    std::string s((size_t)n, '\0');
    va_start(a, format);
    vsnprintf(&s[0], (size_t)n + 1, format, a);
    va_end(a);
    return s;
}

template <typename T>
inline std::string HexStr(const T itbegin, const T itend, bool fSpaces = true) {
    std::string str;
    for (T p = itbegin; p != itend; ++p)
        str += strprintf((fSpaces && p != itend - 1 ? "%02x " : "%02x"), (unsigned char)*p);
    return str;
}

inline std::string HexStr(const std::vector<unsigned char>& v, bool fSpaces = true) {
    return HexStr(v.begin(), v.end(), fSpaces);
}

template <typename T>
inline std::string HexNumStr(const T itbegin, const T itend, bool f0x = true) {
    std::string str = f0x ? "0x" : "";
    for (T p = itbegin; p != itend; ++p) str += strprintf("%02x", (unsigned char)*p);
    return str;
}
