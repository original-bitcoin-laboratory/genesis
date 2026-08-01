#!/usr/bin/env python3
"""One-command reproducer for the JAN09 edition's executable layer.

Runs every headless derivatives test suite, and regenerates the two derived
artifacts (the neutral descendant matrix and the NOV08-X differential) to prove they
reproduce from source. Python only by default — no build step. Pass --rust to also run
the Rust node's `cargo test` suite, and/or --cpp to run the C++/OpenSSL port differentials.

    python scripts/reproduce.py          # all Python suites + regenerate artifacts
    python scripts/reproduce.py --rust   # + the Rust node suite (needs cargo)
    python scripts/reproduce.py --cpp    # + the C++ port differentials (needs MSYS2 g++)

Exit code 0 iff everything passed.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent            # genesis/
DERIV = ROOT / "derivatives"

# (label, working dir) — one pytest run per suite (each has its own local imports)
SUITES = [
    ("profiles   (rule postures declared == inventory == live engine)", DERIV / "profiles"),
    ("model      (script engine, sighash, checksig, instruments)", DERIV / "model"),
    ("p2p        (wire relay + chain sync)",                        DERIV / "p2p"),
    ("wallet     (SelectCoins / CreateTransaction)",               DERIV / "wallet"),
    ("persist    (CDiskBlockIndex save/reload)",                    DERIV / "persist"),
    ("conformance(6-chain matrix, every column execution-checked)", DERIV / "conformance"),
    ("crypto     (v0.1 ECDSA vs real libsecp256k1 — Thread A)",     DERIV / "crypto_conformance"),
    ("overflow   (v0.1 CheckTransaction vs the Aug-2010 MoneyRange fix)", DERIV / "overflow"),
    ("script_lim (v0.1 EvalScript has no element/op/stack ceilings)", DERIV / "script_limits"),
    ("retarget   (v0.1 GetNextWorkRequired fencepost + timewarp boundary)", DERIV / "retarget"),
    ("temporal   (median-time-past, block timestamps, tx finality)", DERIV / "temporal"),
    ("tracker    (origin-distance of each claimant over time)",      DERIV / "tracker"),
    ("nov08x     (NOV08 counterfactual + live network)",           DERIV / "nov08x"),
    ("jan09x     (released chain, full vocab + live network)",     DERIV / "jan09x"),
    ("ledger     (UTXO ConnectInputs/ConnectBlock; transacting)",   DERIV / "ledger"),
    ("market     (R6 commerce model: signatures + atoms reputation)", DERIV / "market"),
    ("studio     (R7 script debugger / stack tracer)",              DERIV / "studio"),
    ("console    (R7 capstone: full-stack driver on both X-chains)", DERIV / "console"),
    ("netnode    (Path B: hardened joinable node — TCP sync, checksums, persistence)", DERIV / "netnode"),
    ("dnsseed    (bootstrap DNS seed: crawl reachable nodes, answer A queries)",       DERIV / "dnsseed"),
]

# (label, script, dir) — regenerate a committed artifact and confirm it still runs
ARTIFACTS = [
    ("descendant matrix  -> MATRIX.md / conformance.json", "conformance.py", DERIV / "conformance"),
    ("NOV08-X differential-> DIFFERENTIAL.md / PROVENANCE.json", "differential.py", DERIV / "nov08x"),
    ("eternal recipe -> both genesis blocks re-derive from source", "verify_genesis.py", ROOT / "scripts"),
]

CPP = [  # optional: C++/OpenSSL port differentials (bash run scripts)
    ("port  differential (MODEL == PORT interpreter)", DERIV / "port" / "run.sh"),
    ("node  ports (genesis + chain connect)",          DERIV / "node" / "run.sh"),
]

# `--core`: the consensus / script / value / ledger reconstruction core only. Excludes the neutral
# descendant tracker + conformance matrix (a separate comparison study), the UI tools, and the
# bootstrap seed — none of which are part of the reconstruction's own fidelity claims.
CORE_EXCLUDE_SUITES = {"conformance", "tracker", "console", "studio", "dnsseed"}
CORE_EXCLUDE_ARTIFACTS = {"conformance.py"}


def _manifest(steps, args, path) -> None:
    import datetime
    import json
    import platform
    ok_git, commit = run(["git", "rev-parse", "HEAD"], ROOT)
    doc = {
        "schema": 1,
        "generated": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "commit": commit if ok_git else None,
        "core_only": args.core,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "backends": {"rust": args.rust, "cpp": args.cpp},
        "steps": [{"step": lbl.split("(")[0].strip(), "passed": ok} for lbl, ok in steps],
        "passed": sum(1 for _, ok in steps if ok),
        "total": len(steps),
        "all_passed": all(ok for _, ok in steps),
    }
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(f"manifest -> {path.name} ({doc['passed']}/{doc['total']} green, commit {(commit or '?')[:12]})")


def run(cmd, cwd) -> tuple[bool, str]:
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    return p.returncode == 0, (p.stdout + p.stderr).strip().splitlines()[-1] if (p.stdout + p.stderr).strip() else ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rust", action="store_true", help="also run the Rust node suite (needs cargo)")
    ap.add_argument("--cpp", action="store_true", help="also run the C++ port differentials (needs g++)")
    ap.add_argument("--core", action="store_true",
                    help="run only the consensus/script/value/ledger reconstruction core (excludes the "
                         "descendant tracker + conformance matrix, UI tools, and bootstrap seed); "
                         "writes a machine-readable results manifest")
    ap.add_argument("--manifest", type=Path, default=None,
                    help="write a results manifest to this path (implied by --core)")
    args = ap.parse_args()
    py = sys.executable
    steps: list[tuple[str, bool]] = []

    def _first_word(label: str) -> str:                  # "conformance(6-chain ...)" -> "conformance"
        return label.split("(")[0].split()[0]

    suites, artifacts = SUITES, ARTIFACTS
    if args.core:
        suites = [(l, d) for (l, d) in SUITES if _first_word(l) not in CORE_EXCLUDE_SUITES]
        artifacts = [(l, s, d) for (l, s, d) in ARTIFACTS if s not in CORE_EXCLUDE_ARTIFACTS]

    print(f"== derivatives test suites{' (core)' if args.core else ''} ==")
    for label, d in suites:
        ok, tail = run([py, "-m", "pytest", "-q"], d)
        steps.append((label, ok))
        print(f"  [{'PASS' if ok else 'FAIL'}] {label:60} {tail}")

    print("== regenerate derived artifacts ==")
    for label, script, d in artifacts:
        ok, tail = run([py, script], d)
        steps.append((label, ok))
        print(f"  [{'PASS' if ok else 'FAIL'}] {label:60} {tail}")

    if args.rust:
        print("== Rust node (validator-rs) ==")
        import shutil
        cargo = shutil.which("cargo")
        rs_dir = DERIV / "validator-rs"
        if not cargo or not rs_dir.exists():
            print(f"  [FAIL] {'validator-rs (cargo test)':60} cargo/crate unavailable (--rust was requested)")
            steps.append(("validator-rs (cargo test)", False))   # a REQUESTED backend must fail hard, not skip-pass
        else:
            ok, tail = run([cargo, "test", "--locked", "--quiet"], rs_dir)
            steps.append(("validator-rs (cargo test)", ok))
            msg = "all Rust suites passed" if ok else tail   # (cargo's per-binary tails are noisy)
            print(f"  [{'PASS' if ok else 'FAIL'}] {'validator-rs (cargo test)':60} {msg}")

    if args.cpp:
        print("== C++/OpenSSL port differentials ==")
        import shutil
        bash = shutil.which("bash")
        for label, script in CPP:
            if not bash or not script.exists():
                print(f"  [FAIL] {label:60} bash/script unavailable (--cpp was requested)")
                steps.append((label, False))             # requested backend unavailable -> fail, not skip
                continue
            ok, tail = run([bash, str(script)], script.parent)
            steps.append((label, ok))
            print(f"  [{'PASS' if ok else 'FAIL'}] {label:60} {tail}")

    ok_all = all(ok for _, ok in steps)
    print(f"\n{'ALL PASSED' if ok_all else 'FAILURES ABOVE'} — {sum(ok for _, ok in steps)}/{len(steps)} steps green.")
    if args.core or args.manifest:
        _manifest(steps, args, args.manifest or (ROOT / "reproduce-manifest.json"))
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
