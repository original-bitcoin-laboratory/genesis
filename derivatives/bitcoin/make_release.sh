#!/usr/bin/env bash
# make_release.sh -- assemble bitcoin-0.1.3.tar.gz: the client binary, license.txt, readme.txt,
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
# NAME is overridable for the same reason EXE is: cutting v0.1.4 must not require editing this
# script, and a hardcoded version is how a release quietly ships under the previous name.
NAME="${NAME:-bitcoin-0.1.3}"

[ -d "$SRC" ]  || { echo "!! run: python make_chain.py"; exit 2; }
[ -f "$EXE" ]  || { echo "!! build first: SRC=$SRC bash ../build-reconstruction/full_build_wsl.sh"; exit 2; }

rm -rf "$OUT/$NAME"; mkdir -p "$OUT/$NAME"
cp -r "$SRC"                  "$OUT/$NAME/src"
cp    "$ORIG/license.txt"     "$OUT/$NAME/license.txt"      # MIT, unmodified
cp    "$ORIG/readme.txt"      "$OUT/$NAME/readme.txt"       # unmodified
cp    "$EXE"                  "$OUT/$NAME/bitcoin.exe"

if [ -n "${RELEASE_NOTES:-}" ] && [ -f "$RELEASE_NOTES" ]; then
  cp "$RELEASE_NOTES" "$OUT/$NAME/RELEASE.txt"
else
cat > "$OUT/$NAME/RELEASE.txt" <<'TXT'
Bitcoin v0.1.3
==============

The client, the chain and the protocol are unchanged from v0.1.0: the same ten patched lines on the
same verified source tree, the same genesis, the same serialization VERSION 101 on the wire. A node
built from any of the four releases speaks to a node built from any other. This is a build-level
release, the third one.

What changed
------------
The binary is reproducible. You can rebuild it and get the same bytes.

  bitcoin.exe  c3f15fc5b7bd80f4d08fe5ff356256214734eb1a3e4a7c953c9e8fc8453d2c7d

Until now the signature on a release said only that we built something. It now says something a
stranger can check: build it yourself from the published 2009 archive, and if your bytes hash to
that, the signed file is the file you just made. A GitHub-hosted runner does exactly this on every
change to the build inputs and fails if the hash moves --
.github/workflows/reproducible.yml, which starts by fetching bitcoin-0.1.0.tgz over the network
rather than trusting anything in the repository.

It took two flags, both found by building twice and comparing, which nobody had done before.

  * -Wl,--no-insert-timestamp. Two builds of identical inputs on one machine differed in 4 bytes of
    15,529,604: two in the PE TimeDateStamp at 0x88, two in the CheckSum at 0xd8 that derives from
    it. ld writes the build clock into the header.

  * SOURCE_DATE_EPOCH. With the timestamp fixed, a second machine with an identical toolchain still
    differed in 8 bytes. Six were in .rodata and every one was an ASCII digit -- wxWidgets stamping
    its own build clock through wxGetLibraryVersionInfo. gcc honours SOURCE_DATE_EPOCH for __DATE__
    and __TIME__, and the build pins it to 1785781375: 2026-08-03 18:22:55 UTC, this chain's own
    genesis. The string inside the binary reads "Aug  3 2026" / "18:22:55".

Not one instruction ever differed. Not a symbol, not a section, not an offset, not a byte of any of
the four statically linked period libraries. Two machines hours apart emitted identical machine code
and disagreed only about what time it was.

What this does not buy
----------------------
Freedom from the toolchain. The bytes above are reproducible with gcc 13.2.0 using the *win32*
thread model, binutils 2.41.90, mingw-w64 11.0.1, on Ubuntu 24.04. A different compiler emits
different code. Ubuntu ships a posix thread variant alongside the win32 one; they are not
interchangeable and do not produce the same binary. The CI job sets the alternative explicitly and
prints the full package set on every run, so a mismatch is diagnosable rather than mysterious.

This is what reproducible building means everywhere. Bitcoin Core pins its toolchain with Guix for
the same reason.

To rebuild it yourself
----------------------
  git clone https://github.com/original-bitcoin-laboratory/genesis && cd genesis
  bash scripts/fetch-artifacts.sh          # bitcoin-0.1.0.tgz, from the Nakamoto Institute
  tar xzf artifacts/jan09/bitcoin-0.1.0.tgz -C extracted
  python3 derivatives/bitcoin/make_chain.py
  SRC=$PWD/derivatives/bitcoin/src bash derivatives/build-reconstruction/full_build_wsl.sh
  sha256sum derivatives/bitcoin/build/bitcoin-0.1.0-reconstructed.exe

make_chain.py refuses unless each of the ten edits matches exactly once, so that step re-verifies
the extracted tree as a side effect. Full working: docs/BUILD_NOTES.md.

v0.1.0, v0.1.1 and v0.1.2 remain published and their signatures remain valid. Nothing about the
chain is affected: consensus, the wire format and the genesis are untouched, and block 1 was mined
and relayed by the v0.1.1 binary.

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

That is what the client does, and it is left alone for the same reason everything else is:
changing it would make this a different program. But 2009's Freenode is not 2026's, and you should
decide knowingly. ThreadIRCSeed starts unconditionally from net.cpp -- v0.1.0 has no -noirc switch,
so the only lever is the client's own /proxy option, which leaves addrLocalHost unroutable and makes
it fall back to a random nickname. Everything else in the client is equally period-accurate: no
encryption, no authentication, and a wallet.dat written in the clear.

NOT MONEY. No premine of value, no token, no sale, no market. Experimental research artifact.
Run the client only in an isolated VM: it is a live node.
TXT
fi

cd "$OUT"
tar --format=ustar -czf "$NAME.tar.gz" "$NAME"
sha256sum "$NAME.tar.gz" > "$NAME.tar.gz.sha256"

echo "built $OUT/$NAME.tar.gz"
echo "  $(cat "$NAME.tar.gz.sha256")"
echo "  contents:"
tar -tzf "$NAME.tar.gz" | sed -n '1,8p;$!d' | sed 's/^/    /'   # sed, not head: head exits early and SIGPIPEs under pipefail
echo "    ... $(tar -tzf "$NAME.tar.gz" | wc -l) entries"
