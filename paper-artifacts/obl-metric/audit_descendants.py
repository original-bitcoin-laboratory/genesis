#!/usr/bin/env python3
"""Census the BCH / BSV / XEC columns against their primary specifications. NOT money.

`audit_btc.py` did this for BTC against the BIPs repository and found 8/8. **The other three
columns were the paper's largest unverified surface** — 51 specified cells resting on citations
that had never been fetched. Two referee rounds asked for exactly this.

⚠️ WHAT A PASS MEANS, AND WHAT IT DOES NOT — same limit as audit_btc.py.
   A specification says what a rule IS and, sometimes, when it activates. It does not by itself
   prove the rule is in force on mainnet at the freeze. Where a spec states an activation height
   or MTP, this reports it.

⚠️ EVERY FETCH CARRIES A SELF-NAMING CONTROL, and it is not decoration.
   An HTTP 200 from a bot-walled host is a 200 FOR THE CHALLENGE PAGE. A document that does not
   name itself is not the document the URL claims, and its probe is VOID rather than negative.
   ⇒ **A positive control proves the endpoint answers; only this one proves it is answering the
     question we asked.**

★ THE PATTERNS BELOW WERE WRITTEN FROM THE DOCUMENTS, NOT FROM MEMORY. A first pass guessed the
  wording and produced failures against files that were correct — the same way a BIP control once
  demanded `BIP66` where the header reads `BIP: 66`. **Read the source, then write the pattern.**

Run:  python audit_descendants.py
"""
import io
import re
import ssl
import sys
import time
import urllib.error
import urllib.request

try:
    import certifi
    CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    CTX = ssl.create_default_context()
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
UA = {"User-Agent": "Mozilla/5.0 obl-research/1.0 (academic; consensus-rule census)"}

RAW = "https://raw.githubusercontent.com/"
BSVU = RAW + "bitcoin-sv-specs/protocol/master/updates/"
BCN = "https://upgradespecs.bitcoincashnode.org/"

# doc key -> (url, control regex the document MUST contain to be what the URL claims)
DOCS = {
    "bsv_genesis":   (BSVU + "genesis-spec.md", r"(?i)genesis upgrade specification"),
    "bsv_chronicle": (BSVU + "chronicle-spec.md", r"(?i)chronicle"),
    "bch_2018":      (RAW + "bitcoincashorg/bitcoincash.org/master/spec/may-2018-reenabled-opcodes.md",
                      r"(?i)re-?enabled? opcodes|may,? 2018"),
    "bch_ctor":      (BCN + "2018-nov-upgrade/", r"(?i)2018-nov|november,? 2018"),
    "bch_schnorr":   (BCN + "2019-05-15-upgrade/", r"(?i)2019-05-15|may,? 2019"),
    "bch_asert":     (BCN + "2020-11-15-upgrade/", r"(?i)2020-11-15|november,? 2020"),
    "bch_int64":     (BCN + "2022-05-15-upgrade/", r"(?i)2022-05-15|may,? 2022"),
    "bch_abla":      (BCN + "2024-05-15-upgrade/", r"(?i)2024-05-15|may,? 2024"),
    "bch_vm_limits": (RAW + "bitjson/bch-vm-limits/master/readme.md",
                      r"(?i)vm limits|virtual machine limits"),
    "bch_bigint":    (RAW + "bitjson/bch-bigint/master/readme.md", r"(?i)bigint|big ?integer"),
    "abc_src":       (RAW + "Bitcoin-ABC/bitcoin-abc/master/src/script/script.h",
                      r"(?i)MAX_SCRIPT|SCRIPT_H"),
    # ★ R5: BTG entered as the fifth column with ZERO fetched cells while its source was a
    #   fetchable file the whole time. "The newest column entered unfetched" is exactly the
    #   drift this script exists to prevent.
    "btg_src":       (RAW + "BTCGPU/BTCGPU/master/src/chainparams.cpp",
                      r"(?i)chainparams|CMainParams"),
}

# (chain, axis, our cell value, doc key, regex, what a hit proves)
CHECKS = [
    # ---- BSV --------------------------------------------------------------------------------
    ("BSV", "block_size_rule", "no-consensus-cap", "bsv_genesis",
     r"(?i)configurable consensus rule[^.]{0,140}maximum accepted block size",
     "the maximum block size is a CONFIGURABLE consensus rule, not a constant"),
    ("BSV", "p2sh", "none", "bsv_genesis",
     r"(?i)#+\s*sunset p2sh", "P2SH is sunset by the Genesis upgrade"),
    ("BSV", "timelock_opcodes", "nops", "bsv_genesis",
     r"(?i)#+\s*sunset op_checklocktimeverify\s*&\s*op_checksequenceverify",
     "★ CLTV/CSV are sunset — the cell an earlier round corrected, now confirmed at the heading"),
    ("BSV", "element_size_limit", "none", "bsv_genesis",
     r"(?i)limits the maximum size of a script element has been removed",
     "the script-element size limit is removed in terms"),
    ("BSV", "script_opcodes", "broad", "bsv_genesis",
     r"(?i)OP_MUL|OP_LSHIFT|OP_RSHIFT|OP_INVERT|OP_CAT",
     "previously-disabled operations are named as available"),
    ("BSV", "script_number_width", "32mb-limit", "bsv_chronicle",
     r"(?i)maximum script number size is increased from 750KB to 32MB",
     "★ Chronicle raises the script-number consensus limit 750KB -> 32MB"),
    ("BSV", "script_number_width", "32mb-limit", "bsv_chronicle",
     r"943,?835", "Chronicle's stated mainnet activation height"),
    # ---- BCH --------------------------------------------------------------------------------
    ("BCH", "block_size_rule", "abla-dynamic", "bch_abla",
     r"(?i)ABLA|adaptive block ?size", "the block-size limit became algorithmically varying"),
    ("BCH", "element_size_limit", "10000-byte", "bch_vm_limits",
     r"(?i)10,?000", "the stack element limit is raised to 10,000 bytes"),
    ("BCH", "script_number_width", "large-bigint", "bch_bigint",
     r"(?i)big.?int", "★ arbitrary-precision script integers (the 2025 upgrade, NOT 2022's 64-bit)"),
    ("BCH", "difficulty_algorithm", "asert", "bch_asert",
     r"(?i)aserti3|ASERT", "ASERT is the difficulty algorithm"),
    ("BCH", "tx_ordering", "ctor", "bch_ctor",
     r"(?i)canonical.{0,40}order|CTOR", "canonical transaction ordering"),
    ("BCH", "sig_scheme", "ecdsa+schnorr", "bch_schnorr",
     r"(?i)schnorr", "Schnorr signatures alongside ECDSA"),
    ("BCH", "script_opcodes", "partial-restore", "bch_2018",
     r"(?i)OP_CAT|OP_SPLIT", "opcodes are partially restored"),
    # ---- XEC --------------------------------------------------------------------------------
    ("XEC", "element_size_limit", "520-byte", "abc_src",
     r"MAX_SCRIPT_ELEMENT_SIZE\s*=\s*520",
     "★ ABC still enforces 520 — for a chain the implementation IS the rule"),
    ("XEC", "script_number_width", "8-byte", "abc_src",
     r"MAX_SCRIPTNUM_BYTE_SIZE\s*=\s*8", "★ ABC's script-number width is 8 bytes"),
    ("XEC", "script_opcodes", "partial-restore", "bch_2018",
     r"(?i)OP_CAT|OP_SPLIT", "XEC inherits the May-2018 opcode restoration"),
    ("XEC", "difficulty_algorithm", "asert+rtt", "bch_asert",
     r"(?i)aserti3|ASERT", "XEC inherits ASERT as its base DAA (RTT is scored on the same axis)"),
    # ---- BTG ---------------------------------------------------------------------------------
    ("BTG", "pow_function", "equihash-btg", "btg_src",
     r"(?i)equihash", "★ BTG's own chainparams names Equihash -- the axis BTG was added to expose"),
    ("BTG", "difficulty_algorithm", "lwma", "btg_src",
     r"(?i)LWMA", "★ LWMA is a POSITIVE rule in BTG's chainparams, not an absence"),
    ("BTG", "coinbase_height", "required", "btg_src",
     r"BIP34Height\s*=\s*227931", "BTG inherits Bitcoin's BIP34 height -- it forked after it"),
    ("BTG", "segwit", "segwit", "btg_src",
     r"SegwitHeight\s*=\s*481824", "BTG inherits segwit -- it forked at 491,406, after activation"),
    ("BTG", "block_spacing", "10-min", "btg_src",
     r"nPowTargetSpacing\s*=\s*10\s*\*\s*60", "the 10-minute target is unchanged"),
]

# Cells this script does NOT probe, and exactly why. Listed so coverage is never overstated.
ELSEWHERE = {
    "sig_encoding (all 3)": "BIP66 — confirmed by audit_btc.py",
    "p2sh (BCH, XEC)": "BIP16 — confirmed by audit_btc.py",
    "value_range_check (all 3)": "CVE-2010-5139 / MoneyRange — pre-dates every fork",
    "fork_choice (BCH, BSV)": "commit 3b7cd5d8 — content-addressed, pre-dates every fork",
    "replay_protection (all 3)": "SIGHASH_FORKID, Aug 2017 — shared ancestor of all three",
    "subsidy_base, block_spacing": "class-ii axes: unchanged everywhere, by construction",
    "block_size_rule (XEC)": "32 MB inherited from BCH May 2018; XEC has not adopted ABLA",
    "fork_choice (XEC)": "Avalanche post-consensus — e.cash, not a versioned spec document",
    "tx_ordering (BSV)": "topological — Genesis reverts CTOR; engine already marks it medium",
}

# ★ Cells that are CLAIMS OF ABSENCE. No document proves an absence, so these can never be
#   'confirmed' by this instrument and it would be dishonest to let them look confirmable.
ABSENCE = {
    "segwit = none (BCH, BSV, XEC)":
        "BCH forked 1 Aug 2017, three weeks BEFORE segwit locked in on BTC — it never had it to "
        "remove. Rests on chronology plus no upgrade spec introducing it",
    "taproot = none (BCH, BSV, XEC)":
        "same shape: taproot activated on BTC in Nov 2021, after all three had diverged",
    "sig_scheme = ecdsa-only (BSV)":
        "⚠️ FOUND BY THIS AUDIT: genesis-spec.md contains ZERO occurrences of 'ECDSA', 'Schnorr' "
        "or 'signature scheme'. The cell is right but its CITATION was wrong — it is an absence "
        "(BSV never adopted Schnorr), not something the Genesis spec states",
}


def get(u):
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60, context=CTX)
        return r.getcode(), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return None, str(e)


def body_text(t):
    """Strip site chrome before matching. ⛔ WHY THIS EXISTS — a real defect in the first run.

    Three probes 'confirmed' by matching inside navigation: `<link rel="next" href="../2020-11-15-
    asert/">` contains the string ASERT, and `<link rel="prev" href="../2019-11-15-minimaldata/">`
    sits next to one containing 'schnorr'. **A term in a nav href is not the page saying anything.**

    ★★ THAT IS THE BOT-WALLED-200 ERROR IN A NEW COSTUME: reading the ENVELOPE and calling it the
       LETTER. The fix is not a cleverer regex — it is to delete the envelope before reading.
    """
    t = re.sub(r"(?is)<(script|style|head)\b.*?</\1>", " ", t)
    t = re.sub(r"(?is)<[^>]+>", " ", t)            # all tags, therefore all href attributes
    return re.sub(r"\s+", " ", t)


print("""
  Census of the BCH / BSV / XEC columns against their primary specifications.
  ⚠️ Control on every fetch: the document must NAME ITSELF, or the probe is VOID — a 200 from a
     bot-walled host is a 200 for the challenge page, not an answer.""")

cache = {}
print("\n  FETCHING %d primary documents" % len(DOCS))
for k, (u, ctl) in DOCS.items():
    c, t = get(u)
    # ⛔ THE HEURISTIC WAS "does it contain a '<'", AND C++ SOURCE CONTAINS `#include <string>`.
    #    So chainparams.cpp was HTML-stripped: every `<...>` deleted, the file mangled, and two
    #    correct BTG probes reported EXPECTED TEXT NOT FOUND. **The patterns were right and the
    #    reader corrupted the evidence before they ran.**
    #    ★ A detector for a format must look for that FORMAT, not for one character it uses.
    # ⛔ BROKEN FROM 15 Aug 2026 UNTIL A GATE FOUND IT (stress_test test_I). Written through a
    #    shell heredoc, which turned each backslash-b into a real 0x08 byte, so this matched "<html"
    #    followed by a literal BACKSPACE and could never fire. Only the doctype alternative worked,
    #    so **HTML omitting a doctype was treated as source code** -- the failure mode that once let
    #    navigation chrome be read as a consensus value. Same slip a referee found in audit_btc.py.
    #    ⇒ Rewritten with a character class so no escape survives to be mangled again.
    is_html = bool(re.search(r"(?i)<!doctype html|<html[ >]|<head[ >]|<body[ >]", t[:4000])) if t else False
    t = body_text(t) if is_html else t
    good = c == 200 and len(t) > 400 and re.search(ctl, t) is not None
    cache[k] = (c, t, good)
    mark = "ok" if good else ("CONTROL FAILED" if c == 200 else "HTTP %s" % c)
    print("    %-14s %-15s %8s B" % (k, mark, len(t) if t else 0))
    time.sleep(0.4)

ok = bad = void = 0
cur = None
for chain, axis, val, doc, rx, proves in CHECKS:
    if chain != cur:
        print("\n" + "=" * 104 + "\n  " + chain)
        cur = chain
    c, t, docok = cache[doc]
    print("\n  %-22s %-20s <- %s" % (axis, val, doc))
    if not docok:
        print("     ⚠ SOURCE UNRESOLVED (HTTP %s) — NOT a negative; the probe is void" % c)
        void += 1
        continue
    m = re.search(rx, t)
    if m:
        ok += 1
        a, z = max(0, m.start() - 110), min(len(t), m.end() + 150)
        print("     ✅ %s" % proves)
        print("        …%s…" % re.sub(r"\s+", " ", t[a:z]).strip()[:205])
    else:
        bad += 1
        print("     ⛔ EXPECTED TEXT NOT FOUND — our value may be wrong, or the regex is")

print("\n" + "=" * 104)
print(" DESCENDANT PROBES: %d confirmed, %d not found, %d void" % (ok, bad, void))
print("=" * 104)

# ── emit the audit artifact, and BE A GATE ────────────────────────────────────────────────────
# ⛔ R4: this script printed totals and exited 0 EVEN WITH EVERY PROBE VOID. A CI run with no
#    network could "pass the source audit" while verifying nothing, and METHOD.md advertises it as
#    yielding 18/18. ★★ A script that cannot fail is not a gate, it is a report — the same finding
#    as the vacuous table check and the silent guardrail, now at the network layer.
#
# ★★★ AND THE DICT GOES AWAY. The engine carried AUDITED as a hand-maintained dictionary, so it
#     drifted one cell behind the probes (BSV/block_size_rule was fetched and reported unfetched).
#     Now the audit WRITES what it actually verified -- with the body SHA-256 of each document --
#     and the engine READS it. Same move, one layer out, as generating the tables and the captions.
import hashlib  # noqa: E402
import json  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

records = []
for chain, axis, val, doc, rx, proves in CHECKS:
    c, t, docok = cache[doc]
    m = re.search(rx, t) if docok else None
    records.append({
        "chain": chain, "axis": axis, "value": val, "doc": doc, "url": DOCS[doc][0],
        "http": c, "control_passed": bool(docok),
        "matched": bool(m), "match_text": (m.group(0)[:120] if m else None),
        "body_sha256": hashlib.sha256(t.encode("utf-8", "replace")).hexdigest() if docok else None,
        "proves": proves,
    })
ART = HERE_TABLES = None
try:
    from pathlib import Path as _P
    ART = _P(__file__).resolve().parent / "tables"
    ART.mkdir(exist_ok=True)
    payload = {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "script": "audit_descendants.py",
               "confirmed": ok, "not_found": bad, "void": void, "records": records}
    (ART / "audit_descendants.json").write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print("\n  wrote tables/audit_descendants.json  (%d records, each with its document's SHA-256)"
          % len(records))
except Exception as e:
    print("\n  ⚠ could not write the audit artifact: %s" % e)
print("\n  AUDITED ELSEWHERE, OR SHARED (%d groups):" % len(ELSEWHERE))
for k, v in ELSEWHERE.items():
    print("     %-30s %s" % (k, v))
print("\n  ★★ CLAIMS OF ABSENCE (%d) — UNCONFIRMABLE BY CONSTRUCTION, not merely unchecked:"
      % len(ABSENCE))
for k, v in ABSENCE.items():
    print("     %s\n        %s" % (k, v))
print("""
  ⇒ No document proves a rule is ABSENT. These rest on chronology — a fork cannot remove what it
    never had — plus the absence of any upgrade spec introducing it. **That is weaker than a
    positive citation, it is the weakest footing in the dataset, and the paper must keep saying so.**""")

# ⇒ THE GATE. Exit nonzero on any failed or unresolved probe, so a network-blind CI run cannot
#   certify an artifact it did not verify. `--report` restores the old advisory behaviour for
#   interactive use, and says so, because a flag that silently weakens a gate is worse than none.
if "--report" in sys.argv:
    print("\n  --report: exiting 0 regardless of outcome (advisory mode, NOT a certification).")
    sys.exit(0)
if bad or void:
    print("\n  ⛔ GATE FAILED: %d not found, %d void. An unresolved probe is not a pass." % (bad, void))
    sys.exit(1)
print("\n  ✅ GATE PASSED: every probe fetched, controlled and matched.")
sys.exit(0)
