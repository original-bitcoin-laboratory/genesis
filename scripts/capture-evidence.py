#!/usr/bin/env python3
"""Hash captured R3 VM artifacts into a committed manifest + findings skeleton.

Raw captured bytes (debug.log, blk*.dat, blkindex.dat, wallet.dat, screenshots)
live under `r3-evidence/<run>/` (gitignored — bytes never committed). This walks
that folder, records SHA-256 for every file, and writes:

    r3-findings/<run>/EVIDENCE_MANIFEST.json   (committed)
    r3-findings/<run>/SHA256SUMS               (committed)
    r3-findings/<run>/FINDINGS.md              (skeleton, from the template)

so JAN09-EXECUTED results re-enter the repo with the same provenance discipline as
the rest of the lab: hashes and written findings, not bytes.

Usage:
    python scripts/capture-evidence.py --run 2026-07-26-run1
    python scripts/capture-evidence.py --run <label> --evidence-dir <dir> --findings-dir <dir>
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # genesis/
CHUNK = 1024 * 1024


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while block := f.read(CHUNK):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="run label, e.g. 2026-07-26-run1")
    ap.add_argument("--evidence-dir", type=Path, default=ROOT / "r3-evidence")
    ap.add_argument("--findings-dir", type=Path, default=ROOT / "r3-findings")
    args = ap.parse_args()

    src = args.evidence_dir / args.run
    if not src.is_dir():
        raise SystemExit(f"error: {src} not found — drop the captured VM artifacts there first")

    entries = []
    for p in sorted(x for x in src.rglob("*") if x.is_file()):
        entries.append({
            "path": p.relative_to(src).as_posix(),
            "size": p.stat().st_size,
            "sha256": sha256(p),
        })

    out = args.findings_dir / args.run
    out.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": 1,
        "evidence_level": "JAN09-EXECUTED",
        "run": args.run,
        "generated": datetime.date.today().isoformat(),
        "evidence_dir": f"r3-evidence/{args.run} (gitignored)",
        "file_count": len(entries),
        "files": entries,
    }
    (out / "EVIDENCE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (out / "SHA256SUMS").write_text(
        "".join(f"{e['sha256']}  {e['path']}\n" for e in entries), encoding="utf-8")

    findings = out / "FINDINGS.md"
    tmpl = ROOT / "docs" / "R3_EVIDENCE_TEMPLATE.md"
    if not findings.exists() and tmpl.exists():
        findings.write_text(tmpl.read_text(encoding="utf-8").replace("<RUN>", args.run), encoding="utf-8")

    # relative_to(ROOT) raises when --findings-dir is given as a relative path (e.g. "r4-findings"),
    # which is how the R4 runs invoke this. Fall back to the path as given rather than crashing
    # AFTER the manifest has already been written — the files are fine; only the report was not.
    try:
        _shown = out.relative_to(ROOT)
    except ValueError:
        _shown = out
    print(f"wrote {_shown}/EVIDENCE_MANIFEST.json ({len(entries)} files)")
    if not entries:
        print("  (no files found — nothing captured yet)")
    for e in entries:
        print(f"  {e['sha256'][:16]}…  {e['path']}  ({e['size']} B)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
