#!/usr/bin/env python3
"""Census the BTC column against the BIPs repository. NOT money.

The BTC cells cite BIPs. **The BIPs repository is the primary record and it is fetchable**, so this
column can be audited exhaustively rather than sampled — which is what the paper's disclosure needs
and what two referee rounds found missing.

⚠️ WHAT A PASS HERE MEANS, AND WHAT IT DOES NOT.
   A BIP says what a rule IS and when it was PROPOSED. It does not by itself prove the rule is in
   force on mainnet at the freeze. For BTC that gap is closed by these deployments being long
   settled and universally documented; **for anything contested it would not be, and the check
   below reports the BIP text rather than asserting activation.**

Run:  python audit_btc.py
"""
import io
import re
import ssl
import sys
import time
import urllib.request

try:
    import certifi
    CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    CTX = ssl.create_default_context()
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
UA = {"User-Agent": "Mozilla/5.0 obl-research/1.0"}
BASE = "https://raw.githubusercontent.com/bitcoin/bips/master/"

# axis -> (bip file, our cell value, a regex that MUST appear if our value is right, what it proves)
CHECKS = [
    ("p2sh", "bip-0016.mediawiki", "p2sh",
     r"(?i)pay.to.script.hash|OP_HASH160 <20.byte hash> OP_EQUAL",
     "P2SH is a consensus rule with a special output template"),
    ("sig_encoding", "bip-0066.mediawiki", "strict-der",
     r"(?i)strict DER|DER.encoded", "strict-DER signature encoding is enforced"),
    ("timelock_opcodes", "bip-0065.mediawiki", "cltv+csv",
     r"(?i)CHECKLOCKTIMEVERIFY", "CLTV exists as a consensus opcode"),
    ("timelock_opcodes", "bip-0112.mediawiki", "cltv+csv",
     r"(?i)CHECKSEQUENCEVERIFY", "CSV exists as a consensus opcode"),
    ("segwit", "bip-0141.mediawiki", "segwit",
     r"(?i)segregated witness", "segwit is a consensus rule"),
    ("block_size_rule", "bip-0141.mediawiki", "1mb+weight",
     r"(?i)block weight|weight.*4,?000,?000|4000000",
     "the size rule became a WEIGHT limit, so '1mb+weight' is the right shape"),
    ("taproot", "bip-0341.mediawiki", "taproot",
     r"(?i)taproot", "Taproot outputs are a consensus rule"),
    ("sig_scheme", "bip-0340.mediawiki", "ecdsa+schnorr",
     r"(?i)schnorr", "Schnorr signatures exist alongside ECDSA"),
]

# Cells whose authority is NOT a BIP — recorded so the census is honest about its own coverage.
NON_BIP = {
    "fork_choice": "commit 3b7cd5d8 (v0.3.3) — most-work chain selection",
    "script_opcodes": "commit 4bd188c4 (15 Aug 2010) — opcode disable",
    "script_number_width": "commit 4bd188c4 — nMaxNumSize 258 -> 4",
    "element_size_limit": "commit 4bd188c4 — 520-byte element limit",
    "value_range_check": "CVE-2010-5139 fix — MoneyRange",
    "difficulty_algorithm": "unchanged from v0.1.0 (2016-block retarget)",
    "replay_protection": "unchanged from v0.1.0 (none)",
    "tx_ordering": "unchanged from v0.1.0 (topological)",
    "subsidy_base": "unchanged from v0.1.0 (50)",
    "block_spacing": "unchanged from v0.1.0 (10-min)",
}


def get(u):
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60, context=CTX)
        return r.getcode(), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return None, str(e)


print("""
  Census of the BTC column against the BIPs repository.
  ⚠️ A control runs on every fetch: the document must name its own BIP number, or it is not the
     document the URL claims and the probe is void.""")
cache, ok, bad, void = {}, 0, 0, 0
for axis, f, val, rx, proves in CHECKS:
    if f not in cache:
        c, t = get(BASE + f)
        cache[f] = (c, t)
        time.sleep(0.5)
    c, t = cache[f]
    num = re.search(r"bip-0*(\d+)", f).group(1)
    # ⚠️ The header reads "BIP: 66" — with a COLON. An earlier version of this pattern demanded
    #    "BIP66" or "BIP 66" and voided two probes that were fine. **The control was wrong, not the
    #    documents**, which is the third time this week a regex has convicted an innocent file.
    control = re.search(r"(?i)BIP:?\s*[- ]?0*%s\b" % num, t) is not None
    print("\n  %-22s %-22s %s" % (axis, val, f))
    if c != 200 or len(t) < 500:
        print("     HTTP %s — UNRESOLVED, not a negative" % c)
        void += 1
        continue
    if not control:
        print("     ⚠ CONTROL FAILED (document does not name BIP %s) — probe VOID" % num)
        void += 1
        continue
    m = re.search(rx, t)
    if m:
        ok += 1
        a, z = max(0, m.start() - 130), min(len(t), m.end() + 170)
        print("     ✅ %s" % proves)
        print("        …%s…" % re.sub(r"\s+", " ", t[a:z]).strip()[:230])
    else:
        bad += 1
        print("     ⛔ EXPECTED TEXT NOT FOUND — our value may be wrong, or the regex is")

print("\n" + "=" * 92)
print(" BIP-BACKED CELLS: %d confirmed, %d not found, %d void" % (ok, bad, void))
print("=" * 92)
print("\n  CELLS WHOSE AUTHORITY IS NOT A BIP (%d) — listed so coverage is not overstated:"
      % len(NON_BIP))
for k, v in sorted(NON_BIP.items()):
    print("     %-22s %s" % (k, v))
print("""
  ⇒ The commit-anchored ones (4bd188c4, 3b7cd5d8) are CONTENT-ADDRESSED and therefore stronger
    than any prose citation — a hash cannot go stale. The 'unchanged from v0.1.0' ones are claims
    about ABSENCE OF CHANGE, which no single document proves; they rest on the BIP index containing
    no proposal that alters them. **That is a weaker footing and the paper should say so.**""")


# ── the same gate, for the same reason (R4) ───────────────────────────────────────────────────
# ⛔ This script reported "0 confirmed, 0 not found, 8 void" in a network-blind environment and
#    STILL EXITED 0. METHOD.md advertises it as yielding 8/8. **A run that verified nothing must
#    not be able to certify anything.**
import json as _json, hashlib as _hl
from datetime import datetime as _dt, timezone as _tz
_recs = []
for _axis, _f, _val, _rx, _proves in CHECKS:
    _c, _t = cache.get(_f, (None, ""))
    _num = re.search(r"bip-0*(\d+)", _f).group(1)
    _ctl = re.search(r"(?i)BIP:?\s*[- ]?0*%s\b" % _num, _t) is not None if _t else False
    _m = re.search(_rx, _t) if (_c == 200 and _ctl) else None
    _recs.append({"chain": "BTC", "axis": _axis, "value": _val, "doc": _f, "url": BASE + _f,
                  "http": _c, "control_passed": bool(_ctl), "matched": bool(_m),
                  "match_text": (_m.group(0)[:120] if _m else None),
                  "body_sha256": _hl.sha256(_t.encode("utf-8", "replace")).hexdigest() if _t else None,
                  "proves": _proves})
try:
    from pathlib import Path as _P
    _a = _P(__file__).resolve().parent / "tables"; _a.mkdir(exist_ok=True)
    (_a / "audit_btc.json").write_text(_json.dumps(
        {"generated_utc": _dt.now(_tz.utc).isoformat(timespec="seconds"), "script": "audit_btc.py",
         "confirmed": ok, "not_found": bad, "void": void, "records": _recs}, indent=1),
        encoding="utf-8")
    print("\n  wrote tables/audit_btc.json  (%d records, each with its document's SHA-256)"
          % len(_recs))
except Exception as _e:
    print("\n  ⚠ could not write the audit artifact: %s" % _e)

# ⇒ THE GATE. `--report` restores advisory behaviour and says so, because a flag that silently
#   weakens a gate is worse than no gate at all.
if "--report" in sys.argv:
    print("\n  --report: exiting 0 regardless of outcome (advisory mode, NOT a certification).")
    sys.exit(0)
if bad or void:
    print("\n  ⛔ GATE FAILED: %d not found, %d void. An unresolved probe is not a pass."
          % (bad, void))
    sys.exit(1)
print("\n  ✅ GATE PASSED: every probe fetched, controlled and matched.")
sys.exit(0)
