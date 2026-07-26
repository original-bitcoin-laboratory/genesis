#!/usr/bin/env python3
"""One-command reproducer for the JAN09 edition's executable layer.

Runs every headless derivatives test suite, and regenerates the two derived
artifacts (the neutral descendant matrix and the NOV08-X differential) to prove they
reproduce from source. Python only by default — no build step. Pass --cpp to also run
the C++/OpenSSL port differentials (needs MSYS2 g++ on PATH).

    python scripts/reproduce.py          # all Python suites + regenerate artifacts
    python scripts/reproduce.py --cpp    # + the C++ port differentials

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
    ("model      (script engine, sighash, checksig, instruments)", DERIV / "model"),
    ("p2p        (wire relay + chain sync)",                        DERIV / "p2p"),
    ("wallet     (SelectCoins / CreateTransaction)",               DERIV / "wallet"),
    ("persist    (CDiskBlockIndex save/reload)",                    DERIV / "persist"),
    ("conformance(6-chain matrix, every column execution-checked)", DERIV / "conformance"),
    ("nov08x     (NOV08 counterfactual + live network)",           DERIV / "nov08x"),
    ("jan09x     (released chain, full vocab + live network)",     DERIV / "jan09x"),
    ("ledger     (UTXO ConnectInputs/ConnectBlock; transacting)",   DERIV / "ledger"),
    ("market     (R6 commerce model: signatures + atoms reputation)", DERIV / "market"),
    ("studio     (R7 script debugger / stack tracer)",              DERIV / "studio"),
    ("console    (R7 capstone: full-stack driver on both X-chains)", DERIV / "console"),
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


def run(cmd, cwd) -> tuple[bool, str]:
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    return p.returncode == 0, (p.stdout + p.stderr).strip().splitlines()[-1] if (p.stdout + p.stderr).strip() else ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cpp", action="store_true", help="also run the C++ port differentials (needs g++)")
    args = ap.parse_args()
    py = sys.executable
    results = []

    print("== derivatives test suites ==")
    for label, d in SUITES:
        ok, tail = run([py, "-m", "pytest", "-q"], d)
        results.append(ok)
        print(f"  [{'PASS' if ok else 'FAIL'}] {label:60} {tail}")

    print("== regenerate derived artifacts ==")
    for label, script, d in ARTIFACTS:
        ok, tail = run([py, script], d)
        results.append(ok)
        print(f"  [{'PASS' if ok else 'FAIL'}] {label:60} {tail}")

    if args.cpp:
        print("== C++/OpenSSL port differentials ==")
        import shutil
        bash = shutil.which("bash")
        for label, script in CPP:
            if not bash or not script.exists():
                print(f"  [SKIP] {label:60} (bash/script unavailable)")
                continue
            ok, tail = run([bash, str(script)], script.parent)
            results.append(ok)
            print(f"  [{'PASS' if ok else 'FAIL'}] {label:60} {tail}")

    ok_all = all(results)
    print(f"\n{'ALL PASSED' if ok_all else 'FAILURES ABOVE'} — {sum(results)}/{len(results)} steps green.")
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
