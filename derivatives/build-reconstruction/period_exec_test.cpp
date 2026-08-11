// SPDX-License-Identifier: MIT
// Reproduces logic from Bitcoin v0.1, Copyright (c) 2009 Satoshi Nakamoto, MIT.
// Their notice travels with their logic; the surrounding scaffolding is this laboratory's, 2026.
// Executes Satoshi's ORIGINAL bignum.h + key.h under a PERIOD toolchain
// (i686 target + OpenSSL 1.0.2, where BIGNUM is still a public struct).
//
// These are the two units the modern-host probe (build.sh) proved BLOCKED:
// serialize.h:462 needs a 32-bit target, and bignum.h:49 (class CBigNum :
// public BIGNUM) needs OpenSSL <= 1.0.2. Cross-compiled i686 + real OpenSSL
// 1.0.2 lifts both, and this driver shows the original code not only compiles
// but RUNS byte-correct: CBigNum arithmetic, the Script sign-magnitude codec,
// and secp256k1 ECDSA sign/verify. Built and run by period_build_wsl.sh.
//
// The driver adds nothing to the algorithms -- it only calls the original
// classes and checks known results. NOT money.

#include "compat/prelude.h"     // headless stand-in for headers.h (std + OpenSSL)
#include "serialize.h"          // ORIGINAL (VERSION, secure_allocator, int64)
#include "uint256.h"            // ORIGINAL
#include "bignum.h"             // ORIGINAL  (class CBigNum : public BIGNUM)
#include "key.h"                // ORIGINAL  (CKey: secp256k1 via EC_KEY)
#include <cstdio>

static string hx(const vector<unsigned char>& v) {
    string s; char b[3];
    for (size_t i = 0; i < v.size(); ++i) { sprintf(b, "%02x", v[i]); s += b; }
    return s;
}

int main() {
    int fail = 0;

    // --- CBigNum (bignum.h): arithmetic + the Script sign-magnitude vch codec ---
    CBigNum a(1000000), b(1000);
    CBigNum c = a * b;
    bool bn = (c.getulong() == 1000000000UL);
    bool vch = (hx(CBigNum(0).getvch())   == ""
             && hx(CBigNum(1).getvch())   == "01"
             && hx(CBigNum(-1).getvch())  == "81"
             && hx(CBigNum(127).getvch()) == "7f"
             && hx(CBigNum(128).getvch()) == "8000");
    printf("%-4s CBigNum  1000000*1000=%lu\n", bn ? "PASS" : "FAIL", c.getulong());
    printf("%-4s CBigNum  sign-mag vch {0,1,-1,127,128}\n", vch ? "PASS" : "FAIL");
    fail += (!bn) + (!vch);

    // --- CKey (key.h): secp256k1 ECDSA generate / sign / verify ---
    CKey k; k.MakeNewKey();
    vector<unsigned char> pub = k.GetPubKey();
    bool pk = (pub.size() == 65 && pub[0] == 0x04);   // uncompressed point
    uint256 h1((uint64)0x0123456789abcdefULL), h2((uint64)0xfedcba9876543210ULL);
    vector<unsigned char> sig;
    bool sg  = k.Sign(h1, sig) && !sig.empty();
    bool vok = k.Verify(h1, sig);                      // correct hash -> true
    bool vbad = k.Verify(h2, sig);                     // different hash -> false
    bool vpub = CKey::Verify(pub, h1, sig);            // static verify via pubkey
    printf("%-4s CKey     pubkey 65-byte uncompressed 0x04 (got %u)\n", pk ? "PASS" : "FAIL", (unsigned)pub.size());
    printf("%-4s CKey     secp256k1 sign (%u-byte DER)\n", sg ? "PASS" : "FAIL", (unsigned)sig.size());
    printf("%-4s CKey     verify(correct)=T verify(wrong)=F\n", (vok && !vbad) ? "PASS" : "FAIL");
    printf("%-4s CKey     static Verify(pubkey) round-trip\n", vpub ? "PASS" : "FAIL");
    fail += (!pk) + (!sg) + (!(vok && !vbad)) + (!vpub);

    printf("\n%s  (original bignum.h + key.h; i686 + OpenSSL 1.0.2, period toolchain)\n",
           fail ? "SOME FAILED" : "ALL PASS");
    return fail;
}
