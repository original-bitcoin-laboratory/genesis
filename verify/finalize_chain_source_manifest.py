"""Finalize schema 2 of the chain source manifest AFTER the key holder has signed its hash.

The key holder runs ONE command and pastes two numbers:

    python verify/prove.py sign <staged sha256> --key <secret.hex>      -> prints r and s

Everything else is mechanical, and mechanical steps done by hand are where signature files get a
layout the verifier cannot parse, or a superseded manifest gets deleted instead of renamed. So:

    python verify/finalize_chain_source_manifest.py --r <hex> --s <hex> --dry-run   # rehearse in a temp copy
    python verify/finalize_chain_source_manifest.py --r <hex> --s <hex>             # do it

ORDER, AND WHY THE ORDER
  0. VERIFY the (r, s) against the STAGED hash and the agent key BEFORE touching any file. A bad
     signature stops here with nothing changed. (The signature is over the ASCII hex of the sha256,
     double-SHA-256'd, RFC 6979 deterministic, low-s -- exactly what prove.py signs and checks.)
  1. Write CHAIN_SOURCE_MANIFEST.json.secp256k1 in the layout prove.py's parser requires:
     "message signed <hex>", "r <hex>", "s <hex>" on their own lines, "public key" split over two
     lines totalling 130 hex characters -- the same layout as the schema-1 file.
  2. RENAME the four schema-1 files under SUPERSEDED-2026-08-12_ ... v1.*  Nothing is deleted: the
     OpenTimestamps proofs are over bytes, not names, and remain valid.
  3. Rename the staged document to CHAIN_SOURCE_MANIFEST.json, beside its new signature.
  4. Re-check: prove.py check must VERIFY; the pinned set must equal what the rule selects; the
     identity must equal net.py and the patch. Any failure after step 2 is reported with the exact
     rename to reverse -- but step 0 makes that path very hard to reach.
Then the remaining human steps are printed: OTS-stamp the two new files, commit (parthod0x, no
trailer), push, rad-sync, and remove the signing note.
"""
import hashlib
import os
import shutil
import sys
import tempfile
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
GEN = HERE.parent
MAN = GEN / "manifests"
sys.path.insert(0, str(HERE))
import prove                                   # noqa: E402
import build_chain_source_manifest as bcsm     # noqa: E402

STAGED = MAN / "CHAIN_SOURCE_MANIFEST.v2-UNSIGNED.json"
LIVE = MAN / "CHAIN_SOURCE_MANIFEST.json"
V1_PREFIX = "SUPERSEDED-2026-08-12_CHAIN_SOURCE_MANIFEST.v1"
V1_SUFFIXES = [".json", ".json.secp256k1", ".json.ots", ".json.secp256k1.ots"]

SIGFILE = """secp256k1 signature by the Bitcoin (2026) genesis key over the SHA-256 of
CHAIN_SOURCE_MANIFEST.json (schema 2).

  message signed   {digest}
                   (the ASCII hex string above, 64 characters -- NOT the raw digest bytes)
  public key       {pub1}
                   {pub2}
  genesis          {genesis}

  r  {r}
  s  {s}

Signing is RFC6979-deterministic, so re-running prove.py with the same challenge reproduces these
exact values. Low-s normalised. The digest convention is Bitcoin's own: double-SHA256 of the ASCII
hex challenge.

  reproduce   python verify/build_chain_source_manifest.py --check
              python verify/prove.py check manifests/CHAIN_SOURCE_MANIFEST.json


WHAT THIS BINDS
---------------

This laboratory measures whether four identities are cryptographically bound -- the whitepaper
author line (W), the source copyright line (L), the chain keys (K) and the OpenPGP key (P). For
Satoshi Nakamoto's 2008-2009 record, every one of the six pairs is unbound: zero of six, measured.
For this project, L <-> K is bound by this file: the key that mined block 0 has signed a manifest of
the source that built block 0.

This is the second signed manifest. The first, schema 1, was signed on 12 August 2026 over
{v1hash}
and is retained beside this file under a SUPERSEDED- prefix with its own signature and timestamps.
It was true when signed. It pinned PROVENANCE.txt -- a note for a reader that the compiler does not
read -- so a prose correction on 12 September left it describing a tree that had moved, and it did
not pin net.py, which holds the chain's identity. The succession is recorded inside the signed
document itself (the "supersedes" field), so it is part of what this signature covers.

Schema 2 pins by two rules, chosen by what a change would mean:

  BY BYTES   src/** and bitcoin-v0.1.0.patch -- {nfiles} files, {ncopy} of which carry
             "Copyright (c) 2009 Satoshi Nakamoto" with the MIT/X11 notice intact. These were
             compiled into the binary that mined block 0. A byte change here is a different program.
  BY VALUE   the chain's identity -- magic {magic}, port {port}, the coinbase headline, the genesis
             hash, time, nonce, bits and public key -- read out of net.py and checked against the
             substitution patch. A changed value is a different chain. A prose edit is nothing.

Build outputs are excluded by class. They are products of the source rather than the source, and
they are not byte-reproducible across toolchains. A root entry that matches no class makes the
builder refuse, so the set is decided by a rule and not by a list.


WHAT IT DOES NOT DO
-------------------

  DOES NOT   claim authorship of Satoshi's 2009 code. The copyright line is retained BECAUSE it is
             his. This signature attests to what the tree contains, not to who wrote it.

  DOES NOT   prove who operates this key, or that any person is any other person. A signature
             binds keys to bytes. It does not bind a key to a person, here or anywhere.

  DOES NOT   assert any right in the name "Bitcoin" or the name "Satoshi Nakamoto", make this
             chain money, or create any claim on the 2009 chain. No premine, no token, no sale,
             no price, no offer.

  DOES NOT   change the source. Re-running the builder on an unchanged tree reproduces the
             manifest byte-for-byte, so this signature stays valid until the program or the chain
             itself changes. When that happens the manifest is rebuilt and re-signed, and this
             signature correctly stops verifying -- which is the point.
"""


def say(msg):
    print("  " + msg)


def finalize(r_hex, s_hex, man_dir: pathlib.Path, dry: bool):
    staged, live = man_dir / STAGED.name, man_dir / LIVE.name
    if not staged.exists():
        raise SystemExit(f"nothing staged at {staged}")
    blob = staged.read_bytes()
    digest = hashlib.sha256(blob).hexdigest()
    doc = __import__("json").loads(blob.decode("utf-8"))
    # This tool finalizes SCHEMA 2 only. A schema-1 document has no chain_identity and no supersedes
    # field; refuse it up front rather than fail half-way through with a KeyError.
    if int(doc.get("schema", 1)) != 2:
        raise SystemExit(f"  ⛔ staged document is schema {doc.get('schema')}, not 2. Nothing was changed.")
    pub = doc["agent_public_key"]
    r, s = int(r_hex, 16), int(s_hex, 16)

    # 0. verify BEFORE touching anything
    say(f"staged sha256   {digest}")
    if not prove.verify(digest, r, s, pub):
        raise SystemExit("  ⛔ (r, s) does NOT verify against the staged hash and the agent key. "
                         "Nothing was changed. Check the hash you signed and the key you used.")
    say("signature       VERIFIES against the staged hash with the agent key")

    # 1. the signature file, in the parseable layout
    ci = doc["chain_identity"]
    sigtext = SIGFILE.format(digest=digest, pub1=pub[:68], pub2=pub[68:], genesis=doc["genesis"],
                             r=f"{r:064x}", s=f"{s:064x}", v1hash=doc["supersedes"]["manifest_sha256"],
                             nfiles=doc["file_count"], ncopy=doc["files_carrying_satoshi_copyright"],
                             magic=ci["magic"], port=ci["port"])
    # prove.py must be able to parse what we are about to write -- prove it on the text first
    tmpsig = man_dir / (LIVE.name + ".secp256k1.PENDING")
    tmpsig.write_text(sigtext, encoding="utf-8", newline="\n")
    msg2, r2, s2, pub2 = prove._from_sigfile(tmpsig)
    assert (msg2, r2, s2, pub2) == (digest, r, s, pub), "the signature file would not parse back to what was signed"
    say("signature file  parses back exactly (message, r, s, pubkey)")

    # 2. retire schema 1 -- rename, never delete
    v1_present = [suf for suf in V1_SUFFIXES if (man_dir / ("CHAIN_SOURCE_MANIFEST" + suf)).exists()]
    for suf in v1_present:
        src, dst = man_dir / ("CHAIN_SOURCE_MANIFEST" + suf), man_dir / (V1_PREFIX + suf)
        if dst.exists():
            raise SystemExit(f"refusing: {dst.name} already exists")
        src.rename(dst)
        say(f"retired         {src.name}  ->  {dst.name}")

    # 3. schema 2 in place
    staged.rename(live)
    tmpsig.rename(man_dir / (LIVE.name + ".secp256k1"))
    say(f"in place        {live.name} + .secp256k1")

    # 4. re-check on the real paths (prove.py + the rule)
    d2 = hashlib.sha256(live.read_bytes()).hexdigest()
    m3, r3, s3, p3 = prove._from_sigfile(man_dir / (LIVE.name + ".secp256k1"))
    ok = (m3 == d2 == digest) and prove.verify(d2, r3, s3, p3)
    say(f"prove.py check  {'VERIFIES' if ok else 'DOES NOT VERIFY'} over {d2[:16]}...")
    if not dry:
        now = set(bcsm.collect(2)); listed = {f["path"] for f in doc["files"]}
        net, patch = bcsm.identity_from_net(), bcsm.identity_from_patch(); bcsm.cross_check(net, patch)
        drift = sorted(k for k in net if ci.get(k) != net[k])
        say(f"rule == pinned  {now == listed} ({len(now)} files)   identity == net.py+patch  {not drift}")
        if not (ok and now == listed and not drift):
            raise SystemExit("  ⛔ post-check failed. Reverse: rename the SUPERSEDED- files back and "
                             "CHAIN_SOURCE_MANIFEST.json back to .v2-UNSIGNED.json; delete the new .secp256k1.")
    return digest


def main(argv):
    r = s = None; dry = False
    i = 0
    while i < len(argv):
        if argv[i] == "--r": r = argv[i + 1]; i += 2
        elif argv[i] == "--s": s = argv[i + 1]; i += 2
        elif argv[i] == "--dry-run": dry = True; i += 1
        else: print(__doc__); return 2
    if not (r and s):
        print(__doc__); return 2
    if dry:
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="finalize_"))
        for p in MAN.iterdir():
            if p.is_file():
                shutil.copy2(p, tmp / p.name)
        print("DRY RUN in a temp copy of manifests/ -- nothing in the repository is touched")
        finalize(r, s, tmp, dry=True)
        print("  resulting files:", sorted(p.name for p in tmp.iterdir()))
        shutil.rmtree(tmp, ignore_errors=True)
        print("DRY RUN OK -- rerun without --dry-run to apply")
        return 0
    digest = finalize(r, s, MAN, dry=False)
    print()
    print("DONE. Remaining human steps:")
    print("  python ../../../_ots_stamp.py manifests/CHAIN_SOURCE_MANIFEST.json manifests/CHAIN_SOURCE_MANIFEST.json.secp256k1")
    print("  git rm manifests/CHAIN_SOURCE_MANIFEST-v2-SIGNING.md   (or rewrite its header to say it is done)")
    print("  git add -A manifests/ && git -c user.name=parthod0x -c user.email=parthms.id@gmail.com commit")
    print("  git push origin main && python ../../../_rad_sync.py")
    print(f"  python ../../../_verify_self_sufficient.py   -> section 6b: four ok lines, no staged note")
    print(f"  signed manifest sha256: {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
