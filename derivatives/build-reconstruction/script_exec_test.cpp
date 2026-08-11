// SPDX-License-Identifier: MIT
// Reproduces logic from Bitcoin v0.1, Copyright (c) 2009 Satoshi Nakamoto, MIT.
// Their notice travels with their logic; the surrounding scaffolding is this laboratory's, 2026.
// Executes Satoshi's ORIGINAL script.cpp interpreter under the period toolchain.
//
// script.cpp is one of the "coupling" units: it #includes headers.h and references the
// tx types (main.h) and Hash()/Hash160() (util.h). With the donor scaffolding
// (compat/donor_tx.h + compat/donor_hashes.h) supplying just those surfaces -- no wxWidgets,
// no Berkeley DB -- the ORIGINAL script.cpp compiles and links, and this driver runs a real
// pay-to-pubkey verification through it end to end: EvalScript + SignatureHash + CheckSig,
// against a genuine secp256k1 signature from the original CKey.
//
// The signature is produced over exactly the digest the original SignatureHash computes, so
// the check is self-consistent through Satoshi's own code path. NOT money.

#include "headers.h"   // -> compat/headers_headless.h (build-dir shim)
#include <cstdio>

// keystore globals script.cpp expects (extern in donor_tx.h / main.h); defined once here.
map<vector<unsigned char>, CPrivKey> mapKeys;
map<uint160, vector<unsigned char> > mapPubKeys;

int main() {
    int fail = 0;

    // --- build a P2PK output: <pubkey> OP_CHECKSIG ---
    CKey key; key.MakeNewKey();
    vector<unsigned char> pub = key.GetPubKey();
    CScript scriptPubKey; scriptPubKey << pub << OP_CHECKSIG;

    CTransaction txFrom; txFrom.vout.resize(1);
    txFrom.vout[0].nValue = 5000000000LL;         // 50.00000000, cosmetic
    txFrom.vout[0].scriptPubKey = scriptPubKey;

    CTransaction txTo; txTo.vin.resize(1); txTo.vout.resize(1);
    txTo.vin[0].prevout = COutPoint(txFrom.GetHash(), 0);
    txTo.vout[0].nValue = 5000000000LL;

    // --- sign the digest the ORIGINAL SignatureHash computes, set scriptSig ---
    uint256 h = SignatureHash(scriptPubKey, txTo, 0, SIGHASH_ALL);
    vector<unsigned char> sig; key.Sign(h, sig); sig.push_back((unsigned char)SIGHASH_ALL);
    txTo.vin[0].scriptSig = CScript() << sig;

    // --- verify through the ORIGINAL interpreter (EvalScript -> OP_CHECKSIG -> CheckSig) ---
    bool ok = VerifySignature(txFrom, txTo, 0);
    printf("%-4s VerifySignature P2PK  (original EvalScript + SignatureHash + CheckSig)\n", ok ? "PASS" : "FAIL");
    fail += !ok;

    // --- tamper: change the spent-to amount -> SIGHASH_ALL digest differs -> reject ---
    CTransaction txBad = txTo; txBad.vout[0].nValue -= 1;
    bool bad = VerifySignature(txFrom, txBad, 0);
    printf("%-4s tampered output rejected\n", (!bad) ? "PASS" : "FAIL");
    fail += bad;

    // --- a second key must NOT verify the first key's signature ---
    CKey other; other.MakeNewKey();
    CScript spkOther; spkOther << other.GetPubKey() << OP_CHECKSIG;
    CTransaction txFrom2; txFrom2.vout.resize(1); txFrom2.vout[0].scriptPubKey = spkOther;
    CTransaction txTo2 = txTo; txTo2.vin[0].prevout = COutPoint(txFrom2.GetHash(), 0);
    bool wrongkey = VerifySignature(txFrom2, txTo2, 0);
    printf("%-4s wrong pubkey rejected\n", (!wrongkey) ? "PASS" : "FAIL");
    fail += wrongkey;

    printf("\n%s  (ORIGINAL script.cpp interpreter; i686 + OpenSSL 1.0.2, period toolchain)\n",
           fail ? "SOME FAILED" : "ALL PASS");
    return fail;
}
