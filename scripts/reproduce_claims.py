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

Completeness is reported in three states, not one boolean: `all_internal_checks_passed` (the runnable
checks), `cross_implementation_complete` (C1b's Python+Rust+C++ agreement — needs `--rust --cpp`), and
`external_claims_complete` (the author-reported historical claim C1d, false until its archival deposit is
public). Exit code 0 iff every internal runnable check passed; the external claim never flips it.
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
# (jan09-faithful, nov08-source-bounded). The experimental-genesis determinism check is NOT a paper claim --
# it is recorded separately under `auxiliary_checks` (a lab sanity check that the isolated NOV08-X/JAN09-X
# blocks reproduce and differ from the historical hash). The historical-binary results (C1d-C1g) are EXTERNAL,
# author-reported and carried by the deposited legacy-toolchain source build + the unmodified 2009 binary --
# NOT by the modern differential C++/OpenSSL port (--cpp), which never executes the historical build.
CLAIMS = {
    "C1b-consensus-core-cross-implemented": (
        "The consensus core (sighash, CHECKSIG/CHECKMULTISIG, Script) is cross-implemented and agrees -- "
        "Python here, Rust via --rust, C++/OpenSSL via --cpp",
        [("consensus core (sighash/checksig/script), Python", DERIV / "model",
          ["-k", "sighash or checksig or evalscript or cscript"])],
    ),
    "C1c-reorg-safety": (
        "The validated chainstate reorganises safely: it activates the taller VALID branch and aborts a "
        "reorg to an invalid branch, restoring the prior tip",
        [("reorg-safety", DERIV / "netnode", ["-k", "reorg or disconnect"])],
    ),
    # Each external claim carries its OWN carrier note: C1d (genesis) is the legacy source build + the
    # binary; C1e-C1g are the unmodified-binary two-node RUN and its archived artifacts, NOT the source build.
    "C1d-historical-genesis": (
        "The HISTORICAL January genesis (000000000019d668...) is re-derived by a legacy-toolchain source "
        "build and the unmodified 2009 binary (the historical-binary witness). EXTERNAL -- author-reported "
        "and hash-manifested, archival deposit pending; not executed here",
        ("EXTERNAL", "carried by a legacy-toolchain source build AND the unmodified 2009 binary (deposited "
                     "separately), not by the differential C++/OpenSSL port; author-reported, archival deposit pending"),
    ),
    "C1e-historical-block-production-and-relay": (
        "Two unmodified 2009 binaries mine at difficulty-1 on the real genesis and relay blocks peer-to-peer "
        "(discovery via a local IRC daemon reproducing the client's hard-coded path); the receiver accepts "
        "each, leaving byte-identical block files (blk0001.dat). EXTERNAL -- author-reported, archival deposit pending",
        ("EXTERNAL", "carried by the unmodified-binary two-node run and its archived logs, block files, and "
                     "evidence manifest (not the legacy source build); author-reported, archival deposit pending"),
    ),
    "C1f-historical-bidirectional-chain-growth": (
        "Both unmodified binaries mine and validate/accept each other's blocks, growing a 14-block chain "
        "bidirectionally -- byte-identical block files on both and persisting across an unplanned restart. "
        "EXTERNAL -- author-reported, archival deposit pending",
        ("EXTERNAL", "carried by the unmodified-binary two-node run and its archived logs, block files, and "
                     "evidence manifest (not the legacy source build); author-reported, archival deposit pending"),
    ),
    "C1g-historical-reorganisation": (
        "Deliberately partitioned, the two binaries build divergent valid branches; on reconnection the "
        "shorter node executes the client's REORGANIZE path, orphans its own valid block, and both converge "
        "on the longer branch (the retained orphan a one-block on-disk difference). EXTERNAL -- "
        "author-reported, archival deposit pending",
        ("EXTERNAL", "carried by the unmodified-binary two-node run and its archived logs, block files, and "
                     "evidence manifest (not the legacy source build); author-reported, archival deposit pending"),
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


def _cpp_toolchain(gxx: str) -> dict:
    """The OpenSSL the C++ port actually links: the toolchain's `openssl version` and the libcrypto DLL
    imported by port.exe (name / path / sha256) -- not Python's OpenSSL, which need not be the same lib."""
    info: dict = {}
    gp = Path(gxx)
    mingw_bin = gp.resolve().parent if gp.exists() else None
    ossl = shutil.which("openssl") or (str(mingw_bin / "openssl.exe") if mingw_bin else None)
    if ossl and Path(ossl).exists():
        r = subprocess.run([ossl, "version"], capture_output=True, text=True)
        info["openssl_version"] = r.stdout.strip() if r.returncode == 0 else None
    objdump = shutil.which("objdump")
    port_exe = DERIV / "port" / "port.exe"
    if objdump and port_exe.exists():
        r = subprocess.run([objdump, "-p", str(port_exe)], capture_output=True, text=True)
        dlls = re.findall(r"DLL Name:\s*(\S*crypto\S*)", r.stdout, re.IGNORECASE)
        if dlls:
            dll = (mingw_bin / dlls[0]) if mingw_bin else None
            info["libcrypto"] = {"name": dlls[0], "path": str(dll) if dll and dll.exists() else None,
                                 "sha256": _sha256(dll) if dll and dll.exists() else None}
    return info


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


def _external_evidence(path: Path) -> dict:
    """Derive external-claim (C1d-C1g) completeness from a frozen deposit descriptor rather than a hand-set
    boolean. Complete iff the file exists and carries a DOI, an archive sha256, an evidence-manifest sha256,
    and a claim map covering every external claim C1d-C1g. Absent -> incomplete (the correct pre-deposit
    state). This keeps `external_claims_complete` machine-verifiable: the author drops in the descriptor at
    deposit; nobody flips the flag by hand."""
    required = {"C1d", "C1e", "C1f", "C1g"}
    doc = None
    if path.exists():
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            doc = None
    if not doc:
        return {"complete": False, "source": None, "reason": "no historical-evidence.json (pre-deposit state)"}
    mapped = {str(c).split("-")[0] for c in (doc.get("claim_map") or {})}
    complete = bool(doc.get("doi") and doc.get("archive_sha256")
                    and doc.get("evidence_manifest_sha256") and required <= mapped)
    return {"complete": complete, "source": str(path), "doi": doc.get("doi"),
            "archive_sha256": doc.get("archive_sha256"),
            "evidence_manifest_sha256": doc.get("evidence_manifest_sha256"),
            "claims_mapped": sorted(mapped),
            "reason": None if complete else "descriptor present but missing DOI / archive hash / manifest hash / full C1d-C1g map"}


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
    ap.add_argument("--historical-evidence", type=Path,
                    default=ROOT / "paper-artifacts" / "historical-evidence.json",
                    help="frozen external-evidence descriptor (DOI + archive/evidence-manifest sha256 + a "
                         "C1d-C1g claim map); its presence and validity DERIVE external_claims_complete -- "
                         "never set that boolean by hand. Absent (pre-deposit) -> external stays incomplete")
    args = ap.parse_args()
    py = sys.executable
    results, skipped_requested = [], 0

    print("== claim-scoped reproduction (faithful profiles only) ==")
    claim_docs = []
    for cid, (desc, checks) in CLAIMS.items():
        print(f"\n{cid}: {desc}")
        is_external = checks == "EXTERNAL" or (isinstance(checks, tuple) and checks and checks[0] == "EXTERNAL")
        if is_external:
            # A claim whose evidence lives outside this reproducer (the deposited historical-binary
            # witness). Recorded with its own per-claim carrier note -- author-reported -- and NOT folded
            # into all_passed. C1d is the legacy source build + binary; C1e-C1g the unmodified-binary run.
            note = checks[1] if isinstance(checks, tuple) else ("author-reported and hash-manifested; "
                   "carried by the deposited historical-binary evidence (see the archival deposit)")
            print("  [EXTERNAL] author-reported (historical-binary witness); not executed by this reproducer")
            claim_docs.append({"id": cid, "description": desc, "external": True, "passed": None, "note": note})
            continue
        checks_doc, claim_ok = [], True
        for label, d, extra in checks:
            if extra is None and (d / "run.sh").exists() is False and (d.name == "scripts"):
                ok, tail = run([py, "verify_genesis.py"], d)          # experimental-genesis script check
            elif extra is None:
                ok, tail = run([py, "-m", "pytest", "-q"], d)          # whole small suite
            else:
                ok, tail = run([py, "-m", "pytest", "-q", *extra], d)  # selected tests
            print(f"  [{'PASS' if ok else 'FAIL'}] {label:52} {tail}")
            checks_doc.append({"check": label, "dir": d.name, "selector": extra, "passed": ok})
            claim_ok = claim_ok and ok
        claim_docs.append({"id": cid, "description": desc, "checks": checks_doc, "passed": claim_ok})
        results.append(claim_ok)

    # auxiliary (non-claim) lab sanity check: experimental-network genesis determinism. This is explicitly
    # NOT evidence for any paper finding (the isolated NOV08-X/JAN09-X blocks reproduce and differ from the
    # historical hash) — it lives outside the claim set so the claim map contains only paper claims.
    print("\n== auxiliary check (not a paper claim) ==")
    aux_ok, aux_tail = run([py, "verify_genesis.py"], ROOT / "scripts")
    print(f"  [{'PASS' if aux_ok else 'FAIL'}] experimental-genesis determinism (verify_genesis.py) {aux_tail}")
    results.append(aux_ok)
    auxiliary_checks = {"experimental_genesis_determinism": {
        "description": "NOV08-X/JAN09-X genesis blocks re-derive deterministically and differ from the "
                       "historical hash -- a lab sanity check, NOT evidence for any paper claim",
        "check": "verify_genesis.py", "passed": aux_ok}}

    # artifact regeneration: regenerate each paper artifact and confirm it is byte-stable (a real
    # reproducibility check on the paper's frozen numbers — not the experimental X-network differential).
    print("\n== artifact regeneration ==")
    art_scripts = {
        "monetary-difference.json": (DERIV / "profiles", "test_source_bounded_monetary.py"),
        "height-vs-work.json": (DERIV / "netnode", "height_vs_work.py"),
    }
    artifact_reg, artifact_sha = {}, {}
    for name, (d, script) in art_scripts.items():
        art = ROOT / "paper-artifacts" / name
        ok1, _ = run([py, script], d)
        first = art.read_bytes() if art.exists() else b""
        ok2, _ = run([py, script], d)
        second = art.read_bytes() if art.exists() else b""
        stable = bool(ok1 and ok2 and first and first == second)
        print(f"  [{'PASS' if stable else 'FAIL'}] paper-artifacts/{name} regenerates byte-identically")
        results.append(stable)
        artifact_reg[name] = stable
        artifact_sha[name] = hashlib.sha256(second).hexdigest() if second else None  # freeze expected output hash
    drift_ok = all(artifact_reg.values())
    # embed the frozen height-vs-work numbers in the manifest (not just "the test passed")
    hvw_path = ROOT / "paper-artifacts" / "height-vs-work.json"
    hvw = json.loads(hvw_path.read_text(encoding="utf-8")) if hvw_path.exists() else {}
    height_vs_work = {k: hvw.get(k) for k in ("incumbent_branch_B", "challenger_branch_A",
                     "challenger_has_less_work", "selected_tip", "selected_by",
                     "retarget_interval_used", "historical_interval")}

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
            eval_data = rs / "tests" / "data" / "eval_data.rs"
            nvec = (len(re.findall(r'\(\s*"', eval_data.read_text(encoding="utf-8")))
                    if eval_data.exists() else None)     # opcode differential vectors (paper §3: "73")
            backends["rust"] = {"requested": True, "ran": True, "passed": ok, "cargo": ver,
                                "cargo_lock_sha256": _sha256(rs / "Cargo.lock"),
                                "tests_passed": npass, "opcode_differential_vectors": nvec, "result": summary}
    if args.cpp:
        print("\n== C++/OpenSSL port (differential + sighash + CHECKSIG/CHECKMULTISIG) ==")
        bash = shutil.which("bash")
        port = DERIV / "port"
        harnesses = [("bn_opcode_differential", port / "run.sh"),               # BN/opcode vectors
                     ("sighash_incl_anyonecanpay", port / "run_sighash.sh"),     # SignatureHash + ANYONECANPAY
                     ("checksig_checkmultisig_e2e", port / "run_checksig.sh")]   # end-to-end secp256k1
        if not bash or not all(s.exists() for _, s in harnesses):
            print("  [FAIL] port: bash/scripts unavailable (--cpp requested)"); results.append(False); skipped_requested += 1
            backends["cpp"] = {"requested": True, "ran": False}
        else:
            runs, all_cpp = {}, True
            for name, script in harnesses:
                ok, tail = run([bash, str(script)], port)
                print(f"  [{'PASS' if ok else 'FAIL'}] {name:28} {tail}")
                results.append(ok); all_cpp = all_cpp and ok
                m = re.search(r"\bon (\d+)\b", tail) or re.search(r"\b(\d+)\s+PASS\b", tail)  # count exercised
                runs[name] = {"passed": ok, "result": tail, "count": int(m.group(1)) if m else None}
            gxx = shutil.which("g++") or "/c/msys64/mingw64/bin/g++"
            gver = (subprocess.run([gxx, "--version"], capture_output=True, text=True).stdout.splitlines() or [""])[0]
            backends["cpp"] = {"requested": True, "ran": True, "passed": all_cpp, "g++": gver,
                               "cpp_toolchain": _cpp_toolchain(gxx), "harnesses": runs}

    ok_git, commit = run(["git", "rev-parse", "HEAD"], ROOT)

    # Bind the cross-implementation claim (C1b) to the ACTUAL backend results, not the Python check
    # alone: it counts as passed only when Python AND Rust AND C++ all ran and agreed. A Python-only or
    # single-backend run leaves it null (incomplete) — never a false pass on unrun evidence.
    rust_ok = backends.get("rust", {}).get("passed") is True
    cpp_ok = backends.get("cpp", {}).get("passed") is True
    for c in claim_docs:
        if c["id"].startswith("C1b"):
            py_ok = c["passed"] is True
            c["cross_implementation"] = {"python": py_ok,
                                         "rust": rust_ok if args.rust else None,
                                         "cpp": cpp_ok if args.cpp else None}
            if args.rust and args.cpp:
                c["passed"] = bool(py_ok and rust_ok and cpp_ok)
            else:
                c["passed"] = None
                c["incomplete"] = "cross-implementation requires --rust --cpp"

    internal = [c for c in claim_docs if not c.get("external")]
    backends_ok = all(b.get("passed") for b in backends.values() if b.get("requested"))
    all_internal = (all(c.get("passed") is True for c in internal)
                    and drift_ok and backends_ok and skipped_requested == 0)
    cross_impl_complete = bool(args.rust and args.cpp and rust_ok and cpp_ok)
    # external completeness is DERIVED from a frozen deposit descriptor, never a hand-set boolean: at deposit
    # the author adds historical-evidence.json (DOI + archive/evidence-manifest hashes + a C1d-C1g claim map)
    # and this computes True; absent or incomplete (the pre-deposit state) it stays False.
    external_evidence = _external_evidence(args.historical_evidence)
    external_complete = external_evidence["complete"]
    submission_complete = bool(all_internal and cross_impl_complete and external_complete)

    manifest = {
        "schema": 3,   # 3: C1a->auxiliary_checks; historical-binary split into external C1d-C1g
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
        "auxiliary_checks": auxiliary_checks,
        "artifact_regeneration": {"reproducible": artifact_reg, "sha256": artifact_sha,
                                  "height_vs_work": height_vs_work},
        # completeness is three-state: internal runnable checks are separate from the external
        # (author-reported) historical claim and from cross-implementation coverage.
        "all_internal_checks_passed": all_internal,
        "cross_implementation_complete": cross_impl_complete,
        "external_claims_complete": external_complete,
        "external_evidence": external_evidence,   # derived, not hand-set (see historical-evidence.json)
        "submission_evidence_complete": submission_complete,
    }
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if all_internal and not external_complete:
        print("\nAll internally runnable claims passed; one external historical claim (C1d) remains "
              "author-reported pending archival deposit — submission evidence is NOT yet complete.")
    elif all_internal:
        print("\nAll internal claims passed and external claims complete.")
    else:
        print("\nINCOMPLETE or FAILURES above — see per-claim states (C1b needs --rust --cpp).")
    print(f"  internal claims {sum(1 for c in internal if c.get('passed') is True)}/{len(internal)}, "
          f"{sum(results)}/{len(results)} checks; cross-impl complete: {cross_impl_complete}; "
          f"external complete: {external_complete}")
    print(f"manifest -> {args.manifest.name}")
    return 0 if all_internal else 1


if __name__ == "__main__":
    raise SystemExit(main())
