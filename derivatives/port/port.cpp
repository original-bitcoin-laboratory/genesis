// SPDX-License-Identifier: MIT
// Reproduces logic from Bitcoin v0.1, Copyright (c) 2009 Satoshi Nakamoto, MIT.
// Their notice travels with their logic; the surrounding scaffolding is this laboratory's, 2026.
// C++ PORT harness for OBL-JAN09 EvalScript opcode semantics.
// Evidence level: PORT (a compiled derivative). Numeric engine is REAL OpenSSL BN;
// number codec is the original bignum.h logic. Opcode bodies reproduced from
// script.cpp. Coverage: push, control flow (fExec/vfExec), stack + alt-stack ops,
// splice, bitwise, numeric, crypto hashes, OP_CODESEPARATOR. (CHECKSIG lives in
// the sighash build, stage C.) Reads scripts from stdin (tokens n:<int>, x:<hex>,
// OP_NAME) and prints "<line> => <hex|(empty)|(empty-stack)|FAIL>".

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

struct CBigNum {  // ported to opaque OpenSSL (logic from bignum.h)
    BIGNUM* bn;
    CBigNum(){ bn = BN_new(); }
    CBigNum(const CBigNum& b){ bn = BN_dup(b.bn); }
    CBigNum(long n){ bn = BN_new(); setlong(n); }
    CBigNum(const valtype& vch){ bn = BN_new(); setvch(vch); }
    ~CBigNum(){ BN_free(bn); }
    CBigNum& operator=(const CBigNum& b){ BN_copy(bn, b.bn); return *this; }
    BIGNUM* get() const { return bn; }
    void setlong(long n){ if (n>=0) BN_set_word(bn,(unsigned long)n); else { BN_set_word(bn,(unsigned long)(-n)); BN_set_negative(bn,1); } }
    int getint() const { unsigned long n=BN_get_word(bn); if(!BN_is_negative(bn)) return (n>(unsigned long)INT_MAX?INT_MAX:(int)n); else return (n>(unsigned long)INT_MAX?INT_MIN:-(int)n); }
    unsigned long getulong() const { return BN_get_word(bn); }
    void setvch(const valtype& vch){ valtype v2(vch.size()+4); unsigned int nSize=vch.size(); v2[0]=(nSize>>24)&0xff; v2[1]=(nSize>>16)&0xff; v2[2]=(nSize>>8)&0xff; v2[3]=nSize&0xff; reverse_copy(vch.begin(),vch.end(),v2.begin()+4); BN_mpi2bn(&v2[0],v2.size(),bn); }
    valtype getvch() const { unsigned int nSize=BN_bn2mpi(bn,NULL); if(nSize<4) return valtype(); valtype vch(nSize); BN_bn2mpi(bn,&vch[0]); vch.erase(vch.begin(),vch.begin()+4); reverse(vch.begin(),vch.end()); return vch; }
};
static bool CastToBool(const valtype& vch){ CBigNum b(vch); return !BN_is_zero(b.bn); }

static bool run(const vector<string>& toks, valtype& outTop, bool& hasTop){
    vector<valtype> st, alt;
    vector<char> vfExec;   // exec-guard stack
    AutoCtx ctx;
    auto need=[&](size_t n){ return st.size()>=n; };
    bool stop=false;
    for (size_t pc=0; pc<toks.size() && !stop; pc++){
        const string& t = toks[pc];
        bool fExec = (find(vfExec.begin(),vfExec.end(),(char)0)==vfExec.end());
        bool isData = (t.rfind("x:",0)==0 || t.rfind("n:",0)==0);
        bool isNumPush = (t=="OP_0"||t=="OP_FALSE"||t=="OP_1NEGATE"||t=="OP_1"||t=="OP_TRUE"||t=="OP_2"||t=="OP_3"||t=="OP_4"||t=="OP_5"||t=="OP_6"||t=="OP_7"||t=="OP_8"||t=="OP_9"||t=="OP_10"||t=="OP_11"||t=="OP_12"||t=="OP_13"||t=="OP_14"||t=="OP_15"||t=="OP_16");
        bool isIfElse = (t=="OP_IF"||t=="OP_NOTIF"||t=="OP_ELSE"||t=="OP_ENDIF");
        if (fExec && isData){
            if (t.rfind("x:",0)==0){ valtype v; string h=t.substr(2); for(size_t i=0;i+1<h.size();i+=2) v.push_back((unsigned char)strtol(h.substr(i,2).c_str(),0,16)); st.push_back(v); }
            else st.push_back(CBigNum((long)atol(t.substr(2).c_str())).getvch());
            continue;
        }
        if (!(fExec || isIfElse)) continue;
        if (isNumPush){ long v = (t=="OP_0"||t=="OP_FALSE")?0:(t=="OP_1NEGATE")?-1:(t=="OP_TRUE")?1:atol(t.substr(3).c_str()); st.push_back(CBigNum(v).getvch()); }
        else if (t=="OP_NOP"){}
        else if (t=="OP_IF"||t=="OP_NOTIF"){ char v=0; if(fExec){ if(!need(1))return false; bool b=CastToBool(st.back()); st.pop_back(); if(t=="OP_NOTIF")b=!b; v=b?1:0; } vfExec.push_back(v); }
        else if (t=="OP_ELSE"){ if(vfExec.empty())return false; vfExec.back()=!vfExec.back(); }
        else if (t=="OP_ENDIF"){ if(vfExec.empty())return false; vfExec.pop_back(); }
        else if (t=="OP_VERIFY"){ if(!need(1))return false; if(!CastToBool(st.back())){ stop=true; } else st.pop_back(); }
        else if (t=="OP_RETURN"){ stop=true; }
        else if (t=="OP_CODESEPARATOR"){}
        // stack / alt-stack
        else if (t=="OP_TOALTSTACK"){ if(!need(1))return false; alt.push_back(st.back()); st.pop_back(); }
        else if (t=="OP_FROMALTSTACK"){ if(alt.empty())return false; st.push_back(alt.back()); alt.pop_back(); }
        else if (t=="OP_2DROP"){ if(!need(2))return false; st.pop_back(); st.pop_back(); }
        else if (t=="OP_2DUP"){ if(!need(2))return false; valtype a=st[st.size()-2],b=st[st.size()-1]; st.push_back(a); st.push_back(b); }
        else if (t=="OP_3DUP"){ if(!need(3))return false; valtype a=st[st.size()-3],b=st[st.size()-2],c=st[st.size()-1]; st.push_back(a); st.push_back(b); st.push_back(c); }
        else if (t=="OP_2OVER"){ if(!need(4))return false; valtype a=st[st.size()-4],b=st[st.size()-3]; st.push_back(a); st.push_back(b); }
        else if (t=="OP_2ROT"){ if(!need(6))return false; valtype x1=st[st.size()-6],x2=st[st.size()-5]; st.erase(st.end()-6,st.end()-4); st.push_back(x1); st.push_back(x2); }
        else if (t=="OP_2SWAP"){ if(!need(4))return false; swap(st[st.size()-4],st[st.size()-2]); swap(st[st.size()-3],st[st.size()-1]); }
        else if (t=="OP_IFDUP"){ if(!need(1))return false; if(CastToBool(st.back())) st.push_back(st.back()); }
        else if (t=="OP_DEPTH"){ st.push_back(CBigNum((long)st.size()).getvch()); }
        else if (t=="OP_DROP"){ if(!need(1))return false; st.pop_back(); }
        else if (t=="OP_DUP"){ if(!need(1))return false; st.push_back(st.back()); }
        else if (t=="OP_NIP"){ if(!need(2))return false; st.erase(st.end()-2); }
        else if (t=="OP_OVER"){ if(!need(2))return false; st.push_back(st[st.size()-2]); }
        else if (t=="OP_PICK"||t=="OP_ROLL"){ if(!need(1))return false; int n=CBigNum(st.back()).getint(); st.pop_back(); if(n<0||(size_t)n>=st.size())return false; valtype v=st[st.size()-1-n]; if(t=="OP_ROLL")st.erase(st.end()-1-n); st.push_back(v); }
        else if (t=="OP_ROT"){ if(!need(3))return false; valtype x1=st[st.size()-3]; st.erase(st.end()-3); st.push_back(x1); }
        else if (t=="OP_SWAP"){ if(!need(2))return false; swap(st[st.size()-1],st[st.size()-2]); }
        else if (t=="OP_TUCK"){ if(!need(2))return false; valtype v=st.back(); st.insert(st.end()-2,v); }
        // splice
        else if (t=="OP_CAT"){ if(!need(2))return false; valtype b=st.back(); st.pop_back(); st.back().insert(st.back().end(),b.begin(),b.end()); }
        else if (t=="OP_SUBSTR"){ if(!need(3))return false; int sz=CBigNum(st.back()).getint(); st.pop_back(); int bg=CBigNum(st.back()).getint(); st.pop_back(); valtype& v=st.back(); int en=bg+sz; if(bg<0||en<bg)return false; if(bg>(int)v.size())bg=v.size(); if(en>(int)v.size())en=v.size(); v.erase(v.begin()+en,v.end()); v.erase(v.begin(),v.begin()+bg); }
        else if (t=="OP_LEFT"||t=="OP_RIGHT"){ if(!need(2))return false; int sz=CBigNum(st.back()).getint(); st.pop_back(); valtype& v=st.back(); if(sz<0)return false; if(sz>(int)v.size())sz=v.size(); if(t=="OP_LEFT")v.erase(v.begin()+sz,v.end()); else v.erase(v.begin(),v.end()-sz); }
        else if (t=="OP_SIZE"){ if(!need(1))return false; st.push_back(CBigNum((long)st.back().size()).getvch()); }
        // bitwise
        else if (t=="OP_INVERT"){ if(!need(1))return false; for(auto&c:st.back())c=~c; }
        else if (t=="OP_AND"||t=="OP_OR"||t=="OP_XOR"){ if(!need(2))return false; valtype b=st.back(); st.pop_back(); valtype& a=st.back(); size_t n=max(a.size(),b.size()); a.resize(n,0); b.resize(n,0); for(size_t i=0;i<n;i++){ if(t=="OP_AND")a[i]&=b[i]; else if(t=="OP_OR")a[i]|=b[i]; else a[i]^=b[i]; } }
        else if (t=="OP_EQUAL"||t=="OP_EQUALVERIFY"){ if(!need(2))return false; valtype b=st.back(); st.pop_back(); valtype a=st.back(); st.pop_back(); bool eq=(a==b); st.push_back(eq?valtype(1,1):valtype()); if(t=="OP_EQUALVERIFY"){ if(eq)st.pop_back(); else stop=true; } }
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
        else if (t=="OP_ADD"||t=="OP_SUB"||t=="OP_MUL"||t=="OP_DIV"||t=="OP_MOD"||t=="OP_LSHIFT"||t=="OP_RSHIFT"||t=="OP_BOOLAND"||t=="OP_BOOLOR"||t=="OP_NUMEQUAL"||t=="OP_NUMEQUALVERIFY"||t=="OP_NUMNOTEQUAL"||t=="OP_LESSTHAN"||t=="OP_GREATERTHAN"||t=="OP_LESSTHANOREQUAL"||t=="OP_GREATERTHANOREQUAL"||t=="OP_MIN"||t=="OP_MAX"){
            if(!need(2))return false; CBigNum b2(st.back()); st.pop_back(); CBigNum b1(st.back()); st.pop_back(); CBigNum r; int c=BN_cmp(b1.get(),b2.get());
            if(t=="OP_ADD") BN_add(r.get(),b1.get(),b2.get());
            else if(t=="OP_SUB") BN_sub(r.get(),b1.get(),b2.get());
            else if(t=="OP_MUL"){ if(!BN_mul(r.get(),b1.get(),b2.get(),ctx))return false; }
            else if(t=="OP_DIV"){ if(BN_is_zero(b2.get())||!BN_div(r.get(),NULL,b1.get(),b2.get(),ctx))return false; }
            else if(t=="OP_MOD"){ if(BN_is_zero(b2.get())||!BN_div(NULL,r.get(),b1.get(),b2.get(),ctx))return false; }
            else if(t=="OP_LSHIFT"){ if(BN_is_negative(b2.get()))return false; BN_lshift(r.get(),b1.get(),b2.getulong()); }
            else if(t=="OP_RSHIFT"){ if(BN_is_negative(b2.get()))return false; BN_rshift(r.get(),b1.get(),b2.getulong()); }
            else if(t=="OP_BOOLAND") r.setlong((!BN_is_zero(b1.get())&&!BN_is_zero(b2.get()))?1:0);
            else if(t=="OP_BOOLOR") r.setlong((!BN_is_zero(b1.get())||!BN_is_zero(b2.get()))?1:0);
            else if(t=="OP_NUMEQUAL"||t=="OP_NUMEQUALVERIFY") r.setlong(c==0?1:0);
            else if(t=="OP_NUMNOTEQUAL") r.setlong(c!=0?1:0);
            else if(t=="OP_LESSTHAN") r.setlong(c<0?1:0);
            else if(t=="OP_GREATERTHAN") r.setlong(c>0?1:0);
            else if(t=="OP_LESSTHANOREQUAL") r.setlong(c<=0?1:0);
            else if(t=="OP_GREATERTHANOREQUAL") r.setlong(c>=0?1:0);
            else if(t=="OP_MIN") r=(c<0?b1:b2);
            else r=(c>0?b1:b2);
            st.push_back(r.getvch());
            if(t=="OP_NUMEQUALVERIFY"){ if(CastToBool(st.back()))st.pop_back(); else stop=true; }
        }
        else if (t=="OP_WITHIN"){ if(!need(3))return false; CBigNum mx(st.back()); st.pop_back(); CBigNum mn(st.back()); st.pop_back(); CBigNum x(st.back()); st.pop_back(); bool v=(BN_cmp(mn.get(),x.get())<=0 && BN_cmp(x.get(),mx.get())<0); st.push_back(v?valtype(1,1):valtype()); }
        else if (t=="OP_SHA1"||t=="OP_SHA256"||t=="OP_HASH256"){ if(!need(1))return false; valtype in=st.back(); st.pop_back(); unsigned char h[64]; unsigned int hl=0; const EVP_MD* md=(t=="OP_SHA1")?EVP_sha1():EVP_sha256(); EVP_Digest(in.data(),in.size(),h,&hl,md,NULL); if(t=="OP_HASH256"){ unsigned char h2[64]; unsigned int hl2=0; EVP_Digest(h,hl,h2,&hl2,EVP_sha256(),NULL); st.push_back(valtype(h2,h2+hl2)); } else st.push_back(valtype(h,h+hl)); }
        else return false;
    }
    if(st.empty()){ hasTop=false; return true; }
    hasTop=true; outTop=st.back(); return true;
}

int main(){
    string line;
    while(getline(cin,line)){
        if(line.empty()||line[0]=='#') continue;
        istringstream ss(line); vector<string> toks; string t; while(ss>>t) toks.push_back(t);
        valtype top; bool hasTop=false; bool ok=run(toks,top,hasTop);
        printf("%s => ", line.c_str());
        if(!ok) printf("FAIL\n");
        else if(!hasTop) printf("(empty-stack)\n");
        else { if(top.empty())printf("(empty)"); for(unsigned char c:top)printf("%02x",c); printf("\n"); }
    }
    return 0;
}
