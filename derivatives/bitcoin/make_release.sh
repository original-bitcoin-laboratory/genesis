#!/usr/bin/env bash
# make_release.sh -- assemble bitcoin-0.1.0.tar.gz, mirroring the January 2009 release archive.
#
# The original was distributed as bitcoin-0.1.0.rar / bitcoin-0.1.0.tgz (same source tree): the client
# binary, its runtime DLLs, license.txt, readme.txt, and src/. This mirrors that layout so the release
# is recognisably the same kind of artifact -- with two honest differences noted in RELEASE.txt:
#
#   * no DLLs. The original shipped libeay32.dll + mingwm10.dll alongside bitcoin.exe; this build is
#     statically linked, so the binary is self-contained. Fewer files, same code.
#   * src/ is the derived tree (bitcoin-v0.1.0.patch applied), not the 2009 tree verbatim.
#
# Run:  bash make_release.sh          (after make_chain.py and the period build)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORIG="$HERE/../../extracted/bitcoin"          # the verified 2009 archive (for license.txt / readme.txt)
SRC="$HERE/src"                                # derived tree from make_chain.py
EXE="$HERE/build/bitcoin-0.1.0-reconstructed.exe"
OUT="$HERE/dist"
NAME="bitcoin-0.1.0"

[ -d "$SRC" ]  || { echo "!! run: python make_chain.py"; exit 2; }
[ -f "$EXE" ]  || { echo "!! build first: SRC=$SRC bash ../build-reconstruction/full_build_wsl.sh"; exit 2; }

rm -rf "$OUT/$NAME"; mkdir -p "$OUT/$NAME"
cp -r "$SRC"                  "$OUT/$NAME/src"
cp    "$ORIG/license.txt"     "$OUT/$NAME/license.txt"      # MIT, unchanged from 2009
cp    "$ORIG/readme.txt"      "$OUT/$NAME/readme.txt"       # Satoshi's, unchanged from 2009
cp    "$EXE"                  "$OUT/$NAME/bitcoin.exe"      # named as the original shipped it

cat > "$OUT/$NAME/RELEASE.txt" <<'TXT'
Bitcoin v0.1.0 (August 2026)
============================

This is the January 2009 Bitcoin client -- Satoshi Nakamoto's released v0.1.0 source, built with
period libraries -- running a new chain. readme.txt and license.txt are his, unchanged.

Genesis
-------
  hash      00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a
  coinbase  The Times 03/Aug/2026 Toll of schooling 'straitjacket'
  output    50.00000000 -> P2PK 04c0414c...  (no value assigned)
  nTime     1785781375 = 2026-08-03 18:22:55 UTC
  nBits     0x1d00ffff   (the original difficulty-1)
  nNonce    33394338

Network
-------
  magic     f00ba726          port 18026
  seed      bitcoin.bitcoin-lab.org:18026

The chain at this release
-------------------------
One block: the genesis. Nobody has mined block 1 yet, and anyone may -- that is what this
release is for. Satoshi's genesis was timestamped 3 January 2009 and block 1 was not mined
until the 9th; for six days his chain was exactly this. A release is of the software and its
genesis; the chain is what people who run it make of it.

Point a node at the seed above and mine, and you are as much a part of this chain's history
as anyone. There is nothing to buy, nothing to claim, and nothing owed to whoever mined first.

What differs from January 2009
------------------------------
Ten lines, in src/ -- see bitcoin-v0.1.0.patch in the repository:

  main.cpp (6)  the genesis: headline, output key, nTime, nNonce, merkle assert, genesis hash
  net.h    (2)  network magic, default port
  irc.cpp  (2)  bootstrap channel

The coinbase headline is the front page of the day this genesis was mined, not a copy of his --
his headline was a proof of time, and only a current one performs that function. The output key is
the author's, because a chain whose genesis key you do not hold is not yours. The magic and port
differ because running f9beb4d9/8333 would put these nodes into the real Bitcoin network's traffic.

Consensus rules, script, difficulty, serialization, wallet and UI are untouched 2009 code, including
the origin's absent guardrails (no MoneyRange, no size cap, unbounded script arithmetic). Those are
safe here for one reason only: there is nothing to steal.

Verify
------
  python make_chain.py --check     # proves src/ is the 2009 tree plus exactly nine substitutions
  python net.py                    # re-derives the genesis hash and checks it meets difficulty-1

NOT MONEY. No premine of value, no token, no sale, no market. Experimental research artifact.
Run the client only in an isolated VM: it is a live 2009 node.
TXT

cd "$OUT"
tar --format=ustar -czf "$NAME.tar.gz" "$NAME"
sha256sum "$NAME.tar.gz" > "$NAME.tar.gz.sha256"

echo "built $OUT/$NAME.tar.gz"
echo "  $(cat "$NAME.tar.gz.sha256")"
echo "  contents:"
tar -tzf "$NAME.tar.gz" | head -8 | sed 's/^/    /'
echo "    ... $(tar -tzf "$NAME.tar.gz" | wc -l) entries"
