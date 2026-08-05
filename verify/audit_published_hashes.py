"""Stress test: every SHA-256 published in our documents, checked against the real artifact.

Written after finding an INCORRECT hash for the canonical whitepaper published in four documents,
two of them public. A project whose entire premise is machine-verifiable hashes cannot publish a
hash nobody checks. This makes that class of defect impossible to leave standing.

What it does:
  1. scans .md / .html for 64-hex strings
  2. for each, looks for a local file whose sha256 matches -> CONFIRMED
  3. for hashes with no matching local artifact, reports them as UNVERIFIED-HERE so they can be
     eyeballed rather than silently trusted
  4. flags NEAR-MISSES: a published hash sharing a long prefix with a real artifact's hash is
     almost certainly a typo or a stale paste, which is exactly the failure that occurred

Usage:  python audit_published_hashes.py <doc-dir> [<doc-dir> ...] --artifacts <dir> [<dir> ...]
Exit code 1 if any near-miss is found.
"""

# KNOWN LOOK-ALIKE (added 2026-08-06). A 2024 re-save of the 3 October 2008 draft circulates on
# GitHub (2ndEntropy/BitcoinWP-Steganalysis) under a 2008 filename. It keeps the original
# /CreationDate, so it reads as a 2008 file, but carries /ModDate D:20240330175340+10'00' and an
# unequal /ID pair. Publishing its hash as "the October 2008 draft" would be wrong.
#     188,867 bytes  sha256 f5aa8f4b8ea559d4e37052ee6c5b398bc9e1fff86f99ad1d9e3e0a6f64b63c96
#     the genuine draft: 183,697 bytes  sha256 427c63b364c6db914cf23072a09ffd53ee078397b7c6ab2d604e12865a982faa

import hashlib, os, re, sys

sys.stdout.reconfigure(encoding="utf-8")

HEX64 = re.compile(r"\b([0-9a-f]{64})\b")
DOCEXT = (".md", ".html", ".txt")
SKIP_DIRS = {".git", "node_modules", "__pycache__", "OBL-BACKUP"}

argv = sys.argv[1:]
if "--artifacts" in argv:
    i = argv.index("--artifacts")
    doc_dirs, art_dirs = argv[:i], argv[i + 1:]
else:
    doc_dirs, art_dirs = argv, argv
if not doc_dirs:
    print(__doc__); sys.exit(2)


def walk(dirs, exts=None):
    for d in dirs:
        for root, subs, files in os.walk(d):
            subs[:] = [s for s in subs if s not in SKIP_DIRS]
            for f in files:
                if exts is None or f.lower().endswith(exts):
                    yield os.path.join(root, f)


# --- every hash we actually have an artifact for -------------------------------------------------
real = {}
for p in walk(art_dirs):
    try:
        if os.path.getsize(p) > 80_000_000:
            continue
        real.setdefault(hashlib.sha256(open(p, "rb").read()).hexdigest(), []).append(p)
    except Exception:
        pass
print(f"  hashed {len(real):,} distinct artifacts")

# --- every hash we publish ------------------------------------------------------------------------
published = {}
for p in walk(doc_dirs, DOCEXT):
    try:
        for h in set(HEX64.findall(open(p, encoding="utf-8", errors="replace").read())):
            published.setdefault(h, []).append(p)
    except Exception:
        pass
print(f"  found  {len(published):,} distinct 64-hex strings in documents\n")

confirmed = [h for h in published if h in real]
unknown = [h for h in published if h not in real]
print(f"  CONFIRMED against a local artifact : {len(confirmed)}")
print(f"  no local artifact to check against : {len(unknown)}")

# --- near-misses: shares a long prefix with a real hash but is not equal ---------------------------
near = []
for h in unknown:
    for r in real:
        n = len(os.path.commonprefix([h, r]))
        if n >= 8:
            near.append((n, h, r, published[h], real[r]))
near.sort(reverse=True)

if near:
    print(f"\n  *** {len(near)} NEAR-MISS(ES) -- a published hash that ALMOST matches a real artifact.")
    print("      This is what a typo or a stale paste looks like. Check each one.\n")
    for n, h, r, docs, arts in near:
        print(f"      shared prefix {n} chars")
        print(f"        published : {h}")
        print(f"        actual    : {r}   <- {os.path.basename(arts[0])}")
        for d in docs:
            print(f"        in        : {d}")
        print()
else:
    print("\n  no near-misses -- no published hash resembles a real artifact without matching it")

sys.exit(1 if near else 0)
