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
- for the constitution series it prints the `message_match` tally with its denominator, the rows
  entered against the rows of `common/conformance/CONSENSUS_SURFACE.md`, so the count is not
  reported without the bound that produced it. The tally counts RULES (one row each); a rule whose
  history has several origin commits carries them in a `commits` cell as `sha:false,sha:true`, and
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
GRADES = {"NOV08-SOURCE", "JAN09-SOURCE", "JAN09-EXECUTED", "MODEL", "DERIVATIVE", "DESCENDANT", "UNRESOLVED", "EXECUTED"}
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

    # the constitution tally, always with its denominator
    c_rows = [r for r in known.values() if r["id"].startswith("OBL-C-")]
    if SURFACE.exists():
        surface_rows = sum(1 for l in SURFACE.read_text(encoding="utf-8").splitlines() if l.startswith("| **"))
        denom = f"{surface_rows} rows of common/conformance/CONSENSUS_SURFACE.md"
    else:
        denom = "surface table not in this checkout"
    mm_false = sum(1 for r in c_rows if any(c.strip("` ").lower() == "false" for c in r["cells"]))
    commit_pairs = [m for r in c_rows for c in r["cells"] for m in re.findall(r"([0-9a-f]{7,40}):(true|false)", c)]
    commit_false = sum(1 for _, v in commit_pairs if v == "false")
    say(f"findings register: {sum(1 for k in known if k.startswith('OBL-F-'))} rows; constitution register: {len(c_rows)} rules entered ({denom}); "
        f"message_match false: {mm_false} of {len(c_rows)} rules, {commit_false} of {len(commit_pairs)} origin commits")
    for n in notes:
        say("note", n)
    for x in failures:
        print("FAIL", x)
    say("register:", "clean" if not failures else f"{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
