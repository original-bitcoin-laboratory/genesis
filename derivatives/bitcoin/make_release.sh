#!/usr/bin/env bash
# make_release.sh -- assemble bitcoin-0.1.0.tar.gz: the client binary, license.txt, readme.txt,
# src/, and RELEASE.txt. The binary is statically linked, so it ships no DLLs.
#
# Run:  bash make_release.sh          (after make_chain.py and the build)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORIG="$HERE/../../extracted/bitcoin"          # the verified source tree (for license.txt / readme.txt)
SRC="$HERE/src"                                # derived tree from make_chain.py
EXE="$HERE/build/bitcoin-0.1.0-reconstructed.exe"
OUT="$HERE/dist"
NAME="bitcoin-0.1.0"

[ -d "$SRC" ]  || { echo "!! run: python make_chain.py"; exit 2; }
[ -f "$EXE" ]  || { echo "!! build first: SRC=$SRC bash ../build-reconstruction/full_build_wsl.sh"; exit 2; }

rm -rf "$OUT/$NAME"; mkdir -p "$OUT/$NAME"
cp -r "$SRC"                  "$OUT/$NAME/src"
cp    "$ORIG/license.txt"     "$OUT/$NAME/license.txt"      # MIT, unmodified
cp    "$ORIG/readme.txt"      "$OUT/$NAME/readme.txt"       # unmodified
cp    "$EXE"                  "$OUT/$NAME/bitcoin.exe"

cat > "$OUT/$NAME/RELEASE.txt" <<'TXT'
Bitcoin v0.1.0
==============

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

Consensus rules, script, difficulty, serialization, wallet and UI carry no guardrails: no
MoneyRange, no block-size cap, no script limits. Safe here for one reason only -- there is
nothing to steal.

Verify
------
  python make_chain.py --check     # src/ is those two inputs and nothing else
  python net.py                    # re-derives the genesis hash; checks it meets difficulty-1

The client asserts the genesis hash on startup, so a wrong build does not run.

readme.txt and license.txt are the source tree's own, unmodified.

NOT MONEY. No premine of value, no token, no sale, no market. Experimental research artifact.
Run the client only in an isolated VM: it is a live node.
TXT

cd "$OUT"
tar --format=ustar -czf "$NAME.tar.gz" "$NAME"
sha256sum "$NAME.tar.gz" > "$NAME.tar.gz.sha256"

echo "built $OUT/$NAME.tar.gz"
echo "  $(cat "$NAME.tar.gz.sha256")"
echo "  contents:"
tar -tzf "$NAME.tar.gz" | head -8 | sed 's/^/    /'
echo "    ... $(tar -tzf "$NAME.tar.gz" | wc -l) entries"
