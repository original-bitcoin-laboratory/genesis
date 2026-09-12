#!/usr/bin/env python3
"""Grade a replay: results.json against the corpus, and optionally the guest's debug.log against the
exact main.cpp strings each rejected case should have produced.

    python grade_replay.py results/<run>/results.json [--log nodeA/debug.log ...] [--json out.json]

Prints, per suite, how many vectors the binary agreed with, lists every disagreement, and for the
checksig vectors whose binary column was pending prints the values the binary gave — the numbers a
later export can freeze into checksig.json as expected_binary. Exit code 0 iff no disagreement.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
CORPUS = HERE.parent


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("results")
    ap.add_argument("--log", action="append", default=[])
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    res = json.loads(pathlib.Path(a.results).read_text())["results"]
    logs = "\n".join(pathlib.Path(p).read_text(encoding="utf-8", errors="replace") for p in a.log)
    report = {"suites": {}, "disagreements": [], "pending_binary_values": {}, "log_checks": []}

    for suite in ("evalscript", "checksig", "blocks"):
        rows = res.get(suite, {})
        graded = {k: v for k, v in rows.items() if v.get("agree") is not None}
        agree = sum(1 for v in graded.values() if v["agree"])
        report["suites"][suite] = {"run": len(rows), "graded": len(graded), "agree": agree}
        for k, v in graded.items():
            if not v["agree"]:
                report["disagreements"].append({"suite": suite, "label": k, "observed": v})
        if suite == "checksig":
            for k, v in rows.items():
                if v.get("expected_binary") is None:
                    report["pending_binary_values"][k] = v["accepted"]

    if logs:
        blocks = json.loads((CORPUS / "blocks.json").read_text(encoding="ascii"))["vectors"]
        expect = {v["label"]: v for v in blocks}
        for k, v in res.get("blocks", {}).items():
            e = expect[k]
            for needle in [e["reason"]] + ([e["inner"]] if "inner" in e else []):
                if e["expect"] == "accept":
                    continue
                found = needle in logs
                report["log_checks"].append({"label": k, "needle": needle, "found": found})

    for suite, s in report["suites"].items():
        print(f"{suite:12s} run {s['run']:4d}  graded {s['graded']:4d}  agree {s['agree']:4d}")
    for d in report["disagreements"]:
        print(f"  DISAGREE {d['suite']}/{d['label']}: {json.dumps(d['observed'])[:200]}")
    if report["pending_binary_values"]:
        print("binary verdicts recorded for pending checksig vectors:")
        for k, v in report["pending_binary_values"].items():
            print(f"  {k:30s} {v}")
    if report["log_checks"]:
        miss = [c for c in report["log_checks"] if not c["found"]]
        print(f"debug.log: {len(report['log_checks']) - len(miss)}/{len(report['log_checks'])} expected error strings found")
        for c in miss:
            print(f"  MISSING {c['label']}: {c['needle']}")
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(report, indent=1, sort_keys=True))
    return 1 if report["disagreements"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
