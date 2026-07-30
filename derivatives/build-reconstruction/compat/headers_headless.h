#pragma once
// Headless replacement for Satoshi's headers.h, extended to the SCRIPT layer.
// Same idea as prelude.h (std + OpenSSL, no wx/winsock/BDB), but it also includes the
// original project headers in dependency order and the donor scaffolding, so the ORIGINAL
// script.cpp compiles and links. The build script (period_build_wsl.sh) drops a one-line
// headers.h next to a verbatim copy of script.cpp so its `#include "headers.h"` resolves
// here. Nothing below edits Satoshi's files. NOT money.

#include "prelude.h"          // std + OpenSSL + using namespace std
#include "donor_util.h"       // donor: foreach/UBEGIN/UEND/REF + strprintf/HexStr (from util.h)
#include "serialize.h"        // ORIGINAL: VERSION, secure_allocator, CDataStream, IMPLEMENT_SERIALIZE
#include "uint256.h"          // ORIGINAL
#include "donor_hashes.h"     // donor: Hash / Hash160 / SerializeHash (from util.h)
#include "bignum.h"           // ORIGINAL
#include "base58.h"           // ORIGINAL (needs Hash160 + CBigNum)
#include "key.h"              // ORIGINAL (CKey, CPrivKey)
#include "script.h"           // ORIGINAL (CScript, EvalScript/SignatureHash/VerifySignature decls)
#include "donor_tx.h"         // donor: COutPoint/CTxIn/CTxOut/CTransaction + keystore externs
