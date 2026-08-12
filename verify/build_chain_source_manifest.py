"""Build a deterministic manifest of the SOURCE THAT PRODUCED THIS CHAIN'S GENESIS BLOCK.

WHY THIS EXISTS
---------------
The laboratory measures whether four identities are cryptographically bound -- the whitepaper
author line (W), the source copyright line (L), the chain keys (K) and the OpenPGP key (P). For
Satoshi's 2008-09 record every pair is unbound: zero of six.

Run on ourselves, five of six were bound as of 12 August 2026. The exception was L <-> K, which
sat at "by construction": the source carrying the copyright line is the source that mined our
genesis, but nobody had SIGNED anything to that effect -- exactly the status Satoshi's L <-> K has,
and exactly the kind of administrative-not-cryptographic link this laboratory refuses to count
when somebody else offers it.

This manifest is the object that closes it. The genesis key signs the manifest's SHA-256, so the
key that mined block 0 has signed the source that built block 0.

WHAT IT COVERS, AND WHY EXACTLY THIS SET
----------------------------------------
  src/                 the 34 files of the client, 28 of which still carry
                       "Copyright (c) 2009 Satoshi Nakamoto" and the MIT/X11 notice -- this IS L
  PROVENANCE.txt       the statement of what is Satoshi's, what is Wei Dai's, and what is ours
  bitcoin-v0.1.0.patch the 10 lines that separate this chain from Satoshi's

Build outputs, __pycache__, dist/ and the several build-* trees are DELIBERATELY EXCLUDED: they are
products of the source, not the source, and they are not reproducible byte-for-byte across
toolchains. Including them would make the manifest fail for an honest verifier on a different
machine, which is worse than not covering them.

DETERMINISM
-----------
Files are sorted by path, hashed as raw bytes, and emitted with sorted JSON keys and a fixed
separator. Running this twice on an unchanged tree produces byte-identical output, so the signature
over it remains valid until the source actually changes.
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "derivatives", "bitcoin"))
OUT = os.path.join(os.path.dirname(HERE), "manifests", "CHAIN_SOURCE_MANIFEST.json")

GENESIS = "00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a"
AGENT_PUB = ("04c0414cfdcc009830708543b06e43a03570dc1ffa45ddf98657045e594a815eba7"
             "94ca0602e8527d7ba3197e53c0c2f226892212aa99b827e8e2fd95fcea2f834")
COPYRIGHT = b"Copyright (c) 2009 Satoshi Nakamoto"


def collect():
    entries = []
    # the client source
    src = os.path.join(ROOT, "src")
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames[:] = sorted(d for d in dirnames if d not in ("obj", "__pycache__"))
        for fn in sorted(filenames):
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, ROOT).replace(os.sep, "/")
            entries.append(rel)
    # the two standalone files that carry provenance and the diff
    for extra in ("PROVENANCE.txt", "bitcoin-v0.1.0.patch"):
        p = os.path.join(ROOT, extra)
        if os.path.exists(p):
            entries.append(extra)
    return sorted(set(entries))


def main():
    files, carry = [], 0
    for rel in collect():
        raw = open(os.path.join(ROOT, rel), "rb").read()
        if COPYRIGHT in raw:
            carry += 1
        files.append({
            "path": rel,
            "size": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        })

    doc = {
        "schema": 1,
        "what": ("the source that produced this chain's genesis block, and the copyright line it "
                 "carries"),
        "genesis": GENESIS,
        "agent_public_key": AGENT_PUB,
        "root": "derivatives/bitcoin",
        "file_count": len(files),
        "files_carrying_satoshi_copyright": carry,
        "excluded": ["build outputs", "dist/", "build-*/", "obj/", "__pycache__/"],
        "files": files,
    }
    blob = json.dumps(doc, indent=1, sort_keys=True, separators=(",", ": ")).encode() + b"\n"

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    prior = open(OUT, "rb").read() if os.path.exists(OUT) else None
    with open(OUT, "wb") as fd:
        fd.write(blob)

    h = hashlib.sha256(blob).hexdigest()
    print("files covered                       %d" % len(files))
    print("carrying Satoshi's copyright line   %d" % carry)
    print("manifest bytes                      %d" % len(blob))
    print("manifest sha256                     %s" % h)
    if prior is not None:
        print("unchanged since last build          %s" % (prior == blob))
    print()
    print("To bind L <-> K, sign that sha256 with the genesis key:")
    print('    python prove.py "%s"' % h)
    return 0


if __name__ == "__main__":
    sys.exit(main())
