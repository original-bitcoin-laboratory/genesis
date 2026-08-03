#!/usr/bin/env python3
"""
make_chain.py -- derive the Bitcoin v0.1.0 (Aug 2026) client from the verified January 2009 tree.

This chain runs the ORIGINAL v0.1.0 code. It is not a reimplementation and not a fork of a later
Bitcoin: it starts from the archive Hal Finney sent mrb (bitcoin-0.1.0.rar, SHA256
8b17eb9a5707f2519defda4cdf8d14fa1b8dee630e11e6ef85ff9f5547555b56 -> zorinaq -> SNI), which this
lab already verified and built (`manifests/EXPECTED_CHECKSUMS.json`, `docs/R2_BUILD_RECONSTRUCTION.md`).

It applies exactly NINE changes, listed below, and refuses to run if any of them fails to match
exactly once -- so it cannot silently drift from the 2009 source.

  the chain          the genesis block is this chain's own: a coinbase carrying The Times of the day
                     it was mined, 50 coins to a key generated and held by its author, mined at the
                     original difficulty-1. Same three fields Satoshi's differed in from any other
                     chain's: message, key, time.
  the network        distinct magic + port, so this network is separate from Bitcoin's and from this
                     lab's NOV08-X / JAN09-X. Running the original's f9beb4d9/8333/#bitcoin would put
                     these nodes into the real network's traffic and peer discovery -- separate magic
                     is what makes a separate network separate, and it is what every distinct network
                     since 2011 has done.

Everything else -- consensus rules, serialization, difficulty, script, the wire protocol, the wallet,
the UI -- is untouched 2009 code.

  python make_chain.py            # write the patch + the patched tree
  python make_chain.py --check    # verify only: source matches, all 9 substitutions locate

Not money. Experimental.
"""
import sys, shutil, hashlib, difflib
from pathlib import Path
try:                                    # Windows console defaults to cp1252
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
SRC  = HERE.parent.parent / "extracted" / "bitcoin" / "src"     # the verified 2009 tree (never written to)
OUT  = HERE / "src"                                              # the derived tree
PATCH= HERE / "bitcoin-v0.1.0.patch"

# ---- this chain's identity ------------------------------------------------------------------
GENESIS_HASH = "00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a"
MERKLE_ROOT  = "aaa5bdfd6c4075a646db9975aab8515781c67fdd73b02df1773a4e1e21a38085"
HEADLINE     = "The Times 03/Aug/2026 Toll of schooling 'straitjacket'"
NTIME        = 1785781375          # 2026-08-03 18:22:55 UTC -- the day the headline was published
NNONCE       = 33394338            # found at real difficulty-1 (nBits 0x1d00ffff), lowest such nonce
# the coinbase output key, byte-reversed: CBigNum parses big-endian and pushes little-endian, so the
# literal below is the pubkey 04c0414c...f834 reversed -- exactly as Satoshi's 04678afd...11d5f appears
# in the original as 5F1DF16B...6704
PUBKEY_CBIGNUM = "34F8A2CE5FD92F8E7E829BA92A219268222F0C3CE59731BAD727852E60A04C79BA5E814A595E045786F9DD45FA1FDC7035A0436EB0438570309800CCFD4C41C004"
MAGIC        = "{ 0xf0, 0x0b, 0xa7, 0x26 }"   # NOV08-X f00ba708, JAN09-X f00ba709, this f00ba726 (2026)
PORT         = 18026
IRC_CHANNEL  = "#bitcoin26"

# ---- the nine changes, as exact (file, old, new) --------------------------------------------
EDITS = [
    ("main.cpp",
     'const uint256 hashGenesisBlock("0x000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f");',
     f'const uint256 hashGenesisBlock("0x{GENESIS_HASH}");'),

    ("main.cpp",
     'char* pszTimestamp = "The Times 03/Jan/2009 Chancellor on brink of second bailout for banks";',
     f'char* pszTimestamp = "{HEADLINE}";'),

    ("main.cpp",
     'CBigNum("0x5F1DF16B2B704C8A578D0BBAF74D385CDE12C11EE50455F3C438EF4C3FBCF649B6DE611FEAE06279A60939E028A8D65C10B73071A6F16719274855FEB0FD8A6704")',
     f'CBigNum("0x{PUBKEY_CBIGNUM}")'),

    ("main.cpp", "block.nTime    = 1231006505;",  f"block.nTime    = {NTIME};"),
    ("main.cpp", "block.nNonce   = 2083236893;",  f"block.nNonce   = {NNONCE};"),

    ("main.cpp",
     'assert(block.hashMerkleRoot == uint256("0x4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b"));',
     f'assert(block.hashMerkleRoot == uint256("0x{MERKLE_ROOT}"));'),

    ("net.h",
     "static const char pchMessageStart[4] = { 0xf9, 0xbe, 0xb4, 0xd9 };",
     f"static const char pchMessageStart[4] = {MAGIC};"),

    ("net.h",
     "static const unsigned short DEFAULT_PORT = htons(8333);",
     f"static const unsigned short DEFAULT_PORT = htons({PORT});"),

    ("irc.cpp",
     'Send(hSocket, "JOIN #bitcoin\\r");\n        Send(hSocket, "WHO #bitcoin\\r");',
     f'Send(hSocket, "JOIN {IRC_CHANNEL}\\r");\n        Send(hSocket, "WHO {IRC_CHANNEL}\\r");'),
]


def sha256(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def main(check_only):
    if not SRC.is_dir():
        sys.exit(f"the verified 2009 tree is missing: {SRC}")

    originals, patched, diffs = {}, {}, []
    for name in sorted({f for f, _, _ in EDITS}):
        originals[name] = (SRC / name).read_text(encoding="utf-8", errors="surrogateescape")
        patched[name] = originals[name]

    for name, old, new in EDITS:
        n = patched[name].count(old)
        if n != 1:
            sys.exit(f"REFUSING: in {name}, expected exactly 1 match, found {n}:\n  {old[:90]}…\n"
                     f"  (is {SRC} the verified bitcoin-0.1.0 tree?)")
        patched[name] = patched[name].replace(old, new)

    print(f"source tree : {SRC}")
    for name in sorted(originals):
        print(f"  {name:10s} sha256 {sha256(SRC / name)}")
    print(f"\nall {len(EDITS)} substitutions located exactly once  ✓")

    for name in sorted(originals):
        d = list(difflib.unified_diff(originals[name].splitlines(keepends=True),
                                      patched[name].splitlines(keepends=True),
                                      fromfile=f"a/src/{name}", tofile=f"b/src/{name}"))
        diffs.extend(d)
        changed = sum(1 for l in d if l.startswith(("+", "-")) and not l.startswith(("+++", "---")))
        print(f"  {name:10s} {changed//2} line(s) changed")

    if check_only:
        print("\n--check: nothing written.")
        return 0

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SRC, OUT)
    for name, text in patched.items():
        (OUT / name).write_text(text, encoding="utf-8", errors="surrogateescape")
    PATCH.write_text("".join(diffs), encoding="utf-8")

    print(f"\nwrote {OUT}  (the derived tree -- build this)")
    print(f"wrote {PATCH.name}  ({len(diffs)} diff lines -- the entire delta from January 2009)")
    print(f"\nchain identity: genesis {GENESIS_HASH}")
    print(f"                magic {MAGIC.strip('{} ').replace('0x','').replace(', ','')}   port {PORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
