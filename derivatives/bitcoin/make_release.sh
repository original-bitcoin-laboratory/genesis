#!/usr/bin/env bash
# make_release.sh -- assemble bitcoin-0.1.2.tar.gz: the client binary, license.txt, readme.txt,
# src/, and RELEASE.txt. The binary is statically linked, so it ships no DLLs.
#
# Run:  bash make_release.sh          (after make_chain.py and the build)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORIG="$HERE/../../extracted/bitcoin"          # the verified source tree (for license.txt / readme.txt)
SRC="$HERE/src"                                # derived tree from make_chain.py
# EXE is overridable so a new release can be cut without overwriting the binary of the previous
# one. That matters here: build/ holds cfb59606..., the v0.1.1 exe that mined block 1, and it
# has to stay exactly where the evidence records say it is.
EXE="${EXE:-$HERE/build/bitcoin-0.1.0-reconstructed.exe}"
OUT="$HERE/dist"
NAME="bitcoin-0.1.2"

[ -d "$SRC" ]  || { echo "!! run: python make_chain.py"; exit 2; }
[ -f "$EXE" ]  || { echo "!! build first: SRC=$SRC bash ../build-reconstruction/full_build_wsl.sh"; exit 2; }

rm -rf "$OUT/$NAME"; mkdir -p "$OUT/$NAME"
cp -r "$SRC"                  "$OUT/$NAME/src"
cp    "$ORIG/license.txt"     "$OUT/$NAME/license.txt"      # MIT, unmodified
cp    "$ORIG/readme.txt"      "$OUT/$NAME/readme.txt"       # unmodified
cp    "$EXE"                  "$OUT/$NAME/bitcoin.exe"

cat > "$OUT/$NAME/RELEASE.txt" <<'TXT'
Bitcoin v0.1.2
==============

The client, the chain and the protocol are unchanged from v0.1.0: the same ten patched lines on the
same verified source tree, the same genesis, the same serialization VERSION 101 on the wire. A node
built from any of the three releases speaks to a node built from either other. This is a build-level
release, the second one.

What changed
------------
The client was executed for the first time on 4 August 2026, to mine block 1. It mined it. It also
showed two things three days of hashing and string-scanning had not: it wrote no debug.log, and
wxWidgets logged "Can't load bitmap 'send20' from resources!" at startup.

Both are divergences in how we built it, not in what it does. This release removes them.

  * __WXDEBUG__ is now defined, and wxWidgets is rebuilt --enable-debug to match. The whole body of
    OutputDebugStringF sits inside #ifdef __WXDEBUG__, so without it the client emits no diagnostic
    output at all -- not to file, not to OutputDebugString. It now writes debug.log as the 2009
    client does.

  * windres ui.rc now runs, producing the .rsrc section with the eleven bitmaps and icons. Our
    binary had no resource directory at all; the missing toolbar images were the visible symptom.

  * -mthreads is set, as makefile:28 sets it. On MinGW it selects thread-safe C++ exception handling
    and the _beginthreadex runtime. This client runs five threads.

  * sha.cpp is compiled -O3, overriding the -O0 every other unit gets, exactly as his makefile does.
    It is the mining inner loop.

Reading the makefile is not what settled this. It takes BUILD=debug|release and defaults to debug,
but `make BUILD=release` is an equally legal build of the same tree, so the default is suggestive
and nothing more. What settled it was measuring the released 2009 binary, sha256 fbcac071...:

    "debug.log"                     7 occurrences   (and that literal occurs in exactly one place
                                                     in the whole source: util.h:236, inside the
                                                     #ifdef -- there is no other way in)
    'assert "%s" failed'            1
    ../../include/wx/*.h paths     24 distinct      (__FILE__ expansions from wxASSERT in wx inline
                                                     headers; they vanish without __WXDEBUG__)
    .rsrc PE section                present

Our v0.1.1 binary had none of the first three and no .rsrc. His client is a debug build; ours was
not. Full working: docs/BUILD_FIDELITY.md.

One divergence is left in place and disclosed rather than fixed. He linked OpenSSL and the MinGW
runtime dynamically and shipped libeay32.dll and mingwm10.dll beside the executable; this binary is
static and ships neither. DLLs we shipped could not be his -- ours come from a modern mingw-w64 --
so matching the shape would buy a resemblance while adding two files that must survive intact for
the client to start. One self-contained executable is the more durable form, and no peer can
observe the difference.

v0.1.0 and v0.1.1 remain published and their signatures remain valid. Nothing about the chain is
affected: consensus, the wire format and the genesis are untouched, and block 1 was mined and
relayed by the v0.1.1 binary. If you are running either, you are on the same network.

Genesis
-------
  hash      00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a
  coinbase  The Times 03/Aug/2026 Toll of schooling 'straitjacket'
  output    50.00000000 -> P2PK 04c0414c...  (no value assigned)
  nTime     1785781375 = 2026-08-03 18:22:55 UTC
  nBits     0x1d00ffff
  nNonce    33394338

Network
-------
  magic     f00ba726          port 18026
  seed      bitcoin.bitcoin-lab.org:18026

Mining
------
  height 0  00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a   3 Aug 2026
  height 1  000000007beb32b8380089595a91261a5ce4fbd4ece0cd661683cb1ce81e407c   4 Aug 2026

Block 1 was mined by the v0.1.1 client, from this distribution, and relayed to the seed, which
validated and stored it with a different implementation. Block 2 onward are unmined and anyone may
take them. Blocks cost difficulty-1 work -- about 2^32 hashes -- so the client's own miner takes
roughly an hour per block on one core. There is nothing to buy, nothing to claim, and nothing owed
to whoever mines next.


Build
-----
src/ is composed by make_chain.py from two inputs: the v0.1.0 source tree, SHA256
8b17eb9a5707f2519defda4cdf8d14fa1b8dee630e11e6ef85ff9f5547555b56, and bitcoin-v0.1.0.patch --
this chain's genesis, network magic and port, and bootstrap channel. Ten lines, in main.cpp,
net.h and irc.cpp.

The binary is cross-compiled by full_build_wsl.sh against the period libraries (OpenSSL 1.0.2u,
wxWidgets 2.8.12, Berkeley DB 4.8, Boost 1.42), statically linked, so it ships no DLLs.

Consensus rules, script, difficulty, serialization, wallet and UI carry no guardrails: no
MoneyRange, no script limits, and no 1 MB block cap -- that arrives in July 2010. The one ceiling
that does exist is MAX_SIZE, 32 MiB, enforced by CheckBlock. Safe here for one reason only --
there is nothing to steal.

Verify
------
  python make_chain.py --check     # src/ is those two inputs and nothing else
  python net.py                    # re-derives the genesis hash; checks it meets difficulty-1

The client asserts the genesis hash on startup, so a wrong build does not run.

readme.txt and license.txt are the source tree's own, unmodified.

What running this client discloses
---------------------------------
Read this before you run it anywhere but an isolated VM.

The 2009 client bootstraps over IRC, and this one still does, unchanged but for the channel name.
On startup it resolves chat.freenode.net, connects on 6667, and joins #bitcoin26 with its NICK set
to a base58 encoding of its own routable address -- so your public IP is published, in a trivially
decodable form, into a public channel on infrastructure nobody here operates. Anyone sitting in the
channel can read it, and IRC servers keep logs.

That is what Satoshi's client did, and it is left alone for the same reason everything else is:
changing it would make this a different program. But 2009's Freenode is not 2026's, and you should
decide knowingly. ThreadIRCSeed starts unconditionally from net.cpp -- v0.1.0 has no -noirc switch,
so the only lever is the client's own /proxy option, which leaves addrLocalHost unroutable and makes
it fall back to a random nickname. Everything else in the client is equally period-accurate: no
encryption, no authentication, and a wallet.dat written in the clear.

NOT MONEY. No premine of value, no token, no sale, no market. Experimental research artifact.
Run the client only in an isolated VM: it is a live node.
TXT

cd "$OUT"
tar --format=ustar -czf "$NAME.tar.gz" "$NAME"
sha256sum "$NAME.tar.gz" > "$NAME.tar.gz.sha256"

echo "built $OUT/$NAME.tar.gz"
echo "  $(cat "$NAME.tar.gz.sha256")"
echo "  contents:"
tar -tzf "$NAME.tar.gz" | sed -n '1,8p;$!d' | sed 's/^/    /'   # sed, not head: head exits early and SIGPIPEs under pipefail
echo "    ... $(tar -tzf "$NAME.tar.gz" | wc -l) entries"
