#!/usr/bin/env bash
# make_release.sh -- assemble bitcoin-0.1.1.tar.gz: the client binary, license.txt, readme.txt,
# src/, and RELEASE.txt. The binary is statically linked, so it ships no DLLs.
#
# Run:  bash make_release.sh          (after make_chain.py and the build)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORIG="$HERE/../../extracted/bitcoin"          # the verified source tree (for license.txt / readme.txt)
SRC="$HERE/src"                                # derived tree from make_chain.py
EXE="$HERE/build/bitcoin-0.1.0-reconstructed.exe"
OUT="$HERE/dist"
NAME="bitcoin-0.1.1"

[ -d "$SRC" ]  || { echo "!! run: python make_chain.py"; exit 2; }
[ -f "$EXE" ]  || { echo "!! build first: SRC=$SRC bash ../build-reconstruction/full_build_wsl.sh"; exit 2; }

rm -rf "$OUT/$NAME"; mkdir -p "$OUT/$NAME"
cp -r "$SRC"                  "$OUT/$NAME/src"
cp    "$ORIG/license.txt"     "$OUT/$NAME/license.txt"      # MIT, unmodified
cp    "$ORIG/readme.txt"      "$OUT/$NAME/readme.txt"       # unmodified
cp    "$EXE"                  "$OUT/$NAME/bitcoin.exe"

cat > "$OUT/$NAME/RELEASE.txt" <<'TXT'
Bitcoin v0.1.1
==============

The client, the chain and the protocol are unchanged from v0.1.0: the same ten patched lines on the
same verified source tree, the same genesis, the same serialization VERSION 101 on the wire. A node
built from either release speaks to a node built from the other. This is a build-level release.

What changed
------------
v0.1.0's binary was compiled with absolute source paths, so it carried the builder's home directory
in its .rodata -- every assert() and BOOST_ASSERT bakes __FILE__ in as a string literal. Satoshi's
own bitcoin.exe carries none: he compiled `-c $<`, a relative filename, from inside src/, with his
dependencies at short rooted paths. This build reproduces both properties, so the binary quotes its
headers the way his does (/boost/boost/array.hpp) and says nothing about the machine that made it.
full_build_wsl.sh now refuses to link if any build-machine path survives.

v0.1.0 remains published and its signature remains valid. Nothing about the chain is affected by
this; if you are already running v0.1.0 you are on the same network and need not do anything.

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
The chain is at its genesis. Block 1 is unmined and anyone may take it. Blocks cost difficulty-1
work -- about 2^32 hashes -- so the client's own miner takes minutes per block. There is nothing
to buy, nothing to claim, and nothing owed to whoever mines first.

Build
-----
src/ is composed by make_chain.py from two inputs: the v0.1.0 source tree, SHA256
8b17eb9a5707f2519defda4cdf8d14fa1b8dee630e11e6ef85ff9f5547555b56, and bitcoin-v0.1.0.patch --
this chain's genesis, network magic and port, and bootstrap channel. Ten lines, in main.cpp,
net.h and irc.cpp.

The binary is cross-compiled by full_build_wsl.sh against the period libraries (OpenSSL 1.0.2u,
wxWidgets 2.8.12, Berkeley DB 4.8, Boost 1.42), statically linked, so it ships no DLLs.

Consensus rules, script, difficulty, serialization, wallet and UI carry no guardrails: no
MoneyRange, no block-size cap, no script limits. Safe here for one reason only -- there is
nothing to steal.

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
