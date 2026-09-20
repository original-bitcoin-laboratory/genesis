#!/usr/bin/env python3
"""Check the findings register and every `OBL-F-` / `OBL-C-` reference across the laboratory.

The register (`FINDINGS-REGISTER.md`) is the index of claims: one row per finding, a stable ID that is
not reused, the evidence grade from `docs/EVIDENCE_POLICY.md`, and the artifact the claim rests on.
This script fails when the register or a reference to it is wrong, so a commit cannot carry a
dangling or renamed ID:

- every ID is well-formed, unique and in ascending order;
- every grade is one the evidence policy defines;
- every artifact path exists (a path may be marked `pending:` while a finding is being written;
  pending rows are reported, not failed);
- every `OBL-F-nnnn` or `OBL-C-nnnn` mentioned in any Markdown file of this repository, and of the
  sibling `common` and `pre-genesis` checkouts when they are present, resolves to a register row;
- every constitution row whose witness cell says `open` is enumerated in each document that
  enumerates the open cells (the register's "What is still open", JAN09-B's §7), and the count
  those documents state matches the rows;
- every anchor height written in prose (`block NNNNNN`) agrees with an OpenTimestamps proof: the
  proof named on the same line, or, when none is named, some proof this repository carries. The
  proofs are read with the standard library (no `opentimestamps` module in CI);
- for the constitution series it prints the `message_match` tally with its denominator, the rows
  entered against the rows of `common/conformance/CONSENSUS_SURFACE.md`, so the count is not
  reported without the bound that produced it. The tally counts RULES (one row each); a rule whose
  history has several origin commits carries them in an origin-commits cell as `sha:date:false`, `sha:date:true`, and
  the script reports commits as a sub-count, so two false values inside one rule's history (the 1 MB
  limit: `a30b56ebe` and `f1e1fb4bd`) count once at the rule level and twice at the commit level.

    python scripts/check_register.py            # exit 0 when clean
    python scripts/check_register.py --quiet    # only failures

NOT money. No network access.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKSPACE = REPO.parent
REGISTER = REPO / "FINDINGS-REGISTER.md"
CONSTITUTION = REPO / "CONSTITUTION-REGISTER.md"          # the OBL-C- series, when it exists
SURFACE = WORKSPACE / "common" / "conformance" / "CONSENSUS_SURFACE.md"
SIBLINGS = ("common", "pre-genesis")
GRADES = {"NOV08-SOURCE", "JAN09-SOURCE", "JAN09-EXECUTED", "MODEL", "DERIVATIVE", "DESCENDANT", "RECORD", "UNRESOLVED", "EXECUTED"}
ID_RE = re.compile(r"\bOBL-([FC])-(\d{4})\b")
ROW_RE = re.compile(r"^\|\s*`(OBL-[FC]-\d{4})`\s*\|(.*)$")
SKIP_DIRS = {".git", "extracted", "artifacts", "target", "node_modules", "__pycache__", ".venv", "r3-evidence", "r4-evidence", "r5-evidence"}


def rows(path: Path) -> list[dict]:
    out = []
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        cells = [c.strip() for c in m.group(2).strip().strip("|").split("|")]
        out.append({"id": m.group(1), "cells": cells, "line": line})
    return out


def resolve(artifact: str) -> tuple[Path | None, str]:
    """Return (path, note). A `pending:` artifact resolves to None with a note. A sibling-repo path
    (`common/...`, `pre-genesis/...`) resolves against the workspace when that checkout is present."""
    art = artifact.strip("` ")
    if art.startswith("pending:"):
        return None, "pending"
    first = art.split("/", 1)[0]
    if first in SIBLINGS:
        root = WORKSPACE / first
        if not root.is_dir():
            return None, f"sibling {first} not checked out"
        return root / art.split("/", 1)[1], ""
    return REPO / art, ""


def markdown_files() -> list[Path]:
    files = []
    for root in [REPO] + [WORKSPACE / s for s in SIBLINGS if (WORKSPACE / s).is_dir()]:
        for p in root.rglob("*.md"):
            if any(part in SKIP_DIRS for part in p.relative_to(root).parts):
                continue
            files.append(p)
    return files


# --- cross-document consistency -----------------------------------------------------------------
# Three assertions added 20 September 2026 after two defects the reference check could not see:
# prose that enumerated the open witness cells disagreed with the rows (three named, five open; then
# five named, four open), and a stated anchor block that disagreed with the proof. Each is a fact
# about two places that must agree, so each is checked in both places.

JAN09B = REPO / "docs" / "JAN09-B-SPECIFICATION.md"
OPEN_SECTIONS = (  # (file, heading that opens the section enumerating the open cells)
    (CONSTITUTION, "## What is still open"),
    (JAN09B, "## 7. What is open"),
)
NUMBER_WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
                "eight": 8, "nine": 9, "ten": 10}
COUNT_RE = re.compile(r"\b(zero|one|two|three|four|five|six|seven|eight|nine|ten|\d+) witness(?:es| cells)\b", re.I)
# Heights attested by proofs that are published but not tracked in this repository: the counter-signing
# key's own proof and the SLH-DSA counter-signatures over release manifests travel as release assets
# (github.com/original-bitcoin-laboratory/genesis/releases) and are kept in the operator's backup. A
# height in prose that only such a proof attests is declared here with its location; anything not
# declared fails closed. This is a list of PLACES a proof lives, not of numbers to wave through.
EXTERNAL_ANCHORS = {
    961803: "release asset: the pq counter-signing public key's proof (docs/PQ-COUNTERSIGN-DESIGNATION.txt names it)",
    961879: "release assets: SHA256SUMS.slhdsa.ots on every release counter-signed on 2026-08-10",
}
HEIGHT_RE = re.compile(r"\bblock\s+(9[5-9]\d{4})\b")   # Bitcoin heights the laboratory has anchored in (950,000+)
TEXT_SUFFIXES = {".md", ".txt", ".html"}

# OpenTimestamps detached proof, read with the standard library: magic, version, file-hash op and
# digest, then an operation tree whose leaves are attestations. Only the Bitcoin attestations'
# heights are wanted here; the tree is walked (forks included) without evaluating the operations.
OTS_MAGIC = bytes([0x00]) + b"OpenTimestamps" + bytes([0x00, 0x00]) + b"Proof" + bytes([0x00]) + bytes([0xbf, 0x89, 0xe2, 0xe8, 0x84, 0xe8, 0x92, 0x94])
OTS_BITCOIN = bytes([0x05, 0x88, 0x96, 0x0d, 0x73, 0xd7, 0x19, 0x01])
OTS_DIGEST_LEN = {0x02: 20, 0x03: 20, 0x08: 32, 0x67: 32}
OTS_OPS_WITH_ARG = {0xf0, 0xf1}
OTS_OPS_PLAIN = {0xf2, 0xf3, 0x02, 0x03, 0x08, 0x67}


def _ots_varuint(b: bytes, i: int) -> tuple[int, int]:
    val, shift = 0, 0
    while True:
        c = b[i]; i += 1
        val |= (c & 0x7f) << shift
        if not c & 0x80:
            return val, i
        shift += 7


def ots_heights(proof: bytes) -> tuple[set[int], int]:
    """(Bitcoin block heights the proof attests, number of pending attestations); ({}, 0) if unreadable.

    The tree is walked as the reference reader does: at a fork (0xff) the first branch is read by a
    recursive call up to its attestation, and the loop continues from where that branch ended, which
    is where the second branch begins. Operations are not evaluated; only the leaves are wanted."""
    heights: set[int] = set()
    pending = [0]
    pos = [0]

    def varuint() -> int:
        val, shift = 0, 0
        while True:
            c = proof[pos[0]]; pos[0] += 1
            val |= (c & 0x7f) << shift
            if not c & 0x80:
                return val
            shift += 7
            if shift > 63:
                raise ValueError("varint longer than any real value")

    def walk(depth: int) -> None:
        if depth > 256:
            raise ValueError("tree deeper than any real proof")
        while True:
            tag = proof[pos[0]]; pos[0] += 1
            if tag == 0x00:                                       # attestation: this branch ends
                kind = proof[pos[0]:pos[0] + 8]; pos[0] += 8
                n = varuint()
                payload = proof[pos[0]:pos[0] + n]; pos[0] += n
                if kind == OTS_BITCOIN:
                    heights.add(_ots_varuint(payload, 0)[0])
                else:
                    pending[0] += 1
                return
            if tag == 0xff:                                       # fork: first branch, then continue
                walk(depth + 1)
                continue
            if tag in OTS_OPS_WITH_ARG:
                n = varuint()                                     # read first: varuint moves pos
                pos[0] += n
                continue
            if tag in OTS_OPS_PLAIN:
                continue
            raise ValueError("unknown operation byte 0x%02x" % tag)

    try:
        if proof[:len(OTS_MAGIC)] != OTS_MAGIC:
            return heights, 0
        pos[0] = len(OTS_MAGIC)
        varuint()
        op = proof[pos[0]]; pos[0] += 1
        pos[0] += OTS_DIGEST_LEN[op]
        walk(0)
    except (IndexError, KeyError, ValueError):
        pass
    return heights, pending[0]


def open_cells(c_rows: list[dict]) -> list[str]:
    """Constitution rows whose witness cell says `open`."""
    return [r["id"] for r in c_rows if any(re.search(r"`open`", c) for c in r["cells"])]


def section_text(path: Path, heading: str) -> str:
    """The text from `heading` to the next heading of the same or higher level, or '' if absent."""
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    i = text.find(heading)
    if i < 0:
        return ""
    level = heading.split(" ")[0]
    rest = text[i + len(heading):]
    m = re.search(r"^#{1,%d} " % len(level), rest, re.M)
    return rest if not m else rest[:m.start()]


def check_open_cells(c_rows: list[dict], failures: list[str], say) -> None:
    opened = open_cells(c_rows)
    for path, heading in OPEN_SECTIONS:
        sec = section_text(path, heading)
        if not sec:
            failures.append(f"{path.name}: section {heading!r} not found; it must enumerate the open witness cells")
            continue
        missing = [rid for rid in opened if rid not in sec]
        if missing:
            failures.append(f"{path.name} {heading!r}: open witness cell(s) not enumerated: {', '.join(missing)}")
        m = COUNT_RE.search(sec)
        if m:
            word = m.group(1).lower()
            n = NUMBER_WORDS.get(word, int(word) if word.isdigit() else -1)
            if n != len(opened):
                failures.append(f"{path.name} {heading!r}: says {m.group(0)!r}, the register has {len(opened)} open witness cell(s)")
    say(f"open witness cells: {len(opened)} ({', '.join(opened) or 'none'}); enumerated in {len(OPEN_SECTIONS)} document(s)")


def check_anchor_heights(failures: list[str], notes: list[str], say) -> None:
    """Every `block NNNNNN` written in prose must agree with a proof: a proof named on the same line,
    or, when none is named, some proof this repository carries."""
    proofs: dict[str, set[int]] = {}
    pending_total = 0
    for p in REPO.rglob("*.ots"):
        if any(part in SKIP_DIRS for part in p.relative_to(REPO).parts):
            continue
        h, pend = ots_heights(p.read_bytes())
        pending_total += pend if not h else 0
        proofs[str(p.relative_to(REPO)).replace("\\", "/")] = h
    all_heights = set().union(*proofs.values()) if proofs else set()
    by_name: dict[str, set[int]] = {}
    for rel, h in proofs.items():
        base = rel.rsplit("/", 1)[-1]
        for key in {base, base[:-4]}:                            # `X.ots` and `X`
            by_name.setdefault(key, set()).update(h)
    checked = 0
    for f in REPO.rglob("*"):
        if f.suffix not in TEXT_SUFFIXES or any(part in SKIP_DIRS for part in f.relative_to(REPO).parts):
            continue
        for ln, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for m in HEIGHT_RE.finditer(line):
                checked += 1
                height = int(m.group(1))
                named = [k for k in by_name if k in line and by_name[k]]
                where = f"{f.relative_to(REPO)}:{ln}"
                if named:
                    ok = any(height in by_name[k] for k in named)
                    if not ok:
                        failures.append(f"{where}: says block {height}; the proof(s) named on that line attest "
                                        + ", ".join(f"{k} -> {sorted(by_name[k])}" for k in named))
                elif height in EXTERNAL_ANCHORS:
                    pass                                          # declared above, with where the proof lives
                elif height not in all_heights:
                    failures.append(f"{where}: says block {height}; no proof in this repository attests that height")
    say(f"anchor heights: {len(proofs)} proof(s) read, {len(all_heights)} distinct Bitcoin heights, "
        f"{checked} height statement(s) in prose checked; {pending_total} proof(s) still pending")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    say = (lambda *x: None) if a.quiet else print
    failures: list[str] = []
    notes: list[str] = []

    if not REGISTER.exists():
        print(f"FAIL missing {REGISTER.name}")
        return 1
    known: dict[str, dict] = {}
    for series, path in (("F", REGISTER), ("C", CONSTITUTION)):
        last = 0
        for r in rows(path):
            rid = r["id"]
            if not rid.startswith(f"OBL-{series}-"):
                failures.append(f"{path.name}: row {rid} belongs to another series")
                continue
            n = int(rid[-4:])
            if rid in known:
                failures.append(f"{path.name}: duplicate id {rid}")
            if n <= last:
                failures.append(f"{path.name}: {rid} is not in ascending order")
            last = n
            known[rid] = r
            if series == "F":
                if len(r["cells"]) < 4:
                    failures.append(f"{path.name}: {rid} has {len(r['cells'])} cells, expected claim | grade | artifact | recorded")
                    continue
                claim, grade, artifact = r["cells"][0], r["cells"][1].strip("` "), r["cells"][2]
                if not claim:
                    failures.append(f"{rid}: empty claim")
                for g in re.split(r"\s*\+\s*", grade):
                    if g.split(" ")[0] not in GRADES:
                        failures.append(f"{rid}: grade {g!r} is not in docs/EVIDENCE_POLICY.md")
                p, note = resolve(artifact)
                if note == "pending":
                    notes.append(f"{rid}: artifact pending ({artifact.strip('` ')})")
                elif note:
                    notes.append(f"{rid}: {note}; artifact not checked")
                elif p is not None and not p.exists():
                    failures.append(f"{rid}: artifact does not exist: {artifact}")

    # every reference in prose resolves
    for f in markdown_files():
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in ID_RE.finditer(text):
            rid = f"OBL-{m.group(1)}-{m.group(2)}"
            if rid not in known:
                where = f.relative_to(WORKSPACE) if WORKSPACE in f.parents else f
                failures.append(f"dangling reference {rid} in {where}")


    # cross-document consistency: open cells enumerated where prose enumerates them, with the right
    # count; anchor heights written in prose agree with the proofs
    c_rows_all = [r for r in known.values() if r["id"].startswith("OBL-C-")]
    check_open_cells(c_rows_all, failures, say)
    check_anchor_heights(failures, notes, say)

    # the constitution tally, always with its denominator
    c_rows = [r for r in known.values() if r["id"].startswith("OBL-C-")]
    if SURFACE.exists():
        surface_rows = sum(1 for l in SURFACE.read_text(encoding="utf-8").splitlines() if l.startswith("| **"))
        denom = f"{surface_rows} rows of common/conformance/CONSENSUS_SURFACE.md"
    else:
        denom = "surface table not in this checkout"
    mm_false = sum(1 for r in c_rows if any(c.strip("` ").lower() == "false" for c in r["cells"]))
    commit_pairs = [m for r in c_rows for c in r["cells"] for m in re.findall(r"([0-9a-f]{7,40}):(?:\d{4}-\d{2}-\d{2}:)?(true|false)", c)]
    # one commit can introduce two rules (f1e1fb4bd: the block-size rule and the sigop limit); count each sha once
    by_sha: dict[str, str] = {}
    for sha, v in commit_pairs:
        by_sha[sha] = "false" if by_sha.get(sha) == "false" or v == "false" else v
    commit_false = sum(1 for v in by_sha.values() if v == "false")
    say(f"findings register: {sum(1 for k in known if k.startswith('OBL-F-'))} rows; constitution register: {len(c_rows)} rules entered ({denom}); "
        f"message_match false: {mm_false} of {len(c_rows)} rules, {commit_false} of {len(by_sha)} distinct origin commits")
    for n in notes:
        say("note", n)
    for x in failures:
        print("FAIL", x)
    say("register:", "clean" if not failures else f"{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
