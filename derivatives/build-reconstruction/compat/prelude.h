#pragma once
// SPDX-License-Identifier: MIT
// Reproduces logic from Bitcoin v0.1, Copyright (c) 2009 Satoshi Nakamoto, MIT.
// Their notice travels with their logic; the surrounding scaffolding is this laboratory's, 2026.
// Headless stand-in for Satoshi's headers.h (the v0.1 master include).
//
// It reproduces the *portable* half of headers.h -- the C++ standard library,
// OpenSSL, and `using namespace std` -- and deliberately DROPS the platform half:
//   <wx/wx.h> etc.  (wxWidgets 2.8 GUI)
//   <windows.h>, <winsock2.h>, <mswsock.h>, <process.h>, <malloc.h>, <io.h>
//   the Berkeley DB / net / irc / ui project headers
//
// The point is to compile the ORIGINAL, byte-verified source unmodified and let
// the compiler report exactly where the portable subset ends. Nothing here edits
// Satoshi's files; this only replaces the environment his headers.h assumed.
// NOT money.

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <climits>
#include <cfloat>
#include <cassert>
#include <memory>
#include <sstream>
#include <string>
#include <vector>
#include <list>
#include <deque>
#include <map>
#include <set>
#include <algorithm>
#include <numeric>
#include <stdexcept>

#include <openssl/ecdsa.h>
#include <openssl/evp.h>
#include <openssl/rand.h>
#include <openssl/sha.h>
#include <openssl/ripemd.h>
#include <openssl/bn.h>
#include <openssl/ec.h>
#include <openssl/obj_mac.h>

using namespace std;
