// C++ PORT of v0.1.0 CTransaction serialization + SignatureHash (script.cpp:818).
// Evidence level: PORT. Builds the SAME fixed transaction as the Python MODEL
// (model/tx_sighash.py demo_tx) and prints the 32-byte signature hashes for each
// nIn x SIGHASH type, for byte-for-byte differential comparison. Hashing is real
// OpenSSL (double SHA-256).

#include <openssl/evp.h>
#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>
using namespace std;
typedef vector<unsigned char> bytes;

static const int SIGHASH_ALL=1, SIGHASH_NONE=2, SIGHASH_SINGLE=3, SIGHASH_ANYONECANPAY=0x80;
static const unsigned char OP_CODESEPARATOR=0xab;

static bytes dsha256(const bytes& b){
    unsigned char h1[32], h2[32]; unsigned int n=0;
    EVP_Digest(b.data(), b.size(), h1, &n, EVP_sha256(), NULL);
    EVP_Digest(h1, 32, h2, &n, EVP_sha256(), NULL);
    return bytes(h2, h2+32);
}
static void put_le(bytes& s, uint64_t v, int len){ for(int i=0;i<len;i++) s.push_back((v>>(8*i))&0xff); }
static bytes compact_size(uint64_t n){ bytes s; if(n<0xfd) s.push_back((unsigned char)n); else if(n<=0xffff){ s.push_back(0xfd); put_le(s,n,2);} else if(n<=0xffffffffULL){ s.push_back(0xfe); put_le(s,n,4);} else { s.push_back(0xff); put_le(s,n,8);} return s; }
static void put_push(bytes& s, const bytes& b){ bytes cs=compact_size(b.size()); s.insert(s.end(),cs.begin(),cs.end()); s.insert(s.end(),b.begin(),b.end()); }

struct TxIn { bytes prevhash; uint32_t n; bytes script; uint32_t seq; };
struct TxOut { int64_t value; bytes script; void set_null(){ value=-1; script.clear(); } };
struct Tx { int32_t version; vector<TxIn> vin; vector<TxOut> vout; uint32_t locktime; };

static bytes serialize(const Tx& tx){
    bytes s; put_le(s,(uint32_t)tx.version,4);
    bytes c=compact_size(tx.vin.size()); s.insert(s.end(),c.begin(),c.end());
    for(const auto& i: tx.vin){ s.insert(s.end(),i.prevhash.begin(),i.prevhash.end()); put_le(s,i.n,4); put_push(s,i.script); put_le(s,i.seq,4); }
    c=compact_size(tx.vout.size()); s.insert(s.end(),c.begin(),c.end());
    for(const auto& o: tx.vout){ put_le(s,(uint64_t)o.value,8); put_push(s,o.script); }
    put_le(s,tx.locktime,4);
    return s;
}
static bytes find_and_delete_cs(const bytes& script){ bytes o; for(unsigned char b: script) if(b!=OP_CODESEPARATOR) o.push_back(b); return o; }

static bytes signature_hash(bytes scriptCode, Tx tx, unsigned int nIn, int hashType){
    if(nIn>=tx.vin.size()){ bytes e(32,0); e[0]=1; return e; }
    scriptCode=find_and_delete_cs(scriptCode);
    for(auto& i: tx.vin) i.script.clear();
    tx.vin[nIn].script=scriptCode;
    int ht=hashType&0x1f;
    if(ht==SIGHASH_NONE){ tx.vout.clear(); for(unsigned k=0;k<tx.vin.size();k++) if(k!=nIn) tx.vin[k].seq=0; }
    else if(ht==SIGHASH_SINGLE){ unsigned nOut=nIn; if(nOut>=tx.vout.size()){ bytes e(32,0); e[0]=1; return e; } tx.vout.resize(nOut+1); for(unsigned k=0;k<nOut;k++) tx.vout[k].set_null(); for(unsigned k=0;k<tx.vin.size();k++) if(k!=nIn) tx.vin[k].seq=0; }
    if(hashType & SIGHASH_ANYONECANPAY){ TxIn keep=tx.vin[nIn]; tx.vin.clear(); tx.vin.push_back(keep); }
    bytes ss=serialize(tx); put_le(ss,(uint32_t)hashType,4);
    return dsha256(ss);
}

static bytes hexb(const string& h){ bytes b; for(size_t i=0;i+1<h.size();i+=2) b.push_back((unsigned char)strtol(h.substr(i,2).c_str(),0,16)); return b; }

int main(){
    Tx tx; tx.version=1; tx.locktime=0;
    tx.vin.push_back({bytes(32,0x11),0,bytes{0xde,0xad},0xffffffff});
    tx.vin.push_back({bytes(32,0x22),7,bytes{0xbe,0xef},0xffffffff});
    bytes spk0=hexb(string("76a914")+string(40,'3')+string("88ac"));  // "33"*20 -> 40 '3' chars
    bytes spk1{0x51};
    tx.vout.push_back({5000000000LL, spk0});
    tx.vout.push_back({1000000000LL, spk1});
    struct { const char* label; int ht; } types[] = {{"0x01",0x01},{"0x02",0x02},{"0x03",0x03},{"0x81",0x81},{"0x82",0x82},{"0x83",0x83}};
    for(unsigned nIn=0; nIn<2; nIn++){
        for(auto& ty: types){
            bytes h=signature_hash(spk0, tx, nIn, ty.ht);
            printf("SH nIn=%u type=%s => ", nIn, ty.label);
            for(unsigned char c: h) printf("%02x", c);
            printf("\n");
        }
    }
    return 0;
}
