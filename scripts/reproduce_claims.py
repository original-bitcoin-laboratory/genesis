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
`external_claims_complete` (the author-reported historical claims C1d–C1h, false until their archival deposit is
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
# blocks reproduce and differ from the historical hash). The historical-binary results (C1d-C1h) are EXTERNAL,
# author-reported: C1d = the unmodified 2009 binary (block 0 of its blk0001.dat); C1e-C1h = the two-node
# binary run and its archived logs/block files -- NOT the modern differential C++/OpenSSL port (--cpp).
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
    # Each external claim carries its OWN carrier note: C1d (genesis) is the unmodified 2009 binary (block 0
    # of blk0001.dat); C1e-C1h are the unmodified-binary two-node RUN and its archived logs/block files.
    "C1d-historical-genesis": (
        "The HISTORICAL January genesis (000000000019d668...) is re-derived by the unmodified 2009 binary "
        "(the historical-binary witness) -- block 0 of its blk0001.dat. EXTERNAL -- author-reported and "
        "hash-manifested, archival deposit pending; not executed here",
        ("EXTERNAL", "carried by the unmodified 2009 binary (deposited separately) -- block 0 of blk0001.dat; "
                     "not by the differential C++/OpenSSL port; author-reported, archival deposit pending"),
    ),
    "C1e-historical-block-production-and-relay": (
        "Two unmodified 2009 binaries mine at difficulty-1 on the real genesis and relay blocks peer-to-peer "
        "(discovery via a local IRC daemon reproducing the client's hard-coded path); the receiver accepts "
        "each, leaving byte-identical block files (blk0001.dat). EXTERNAL -- author-reported, archival deposit pending",
        ("EXTERNAL", "carried by the unmodified-binary two-node run and its archived logs, block files, and "
                     "evidence manifest (not the differential C++/OpenSSL port); author-reported, archival deposit pending"),
    ),
    "C1f-historical-bidirectional-chain-growth": (
        "Both unmodified binaries mine and validate/accept each other's blocks, growing a 14-block chain "
        "including genesis (best-chain height 13) bidirectionally -- byte-identical block files on both and "
        "persisting across an unplanned restart. "
        "EXTERNAL -- author-reported, archival deposit pending",
        ("EXTERNAL", "carried by the unmodified-binary two-node run and its archived logs, block files, and "
                     "evidence manifest (not the differential C++/OpenSSL port); author-reported, archival deposit pending"),
    ),
    "C1g-historical-reorganisation": (
        "Deliberately partitioned, the two binaries build divergent valid branches; on reconnection the "
        "shorter node executes the client's REORGANIZE path, orphans its own valid block, and both converge "
        "on the longer branch (the retained orphan a one-block on-disk difference). EXTERNAL -- "
        "author-reported, archival deposit pending",
        ("EXTERNAL", "carried by the unmodified-binary two-node run and its archived logs, block files, and "
                     "evidence manifest (not the differential C++/OpenSSL port); author-reported, archival deposit pending"),
    ),
    # ⛔ C1h WAS MISSING AND THE GAP WAS INVISIBLE. The deposit shipped 2026-08-06-relayed-spend/,
    #    DEPOSIT_README named it C1h and the manuscript claimed it -- while the required set here
    #    stopped at C1g, so a descriptor mapping only the older claims went green with the newest
    #    result unrepresented. ★ An enumeration that lags the evidence it gates is a gate with a
    #    hole cut in it, and the hole is exactly the shape of the most recent work.
    #  ⚠️ This comment was itself mangled once by a blanket C1g->C1h replace, which rewrote the
    #    description of the bug into a description of the fix. A search-and-replace over prose
    #    edits the explanation as readily as the thing explained.
    "C1h-historical-relayed-spend": (
        "A coinbase output matured under the client's own rule and was spent: node B authors the "
        "spend, relays it to node A (same txid in both logs), and it is mined into block 122 -- the "
        "funding output being a coinbase at height 2, i.e. exactly COINBASE_MATURITY (100) + the 20 "
        "the v0.1 wallet adds. EXTERNAL -- author-reported, carried by the archival deposit",
        ("EXTERNAL", "carried by the unmodified-binary two-node run and its archived logs, block files and "
                     "process-level binding records (not the differential C++/OpenSSL port); "
                     "author-reported, archival deposit"),
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


EXTERNAL_REQUIRED = {"C1d", "C1e", "C1f", "C1g", "C1h"}


# ⛔⛔⛔ THE ARCHIVE IS PINNED HERE, BECAUSE THE CONSUMER RUNS CODE OUT OF IT.
#    A reviewer took the deposit, changed both C1h spend values to 1, REPLACED the deposited
#    verify_r4c.py with a script that always succeeds, resealed every manifest, rebuilt the ZIP,
#    and supplied a descriptor carrying the new matching digests. This checker extracted that
#    archive, ran the four verifiers *from inside it*, and reported external_complete = True. The
#    genuine verify_r4c.py, restored and run against those same block files, returns 1.
#  ★ So "run the deposited verifiers" -- last round's fix -- was circular: the archive supplied
#    both the evidence and the judge, and every digest it was checked against came from a
#    descriptor that travels with it. The online Zenodo fetch does not help; it faithfully proves
#    the bytes checked are the bytes published, and a bad archive with a lying verifier is exactly
#    what would have been published.
#  ⇒ The break in the circle has to come from OUTSIDE the archive and outside the descriptor. The
#    deposit is final, so its digest is a constant of this study and belongs in the code that
#    cites it. Any resealed archive -- altered evidence, altered verifier, or both -- now fails
#    before a single line of it is executed, unless someone breaks SHA-256.
#  ⚠️ Update this ONLY when the deposit itself is re-cut, and update the paper's cited digest in
#    the same commit; a pin that drifts from the manuscript is worse than no pin.
EXPECTED_ARCHIVE_SHA256 = "1b64f2fc3a6a87496accba46a259702d6e3df07696c0bdce398f9db2a4530b5f"
EXPECTED_TOP_MANIFEST_SHA256 = "49cf34837eb960b2a316dee46c7397383ac88c60b6ca878c25ce17cb2d195ffa"

# ⛔⛔ THE CLAIM -> EVIDENCE MAPPING IS OWNED HERE, NEVER READ FROM THE DESCRIPTOR.
#    A reviewer removed the entire C1h folder from an archive, resealed it, and supplied a
#    descriptor whose claim_map listed all five required IDs -- every one of them pointing at the
#    R3 folder. Each ID was "present", each mapped folder "existed", and external completeness went
#    TRUE with the capstone claim's evidence absent from the deposit. ★ "All required claim IDs
#    appear in a dictionary" had been standing in for "each claim's evidence carrier is present and
#    verifies", which is the same substitution as every previous round: a self-asserted field where
#    a checked fact belongs. The descriptor may now only AGREE with this table; it cannot define it.
EXTERNAL_CLAIM_FOLDERS = {
    "C1d": "2026-07-31-twonode-mined-block",
    "C1e": "2026-07-31-twonode-mined-block",
    "C1f": "2026-08-01-sustained-relay",
    "C1g": "2026-08-02-reorg-partition",
    "C1h": "2026-08-06-relayed-spend",
}
# ⇒ AND THE CARRIERS ARE VERIFIED, NOT MERELY COUNTED. The same four runs finalize_deposit.py
#   executes. Without this a published archive whose C1h spend is substituted -- its own verifier
#   returns 1 -- still made submission_evidence_complete true, because the consumer only ever
#   checked digests and folder names. Digests prove the bytes are the deposited ones; only the
#   verifiers say whether those bytes substantiate the claims.
EXTERNAL_VERIFIERS = (
    ("C1d/C1e", "2026-07-31-twonode-mined-block", "verify_r3.py",
     ("nodeA/blk0001.dat", "nodeB/blk0001.dat")),
    ("C1f", "2026-08-01-sustained-relay", "verify_r4.py",
     ("run-b-14/nodeA_blk0001.dat", "run-b-14/nodeB_blk0001.dat")),
    ("C1g", "2026-08-02-reorg-partition", "verify_r4.py",
     ("nodeA_blk0001.dat", "nodeB_blk0001.dat")),
    ("C1h", "2026-08-06-relayed-spend", "verify_r4c.py",
     ("nodeA/blk0001.dat", "nodeB/blk0001.dat", "--binding=.")),
)

_ZENODO_DOI = re.compile(r"^10\.5281/zenodo\.(\d+)$")
_RECEIPT_FIELDS = ("doi", "record_id", "file_url", "filename",
                   "archive_sha256", "downloaded_sha256", "downloaded_bytes", "resolved_utc")


def _validate_receipt(receipt, archive_sha: str, archive: Path, descriptor_doi=None):
    """Return (receipt, None) only if the receipt is internally consistent AND about THIS archive.

    ⚠️ WELL-FORMED IS NOT THE SAME AS TRUE. Everything checked here is offline and deterministic;
       none of it shows a Zenodo record exists. It shows that IF one exists at this DOI, this
       receipt is about the archive in hand -- so a receipt can no longer be a decorative dict.
       Existence is checked, if at all, by _verify_public_deposit_online() over the network.
    """
    if receipt is None:
        return None, "no publication receipt (the correct pre-publication state)"
    if not isinstance(receipt, dict):
        return None, "public_deposit_receipt is not an object"
    missing = [k for k in _RECEIPT_FIELDS if k not in receipt]
    if missing:
        return None, "receipt lacks %s" % ", ".join(missing)
    m = _ZENODO_DOI.match(str(receipt["doi"]).strip())
    if not m:
        return None, "receipt doi %r is not a Zenodo DOI" % receipt["doi"]
    # ⛔ THE RECEIPT MUST BE ABOUT THE DOI THE DESCRIPTOR CITES. Nothing compared these, so a
    #    descriptor could cite DOI A while the receipt proved bytes published at DOI B -- both
    #    internally valid, and the record actually verified would not be the record the paper
    #    names. The manuscript cites one DOI; that is the one the evidence has to be about.
    if descriptor_doi is not None and str(receipt["doi"]).strip() != str(descriptor_doi).strip():
        return None, ("receipt doi %s != the descriptor's doi %s -- the published record verified "
                      "is not the record cited" % (receipt["doi"], descriptor_doi))
    if str(receipt["record_id"]).strip() != m.group(1):
        return None, ("receipt record_id %r does not match the DOI's record %s"
                      % (receipt["record_id"], m.group(1)))
    if not str(receipt["file_url"]).startswith(
            "https://zenodo.org/records/%s/files/" % m.group(1)):
        return None, "receipt file_url does not address record %s" % m.group(1)
    if str(receipt["filename"]) != archive.name:
        return None, ("receipt names %r; the archive supplied is %r"
                      % (receipt["filename"], archive.name))
    # ⛔ THE BINDING THAT MAKES THE RECEIPT ABOUT THIS ARCHIVE RATHER THAN SOME ARCHIVE. Both the
    #    deposited digest and the re-downloaded digest must equal the one recomputed here, so a
    #    receipt for a superseded build -- the archive digest moved five times in this series --
    #    cannot be reused against a rebuilt one.
    for k in ("archive_sha256", "downloaded_sha256"):
        if str(receipt[k]).strip().lower() != archive_sha:
            return None, ("receipt %s %s != the archive sha256 recomputed here %s"
                          % (k, receipt[k], archive_sha))
    try:
        if int(receipt["downloaded_bytes"]) != archive.stat().st_size:
            return None, ("receipt downloaded_bytes %s != archive size %d"
                          % (receipt["downloaded_bytes"], archive.stat().st_size))
    except (TypeError, ValueError):
        return None, "receipt downloaded_bytes is not a number"
    return dict(receipt), None


def _verify_public_deposit_online(receipt, archive: Path | None, timeout: float = 90.0) -> dict:
    """Fetch the published file NOW and compare its bytes to the local archive.

    ⇒ THE ONLY THING THAT CAN EARN `public_deposit_verified`. Existence at a public deposit is a
      property of the network, not of any local file, so no amount of offline checking substitutes.

    ⚠️ The verdict is the DIGEST OF THE PAYLOAD, never the status line. A host behind a bot wall
       answers 200 with a challenge page; a redirect to a login form is also a 200. Hashing what
       came back and requiring it to equal the local archive is what makes that distinction --
       reading the envelope instead of the letter is how a 200 becomes a false finding.
    """
    out = {"attempted": True, "ok": False, "reason": None,
           "url": None, "sha256": None, "bytes": None,
           "checked_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(
               timespec="seconds")}
    if not receipt:
        out["reason"] = "no well-formed receipt to check"
        return out
    if archive is None or not Path(archive).exists():
        out["reason"] = "no local archive to compare the published bytes against"
        return out
    import urllib.request
    out["url"] = url = str(receipt["file_url"])
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "obl-reproduce-claims/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:      # noqa: S310 (https, pinned)
            body = r.read()
    except Exception as e:                                           # noqa: BLE001
        out["reason"] = "fetch failed: %s" % e
        return out
    out["sha256"], out["bytes"] = hashlib.sha256(body).hexdigest(), len(body)
    local = hashlib.sha256(Path(archive).read_bytes()).hexdigest()
    if out["sha256"] != local:
        out["reason"] = ("published bytes hash %s, local archive %s -- not the same file"
                         % (out["sha256"], local))
        return out
    out["ok"] = True
    return out


def _external_evidence(path: Path, archive: Path | None = None) -> dict:
    """Derive external-claim (C1d-C1h) completeness by RE-VERIFYING THE DEPOSIT, not by reading fields.

    ⛔⛔ THIS FUNCTION USED TO TRUST A DESCRIPTOR, AND AN EXTERNAL REVIEWER BROKE IT.
       The previous version required only that historical-evidence.json carried a truthy `doi`, an
       `archive_sha256`, a `top_level_manifest_sha256`, `verified is True`, and a claim map. It never
       opened the archive. A hand-authored file naming an invented DOI (10.5281/zenodo.99999999), an
       all-zero archive hash and `verified: true` turned `external_claims_complete` TRUE with **no
       deposit in existence** -- demonstrated, not argued. Because the internal and cross-implementation
       states are true in the real submission, that one forged field made the entire manifest green.

    ★★ THE OLD DOCSTRING WAS THE TELL: it asserted that `verified: true` "is written ONLY by
       finalize_deposit.py". That is a statement about a WORKFLOW, not an invariant this code
       enforces -- and a consumer cannot inherit a guarantee by describing the producer's habits.
       **A completeness flag must be earned from bytes the checker can see, or it is decoration.**

    ⇒ So: recompute. The descriptor now supplies only *what to check against*; every claim in it is
      re-derived here from the archive itself. Absent archive -> INCOMPLETE with a reason, never
      complete-by-default. ⚠️ `finalize_deposit.py` still performs its own verification at deposit
      time; that is belt and braces, and deliberately not relied on.
    """
    doc = None
    if path.exists():
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            doc = None
    if not doc:
        return {"complete": False, "source": None, "verified_here": False,
                "reason": "no historical-evidence.json (pre-deposit state)"}

    mapped = {str(c).split("-")[0] for c in (doc.get("claim_map") or {})}
    out = {"complete": False, "source": str(path), "doi": doc.get("doi"),
           "archive_sha256": doc.get("archive_sha256"),
           "top_level_manifest_sha256": doc.get("top_level_manifest_sha256"),
           "finalization_log_sha256": doc.get("finalization_log_sha256"),
           "claims_mapped": sorted(mapped), "verified_here": False, "reason": None}

    # ── descriptor shape: necessary, nowhere near sufficient ────────────────────────────────────
    if not (doc.get("doi") and doc.get("archive_sha256") and doc.get("top_level_manifest_sha256")):
        out["reason"] = "descriptor lacks doi / archive_sha256 / top_level_manifest_sha256"
        return out
    if not EXTERNAL_REQUIRED <= mapped:
        out["reason"] = ("claim_map is missing %s -- the deposit carries a claim the descriptor does "
                         "not map" % ", ".join(sorted(EXTERNAL_REQUIRED - mapped)))
        return out

    # ── ⛔ THE ARCHIVE ITSELF. No archive, no completeness. ──────────────────────────────────────
    if archive is None or not Path(archive).exists():
        out["reason"] = ("deposit archive not supplied (--deposit-archive): external completeness is "
                         "re-derived from the archive bytes and cannot be granted from descriptor "
                         "fields alone")
        return out
    archive = Path(archive)
    got = hashlib.sha256(archive.read_bytes()).hexdigest()
    out["archive_sha256_recomputed"] = got
    # ⛔ THE PIN COMES FIRST, BEFORE ANYTHING FROM THE DESCRIPTOR IS BELIEVED AND BEFORE ANY CODE
    #    FROM THE ARCHIVE IS RUN. Checking against the descriptor only proves the two agree; both
    #    travel together and an attacker who reseals supplies both.
    # ⇒ NO BYPASS PARAMETER. An earlier version took `expected_archive_sha` so the controls could
    #    exercise the checks below this one. It was bounded -- unreachable from CLI, environment,
    #    descriptor or archive -- but the pin is now the root of trust, and a production function
    #    should have no unpinned call signature at all. It also silently suppressed the manifest
    #    pin, which the comment did not say. The controls rebind these constants in their own
    #    process instead, a capability any importer already has.
    if got != EXPECTED_ARCHIVE_SHA256:
        out["reason"] = ("archive sha256 %s is not this study's deposit %s -- the expected digest "
                         "is pinned in this checker, not read from the descriptor"
                         % (got, EXPECTED_ARCHIVE_SHA256))
        return out
    if got != doc["archive_sha256"]:
        out["reason"] = ("archive sha256 %s does not match the descriptor's %s"
                         % (got, doc["archive_sha256"]))
        return out

    import tempfile
    import zipfile
    with tempfile.TemporaryDirectory() as td:
        try:
            with zipfile.ZipFile(archive) as z:
                names = z.namelist()
                # ⚠️ Refuse traversal/absolute members before extracting anything.
                if any(n.startswith(("/", "\\")) or ".." in Path(n).parts for n in names):
                    out["reason"] = "archive contains absolute or traversing member paths"
                    return out
                z.extractall(td)
        except (OSError, zipfile.BadZipFile) as e:
            out["reason"] = "archive could not be read: %s" % e
            return out
        root = Path(td) / "obl-historical-binary-evidence"
        sums = root / "SHA256SUMS"
        if not sums.exists():
            out["reason"] = "archive has no top-level SHA256SUMS"
            return out
        man = hashlib.sha256(sums.read_bytes()).hexdigest()
        if man != EXPECTED_TOP_MANIFEST_SHA256:
            out["reason"] = ("top-level SHA256SUMS %s is not this study's %s (pinned here)"
                             % (man, EXPECTED_TOP_MANIFEST_SHA256))
            return out
        if man != doc["top_level_manifest_sha256"]:
            out["reason"] = "top-level SHA256SUMS does not match the descriptor's hash"
            return out

        # ── every listed file re-hashed, in-process: no sha256sum dependency, no subprocess ─────
        listed, bad, missing = 0, [], []
        for line in sums.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "  " not in line:
                continue
            want, name = line.split("  ", 1)
            listed += 1
            f = root / name.strip().lstrip("*").lstrip("./")
            if not f.is_file():
                missing.append(name.strip())
            elif hashlib.sha256(f.read_bytes()).hexdigest() != want.strip():
                bad.append(name.strip())
        out["manifest_entries"] = listed
        if bad or missing:
            out["reason"] = "SHA256SUMS: %d mismatched, %d missing" % (len(bad), len(missing))
            return out

        # ── ★ COVERAGE, not just correctness. A `-c` run passes happily while an UNLISTED file
        #      hides in the archive; the reviewer who found the forgery hole checked this by
        #      set-differencing the two lists, and so does this.
        on_disk = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
        in_list = set()
        for line in sums.read_text(encoding="utf-8", errors="replace").splitlines():
            if "  " in line:
                in_list.add(line.split("  ", 1)[1].strip().lstrip("*").lstrip("./"))
        unlisted = on_disk - in_list - {"SHA256SUMS"}
        if unlisted:
            out["reason"] = "unlisted files in archive: %s" % ", ".join(sorted(unlisted)[:4])
            return out

        # ── ⛔ THE OWNED MAPPING, and the descriptor may only AGREE with it ──────────────────────
        for cid, folder in EXTERNAL_CLAIM_FOLDERS.items():
            if not (root / folder).is_dir():
                out["reason"] = ("%s's evidence folder '%s/' is absent from the archive"
                                 % (cid, folder))
                return out
        for cid, val in (doc.get("claim_map") or {}).items():
            want = EXTERNAL_CLAIM_FOLDERS.get(str(cid).split("-")[0])
            # ⚠️ NOT `got` -- that name already holds the recomputed archive digest, and binding it
            #    here silently replaced a sha256 with a folder name. The receipt check twenty lines
            #    below then compared the receipt against "2026-08-06-relayed-spend" and rejected
            #    every valid receipt: `public_deposit_verified` could never have become true, which
            #    would have surfaced on deposit day with the DOI already minted. Caught only
            #    because a POSITIVE control asserts the receipt path succeeds on good input.
            mapped = str(val).split("/")[0].strip()
            if want and mapped != want:
                out["reason"] = ("descriptor maps %s to '%s/'; this checker requires '%s/'"
                                 % (cid, mapped, want))
                return out

        # ── ⇒ RUN THE DEPOSITED VERIFIERS. Digests say the bytes are the deposited ones; only
        #      these say the bytes substantiate the claims. A published archive whose C1h spend
        #      was substituted passed every check above and failed only here.
        #    ⚠️ This executes code from the archive -- the same code finalize_deposit.py runs, in
        #      a temporary extraction of an archive whose every byte was just re-hashed against a
        #      manifest whose own digest is pinned in the descriptor.
        ran = []
        for cid, folder, script, argv in EXTERNAL_VERIFIERS:
            d = root / folder
            if not (d / script).is_file():
                out["reason"] = "%s: %s missing from '%s/'" % (cid, script, folder)
                return out
            try:
                r = subprocess.run([sys.executable, script, *argv], cwd=str(d),
                                   capture_output=True, text=True, timeout=600)
            except (OSError, subprocess.SubprocessError) as e:
                out["reason"] = "%s: %s could not be run (%s)" % (cid, script, e)
                return out
            if r.returncode != 0:
                tail = [l.strip() for l in (r.stdout or "").splitlines() if "FAILED:" in l]
                out["reason"] = ("%s: %s returned %d -- %s" % (cid, script, r.returncode,
                                                               "; ".join(tail[:3]) or "no detail"))
                out["verifiers_run"] = ran
                return out
            ran.append(cid)
        out["verifiers_run"] = ran

    out["complete"] = True
    out["verified_here"] = True
    # ⛔⛔ THE RECEIPT IS VALIDATED HERE, NOT CARRIED -- AND VALIDATION IS STILL NOT ENOUGH.
    #    The previous version passed any dict straight through and the caller did bool() on it.
    #    A reviewer replayed that gate with {"anything": "truthy"} beside a descriptor DOI reading
    #    `10.5281/zenodo.DOES-NOT-EXIST` and earned `public_deposit_verified` with no Zenodo record
    #    in existence. ★ That is the SAME defect this function was rewritten to close one round
    #    earlier, reopened one field further out: a consumer inheriting a guarantee by describing
    #    what the producer usually does. The old comment even said so out loud -- "carried, never
    #    computed here" -- which named the hole rather than closing it.
    #  ⇒ Two separate things are now kept apart, because they are separate facts:
    #      well-formedness (below) is OFFLINE and deterministic -- the receipt is about THIS
    #        archive, binding its digest, size, filename, DOI and record id together;
    #      existence is a NETWORK property no offline check can establish, so it is earned only by
    #        --verify-public-deposit actually fetching the published bytes in this run.
    out["public_deposit_receipt"], out["public_deposit_receipt_reason"] = _validate_receipt(
        doc.get("public_deposit_receipt"), got, archive, doc.get("doi"))
    return out


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
    ap.add_argument("--deposit-archive", type=Path, default=None,
                    help="the deposit ZIP itself. REQUIRED for external_claims_complete: the archive is "
                         "re-hashed against the descriptor, every SHA256SUMS entry is re-checked, coverage "
                         "is set-differenced for unlisted files, and every claim folder must be present. "
                         "Without it the flag stays false -- descriptor fields alone cannot earn it.")
    ap.add_argument("--verify-public-deposit", action="store_true",
                    help="fetch the published deposit named in the receipt and compare its bytes to "
                         "--deposit-archive. THE ONLY WAY public_deposit_verified becomes true: "
                         "existence at a public deposit is a network fact, and every other check "
                         "here is offline. Without this the run stays deterministic and reports "
                         "false with a reason.")
    ap.add_argument("--historical-evidence", type=Path,
                    default=ROOT / "paper-artifacts" / "historical-evidence.json",
                    help="frozen external-evidence descriptor (DOI + archive_sha256 + top_level_manifest_sha256 "
                         "+ a C1d-C1h claim map); its presence and validity DERIVE external_claims_complete -- "
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
            # into all_passed. C1d = the unmodified 2009 binary (block 0 of blk0001.dat); C1e-C1h the two-node run.
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
    # the author adds historical-evidence.json (DOI + archive/evidence-manifest hashes + a C1d-C1h claim map)
    # and this computes True; absent or incomplete (the pre-deposit state) it stays False.
    external_evidence = _external_evidence(args.historical_evidence, args.deposit_archive)
    external_complete = external_evidence["complete"]
    # ⛔ EARNED FROM THE NETWORK OR NOT EARNED AT ALL. Two conditions, both required:
    #      1. the receipt is well-formed and binds to THIS archive (checked offline, above);
    #      2. the published bytes were fetched IN THIS RUN and hash to the local archive.
    #    Without --verify-public-deposit the offline run stays deterministic and simply reports
    #    false with a reason -- it never asserts a network fact it did not observe. The previous
    #    version granted this flag to any non-empty dict, which a reviewer demonstrated with
    #    {"anything": "truthy"}; a well-formed receipt alone would still only be a claim.
    receipt = external_evidence.get("public_deposit_receipt")
    if args.verify_public_deposit:
        online = _verify_public_deposit_online(receipt, args.deposit_archive)
    else:
        online = {"attempted": False, "ok": False,
                  "reason": "not requested -- pass --verify-public-deposit to check the network"}
    public_deposit = bool(receipt) and bool(online.get("ok"))
    # ⇒ AND submission completeness now requires the PUBLIC state, not the local one. Previously
    #   a verified local archive was enough, so "submission evidence complete" could be true with
    #   nothing published anywhere -- the precise thing the phrase promises a reader.
    # ⇒ `external_complete` IS AN EXPLICIT CONJUNCT, not an implied one. It was safe before only
    #   because _validate_receipt runs after the archive check returns -- a receipt cannot be
    #   well-formed unless the archive verified. A reviewer pointed out that this is POSITIONAL:
    #   hoisting that call, a reasonable refactor, would silently drop the requirement. A
    #   dependency that holds by statement order is not a dependency, it is a coincidence with
    #   good manners.
    submission_complete = bool(all_internal and cross_impl_complete
                               and external_complete and public_deposit)

    manifest = {
        "schema": 3,   # 3: C1a->auxiliary_checks; historical-binary split into external C1d-C1h
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
            "net.cpp": _sha256(ROOT / "extracted" / "bitcoin" / "src" / "net.cpp"),  # hash-anchors the net.cpp:94 (GetMyExternalIP host) cite
        },
        "claims": claim_docs,
        "auxiliary_checks": auxiliary_checks,
        "artifact_regeneration": {"reproducible": artifact_reg, "sha256": artifact_sha,
                                  "height_vs_work": height_vs_work},
        # completeness is three-state: internal runnable checks are separate from the external
        # (author-reported) historical claim and from cross-implementation coverage.
        "all_internal_checks_passed": all_internal,
        "cross_implementation_complete": cross_impl_complete,
        # ⛔ THE NAME NOW MATCHES WHAT IS ACTUALLY CHECKED, AND THIS IS A DELIBERATE DOWNGRADE.
        #    `external_claims_complete` read as "the cited public deposit exists". It never meant
        #    that: the checker re-verifies a LOCAL archive against the descriptor, and treats the
        #    DOI only as a non-empty string. A reviewer put it plainly -- a fabricated DOI plus the
        #    genuine local archive still earns completeness before any Zenodo record exists.
        #
        #  ★★ RESOLVING THE DOI WAS THE OBVIOUS FIX AND IS THE WRONG ONE. It would make a
        #     reproducibility manifest depend on network reachability, so the same bytes would
        #     verify or not according to DNS -- and an artifact whose result varies with the
        #     network is a worse artifact than one with an honestly narrower name.
        #  ⇒ So the state is renamed to what it can prove. The DOI's existence is evidenced by the
        #    deposit record itself, which a reader can open; it is not something this script knows.
        "external_archive_verified": external_complete,
        "external_claims_complete": external_complete,   # retained: prior schema-3 consumers read it
        "external_evidence": external_evidence,   # derived, not hand-set (see historical-evidence.json)
        # ⛔ TWO DIFFERENT QUESTIONS, AND CONFLATING THEM WAS THE REMAINING OVERCLAIM.
        #    A reviewer built an archive of five folders each holding a marker.txt reading
        #    "not evidence", gave it a self-consistent SHA256SUMS and a DOI of
        #    10.5281/zenodo.DOES-NOT-EXIST -- and the predicate returned complete. It had to:
        #    the archive digest and the manifest digest both come from the same descriptor, so
        #    there is no independent anchor saying "these are the bytes published under this DOI".
        #
        #  ★★ THE SPLIT IS THE FIX, NOT A STRONGER CHECK HERE. This script must stay offline:
        #     a reproducibility artifact whose result depends on DNS is worse than one with an
        #     honestly narrow name. So it answers only what bytes on disk can answer, and the
        #     one-time finalizer -- which may legitimately use the network -- writes the receipt
        #     that answers the other.
        "public_deposit_verified": public_deposit,
        # ⇒ HOW the flag was decided travels with it. A bare false is ambiguous between "nothing
        #   published yet", "receipt malformed" and "the network check was not run" -- three very
        #   different states for a reader deciding whether the deposit is citable.
        "public_deposit": {
            "receipt_wellformed": bool(receipt),
            # ⚠️ NEVER null, and never CONFIDENTLY WRONG. Three states, and they must not be
            #    collapsed: validation ran and passed / validation ran and rejected / validation
            #    never ran because the archive check returned first. A draft of this line used
            #    `reason or "never reached validation"`, which printed "never reached validation"
            #    over every SUCCESS -- a null replaced by a false statement is the worse of the two,
            #    and it took a control that asserted the happy path to show it.
            "receipt_reason": (
                (external_evidence["public_deposit_receipt_reason"]
                 or "receipt is well-formed and binds to this archive")
                if "public_deposit_receipt_reason" in external_evidence else
                "receipt never reached validation: %s"
                % (external_evidence.get("reason") or "unknown")),
            "online_check": online,
        },
        "submission_evidence_complete": submission_complete,
    }
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8",
                             newline="\n")   # LF: the manifest is quoted by digest
    if all_internal and not external_complete:
        print("\nAll internally runnable claims passed; the external historical claims (C1d–C1h) remain "
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
