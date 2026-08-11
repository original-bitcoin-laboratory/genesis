// SPDX-License-Identifier: MIT
// Reproduces logic from Bitcoin v0.1, Copyright (c) 2009 Satoshi Nakamoto, MIT.
// Their notice travels with their logic; the surrounding scaffolding is this laboratory's, 2026.
// Headless PORT of v0.1 UTXO block-connect (derivative). Builds a chain of blocks
// with real spends and validates it with faithful reproductions of CheckTransaction,
// ConnectInputs, and ConnectBlock (main.cpp:772-954, main.h:437-465) over an
// in-memory tx index (Berkeley-DB CTxDB is only persistence; the consensus logic is
// these functions). Real OpenSSL secp256k1 + double-SHA-256. Spends are pay-to-pubkey
// and the signature check is the real sighash + ECDSA. Evidence level: PORT.
//
// Demonstrates the ledger's core guarantees: valid spend of a matured coinbase, and
// rejection of double-spend, inflation, tampered signature, immature-coinbase spend,
// and coinbase over-claim.

#include <openssl/bn.h>
#include <openssl/ec.h>
#include <openssl/ecdsa.h>
#include <openssl/evp.h>
#include <openssl/obj_mac.h>
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <map>
#include <string>
#include <vector>
using namespace std;
typedef vector<unsigned char> bytes;

static const int64_t COIN = 100000000LL;
static const int COINBASE_MATURITY = 100;
static const int SIGHASH_ALL = 1, SIGHASH_ANYONECANPAY = 0x80, SIGHASH_NONE = 2, SIGHASH_SINGLE = 3;
static const unsigned char OP_CODESEPARATOR = 0xab, OP_CHECKSIG = 0xac;

static bytes dsha256(const bytes& b){ unsigned char h1[32],h2[32]; unsigned int n=0; EVP_Digest(b.data(),b.size(),h1,&n,EVP_sha256(),NULL); EVP_Digest(h1,32,h2,&n,EVP_sha256(),NULL); return bytes(h2,h2+32); }
static string rhex(const bytes& b){ string s; char t[3]; for(int i=(int)b.size()-1;i>=0;i--){ sprintf(t,"%02x",b[i]); s+=t;} return s; }

static void put_le(bytes& s, uint64_t v, int n){ for(int i=0;i<n;i++) s.push_back((v>>(8*i))&0xff); }
static void cat(bytes& a, const bytes& b){ a.insert(a.end(),b.begin(),b.end()); }
static bytes compact_size(uint64_t n){ bytes s; if(n<0xfd)s.push_back((unsigned char)n); else if(n<=0xffff){s.push_back(0xfd);put_le(s,n,2);} else{s.push_back(0xfe);put_le(s,n,4);} return s; }
static bytes push_data(const bytes& d){ bytes o; size_t n=d.size(); if(n<76)o.push_back((unsigned char)n); else{o.push_back(0x4c);o.push_back((unsigned char)n);} cat(o,d); return o; }
static bytes ser_field(const bytes& b){ bytes o=compact_size(b.size()); cat(o,b); return o; }

struct TxIn { bytes prevhash; uint32_t n; bytes script; uint32_t seq; };
struct TxOut { int64_t value; bytes script; };
struct Tx { int32_t version=1; vector<TxIn> vin; vector<TxOut> vout; uint32_t locktime=0; };

static bytes ser_tx(const Tx& t){ bytes s; put_le(s,(uint32_t)t.version,4); cat(s,compact_size(t.vin.size())); for(auto&i:t.vin){cat(s,i.prevhash);put_le(s,i.n,4);cat(s,ser_field(i.script));put_le(s,i.seq,4);} cat(s,compact_size(t.vout.size())); for(auto&o:t.vout){put_le(s,(uint64_t)o.value,8);cat(s,ser_field(o.script));} put_le(s,t.locktime,4); return s; }
static bytes txid(const Tx& t){ return dsha256(ser_tx(t)); }
static bool IsCoinBase(const Tx& t){ return t.vin.size()==1 && t.vin[0].prevhash==bytes(32,0) && t.vin[0].n==0xFFFFFFFF; }
static int64_t GetValueOut(const Tx& t){ int64_t v=0; for(auto&o:t.vout)v+=o.value; return v; }

struct CKey { EC_KEY* k; CKey(){k=EC_KEY_new_by_curve_name(NID_secp256k1);} void make(){EC_KEY_generate_key(k);} bytes pub()const{int n=i2o_ECPublicKey(k,NULL);bytes v(n);unsigned char*p=&v[0];i2o_ECPublicKey(k,&p);return v;} bytes sign(const bytes&h)const{bytes s(ECDSA_size(k));unsigned int n=0;ECDSA_sign(0,h.data(),h.size(),&s[0],&n,k);s.resize(n);return s;} };

static bytes fad_cs(const bytes& s){ bytes o; for(unsigned char b:s) if(b!=OP_CODESEPARATOR)o.push_back(b); return o; }
static bytes signature_hash(bytes sc, Tx t, unsigned nIn, int ht){
    if(nIn>=t.vin.size()){bytes e(32,0);e[0]=1;return e;}
    sc=fad_cs(sc); for(auto&i:t.vin)i.script.clear(); t.vin[nIn].script=sc;
    int m=ht&0x1f;
    if(m==SIGHASH_NONE){t.vout.clear();for(unsigned k=0;k<t.vin.size();k++)if(k!=nIn)t.vin[k].seq=0;}
    else if(m==SIGHASH_SINGLE){unsigned no=nIn;if(no>=t.vout.size()){bytes e(32,0);e[0]=1;return e;}t.vout.resize(no+1);for(unsigned k=0;k<no;k++){t.vout[k].value=-1;t.vout[k].script.clear();}for(unsigned k=0;k<t.vin.size();k++)if(k!=nIn)t.vin[k].seq=0;}
    if(ht&SIGHASH_ANYONECANPAY){TxIn keep=t.vin[nIn];t.vin.clear();t.vin.push_back(keep);}
    bytes ss=ser_tx(t); put_le(ss,(uint32_t)ht,4); return dsha256(ss);
}
static bool CheckSig(bytes sig, const bytes& pub, const bytes& scriptCode, const Tx& txTo, unsigned nIn){
    if(sig.empty())return false; int ht=sig.back(); sig.pop_back();
    bytes h=signature_hash(scriptCode,txTo,nIn,ht);
    EC_KEY* pk=EC_KEY_new_by_curve_name(NID_secp256k1); const unsigned char* p=&pub[0];
    if(!o2i_ECPublicKey(&pk,&p,pub.size())){EC_KEY_free(pk);return false;}
    bool ok=ECDSA_verify(0,h.data(),h.size(),sig.data(),sig.size(),pk)==1; EC_KEY_free(pk); return ok;
}
static bytes first_push(const bytes& s){ if(s.empty())return bytes(); size_t i=0; unsigned len; if(s[0]<76){len=s[0];i=1;} else if(s[0]==0x4c){len=s[1];i=2;} else return bytes(); if(i+len>s.size())return bytes(); return bytes(s.begin()+i,s.begin()+i+len); }
static bool VerifySignature(const Tx& txPrev, const Tx& txTo, unsigned nIn){   // pay-to-pubkey
    const bytes& scriptPubKey = txPrev.vout[txTo.vin[nIn].n].script;
    if(scriptPubKey.empty()||scriptPubKey.back()!=OP_CHECKSIG)return false;
    bytes sig=first_push(txTo.vin[nIn].script), pub=first_push(scriptPubKey);
    if(sig.empty()||pub.empty())return false;
    return CheckSig(sig,pub,scriptPubKey,txTo,nIn);
}

struct Block { int32_t nVersion=1; bytes hashPrevBlock=bytes(32,0); bytes hashMerkleRoot; uint32_t nTime=0,nBits=0,nNonce=0; vector<Tx> vtx; };
static bytes merkle_root(const vector<Tx>& v){ vector<bytes> h; for(auto&t:v)h.push_back(txid(t)); while(h.size()>1){ if(h.size()&1)h.push_back(h.back()); vector<bytes> n; for(size_t i=0;i<h.size();i+=2){bytes c=h[i];cat(c,h[i+1]);n.push_back(dsha256(c));} h=n;} return h.empty()?bytes(32,0):h[0]; }
static bytes header_bytes(const Block& b){ bytes s; put_le(s,(uint32_t)b.nVersion,4); cat(s,b.hashPrevBlock); cat(s,b.hashMerkleRoot); put_le(s,b.nTime,4); put_le(s,b.nBits,4); put_le(s,b.nNonce,4); return s; }
static bytes block_hash(const Block& b){ return dsha256(header_bytes(b)); }
static int64_t GetBlockValue(int nHeight,int64_t nFees){ int64_t s=50*COIN; s>>=(nHeight/210000); return s+nFees; }
static void target_be(uint32_t nBits, unsigned char out[32]){ unsigned sz=nBits>>24; bytes v(4+sz,0); v[3]=sz; if(sz>=1)v[4]=(nBits>>16)&0xff; if(sz>=2)v[5]=(nBits>>8)&0xff; if(sz>=3)v[6]=nBits&0xff; BIGNUM* bn=BN_new(); BN_mpi2bn(&v[0],v.size(),bn); BN_bn2binpad(bn,out,32); BN_free(bn); }
static bool pow_ok(const Block& b){ unsigned char tb[32]; target_be(b.nBits,tb); bytes h=block_hash(b); bytes hb(h.rbegin(),h.rend()); return memcmp(hb.data(),tb,32)<=0; }

struct TxIndex { Tx tx; vector<bool> vSpent; int height; };
struct Chain {
    map<string,TxIndex> idx; int tipHeight=-1; string lastError;
    bool err(const string& e){ lastError=e; return false; }
    bool CheckTransaction(const Tx& t){
        if(t.vin.empty()||t.vout.empty())return err("vin/vout empty");
        for(auto&o:t.vout) if(o.value<0) return err("negative value");
        if(IsCoinBase(t)){ size_t n=t.vin[0].script.size(); if(n<2||n>100)return err("coinbase script size"); }
        else for(auto&i:t.vin) if(i.prevhash==bytes(32,0)&&i.n==0xFFFFFFFF) return err("null prevout");
        return true;
    }
    bool ConnectInputs(const Tx& t, int heightOfThisBlock, int64_t& nFees, bool commit){
        if(!IsCoinBase(t)){
            int64_t nValueIn=0;
            for(size_t i=0;i<t.vin.size();i++){
                auto it=idx.find(rhex(t.vin[i].prevhash)); if(it==idx.end())return err("prev tx not found");
                TxIndex& ti=it->second; uint32_t on=t.vin[i].n;
                if(on>=ti.tx.vout.size()||on>=ti.vSpent.size())return err("prevout.n out of range");
                if(IsCoinBase(ti.tx) && (heightOfThisBlock - ti.height) < COINBASE_MATURITY-1)
                    return err("immature coinbase (depth "+to_string(heightOfThisBlock-ti.height)+")");
                if(!VerifySignature(ti.tx,t,i))return err("VerifySignature failed");
                if(ti.vSpent[on])return err("output already spent (double-spend)");
                if(commit) ti.vSpent[on]=true;
                nValueIn+=ti.tx.vout[on].value;
            }
            int64_t nTxFee=nValueIn-GetValueOut(t);
            if(nTxFee<0)return err("nTxFee < 0 (inflation)");
            nFees+=nTxFee;
        }
        return true;
    }
    bool ConnectBlock(const Block& b, int height, bool commit){
        int64_t nFees=0;
        for(auto&t:b.vtx) if(!ConnectInputs(t,height,nFees,commit)) return false;
        if(GetValueOut(b.vtx[0]) > GetBlockValue(height,nFees)) return err("coinbase over-claim");
        if(commit) for(auto&t:b.vtx){ TxIndex ti; ti.tx=t; ti.vSpent.assign(t.vout.size(),false); ti.height=height; idx[rhex(txid(t))]=ti; }
        return true;
    }
    bool CheckBlock(const Block& b){
        if(!pow_ok(b))return err("proof-of-work failed");
        if(b.hashMerkleRoot!=merkle_root(b.vtx))return err("merkle mismatch");
        for(auto&t:b.vtx) if(!CheckTransaction(t))return false;
        return true;
    }
    bool AddBlock(Block& b){ int h=tipHeight+1; if(!CheckBlock(b))return false; if(!ConnectBlock(b,h,true))return false; tipHeight=h; return true; }
    bool TestBlock(Block& b){ int h=tipHeight+1; if(!CheckBlock(b))return false; return ConnectBlock(b,h,false); }
};

static bytes p2pk(const bytes& pub){ bytes s=push_data(pub); s.push_back(OP_CHECKSIG); return s; }
static Tx coinbase_tx(int height,const bytes& pub,int64_t value){ Tx t; TxIn in; in.prevhash=bytes(32,0); in.n=0xFFFFFFFF; in.seq=0xFFFFFFFF; in.script={0x01,(unsigned char)(height&0xff),(unsigned char)((height>>8)&0xff)}; t.vin.push_back(in); TxOut o; o.value=value; o.script=p2pk(pub); t.vout.push_back(o); return t; }
static void mine(Block& b){ b.hashMerkleRoot=merkle_root(b.vtx); for(b.nNonce=0;;b.nNonce++) if(pow_ok(b))return; }

static int PASS=0,FAIL=0;
static void ok(const string& name,bool c,const string& why=""){ string tail=(!c&&!why.empty())?("  <- "+why):""; printf("  [%s] %s%s\n",c?"PASS":"FAIL",name.c_str(),tail.c_str()); if(c)PASS++;else FAIL++; }

static bytes g_pubK0;
static Tx make_spend(const bytes& prevtxid, uint32_t vout, int64_t outValue, const CKey& signer, const bytes& prevSPK, const bytes& payTo){
    Tx t; TxIn in; in.prevhash=prevtxid; in.n=vout; in.seq=0xFFFFFFFF; in.script={}; t.vin.push_back(in);
    TxOut o; o.value=outValue; o.script=p2pk(payTo); t.vout.push_back(o);
    bytes sig=signer.sign(signature_hash(prevSPK,t,0,SIGHASH_ALL)); sig.push_back(SIGHASH_ALL);
    t.vin[0].script=push_data(sig); return t;
}
static Block spend_block(const Block& prev, int height, const Tx& spend, int64_t coinbaseValue){
    Block b; b.nBits=0x207fffff; b.nTime=1231006505+height; b.hashPrevBlock=block_hash(prev);
    b.vtx.push_back(coinbase_tx(height,g_pubK0,coinbaseValue)); b.vtx.push_back(spend); mine(b); return b;
}

int main(){
    const uint32_t EASY=0x207fffff;
    Chain chain;
    CKey K0; K0.make(); g_pubK0=K0.pub(); bytes spk0=p2pk(g_pubK0);
    CKey K1; K1.make();

    vector<bytes> cbid; Block prev; bool first=true;
    for(int h=0;h<=120;h++){
        Block b; b.nBits=EASY; b.nTime=1231006505+h; b.hashPrevBlock=first?bytes(32,0):block_hash(prev);
        b.vtx.push_back(coinbase_tx(h,g_pubK0,GetBlockValue(h,0))); mine(b);
        if(!chain.AddBlock(b)){ printf("block %d failed: %s\n",h,chain.lastError.c_str()); return 1; }
        cbid.push_back(txid(b.vtx[0])); prev=b; first=false;
    }
    printf("== chain built ==\n");
    ok("121 blocks connected (genesis + 120), tip height 120", chain.tipHeight==120);

    { Tx t=make_spend(cbid[120],0,49*COIN,K0,spk0,K1.pub()); Block b=spend_block(prev,121,t,GetBlockValue(121,0));
      ok("immature coinbase spend rejected", !chain.TestBlock(b), chain.lastError); }

    printf("== valid spend of a matured coinbase (50 -> 49 + 1 fee) ==\n");
    { Tx t=make_spend(cbid[0],0,49*COIN,K0,spk0,K1.pub());
      Block b=spend_block(prev,121,t,GetBlockValue(121,1*COIN));
      bool r=chain.AddBlock(b); ok("valid spend block connects & commits", r, chain.lastError); prev=b; }

    printf("== consensus rejections (dry-run at height 122) ==\n");
    { Tx t=make_spend(cbid[0],0,49*COIN,K0,spk0,K1.pub()); Block b=spend_block(prev,122,t,GetBlockValue(122,0));
      ok("double-spend rejected", !chain.TestBlock(b), "accepted?!"); }
    { Tx t=make_spend(cbid[1],0,60*COIN,K0,spk0,K1.pub()); Block b=spend_block(prev,122,t,GetBlockValue(122,0));
      ok("inflation (out > in) rejected", !chain.TestBlock(b), "accepted?!"); }
    { Tx t=make_spend(cbid[2],0,49*COIN,K0,spk0,K1.pub()); t.vin[0].script[8]^=0x01; Block b=spend_block(prev,122,t,GetBlockValue(122,0));
      ok("tampered signature rejected", !chain.TestBlock(b), "accepted?!"); }
    { Tx t=make_spend(cbid[3],0,49*COIN,K0,spk0,K1.pub()); Block b=spend_block(prev,122,t,GetBlockValue(122,1*COIN));
      ok("control: a valid new spend passes the dry-run", chain.TestBlock(b), chain.lastError); }
    { Block b; b.nBits=EASY; b.nTime=1; b.hashPrevBlock=block_hash(prev); b.vtx.push_back(coinbase_tx(122,g_pubK0,GetBlockValue(122,0)+1)); mine(b);
      ok("coinbase over-claim rejected", !chain.TestBlock(b), "accepted?!"); }

    printf("\nchain_port: %d PASS, %d FAIL\n",PASS,FAIL);
    return FAIL==0?0:1;
}
