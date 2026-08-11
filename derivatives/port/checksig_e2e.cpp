// SPDX-License-Identifier: MIT
// Reproduces logic from Bitcoin v0.1, Copyright (c) 2009 Satoshi Nakamoto, MIT.
// Their notice travels with their logic; the surrounding scaffolding is this laboratory's, 2026.
// C++ PORT end-to-end for OP_CHECKSIG / OP_CHECKMULTISIG on real secp256k1.
// Evidence level: PORT. Uses the same OpenSSL EC API as v0.1 key.h (EC_KEY on
// NID_secp256k1, ECDSA_sign/verify, i2o_ECPublicKey) + the SignatureHash from
// sighash.cpp. Generates keys, signs the demo transaction, and runs single-sig
// CHECKSIG and a 2-of-3 escrow CHECKMULTISIG (faithful to script.cpp:692/727,
// incl. the off-by-one dummy). Prints PASS/FAIL and writes scenario.txt for the
// Python interpreter to independently verify (cross-language check).
//
// Build: g++ -std=c++17 -O2 -Wno-deprecated-declarations checksig_e2e.cpp -o checksig_e2e.exe -lcrypto

#include <openssl/ec.h>
#include <openssl/ecdsa.h>
#include <openssl/evp.h>
#include <openssl/obj_mac.h>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>
using namespace std;
typedef vector<unsigned char> bytes;

static const int SIGHASH_ALL=1, SIGHASH_NONE=2, SIGHASH_SINGLE=3, SIGHASH_ANYONECANPAY=0x80;
static const unsigned char OP_CODESEPARATOR=0xab;

// ---- tx + SignatureHash (same as sighash.cpp) --------------------------------
static bytes dsha256(const bytes& b){ unsigned char h1[32],h2[32]; unsigned int n=0; EVP_Digest(b.data(),b.size(),h1,&n,EVP_sha256(),NULL); EVP_Digest(h1,32,h2,&n,EVP_sha256(),NULL); return bytes(h2,h2+32); }
static void put_le(bytes& s, uint64_t v, int len){ for(int i=0;i<len;i++) s.push_back((v>>(8*i))&0xff); }
static bytes compact_size(uint64_t n){ bytes s; if(n<0xfd) s.push_back((unsigned char)n); else if(n<=0xffff){s.push_back(0xfd);put_le(s,n,2);} else if(n<=0xffffffffULL){s.push_back(0xfe);put_le(s,n,4);} else {s.push_back(0xff);put_le(s,n,8);} return s; }
static void put_push(bytes& s, const bytes& b){ bytes c=compact_size(b.size()); s.insert(s.end(),c.begin(),c.end()); s.insert(s.end(),b.begin(),b.end()); }
struct TxIn{ bytes prevhash; uint32_t n; bytes script; uint32_t seq; };
struct TxOut{ int64_t value; bytes script; void set_null(){ value=-1; script.clear(); } };
struct Tx{ int32_t version; vector<TxIn> vin; vector<TxOut> vout; uint32_t locktime; };
static bytes serialize(const Tx& tx){ bytes s; put_le(s,(uint32_t)tx.version,4); bytes c=compact_size(tx.vin.size()); s.insert(s.end(),c.begin(),c.end()); for(const auto& i:tx.vin){ s.insert(s.end(),i.prevhash.begin(),i.prevhash.end()); put_le(s,i.n,4); put_push(s,i.script); put_le(s,i.seq,4);} c=compact_size(tx.vout.size()); s.insert(s.end(),c.begin(),c.end()); for(const auto& o:tx.vout){ put_le(s,(uint64_t)o.value,8); put_push(s,o.script);} put_le(s,tx.locktime,4); return s; }
static bytes fad_cs(const bytes& s){ bytes o; for(unsigned char b:s) if(b!=OP_CODESEPARATOR) o.push_back(b); return o; }
static bytes signature_hash(bytes sc, Tx tx, unsigned nIn, int ht){
    if(nIn>=tx.vin.size()){ bytes e(32,0); e[0]=1; return e; }
    sc=fad_cs(sc); for(auto& i:tx.vin) i.script.clear(); tx.vin[nIn].script=sc;
    int t=ht&0x1f;
    if(t==SIGHASH_NONE){ tx.vout.clear(); for(unsigned k=0;k<tx.vin.size();k++) if(k!=nIn) tx.vin[k].seq=0; }
    else if(t==SIGHASH_SINGLE){ unsigned nOut=nIn; if(nOut>=tx.vout.size()){ bytes e(32,0); e[0]=1; return e; } tx.vout.resize(nOut+1); for(unsigned k=0;k<nOut;k++) tx.vout[k].set_null(); for(unsigned k=0;k<tx.vin.size();k++) if(k!=nIn) tx.vin[k].seq=0; }
    if(ht & SIGHASH_ANYONECANPAY){ TxIn keep=tx.vin[nIn]; tx.vin.clear(); tx.vin.push_back(keep); }
    bytes ss=serialize(tx); put_le(ss,(uint32_t)ht,4); return dsha256(ss);
}
static bytes hexb(const string& h){ bytes b; for(size_t i=0;i+1<h.size();i+=2) b.push_back((unsigned char)strtol(h.substr(i,2).c_str(),0,16)); return b; }
static string tohex(const bytes& b){ string s; char t[3]; for(unsigned char c:b){ sprintf(t,"%02x",c); s+=t; } return s; }
// CScript data push (script.h operator<<): [len]|[OP_PUSHDATA1 len]|[OP_PUSHDATA2 len:2]
static bytes push_data(const bytes& d){ bytes o; size_t n=d.size(); if(n<76) o.push_back((unsigned char)n); else if(n<=0xff){ o.push_back(0x4c); o.push_back((unsigned char)n);} else { o.push_back(0x4d); o.push_back(n&0xff); o.push_back((n>>8)&0xff);} o.insert(o.end(),d.begin(),d.end()); return o; }
static void demo_tx(Tx& tx, bytes& spk0){
    tx.version=1; tx.locktime=0;
    tx.vin.push_back({bytes(32,0x11),0,bytes{0xde,0xad},0xffffffff});
    tx.vin.push_back({bytes(32,0x22),7,bytes{0xbe,0xef},0xffffffff});
    spk0=hexb(string("76a914")+string(40,'3')+string("88ac"));
    tx.vout.push_back({5000000000LL,spk0});
    tx.vout.push_back({1000000000LL,bytes{0x51}});
}

// ---- CKey (as in key.h: EC_KEY / secp256k1 / DER sig / SEC pubkey) -----------
struct CKey {
    EC_KEY* k;
    CKey(){ k=EC_KEY_new_by_curve_name(NID_secp256k1); }
    ~CKey(){ EC_KEY_free(k); }
    void make(){ EC_KEY_generate_key(k); }
    bytes pubkey() const { int n=i2o_ECPublicKey(k,NULL); bytes v(n); unsigned char* p=&v[0]; i2o_ECPublicKey(k,&p); return v; }
    bytes sign(const bytes& hash) const { bytes s(ECDSA_size(k)); unsigned int n=0; ECDSA_sign(0,hash.data(),hash.size(),&s[0],&n,k); s.resize(n); return s; }
};
// CheckSig faithful to script.cpp:881
static bool CheckSig(bytes sig, const bytes& pubkey, const bytes& scriptCode, const Tx& tx, unsigned nIn){
    EC_KEY* pk=EC_KEY_new_by_curve_name(NID_secp256k1);
    const unsigned char* p=&pubkey[0];
    if(!o2i_ECPublicKey(&pk,&p,pubkey.size())){ EC_KEY_free(pk); return false; }
    if(sig.empty()){ EC_KEY_free(pk); return false; }
    int ht=sig.back(); sig.pop_back();
    bytes h=signature_hash(scriptCode,tx,nIn,ht);
    bool ok = ECDSA_verify(0,h.data(),h.size(),sig.data(),sig.size(),pk)==1;
    EC_KEY_free(pk); return ok;
}
// CHECKMULTISIG m-of-n (faithful order + short-circuit) over already-collected sigs/keys
static bool CheckMultisig(const vector<bytes>& sigs, const vector<bytes>& keys, const bytes& sc, const Tx& tx, unsigned nIn){
    int nSigs=sigs.size(), nKeys=keys.size(); int isig=0, ikey=0; bool ok=true;
    while(ok && nSigs>0){
        if(CheckSig(sigs[isig], keys[ikey], sc, tx, nIn)){ isig++; nSigs--; }
        ikey++; nKeys--;
        if(nSigs>nKeys) ok=false;
    }
    return ok;
}

static int PASS=0, FAIL=0;
static void check(const char* name, bool got, bool want){ bool ok=(got==want); printf("  [%s] %s (got=%d want=%d)\n", ok?"PASS":"FAIL", name, got, want); if(ok)PASS++; else FAIL++; }

int main(){
    Tx tx; bytes spk0; demo_tx(tx,spk0);
    unsigned nIn=0;
    ofstream scen("scenario.txt");

    printf("== single-sig OP_CHECKSIG ==\n");
    CKey key; key.make();
    bytes pub=key.pubkey();
    bytes p2pk=push_data(pub); p2pk.push_back(0xac);   // scriptPubKey: <pubkey> OP_CHECKSIG
    bytes h=signature_hash(p2pk,tx,nIn,SIGHASH_ALL);
    bytes sig=key.sign(h); sig.push_back(SIGHASH_ALL);
    check("valid sig", CheckSig(sig,pub,p2pk,tx,nIn), true);
    bytes bad=sig; bad[10]^=1;
    check("tampered sig", CheckSig(bad,pub,p2pk,tx,nIn), false);
    CKey other; other.make();
    check("wrong pubkey", CheckSig(sig,other.pubkey(),p2pk,tx,nIn), false);
    scen << "CHECKSIG " << tohex(pub) << " " << tohex(sig) << " 1\n";
    scen << "CHECKSIG " << tohex(other.pubkey()) << " " << tohex(sig) << " 0\n";

    printf("== 2-of-3 escrow OP_CHECKMULTISIG ==\n");
    CKey A,B,C; A.make(); B.make(); C.make();
    vector<bytes> keys={A.pubkey(),B.pubkey(),C.pubkey()};
    // scriptPubKey: OP_2 <pkA> <pkB> <pkC> OP_3 OP_CHECKMULTISIG
    bytes msPub; msPub.push_back(0x52); for(auto&k:keys){ bytes p=push_data(k); msPub.insert(msPub.end(),p.begin(),p.end()); } msPub.push_back(0x53); msPub.push_back(0xae);
    auto mk=[&](CKey& kk){ bytes s=kk.sign(signature_hash(msPub,tx,nIn,SIGHASH_ALL)); s.push_back(SIGHASH_ALL); return s; };
    bytes sA=mk(A), sB=mk(B), sC=mk(C);
    // buyer+arbiter etc.: any 2 of {A,B,C}, sigs in ascending key order
    check("A,C -> ok", CheckMultisig({sA,sC},keys,msPub,tx,nIn), true);
    check("A,B -> ok", CheckMultisig({sA,sB},keys,msPub,tx,nIn), true);
    check("B,C -> ok", CheckMultisig({sB,sC},keys,msPub,tx,nIn), true);
    CKey X; X.make(); bytes sX=mk(X);
    check("A,X -> fail (X not in set)", CheckMultisig({sA,sX},keys,msPub,tx,nIn), false);
    check("C,A wrong order -> fail", CheckMultisig({sC,sA},keys,msPub,tx,nIn), false);
    // scenario for python: <m> <n> pk1..pkn sig1..sigm expected
    scen << "CHECKMULTISIG 2 3 " << tohex(keys[0]) << " " << tohex(keys[1]) << " " << tohex(keys[2])
         << " " << tohex(sA) << " " << tohex(sC) << " 1\n";
    scen << "CHECKMULTISIG 2 3 " << tohex(keys[0]) << " " << tohex(keys[1]) << " " << tohex(keys[2])
         << " " << tohex(sA) << " " << tohex(sX) << " 0\n";
    scen.close();

    printf("C++ e2e: %d PASS, %d FAIL\n", PASS, FAIL);
    return FAIL==0 ? 0 : 1;
}
