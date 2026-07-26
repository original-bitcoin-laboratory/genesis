// C++ PORT harness for OBL-JAN09 EvalScript opcode semantics.
// Evidence level: PORT (a compiled derivative), stronger than the Python MODEL
// because the numeric engine is REAL OpenSSL BN (BN_mul/BN_div/BN_mod/BN_lshift/
// BN_rshift) and the number codec is the original bignum.h logic (BN_mpi2bn/
// BN_bn2mpi). CBigNum is ported to OpenSSL 3.x (opaque BIGNUM -> BIGNUM* member).
// The opcode bodies are reproduced verbatim from script.cpp.
//
// Reads scripts from stdin (one per line; tokens: n:<int>, x:<hex>, OP_NAME) and
// prints "<line> => <hex-of-top>|<empty>|FAIL" for differential testing.

#include <openssl/bn.h>
#include <openssl/evp.h>
#include <algorithm>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
using namespace std;
typedef vector<unsigned char> valtype;

struct AutoCtx { BN_CTX* p; AutoCtx(){p=BN_CTX_new();} ~AutoCtx(){BN_CTX_free(p);} operator BN_CTX*(){return p;} };

// ---- CBigNum ported to opaque OpenSSL (logic from bignum.h) ------------------
struct CBigNum {
    BIGNUM* bn;
    CBigNum(){ bn = BN_new(); }
    CBigNum(const CBigNum& b){ bn = BN_dup(b.bn); }
    CBigNum(long n){ bn = BN_new(); setlong(n); }
    CBigNum(const valtype& vch){ bn = BN_new(); setvch(vch); }
    ~CBigNum(){ BN_free(bn); }
    CBigNum& operator=(const CBigNum& b){ BN_copy(bn, b.bn); return *this; }
    BIGNUM* get() const { return bn; }

    void setlong(long n){
        if (n >= 0) BN_set_word(bn, (unsigned long)n);
        else { BN_set_word(bn, (unsigned long)(-n)); BN_set_negative(bn, 1); }
    }
    // bignum.h getint(): BN_get_word truncated with sign
    int getint() const {
        unsigned long n = BN_get_word(bn);
        if (!BN_is_negative(bn)) return (n > (unsigned long)INT_MAX ? INT_MAX : (int)n);
        else return (n > (unsigned long)INT_MAX ? INT_MIN : -(int)n);
    }
    unsigned long getulong() const { return BN_get_word(bn); }
    // bignum.h setvch(): little-endian vch -> reverse -> 4-byte-len MPI -> BN
    void setvch(const valtype& vch){
        valtype v2(vch.size() + 4);
        unsigned int nSize = vch.size();
        v2[0]=(nSize>>24)&0xff; v2[1]=(nSize>>16)&0xff; v2[2]=(nSize>>8)&0xff; v2[3]=nSize&0xff;
        reverse_copy(vch.begin(), vch.end(), v2.begin()+4);
        BN_mpi2bn(&v2[0], v2.size(), bn);
    }
    // bignum.h getvch(): BN -> MPI -> drop 4-byte len -> reverse -> little-endian
    valtype getvch() const {
        unsigned int nSize = BN_bn2mpi(bn, NULL);
        if (nSize < 4) return valtype();
        valtype vch(nSize);
        BN_bn2mpi(bn, &vch[0]);
        vch.erase(vch.begin(), vch.begin()+4);
        reverse(vch.begin(), vch.end());
        return vch;
    }
};
static bool CastToBool(const valtype& vch){ CBigNum b(vch); return !BN_is_zero(b.bn); }

// ---- opcode execution (bodies from script.cpp EvalScript) --------------------
static const valtype vchTrue(1,1), vchFalse(0);

static bool run(const vector<string>& toks, valtype& top, bool& hasTop){
    vector<valtype> st;
    AutoCtx ctx;
    auto need=[&](size_t n){ return st.size()>=n; };
    for (const string& t : toks){
        if (t.rfind("x:",0)==0){
            valtype v; string h=t.substr(2);
            for(size_t i=0;i+1<h.size();i+=2) v.push_back((unsigned char)strtol(h.substr(i,2).c_str(),0,16));
            st.push_back(v);
        } else if (t.rfind("n:",0)==0){
            st.push_back(CBigNum((long)atol(t.substr(2).c_str())).getvch());
        } else if (t=="OP_DUP"){ if(!need(1))return false; st.push_back(st.back()); }
        else if (t=="OP_DROP"){ if(!need(1))return false; st.pop_back(); }
        else if (t=="OP_SWAP"){ if(!need(2))return false; swap(st[st.size()-1],st[st.size()-2]); }
        else if (t=="OP_OVER"){ if(!need(2))return false; st.push_back(st[st.size()-2]); }
        else if (t=="OP_VERIFY"){ if(!need(1))return false; valtype v=st.back(); st.pop_back(); if(!CastToBool(v))return false; }
        // splice
        else if (t=="OP_CAT"){ if(!need(2))return false; valtype b=st.back(); st.pop_back(); st.back().insert(st.back().end(),b.begin(),b.end()); }
        else if (t=="OP_SUBSTR"){ if(!need(3))return false; int sz=CBigNum(st.back()).getint(); st.pop_back(); int bg=CBigNum(st.back()).getint(); st.pop_back(); valtype& v=st.back(); int en=bg+sz; if(bg<0||en<bg)return false; if(bg>(int)v.size())bg=v.size(); if(en>(int)v.size())en=v.size(); v.erase(v.begin()+en,v.end()); v.erase(v.begin(),v.begin()+bg); }
        else if (t=="OP_LEFT"||t=="OP_RIGHT"){ if(!need(2))return false; int sz=CBigNum(st.back()).getint(); st.pop_back(); valtype& v=st.back(); if(sz<0)return false; if(sz>(int)v.size())sz=v.size(); if(t=="OP_LEFT")v.erase(v.begin()+sz,v.end()); else v.erase(v.begin(),v.end()-sz); }
        else if (t=="OP_SIZE"){ if(!need(1))return false; st.push_back(CBigNum((long)st.back().size()).getvch()); }
        // bitwise
        else if (t=="OP_INVERT"){ if(!need(1))return false; for(auto&c:st.back())c=~c; }
        else if (t=="OP_AND"||t=="OP_OR"||t=="OP_XOR"){ if(!need(2))return false; valtype b=st.back(); st.pop_back(); valtype& a=st.back(); size_t n=max(a.size(),b.size()); a.resize(n,0); b.resize(n,0); for(size_t i=0;i<n;i++){ if(t=="OP_AND")a[i]&=b[i]; else if(t=="OP_OR")a[i]|=b[i]; else a[i]^=b[i]; } }
        else if (t=="OP_EQUAL"||t=="OP_EQUALVERIFY"){ if(!need(2))return false; valtype b=st.back(); st.pop_back(); valtype a=st.back(); st.pop_back(); bool eq=(a==b); st.push_back(eq?vchTrue:vchFalse); if(t=="OP_EQUALVERIFY"){ if(eq)st.pop_back(); else return false; } }
        // numeric unary
        else if (t=="OP_1ADD"||t=="OP_1SUB"||t=="OP_2MUL"||t=="OP_2DIV"||t=="OP_NEGATE"||t=="OP_ABS"||t=="OP_NOT"||t=="OP_0NOTEQUAL"){
            if(!need(1))return false; CBigNum n(st.back()); st.pop_back(); CBigNum r; const CBigNum one((long)1);
            if(t=="OP_1ADD") BN_add(r.get(),n.get(),one.get());
            else if(t=="OP_1SUB") BN_sub(r.get(),n.get(),one.get());
            else if(t=="OP_2MUL") BN_lshift(r.get(),n.get(),1);
            else if(t=="OP_2DIV") BN_rshift(r.get(),n.get(),1);
            else if(t=="OP_NEGATE"){ BN_copy(r.get(),n.get()); if(!BN_is_zero(r.get()))BN_set_negative(r.get(),!BN_is_negative(r.get())); }
            else if(t=="OP_ABS"){ BN_copy(r.get(),n.get()); BN_set_negative(r.get(),0); }
            else if(t=="OP_NOT") r.setlong(BN_is_zero(n.get())?1:0);
            else r.setlong(BN_is_zero(n.get())?0:1);
            st.push_back(r.getvch());
        }
        // numeric binary
        else if (t=="OP_ADD"||t=="OP_SUB"||t=="OP_MUL"||t=="OP_DIV"||t=="OP_MOD"||t=="OP_LSHIFT"||t=="OP_RSHIFT"||t=="OP_BOOLAND"||t=="OP_BOOLOR"||t=="OP_NUMEQUAL"||t=="OP_NUMNOTEQUAL"||t=="OP_LESSTHAN"||t=="OP_GREATERTHAN"||t=="OP_LESSTHANOREQUAL"||t=="OP_GREATERTHANOREQUAL"||t=="OP_MIN"||t=="OP_MAX"){
            if(!need(2))return false; CBigNum b2(st.back()); st.pop_back(); CBigNum b1(st.back()); st.pop_back(); CBigNum r;
            int c=BN_cmp(b1.get(),b2.get());
            if(t=="OP_ADD") BN_add(r.get(),b1.get(),b2.get());
            else if(t=="OP_SUB") BN_sub(r.get(),b1.get(),b2.get());
            else if(t=="OP_MUL"){ if(!BN_mul(r.get(),b1.get(),b2.get(),ctx))return false; }
            else if(t=="OP_DIV"){ if(BN_is_zero(b2.get())||!BN_div(r.get(),NULL,b1.get(),b2.get(),ctx))return false; }
            else if(t=="OP_MOD"){ if(BN_is_zero(b2.get())||!BN_div(NULL,r.get(),b1.get(),b2.get(),ctx))return false; }
            else if(t=="OP_LSHIFT"){ if(BN_is_negative(b2.get()))return false; BN_lshift(r.get(),b1.get(),b2.getulong()); }
            else if(t=="OP_RSHIFT"){ if(BN_is_negative(b2.get()))return false; BN_rshift(r.get(),b1.get(),b2.getulong()); }
            else if(t=="OP_BOOLAND") r.setlong((!BN_is_zero(b1.get())&&!BN_is_zero(b2.get()))?1:0);
            else if(t=="OP_BOOLOR") r.setlong((!BN_is_zero(b1.get())||!BN_is_zero(b2.get()))?1:0);
            else if(t=="OP_NUMEQUAL") r.setlong(c==0?1:0);
            else if(t=="OP_NUMNOTEQUAL") r.setlong(c!=0?1:0);
            else if(t=="OP_LESSTHAN") r.setlong(c<0?1:0);
            else if(t=="OP_GREATERTHAN") r.setlong(c>0?1:0);
            else if(t=="OP_LESSTHANOREQUAL") r.setlong(c<=0?1:0);
            else if(t=="OP_GREATERTHANOREQUAL") r.setlong(c>=0?1:0);
            else if(t=="OP_MIN") r = (c<0?b1:b2);
            else r = (c>0?b1:b2);
            st.push_back(r.getvch());
        }
        else if (t=="OP_WITHIN"){ if(!need(3))return false; CBigNum mx(st.back()); st.pop_back(); CBigNum mn(st.back()); st.pop_back(); CBigNum x(st.back()); st.pop_back(); bool v=(BN_cmp(mn.get(),x.get())<=0 && BN_cmp(x.get(),mx.get())<0); st.push_back(v?vchTrue:vchFalse); }
        else if (t=="OP_SHA1"||t=="OP_SHA256"||t=="OP_HASH256"){
            if(!need(1))return false; valtype in=st.back(); st.pop_back(); unsigned char h[64]; unsigned int hl=0;
            const EVP_MD* md = (t=="OP_SHA1")?EVP_sha1():EVP_sha256();
            EVP_Digest(in.data(),in.size(),h,&hl,md,NULL);
            if(t=="OP_HASH256"){ unsigned char h2[64]; unsigned int hl2=0; EVP_Digest(h,hl,h2,&hl2,EVP_sha256(),NULL); st.push_back(valtype(h2,h2+hl2)); }
            else st.push_back(valtype(h,h+hl));
        }
        else return false;
    }
    if(st.empty()){ hasTop=false; return true; }
    hasTop=true; top=st.back(); return true;
}

int main(){
    string line;
    while(getline(cin,line)){
        if(line.empty()||line[0]=='#'){ continue; }
        istringstream ss(line); vector<string> toks; string t; while(ss>>t) toks.push_back(t);
        valtype top; bool hasTop=false; bool ok=run(toks,top,hasTop);
        printf("%s => ", line.c_str());
        if(!ok) printf("FAIL\n");
        else if(!hasTop) printf("(empty-stack)\n");
        else { if(top.empty())printf("(empty)"); for(unsigned char c:top)printf("%02x",c); printf("\n"); }
    }
    return 0;
}
