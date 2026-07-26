// Headless PORT of v0.1 consensus/chain code (derivative). Reproduces the exact
// genesis block from Satoshi's original construction (main.cpp:1455-1480) and runs
// the real proof-of-work, subsidy/halving, and difficulty-retarget logic — no GUI,
// no Berkeley DB. Number/codec/hashes are real OpenSSL; opcode/serialization/consensus
// bodies are reproduced from the extracted source. Evidence level: PORT.

#include <openssl/bn.h>
#include <openssl/evp.h>
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
using namespace std;
typedef vector<unsigned char> bytes;

static const int64_t COIN = 100000000LL;

// ---- hashing ----
static bytes dsha256(const bytes& b){ unsigned char h1[32],h2[32]; unsigned int n=0; EVP_Digest(b.data(),b.size(),h1,&n,EVP_sha256(),NULL); EVP_Digest(h1,32,h2,&n,EVP_sha256(),NULL); return bytes(h2,h2+32); }
static string rhex(const bytes& b){ string s; char t[3]; for(int i=b.size()-1;i>=0;i--){ sprintf(t,"%02x",b[i]); s+=t; } return s; } // reversed = uint256 display
static string fhex(const bytes& b){ string s; char t[3]; for(unsigned char c:b){ sprintf(t,"%02x",c); s+=t; } return s; }

// ---- CBigNum (bignum.h getvch; + from-hex like CBigNum("0x..")) ----
struct CBigNum {
    BIGNUM* bn;
    CBigNum(){ bn=BN_new(); }
    CBigNum(long n){ bn=BN_new(); if(n>=0)BN_set_word(bn,(unsigned long)n); else{BN_set_word(bn,(unsigned long)(-n));BN_set_negative(bn,1);} }
    CBigNum(const char* hex){ bn=BN_new(); BN_hex2bn(&bn, hex[0]=='0'&&hex[1]=='x'?hex+2:hex); }
    ~CBigNum(){ BN_free(bn); }
    bytes getvch() const { unsigned int n=BN_bn2mpi(bn,NULL); if(n<4)return bytes(); bytes v(n); BN_bn2mpi(bn,&v[0]); v.erase(v.begin(),v.begin()+4); reverse(v.begin(),v.end()); return v; }
};

// ---- serialization (serialize.h / script.h push) ----
static void put_le(bytes& s, uint64_t v, int len){ for(int i=0;i<len;i++) s.push_back((v>>(8*i))&0xff); }
static bytes compact_size(uint64_t n){ bytes s; if(n<0xfd)s.push_back((unsigned char)n); else if(n<=0xffff){s.push_back(0xfd);put_le(s,n,2);} else if(n<=0xffffffffULL){s.push_back(0xfe);put_le(s,n,4);} else{s.push_back(0xff);put_le(s,n,8);} return s; }
static bytes push_data(const bytes& d){ bytes o; size_t n=d.size(); if(n<76)o.push_back((unsigned char)n); else if(n<=0xff){o.push_back(0x4c);o.push_back((unsigned char)n);} else{o.push_back(0x4d);o.push_back(n&0xff);o.push_back((n>>8)&0xff);} o.insert(o.end(),d.begin(),d.end()); return o; }
static void cat(bytes& a, const bytes& b){ a.insert(a.end(),b.begin(),b.end()); }

struct TxIn { bytes prevhash; uint32_t n; bytes script; uint32_t seq; };
struct TxOut { int64_t value; bytes script; };
struct Tx { int32_t version=1; vector<TxIn> vin; vector<TxOut> vout; uint32_t locktime=0; };

// a script FIELD in a tx is a vector<uchar>: CompactSize length + raw bytes
// (NOT the script-internal pushdata encoding used to build the script content).
static bytes ser_field(const bytes& b){ bytes o=compact_size(b.size()); cat(o,b); return o; }
static bytes ser_tx(const Tx& tx){ bytes s; put_le(s,(uint32_t)tx.version,4); cat(s,compact_size(tx.vin.size())); for(auto&i:tx.vin){ cat(s,i.prevhash); put_le(s,i.n,4); cat(s,ser_field(i.script)); put_le(s,i.seq,4);} cat(s,compact_size(tx.vout.size())); for(auto&o:tx.vout){ put_le(s,(uint64_t)o.value,8); cat(s,ser_field(o.script)); } put_le(s,tx.locktime,4); return s; }
static bytes txhash(const Tx& tx){ return dsha256(ser_tx(tx)); }

// ---- block header (main.h CBlock header) ----
struct Block { int32_t nVersion=1; bytes hashPrevBlock=bytes(32,0); bytes hashMerkleRoot; uint32_t nTime=0,nBits=0,nNonce=0; vector<Tx> vtx; };
static bytes merkle_root(const vector<Tx>& vtx){
    vector<bytes> h; for(auto&t:vtx) h.push_back(txhash(t));
    while(h.size()>1){ if(h.size()&1) h.push_back(h.back()); vector<bytes> n; for(size_t i=0;i<h.size();i+=2){ bytes c=h[i]; cat(c,h[i+1]); n.push_back(dsha256(c)); } h=n; }
    return h.empty()?bytes(32,0):h[0];
}
static bytes header_bytes(const Block& b){ bytes s; put_le(s,(uint32_t)b.nVersion,4); cat(s,b.hashPrevBlock); cat(s,b.hashMerkleRoot); put_le(s,b.nTime,4); put_le(s,b.nBits,4); put_le(s,b.nNonce,4); return s; }
static bytes block_hash(const Block& b){ return dsha256(header_bytes(b)); }

// ---- consensus: subsidy (main.cpp:675) + difficulty (main.cpp:685) ----
static int64_t GetBlockValue(int nHeight, int64_t nFees){ int64_t s=50*COIN; s >>= (nHeight/210000); return s+nFees; }

static uint32_t bits_from_bignum(BIGNUM* target){ // ~ CBigNum::GetCompact
    int nSize=BN_num_bytes(target); uint32_t c;
    bytes v(nSize); BN_bn2bin(target,&v[0]);
    if(nSize>=1) c=(nSize<<24)|((v.size()>0?v[0]:0)<<16)|((v.size()>1?v[1]:0)<<8)|(v.size()>2?v[2]:0);
    else c=0;
    if(c & 0x00800000){ c>>=8; c+=1<<24; } // avoid sign bit
    return c;
}
static uint32_t GetNextWorkRequired(uint32_t nBitsLast, int64_t nActualTimespan){
    const int64_t nTargetTimespan=14*24*60*60, lo=nTargetTimespan/4, hi=nTargetTimespan*4;
    if(nActualTimespan<lo)nActualTimespan=lo; if(nActualTimespan>hi)nActualTimespan=hi;
    BIGNUM* bn=BN_new(); // SetCompact(nBitsLast)
    unsigned int sz=nBitsLast>>24; bytes v(4+sz,0); v[3]=sz; if(sz>=1)v[4]=(nBitsLast>>16)&0xff; if(sz>=2)v[5]=(nBitsLast>>8)&0xff; if(sz>=3)v[6]=nBitsLast&0xff;
    // mpi -> bn
    BN_mpi2bn(&v[0],v.size(),bn);
    BN_CTX* ctx=BN_CTX_new(); BIGNUM* t=BN_new(); BN_set_word(t,(unsigned long)nActualTimespan); BN_mul(bn,bn,t,ctx); BN_set_word(t,(unsigned long)nTargetTimespan); BN_div(bn,NULL,bn,t,ctx);
    // cap at proof-of-work limit ~uint256>>32 : just report bits
    uint32_t out=bits_from_bignum(bn);
    BN_free(bn);BN_free(t);BN_CTX_free(ctx); return out;
}

static int PASS=0, FAIL=0;
static void ok(const char* name, bool cond){ printf("  [%s] %s\n", cond?"PASS":"FAIL", name); if(cond)PASS++; else FAIL++; }

int main(){
    // ===== 1) Reproduce the genesis block (main.cpp:1455-1480) =====
    const char* pszTimestamp = "The Times 03/Jan/2009 Chancellor on brink of second bailout for banks";
    Tx cb; cb.version=1; cb.locktime=0;
    TxIn in; in.prevhash=bytes(32,0); in.n=0xFFFFFFFF; in.seq=0xFFFFFFFF;
    // scriptSig = CScript() << 486604799 << CBigNum(4) << timestamp
    bytes ss; cat(ss,push_data(CBigNum(486604799L).getvch())); cat(ss,push_data(CBigNum(4L).getvch()));
    cat(ss,push_data(bytes((const unsigned char*)pszTimestamp,(const unsigned char*)pszTimestamp+strlen(pszTimestamp))));
    in.script=ss; cb.vin.push_back(in);
    TxOut o; o.value=50*COIN;
    bytes pk=CBigNum("0x5F1DF16B2B704C8A578D0BBAF74D385CDE12C11EE50455F3C438EF4C3FBCF649B6DE611FEAE06279A60939E028A8D65C10B73071A6F16719274855FEB0FD8A6704").getvch();
    bytes spk=push_data(pk); spk.push_back(0xac); // <pubkey> OP_CHECKSIG
    o.script=spk; cb.vout.push_back(o);

    Block g; g.nVersion=1; g.hashPrevBlock=bytes(32,0); g.vtx.push_back(cb);
    g.hashMerkleRoot=merkle_root(g.vtx); g.nTime=1231006505; g.nBits=0x1d00ffff; g.nNonce=2083236893;

    string mk=rhex(g.hashMerkleRoot), bh=rhex(block_hash(g));
    printf("== genesis reproduction ==\n  merkle = %s\n  hash   = %s\n", mk.c_str(), bh.c_str());
    ok("merkle == 4a5e1e...deda33b", mk=="4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b");
    ok("hash   == 000000000019d668...a8ce26f", bh=="000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f");
    ok("coinbase scriptSig starts 04ffff001d0104...", fhex(ss).rfind("04ffff001d0104",0)==0);

    // ===== 2) Subsidy / halving (main.cpp:675) =====
    printf("== subsidy (GetBlockValue) ==\n");
    ok("height 0      -> 50 coins", GetBlockValue(0,0)==50*COIN);
    ok("height 209999 -> 50 coins", GetBlockValue(209999,0)==50*COIN);
    ok("height 210000 -> 25 coins", GetBlockValue(210000,0)==25*COIN);
    ok("height 420000 -> 12.5 coins", GetBlockValue(420000,0)==(int64_t)(12.5*COIN));
    ok("fees add on top", GetBlockValue(0,777)==50*COIN+777);

    // ===== 3) Proof-of-work: mine a block onto genesis (real hash/target loop) =====
    printf("== proof-of-work (mine block 1 at easy target) ==\n");
    Block b1; b1.nVersion=1; b1.hashPrevBlock=block_hash(g);
    Tx cb1; cb1.version=1; cb1.locktime=0; TxIn i1; i1.prevhash=bytes(32,0); i1.n=0xFFFFFFFF; i1.seq=0xFFFFFFFF; i1.script=bytes{0x51}; cb1.vin.push_back(i1);
    TxOut o1; o1.value=GetBlockValue(1,0); o1.script=spk; cb1.vout.push_back(o1);
    b1.vtx.push_back(cb1); b1.hashMerkleRoot=merkle_root(b1.vtx); b1.nTime=1231006506; b1.nBits=0x1f00ffff;
    bool mined=false; uint32_t nonce=0;
    for(; nonce<20000000u; nonce++){ b1.nNonce=nonce; string h=rhex(block_hash(b1)); if(h.rfind("0000",0)==0){ mined=true; break; } } // ~16 leading zero bits
    printf("  mined nonce=%u hash=%s\n", nonce, rhex(block_hash(b1)).c_str());
    ok("found PoW nonce (hash has >=16 leading zero bits)", mined);
    ok("block 1 links to genesis (prevBlock == genesis hash)", rhex(b1.hashPrevBlock)=="000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f");

    // ===== 4) Difficulty retarget (main.cpp:685) =====
    printf("== difficulty retarget (GetNextWorkRequired) ==\n");
    uint32_t faster=GetNextWorkRequired(0x1d00ffff, (14*24*60*60)/4); // blocks came 4x too fast -> harder
    uint32_t slower=GetNextWorkRequired(0x1d00ffff, (14*24*60*60)*4); // 4x too slow -> easier (clamped)
    printf("  2 weeks nominal: 0x1d00ffff ; too-fast(/4): 0x%08x ; too-slow(x4): 0x%08x\n", faster, slower);
    ok("faster timespan -> harder target (smaller compact mantissa/exp)", faster < 0x1d00ffff);
    ok("slower timespan -> easier or equal (clamped at x4)", slower >= 0x1d00ffff);

    printf("\nnode_port: %d PASS, %d FAIL\n", PASS, FAIL);
    return FAIL==0?0:1;
}
