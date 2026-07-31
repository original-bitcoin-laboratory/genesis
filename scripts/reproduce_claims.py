#!/usr/bin/env python3
"""Claim-scoped reproducer: re-runs ONLY the checks behind the reconstruction's four findings, under
the faithful profiles (jan09-faithful, nov08-source-bounded), and writes a claim-mapped manifest.

Unlike reproduce.py (the whole lab) and reproduce.py --core (the reconstruction core), this maps each
finding to the exact tests that demonstrate it and records a machine-readable manifest: the two faithful
profiles' consensus configs, the pinned source/inventory hashes, per-claim results with test IDs, the
tool versions of any requested cross-implementation backends (which fail hard rather than skip-pass),
and an artifact-drift check. It deliberately EXCLUDES the experimental X-chain live networks, P2P wire,
wallet, persistence, marketplace/UI tools, the neutral descendant tracker/matrix, and the bootstrap seed
-- none of which the four findings rest on.

    python scripts/reproduce_claims.py                 # Python claim checks + manifest
    python scripts/reproduce_claims.py --rust --cpp    # + cross-implementation backends
    python scripts/reproduce_claims.py --manifest out.json

Exit code 0 iff every requested check passed with zero skips and no artifact drift.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent            # genesis/
DERIV = ROOT / "derivatives"

# claim id -> (description, [(label, dir, pytest args)]). The paper's findings rest on the faithful profiles
# (jan09-faithful, nov08-source-bounded); the one experimental-genesis check under C1 is a determinism-only
# sub-check (the isolated blocks reproduce and differ from the historical hash) and is explicitly NOT evidence
# for the historical-genesis claim, which the C++/OpenSSL port (--cpp) and the deposited binary carry.
CLAIMS = {
    "C1-reconstruction": (
        "Reproducible reconstruction: the experimental-network genesis blocks are deterministic (and differ "
        "from the historical hash); the HISTORICAL January genesis is re-derived by the C++/OpenSSL port "
        "(--cpp) and the unmodified 2009 binary (deposited separately, DOI in the paper); the consensus core "
        "is cross-implemented (Python here, Rust via --rust) and reorg-safe",
        [("experimental-network genesis determinism (NOV08-X, JAN09-X) -- NOT the historical block", ROOT / "scripts", None),
         ("consensus core (sighash/checksig/script), Python", DERIV / "model",
          ["-k", "sighash or checksig or evalscript or cscript"]),
         ("reorg-safety", DERIV / "netnode", ["-k", "reorg or disconnect"])],
    ),
    "C2-broad-interpreter": (
        "A broad spending-predicate interpreter: opcode vocabulary + escrow/hash-lock/assurance + a marketplace source component",
        [("model instruments (escrow/hash-lock/assurance)", DERIV / "model", ["-k", "instrument or multisig"]),
         ("full-node instruments (ConnectBlock path)", DERIV / "netnode", ["-k", "fullnode or op_notequal"]),
         ("marketplace source component (model)", DERIV / "market", None)],
    ),
    "C3-monetary-params-differ": (
        "The five monetary parameters differ between the November preview and the January release "
        "(source-bounded profiles only; no experimental X network involved)",
        [("source-bounded monetary difference (nov08-source-bounded vs jan09-faithful)", DERIV / "profiles",
          ["-k", "source_bounded_monetary"])],
    ),
    "C4-height-fork-and-missing-bounds": (
        "Best chain by height not cumulative work; substantial machinery, several 2010-era bounds absent",
        [("height beats cumulative work (discriminating fork)", DERIV / "netnode", ["-k", "height_beats"]),
         ("value overflow: v0.1 vs the Aug-2010 MoneyRange fix", DERIV / "overflow", None),
         ("script resource limits absent in v0.1", DERIV / "script_limits", None),
         ("temporal rules (median-time-past, finality)", DERIV / "temporal", None)],
    ),
}


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def run(cmd, cwd) -> tuple[bool, str]:
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    out = (p.stdout + p.stderr).strip()
    return p.returncode == 0, (out.splitlines()[-1] if out else "")


def _profiles_block():
    sys.path.insert(0, str(DERIV / "profiles"))
    import profiles as P  # noqa: E402
    block = {}
    for name in ("jan09-faithful", "nov08-source-bounded"):
        pr = P.load(name)
        block[name] = {
            "chain": pr.chain,
            "script_posture": pr.script_posture,
            "class": getattr(pr, "klass", getattr(pr, "class_", None)) or pr.__dict__.get("klass"),
            "consensus_rules": pr.consensus_rules,
            "reopened_opcodes": pr.reopened_opcodes,
            "profile_hash": pr.profile_hash(),          # stable id of the exact profile these claims used
        }
    return block


def _environment() -> dict:
    env = {"python": sys.version.split()[0], "platform": platform.platform()}
    try:
        import ssl
        env["openssl"] = ssl.OPENSSL_VERSION            # the verify backend's actual OpenSSL
    except Exception:                                    # noqa: BLE001
        env["openssl"] = None
    try:
        import cryptography
        env["cryptography"] = cryptography.__version__
    except Exception:                                    # noqa: BLE001
        env["cryptography"] = None
    try:
        import bitcoinx                                  # optional libsecp256k1 accel path
        env["libsecp_accel"] = getattr(bitcoinx, "__version__", "present")
    except Exception:                                    # noqa: BLE001
        env["libsecp_accel"] = None
    return env


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rust", action="store_true", help="also run the Rust node's shared-vector suite (needs cargo)")
    ap.add_argument("--cpp", action="store_true", help="also run the C++/OpenSSL port differential (needs g++)")
    ap.add_argument("--manifest", type=Path, default=ROOT / "reproduce-claims-manifest.json")
    args = ap.parse_args()
    py = sys.executable
    results, skipped_requested = [], 0

    print("== claim-scoped reproduction (faithful profiles only) ==")
    claim_docs = []
    for cid, (desc, checks) in CLAIMS.items():
        print(f"\n{cid}: {desc}")
        checks_doc, claim_ok = [], True
        for label, d, extra in checks:
            if extra is None and (d / "run.sh").exists() is False and (d.name == "scripts"):
                ok, tail = run([py, "verify_genesis.py"], d)          # C1 script check
            elif extra is None:
                ok, tail = run([py, "-m", "pytest", "-q"], d)          # whole small suite
            else:
                ok, tail = run([py, "-m", "pytest", "-q", *extra], d)  # selected tests
            print(f"  [{'PASS' if ok else 'FAIL'}] {label:52} {tail}")
            checks_doc.append({"check": label, "dir": d.name, "selector": extra, "passed": ok})
            claim_ok = claim_ok and ok
        claim_docs.append({"id": cid, "description": desc, "checks": checks_doc, "passed": claim_ok})
        results.append(claim_ok)

    # artifact regeneration: regenerate the paper's monetary-difference artifact and confirm it is byte-stable
    # (a real reproducibility check on a paper artifact — not the experimental X-network differential)
    print("\n== artifact regeneration ==")
    prof = DERIV / "profiles"
    art = ROOT / "paper-artifacts" / "monetary-difference.json"
    ok1, _ = run([py, "test_source_bounded_monetary.py"], prof)
    first = art.read_bytes() if art.exists() else b""
    ok2, _ = run([py, "test_source_bounded_monetary.py"], prof)
    second = art.read_bytes() if art.exists() else b""
    drift_ok = bool(ok1 and ok2 and first and first == second)
    print(f"  [{'PASS' if drift_ok else 'FAIL'}] paper-artifacts/monetary-difference.json regenerates byte-identically")
    results.append(drift_ok)

    # requested cross-implementation backends (fail hard, never skip-pass)
    backends = {}
    if args.rust:
        print("\n== Rust node (shared golden vectors) ==")
        cargo = shutil.which("cargo")
        rs = DERIV / "validator-rs"
        if not cargo or not rs.exists():
            print("  [FAIL] validator-rs: cargo/crate unavailable (--rust requested)"); results.append(False); skipped_requested += 1
            backends["rust"] = {"requested": True, "ran": False}
        else:
            proc = subprocess.run([cargo, "test", "--locked", "--quiet"], cwd=str(rs), capture_output=True, text=True)
            ok = proc.returncode == 0
            # cargo prints one "test result: ok. N passed" per test binary (unit + doc); the LAST line is
            # the doc-test summary (0), so sum across all binaries for the true count rather than tailing.
            blob = proc.stdout + proc.stderr
            npass = sum(int(m) for m in re.findall(r"test result: ok\. (\d+) passed", blob))
            summary = f"{npass} passed" if ok else (blob.strip().splitlines() or ["failed"])[-1]
            print(f"  [{'PASS' if ok else 'FAIL'}] validator-rs cargo test ({summary})")
            results.append(ok)
            _, ver = run([cargo, "--version"], rs)
            backends["rust"] = {"requested": True, "ran": True, "passed": ok, "cargo": ver,
                                "cargo_lock_sha256": _sha256(rs / "Cargo.lock"),
                                "tests_passed": npass, "result": summary}
    if args.cpp:
        print("\n== C++/OpenSSL port differential ==")
        bash, script = shutil.which("bash"), DERIV / "port" / "run.sh"
        if not bash or not script.exists():
            print("  [FAIL] port: bash/script unavailable (--cpp requested)"); results.append(False); skipped_requested += 1
            backends["cpp"] = {"requested": True, "ran": False}
        else:
            ok, tail = run([bash, str(script)], script.parent)
            print(f"  [{'PASS' if ok else 'FAIL'}] MODEL == PORT differential {tail}")
            results.append(ok)
            gxx = shutil.which("g++") or "/c/msys64/mingw64/bin/g++"
            gproc = subprocess.run([gxx, "--version"], capture_output=True, text=True)
            gver = (gproc.stdout.splitlines() or [""])[0]                 # first line = the version
            _, ossl = run([py, "-c", "import ssl;print(ssl.OPENSSL_VERSION)"], ROOT)
            backends["cpp"] = {"requested": True, "ran": True, "passed": ok, "g++": gver, "openssl": ossl,
                               "result": tail}

    ok_git, commit = run(["git", "rev-parse", "HEAD"], ROOT)
    all_passed = all(results) and skipped_requested == 0
    manifest = {
        "schema": 1,
        "kind": "claim-scoped reconstruction reproduction",
        "generated": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "commit": commit if ok_git else None,
        "not_money": True,
        "environment": _environment(),
        "requested_backends": backends,
        "skipped_requested_checks": skipped_requested,
        "profiles": _profiles_block(),
        "pins": {
            "profiles.json": _sha256(DERIV / "profiles" / "profiles.json"),
            "OPCODES.json": _sha256(ROOT / "inventory" / "OPCODES.json"),
            "script.h": _sha256(ROOT / "extracted" / "bitcoin" / "src" / "script.h"),
            "script.cpp": _sha256(ROOT / "extracted" / "bitcoin" / "src" / "script.cpp"),
            "main.cpp": _sha256(ROOT / "extracted" / "bitcoin" / "src" / "main.cpp"),
            "main.h": _sha256(ROOT / "extracted" / "bitcoin" / "src" / "main.h"),
            "util.h": _sha256(ROOT / "extracted" / "bitcoin" / "src" / "util.h"),
        },
        "claims": claim_docs,
        "artifact_regeneration": {"monetary_difference_reproducible": drift_ok, "path": "paper-artifacts/monetary-difference.json"},
        "all_passed": all_passed,
    }
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"\n{'ALL CLAIMS REPRODUCED' if all_passed else 'FAILURES ABOVE'} — "
          f"{sum(results)}/{len(results)} checks, {skipped_requested} skipped-requested.")
    print(f"manifest -> {args.manifest.name}")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
