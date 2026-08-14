#!/usr/bin/env python3
"""Build a signed attestation over the tags that carry no signature of their own. NOT money.

WHY THIS EXISTS
---------------
An audit on 15 Aug 2026 found 10 of 22 tags unsigned across the four laboratory repositories. Three
are **lightweight** tags — a lightweight tag is a bare ref, it has no object to sign, so it cannot
carry a signature at all. Two of those (`Bitcoin-v0.1.2`, `Bitcoin-v0.1.3`) sit *between* signed
releases, which is the awkward part: the series looks continuous and is not.

⛔ THE OBVIOUS FIX IS THE WRONG ONE. Re-creating those tags as signed annotated tags would move what
   16 published releases point at, invalidate every commit SHA quoted in the findings, the papers and
   `PRESERVATION.md`, and break references already in circulation — **and it would still not remove
   the old objects**, which GitHub, Software Heritage, Radicle seeds and every clone already hold.
   ★ That is the identical trade `.mailmap` settles for history rewriting: *pay the full cost of
   breaking things, buy no removal at all.*

⇒ SO ATTEST INSTEAD OF RE-TAGGING. This emits one text file stating, for every unsigned tag, the
  commit and tree it resolves to **right now**. Signed with the same OpenPGP key that signs
  everything else and Bitcoin-anchored, it gives those tags cryptographic backing **without moving
  a single ref**.

  What the attestation proves:  these tag names pointed at these commits, and parthod0x said so at
                                a time provable by the OTS anchor.
  What it does NOT prove:       that they pointed there originally. **A tag could have been moved
                                before this file was written and nothing here would show it.** That
                                limit is printed inside the file itself rather than left implied —
                                an attestation whose weakness is unstated is worse than none.

Run:  python build_tag_attestation.py            # writes TAG-ATTESTATION.txt
      python build_tag_attestation.py --check    # regenerate and diff, fail if it drifted
"""
import io
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
GENESIS = HERE.parent
LAB = GENESIS.parent
WS = LAB.parent.parent
# ⛔ WRITES TO STAGING, NOT TO docs/. An UNSIGNED attestation is a claim by nobody -- publishing
#    one would put a file on bitcoin-lab.org that looks authoritative and proves nothing. The
#    signature is the entire content. The signing key lives ONLY in the cold backup and is
#    deliberately absent from the working keyring, so this step is author-gated by design.
#  ⇒ Sign it, THEN copy it into docs/. `_pending-signature/README.md` carries the exact commands.
OUT = Path(__file__).resolve().parents[4] / "_pending-signature" / "TAG-ATTESTATION.txt"

REPOS = [("genesis", GENESIS),
         ("pre-genesis", LAB / "pre-genesis"),
         ("common", LAB / "common"),
         ("satoshi-onchain", WS / "satoshi-onchain")]


def g(repo, *args):
    r = subprocess.run(["git", "-C", str(repo)] + list(args),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout.strip()


def is_signed(repo, tag):
    if g(repo, "cat-file", "-t", tag) != "tag":
        return False
    return "BEGIN PGP SIGNATURE" in g(repo, "cat-file", "tag", tag)


def build():
    rows = []
    for name, path in REPOS:
        if not (path / ".git").exists():
            print("  skip %s (not a repo here)" % name)
            continue
        for tag in g(path, "tag").split():
            if is_signed(path, tag):
                continue
            kind = "lightweight" if g(path, "cat-file", "-t", tag) == "commit" else "annotated"
            rows.append((name, tag, kind,
                         g(path, "rev-list", "-n1", tag),
                         g(path, "rev-parse", "%s^{tree}" % tag),
                         g(path, "log", "-1", "--format=%cI", tag)))
    L = []
    L.append("ATTESTATION OVER UNSIGNED TAGS")
    L.append("Original Bitcoin Laboratory / satoshi-onchain     NOT money.")
    L.append("")
    L.append("I, parthod0x, holder of OpenPGP key")
    L.append("B128 526A F85A E4A8 F22B  949F B014 5F74 B78C F1DA,")
    L.append("state that at the time this file was signed, the tags listed below resolved to the")
    L.append("commits and trees given beside them.")
    L.append("")
    L.append("WHY THIS FILE EXISTS")
    L.append("  Three of these are LIGHTWEIGHT tags. A lightweight tag is a bare ref with no object,")
    L.append("  so it cannot carry a signature -- not an oversight that can be corrected in place.")
    L.append("  Re-creating them as signed tags would move what 16 published releases point at and")
    L.append("  invalidate commit SHAs already quoted in findings, papers and PRESERVATION.md, while")
    L.append("  removing nothing: GitHub, Software Heritage, Radicle seeds and every clone already")
    L.append("  hold the old objects. So they are attested here instead of being rewritten.")
    L.append("")
    L.append("*** WHAT THIS DOES NOT PROVE -- READ THIS BEFORE RELYING ON IT ***")
    L.append("  It proves these names pointed at these commits WHEN THIS FILE WAS SIGNED, and the")
    L.append("  OpenTimestamps proof beside it fixes that moment in the Bitcoin chain.")
    L.append("  It does NOT prove they pointed there originally. If a tag had been moved before this")
    L.append("  file was written, nothing here would reveal it. This is weaker than a signed tag and")
    L.append("  is not a substitute for one; it is what remains available after the fact.")
    L.append("  Tags signed at creation are listed in the repositories and need none of this.")
    L.append("")
    L.append("HOW TO CHECK A ROW")
    L.append("  git -C <repo> rev-list -n1 <tag>        must equal the commit below")
    L.append("  git -C <repo> rev-parse <tag>^{tree}    must equal the tree below")
    L.append("  gpg --verify TAG-ATTESTATION.txt.asc TAG-ATTESTATION.txt")
    L.append("  python _ots_upgrade.py                  then confirm the .ots is Bitcoin-anchored")
    L.append("")
    L.append("=" * 100)
    L.append("%-16s %-30s %-12s %s" % ("REPOSITORY", "TAG", "KIND", "COMMIT"))
    L.append("%-16s %-30s %-12s %s" % ("", "", "", "TREE"))
    L.append("=" * 100)
    for name, tag, kind, commit, tree, when in rows:
        L.append("%-16s %-30s %-12s %s" % (name, tag, kind, commit))
        L.append("%-16s %-30s %-12s %s   %s" % ("", "", "", tree, when))
    L.append("=" * 100)
    L.append("")
    L.append("%d unsigned tags attested." % len(rows))
    L.append("Tags NOT listed here carry their own OpenPGP signature; verify those with `git tag -v`.")
    body = "\n".join(L) + "\n"
    return body, rows


if __name__ == "__main__":
    body, rows = build()
    if "--check" in sys.argv:
        pub = GENESIS / "docs" / "TAG-ATTESTATION.txt"
        src = pub if pub.exists() else OUT
        cur = src.read_text(encoding="utf-8") if src.exists() else ""
        same = cur == body
        print("  TAG-ATTESTATION.txt %s" % ("matches the repositories" if same else
                                            "DRIFTED -- a tag moved, or a tag was signed since"))
        sys.exit(0 if same else 1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(body, encoding="utf-8", newline="\n")
    print("  wrote %s  (%d unsigned tags)" % (OUT.name, len(rows)))
    for r in rows:
        print("     %-16s %-30s %s" % (r[0], r[1], r[3][:12]))
    print("\n  NEXT: gpg --armor --detach-sign it, stamp it, and mirror to satoshi-onchain/docs/")
