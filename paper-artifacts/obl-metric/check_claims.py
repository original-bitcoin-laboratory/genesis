#!/usr/bin/env python3
"""check_claims.py — the paper's QUALITATIVE claims, as predicates over the dataset.

Every gate in this repo checks that a NUMBER in the prose equals a NUMBER in the engine.
None checks that a CLAIM still follows from the data. Adding `pow_function` and
`coinbase_height` falsified three load-bearing sentences and every gate stayed green,
because none of them is about a number:

    "the three references disagree with each other wherever they overlap at all"
    "the single consensus axis the whitepaper specifies"
    "Every axis the November pre-release shares with v0.1.0 also differs"

A claim that is true of the data today and asserted in prose is a claim that must be
re-derived when the data changes. Below, each is a predicate. If a cell edit falsifies
one, the build fails and names the sentence to rewrite.

    python3 check_claims.py [package dir]
"""
import json, re, sys
from pathlib import Path

D = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
cmp = json.loads((D / "artifacts" / "comparison.json").read_text(encoding="utf-8"))
paper = (D / "paper.md").read_text(encoding="utf-8")
axes, profiles = cmp["axes"], cmp["profiles"]
REFS = ["whitepaper", "nov08", "v0.1.0"]
CHAINS = [p for p in profiles if p not in REFS]
val = lambda a, p: a["p"][p]["value"]
fails = []


def claim(name, sentence, holds, detail=""):
    """`sentence` is a substring of the manuscript that asserts `holds`."""
    asserted = sentence.lower() in re.sub(r"\s+", " ", paper).lower()
    mark = "ok  " if holds else "FAIL"
    if asserted and not holds:
        fails.append(name)
        print(f"  FAIL {name}\n       the manuscript asserts: \u201c{sentence}\u201d\n"
              f"       the data no longer supports it: {detail}")
    elif not asserted and holds:
        print(f"  ok   {name}  (holds; sentence not found — check the wording)")
    else:
        print(f"  {mark} {name}")


print("\nQUALITATIVE CLAIMS, RE-DERIVED FROM THE DATASET\n")

# 1. references disagree wherever they overlap
rd = cmp["reference_disagreement"]
overlapping = {k: v for k, v in rd.items() if v["jointly_specified"] > 0}
agree = {k: v for k, v in overlapping.items() if v["differing"] == 0}
claim("references disagree wherever they overlap",
      "disagree with each other wherever they overlap at all",
      not agree,
      f"{', '.join(agree)} overlap on {[v['jointly_specified'] for v in agree.values()]} axis/axes "
      f"and DIFFER ON NONE")

# 2. every nov08/v0.1.0 shared axis differs
nv = rd.get("nov08|v0.1.0", {})
claim("every nov08 axis shared with v0.1.0 differs",
      "Every axis the November pre-release shares with v0.1.0 also differs",
      nv.get("jointly_specified") == nv.get("differing"),
      f"{nv.get('jointly_specified')} shared, {nv.get('differing')} differing")

# 3. the whitepaper specifies exactly one axis
wp = [a["id"] for a in axes if val(a, "whitepaper") is not None]
claim("whitepaper specifies one axis",
      "the single consensus axis the whitepaper specifies",
      len(wp) == 1,
      f"it specifies {len(wp)}: {', '.join(wp)}")

# 4. the November profile specifies exactly two parameters
nv08 = [a["id"] for a in axes if val(a, "nov08") is not None]
claim("November specifies two parameters",
      "two specified parameters",
      len(nv08) == 2,
      f"it specifies {len(nv08)}: {', '.join(nv08)}")

# 5. no generated table says "no overlap" for a pair that overlaps
t6 = (D / "tables" / "table6_refdis.md")
bad = []
if t6.exists():
    for line in t6.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) == 4 and cells[1].isdigit() and int(cells[1]) > 0 and "no overlap" in cells[3]:
            bad.append(cells[0])
if bad:
    fails.append("table6 no-overlap")
    print(f"  FAIL table6 no-overlap string\n       row {bad[0]!r} reports overlap > 0 and prints "
          f"\u201c(no overlap -- undefined)\u201d in the same row")
else:
    print("  ok   table6 no-overlap string")

# 6. every chain cell's warrant is of the right KIND
#    'absence' is for claims that a rule is ABSENT; a positive value cannot be one.
ABSENT_TOKENS = {"none", "not-required", "nops", "ecdsa-only", "no-consensus-cap",
                 "no-dedicated-cap", "topological"}
sys.path.insert(0, str(D))
import importlib.util
spec = importlib.util.spec_from_file_location("obl", D / "obl_metric.py")
obl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(obl)
byid = {a["id"]: a for a in axes}
miscat = [(c, ax, val(byid[ax], c)) for (c, ax) in getattr(obl, "ABSENCE", set())
          if val(byid[ax], c) not in ABSENT_TOKENS]
if miscat:
    fails.append("absence warrant")
    print("  FAIL absence warrant holds a positive value")
    for c, ax, v in sorted(miscat):
        print(f"       {c}/{ax} = {v!r} is an affirmative claim, not an absence")
else:
    print("  ok   absence warrant holds only absences")

# 7. 'inherited' means pre-dating every fork — a chain-specific innovation cannot be one
innov = []
for (c, ax) in getattr(obl, "INHERITED", set()):
    v = val(byid[ax], c)
    others = {val(byid[ax], p) for p in CHAINS + ["v0.1.0"] if p != c}
    if v not in others:
        innov.append((c, ax, v))
# ⚠️ WARN, not FAIL. A value can be genuinely inherited and yet unique today, because the
#    ancestor has since changed it (BSV's cw-144 came from BCH in Nov 2017; BCH has since moved
#    to ASERT). Distinguishing that from a chain's own innovation needs a `forked_from` /
#    `forked_on` field the dataset does not carry — so this reports for adjudication rather
#    than convicting. A check that convicts an innocent cell is the failure mode this project
#    has hit four times.
if innov:
    print("  WARN inherited warrant holds values unique to one chain — adjudicate each:")
    for c, ax, v in sorted(innov):
        print(f"       {c}/{ax} = {v!r} appears on no other profile")
    print("       (legitimate where the ancestor has since changed; NOT legitimate for a value"
          "\n        the chain introduced at its own fork)")
else:
    print("  ok   inherited warrant holds only shared values")

print("\n" + "-" * 78)
print(f"{len(fails)} claims no longer supported by the data.")
sys.exit(min(len(fails), 120))
