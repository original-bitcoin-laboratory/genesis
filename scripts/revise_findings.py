#!/usr/bin/env python3
"""Issue revision 2 of sealed findings sets without breaking revision 1.

Rule (docs/EVIDENCE_POLICY.md, "Sealed sets and revisions"): a sealed set is never edited in place.
It may be revised by a numbered revision that keeps the previous manifest and proof beside the new
ones, so both seals verify forever and the difference between them is exactly the recorded edit.

For each set this script:
  1. keeps  SHA256SUMS -> SHA256SUMS.r1   and   SHA256SUMS.ots -> SHA256SUMS.r1.ots   (once)
  2. applies the listed text edits to FINDINGS.md (every anchor must match exactly once)
  3. edits the flagged comment lines of the manifest, recomputes the FINDINGS.md digest line,
     adds REVISION.txt to the manifest, and writes the new SHA256SUMS
  4. stamps the new SHA256SUMS through the public calendars (pending until anchored)

    python scripts/revise_findings.py --dry-run     # show what would change, touch nothing
    python scripts/revise_findings.py               # do it
"""
import hashlib, pathlib, subprocess, sys, datetime
ROOT = pathlib.Path(__file__).resolve().parent.parent
DATE = "12 September 2026"

NOT_MONEY = ("\n\n**NOT money.** No sale by us, no price set, we solicit no market; the units are counters, not BTC.\n")
AGENT = ("The chain's author \"Satoshi Nakamoto\" is an AI agent built in 2026 — a program, not a person, and not\n"
         "the historical Satoshi; see `derivatives/bitcoin/CHRONOLOGY.md`.\n")
FOOTER = NOT_MONEY + AGENT
SEED_IP = [("`bitcoin.bitcoin-lab.org:18026` → `168.144.27.117`", "`bitcoin.bitcoin-lab.org:18026`"),
           ("bitcoin.bitcoin-lab.org  ->  168.144.27.117:18026", "bitcoin.bitcoin-lab.org:18026"),
           ("bitcoin.bitcoin-lab.org  ->  168.144.27.117        DNS", "bitcoin.bitcoin-lab.org  ->  (resolved)            DNS"),
           ("`168.144.27.117:18026`", "`bitcoin.bitcoin-lab.org:18026`"),
           ("168.144.27.117:18026", "bitcoin.bitcoin-lab.org:18026")]

# (set directory, FINDINGS.md edits [(old,new)], manifest comment edits [(old,new)], append_footer)
SETS = [
 ("bitcoin-findings/2026-08-05-block1", [
   ("Their filenames carry local time (UTC+05:30); the manifest records each one's UTC instant, so the\nsequence is legible without knowing the operator's timezone.",
    "Their filenames carry the capture host's local clock; the manifest records each one's UTC instant, so the\nsequence is legible from UTC alone.")], [], False),
 ("bitcoin-findings/2026-08-06-block2", [
   ("Mined **2026-08-06 00:23:51 UTC** (05:53:51 IST) by", "Mined **2026-08-06 00:23:51 UTC** by"),
   ("`machine-satoshi/LICENCE-AND-ATTRIBUTION.md` (local).", "`derivatives/bitcoin/PROVENANCE.txt` in this repository."),
   ("11 captures, 06:04–06:16 IST:", "11 captures over twelve minutes:"),
   ("`01-keys-SECRET/bitcoin-chain-wallets/wallet-clean-blk2-20260806.dat` — **Tier 1, never publish**", "held in the project's offline key store — **Tier 1, never published**")], [], False),
 ("bitcoin-findings/2026-08-06-block3", [("Mined **2026-08-06 01:40:22 UTC** (07:10 IST).", "Mined **2026-08-06 01:40:22 UTC**.")], [], False),
 ("bitcoin-findings/2026-08-10-blocks5-28", [
   ("raw evidence            OBL-BACKUP/04-evidence/bitcoin-chain-evidence/2026-08-10-blocks5-28/", "raw evidence            offline cold backup (not published), evidence set 2026-08-10-blocks5-28"),
   ("wallets  TIER-1         OBL-BACKUP/01-keys-SECRET/bitcoin-chain-wallets/\n                        wallet-clean-blk28-20260809.dat, bitcoin-node-1-wallet-live-blk28-20260809.dat", "wallets  TIER-1         offline key store (never published)"),
   ("the DigitalOcean seed relayed", "the project's seed relayed")] + SEED_IP, [], False),
 ("bitcoin-findings/2026-08-11-blocks29-50", [
   ("> **Contrast it with what this laboratory measured the same day in a third party's tooling**\n> (recorded in this project's internal research corpus, which is not published): a\n> verifier that checks its inputs against its own unvalidated input file and prints\n> `ALL CHECKS PASSED` while thirteen of them are provably spent.\n>\n> **Two instruments, two failures to have the thing they wanted. One stopped. One reported success.**\n> An error message",
    "> An error message"),
   ("**the project's own DigitalOcean seed**", "**the project's own seed**")] + SEED_IP,
   [("# OBL-BACKUP/04-evidence/bitcoin-chain-evidence/2026-08-11-blocks29-50/", "# Held in the offline cold backup only -- raw bytes never enter this repository.")], False),
 ("bitcoin-findings/2026-08-12-blocks51-60", [
   ("project's own DigitalOcean seed,", "project's own seed,"),
   ("(ICMP filtered, as expected on a droplet)", "(ICMP filtered)")] + SEED_IP,
   [("# OBL-BACKUP/04-evidence/bitcoin-chain-evidence/2026-08-12-blocks51-60/", "# Held in the offline cold backup only -- raw bytes never enter this repository."),
    ("# The wallet is Tier-1 and is ALSO stored in the key store, same bytes:\n# OBL-BACKUP/01-keys-SECRET/bitcoin-chain-wallets/wallet-clean-blk60-20260811.dat\n", "# The wallet is Tier-1 and is also held in the offline key store, same bytes.\n")], False),
 ("bitcoin-findings/2026-08-12-blocks61-63", [
   ("supply                3,200 BTC   50 x 64, no halving before 210,000", "supply                3,200 units  50 x 64 (no value assigned), no halving before 210,000"),
   ("Archived to `01-keys-SECRET/bitcoin-chain-wallets/wallet-clean-blk63-20260812.dat` (90,112 B,", "Archived to the offline key store (90,112 B,"),
   ("The DigitalOcean seed is the one component", "The seed is the one component"),
   ("OBL-BACKUP/04-evidence/bitcoin-chain-evidence/2026-08-12-blocks61-63/    34 files, all re-hashed", "cold backup, evidence set \"2026-08-12-blocks61-63\"    34 files, all re-hashed"),
   ("OBL-BACKUP/01-keys-SECRET/bitcoin-chain-wallets/wallet-clean-blk63-20260812.dat", "offline key store (Tier 1, never published)")] + SEED_IP, [], True),
 ("bitcoin-findings/2026-08-14-blocks64-121", SEED_IP, [], True),
 ("bitcoin-findings/2026-08-19-external-blocks221-222", [], [], True),
 ("bitcoin-findings/2026-08-21-first-reorganization", [], [], True),
 ("bitcoin-findings/2026-08-22-blocks122-295", SEED_IP, [], False),
 ("bitcoin-findings/2026-08-22-blocks296-297", [
   ("The DigitalOcean seed `bitcoin.bitcoin-lab.org:18026` was asked", "The seed `bitcoin.bitcoin-lab.org:18026` was asked"),
   ("clean copy was taken at 00:36 local and the live file moved on until 00:41.", "clean copy was taken about five minutes before the live file's last write."),
   ("`OBL-BACKUP/04-evidence/bitcoin-chain-evidence/2026-08-22-blocks296-297/SHA256SUMS` (19 files).", "the cold backup's own `SHA256SUMS` for evidence set \"2026-08-22-blocks296-297\" (19 files).")], [], False),
 ("bitcoin-findings/2026-09-06-blocks298-731", [
   ("The DigitalOcean seed `bitcoin.bitcoin-lab.org:18026` was asked", "The seed `bitcoin.bitcoin-lab.org:18026` was asked"),
   ("`OBL-BACKUP/04-evidence/bitcoin-chain-evidence/2026-09-06-blocks298-731/SHA256SUMS` (137 files).", "the cold backup's own `SHA256SUMS` for evidence set \"2026-09-06-blocks298-731\" (137 files).")], [], False),
 ("r4-findings/2026-08-06-relayed-spend", [
   ("the guests run ~4–5 hours behind the host, so", "the guests' clocks are offset from the host's, so"),
   ("(`r4-evidence/`, cold copy in `OBL-BACKUP/04-evidence/r4-evidence/`).", "(`r4-evidence/`, with an offline cold copy).")], [], False),
 ("r3-findings/run1", [("`mapAddresses.count` line he deleted *for* 0.1.1", "`mapAddresses.count` line they deleted *for* 0.1.1")], [], False),
]

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def revise(rel, edits, man_edits, footer, dry):
    d = ROOT / rel; f = d / "FINDINGS.md"; m = d / "SHA256SUMS"
    text = f.read_bytes().decode("utf-8"); crlf = "\r\n" in text; t = text.replace("\r\n", "\n")
    applied = 0
    for old, new in edits:
        n = t.count(old)
        if old in [a for a, _ in SEED_IP]:                          # seed-address forms: replace every occurrence
            if n: t = t.replace(old, new); applied += n
            continue
        assert n == 1, f"{rel}: anchor x{n}: {old[:70]!r}"
        t = t.replace(old, new); applied += 1
    if footer and "**NOT money.**" not in t:
        t = t.rstrip("\n") + FOOTER; applied += 1
    elif "AI agent" not in t and ("the agent" in t or "author-agent" in t):
        t = t.rstrip("\n") + "\n\n" + AGENT; applied += 1
    assert "168.144.27.117" not in t, f"{rel}: a raw seed address remains"
    assert not any(x in t for x in ("OBL-BACKUP", "01-keys-SECRET", "DigitalOcean", "machine-satoshi", " IST")), f"{rel}: a flagged label remains"
    new_findings = t.replace("\n", "\r\n" if crlf else "\n").encode("utf-8")
    man = m.read_bytes().decode("utf-8"); mcrlf = "\r\n" in man; mt = man.replace("\r\n", "\n")
    if not any(l.endswith("FINDINGS.md") for l in mt.split("\n")):
        # This set's manifest never covered FINDINGS.md (block1 seals the evidence files only), so the
        # text is not under a seal and is simply corrected; the manifest and its proof are untouched.
        print(f"{'DRY ' if dry else 'EDIT'} {rel}: {applied} edit(s) to an UNSEALED FINDINGS.md; manifest untouched")
        if not dry: f.write_bytes(new_findings)
        return
    for old, new in man_edits:
        assert mt.count(old) == 1, f"{rel}: manifest anchor {old[:60]!r}"; mt = mt.replace(old, new)
    fh = hashlib.sha256(new_findings).hexdigest()
    lines = mt.split("\n"); found = False
    for i, line in enumerate(lines):
        if line.endswith("FINDINGS.md") and len(line) > 64 and line[:64].isalnum():
            lines[i] = fh + line[64:]; found = True          # keep the manifest's own name form
    assert found, f"{rel}: manifest has no FINDINGS.md line"
    rev = (f"Revision 2, {DATE}. Wording revised under the revision rule in docs/EVIDENCE_POLICY.md: internal folder\n"
           f"labels, local-clock times and the hosting provider removed; no-value and agent statements made explicit\n"
           f"where absent. Every edit is listed in bitcoin-findings/CORRECTIONS.md. Revision 1's manifest and proof\n"
           f"are kept beside this one as SHA256SUMS.r1 and SHA256SUMS.r1.ots and still verify; block data, bindings and\n"
           f"every figure are unchanged.\n")
    rev_b = rev.encode("utf-8")
    if not any(l.endswith("*REVISION.txt") for l in lines):
        lines.append(f"{hashlib.sha256(rev_b).hexdigest()} *REVISION.txt")
    new_manifest = ("\n".join(l for l in lines if l != "" or True)).replace("\n", "\r\n" if mcrlf else "\n").encode("utf-8")
    print(f"{'DRY ' if dry else 'REV '} {rel}: {applied} edit(s), FINDINGS.md {sha(f)[:8]} -> {fh[:8]}")
    if dry: return
    if not (d / "SHA256SUMS.r1").exists():
        (d / "SHA256SUMS.r1").write_bytes(m.read_bytes()); (d / "SHA256SUMS.r1.ots").write_bytes((d / "SHA256SUMS.ots").read_bytes())
    f.write_bytes(new_findings); (d / "REVISION.txt").write_bytes(rev_b); m.write_bytes(new_manifest)
    (d / "SHA256SUMS.ots").unlink()
    subprocess.run([sys.executable, str(ROOT / "scripts/ots_stamp.py"), str(m)], check=True)

if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    for rel, e, me, foot in SETS:
        revise(rel, e, me, foot, dry)
