#pragma once
// SPDX-License-Identifier: MIT
// Reproduces logic from Bitcoin v0.1, Copyright (c) 2009 Satoshi Nakamoto, MIT.
// Their notice travels with their logic; the surrounding scaffolding is this laboratory's, 2026.
// Donor scaffolding (J-DONOR / NEW-EXP): a faithful minimal transaction surface so the
// ORIGINAL script.cpp compiles headless. The data members and IMPLEMENT_SERIALIZE mirror
// main.h EXACTLY (COutPoint/CTxIn/CTxOut/CTransaction), so the serialization -- and hence
// SignatureHash -- is byte-faithful; only main.h's db/net/wallet METHODS (ReadFromDisk,
// ConnectInputs, IsMine, ...) are omitted, since those are what drag in Berkeley DB and
// wxWidgets. Requires script.h (CScript) + key.h (CPrivKey) in scope. NOT money.

class COutPoint {
public:
    uint256 hash;
    unsigned int n;
    COutPoint() { SetNull(); }
    COutPoint(uint256 hashIn, unsigned int nIn) { hash = hashIn; n = nIn; }
    IMPLEMENT_SERIALIZE( READWRITE(FLATDATA(*this)); )
    void SetNull() { hash = 0; n = (unsigned int)-1; }
    bool IsNull() const { return (hash == 0 && n == (unsigned int)-1); }
    friend bool operator<(const COutPoint& a, const COutPoint& b) { return (a.hash < b.hash || (a.hash == b.hash && a.n < b.n)); }
    friend bool operator==(const COutPoint& a, const COutPoint& b) { return (a.hash == b.hash && a.n == b.n); }
    friend bool operator!=(const COutPoint& a, const COutPoint& b) { return !(a == b); }
};

class CTxIn {
public:
    COutPoint prevout;
    CScript scriptSig;
    unsigned int nSequence;
    CTxIn() { nSequence = UINT_MAX; }
    explicit CTxIn(COutPoint prevoutIn, CScript scriptSigIn = CScript(), unsigned int nSequenceIn = UINT_MAX) { prevout = prevoutIn; scriptSig = scriptSigIn; nSequence = nSequenceIn; }
    CTxIn(uint256 hashPrevTx, unsigned int nOut, CScript scriptSigIn = CScript(), unsigned int nSequenceIn = UINT_MAX) { prevout = COutPoint(hashPrevTx, nOut); scriptSig = scriptSigIn; nSequence = nSequenceIn; }
    IMPLEMENT_SERIALIZE( READWRITE(prevout); READWRITE(scriptSig); READWRITE(nSequence); )
    bool IsFinal() const { return (nSequence == UINT_MAX); }
    friend bool operator==(const CTxIn& a, const CTxIn& b) { return (a.prevout == b.prevout && a.scriptSig == b.scriptSig && a.nSequence == b.nSequence); }
    friend bool operator!=(const CTxIn& a, const CTxIn& b) { return !(a == b); }
};

class CTxOut {
public:
    int64 nValue;
    CScript scriptPubKey;
    CTxOut() { SetNull(); }
    CTxOut(int64 nValueIn, CScript scriptPubKeyIn) { nValue = nValueIn; scriptPubKey = scriptPubKeyIn; }
    IMPLEMENT_SERIALIZE( READWRITE(nValue); READWRITE(scriptPubKey); )
    void SetNull() { nValue = -1; scriptPubKey.clear(); }
    bool IsNull() const { return (nValue == -1); }
    uint256 GetHash() const { return SerializeHash(*this); }
    friend bool operator==(const CTxOut& a, const CTxOut& b) { return (a.nValue == b.nValue && a.scriptPubKey == b.scriptPubKey); }
    friend bool operator!=(const CTxOut& a, const CTxOut& b) { return !(a == b); }
};

class CTransaction {
public:
    int nVersion;
    vector<CTxIn> vin;
    vector<CTxOut> vout;
    int nLockTime;
    CTransaction() { SetNull(); }
    IMPLEMENT_SERIALIZE
    (
        READWRITE(this->nVersion);
        nVersion = this->nVersion;
        READWRITE(vin);
        READWRITE(vout);
        READWRITE(nLockTime);
    )
    void SetNull() { nVersion = 1; vin.clear(); vout.clear(); nLockTime = 0; }
    bool IsNull() const { return (vin.empty() && vout.empty()); }
    uint256 GetHash() const { return SerializeHash(*this); }
};

// keystore globals script.cpp's Solver / IsMine / ExtractPubKey / SignSignature consult
// (extern in main.h). Defined once by the test driver.
extern map<vector<unsigned char>, CPrivKey> mapKeys;
extern map<uint160, vector<unsigned char> > mapPubKeys;
