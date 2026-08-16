#!/usr/bin/env python3
"""check_crossrefs.py — three classes of drift that no gate in this repo examines.

`check_template.py` verifies that each table sits under the right caption.
`revision_check_live.py` verifies that numbers in the manuscript match the engine.
Neither looks at:

  1. PROSE CROSS-REFERENCES.  "Table 1 gives the axes" is a hand-typed integer. Inserting a
     table anywhere earlier renumbers every reference after it, silently. This is how the
     current draft points at the exclusion table three times while meaning the axis matrix.

  2. SPELLED-OUT NUMERALS.  check_template.py §4 compares digit literals against figures.json.
     "eighteen" never matches 17, so a quantity written as a word is invisible to every gate.

  3. THE AUDIT CLAIM.  obl_metric.py's AUDITED dict says which cells were fetched. The fetching
     is done by audit_btc.py and audit_descendants.py. The dict is hand-transcribed from them
     and nothing compares the two — the engine-to-paper drift that was just eliminated,
     reintroduced one layer upstream.

    python3 check_crossrefs.py [package dir]
"""
import re, sys, importlib.util
from pathlib import Path

D = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
problems = 0


def say(kind, msg):
    global problems
    problems += 1
    print(f"  {kind:9} {msg}")


paper = (D / "paper.md").read_text(encoding="utf-8")
tpl = (D / "paper.template.md").read_text(encoding="utf-8")

# ── 1. prose "Table N" references against the actual caption order ────────────────────────
print("\n1. PROSE CROSS-REFERENCES vs ACTUAL TABLE ORDER")
# Captions are the ': ' blocks bound to a pipe table. Pandoc binds a caption on EITHER side of the
# table, and this only looked BELOW the caption for a table.
#
# ⛔ THAT BLIND SPOT MADE THIS CHECK REPORT THE OPPOSITE OF THE TRUTH. The axis table's caption sits
#    AFTER its table (it must: the table is wrapped in \blandscape…\elandscape, and a caption on the
#    far side of a raw-LaTeX block cannot bind). This scanner skipped that table entirely, renumbered
#    everything after it one lower, and then flagged the manuscript's CORRECT "Table 2" as stale.
#  ★ A checker with a stale model of the document does not fail quietly — it accuses the document.
order, seen = [], 0
for m in re.finditer(r"^: (.+?)(?=\n\n)", paper, re.M | re.S):
    tail = paper[m.end():m.end() + 400]
    head = paper[max(0, m.start() - 400):m.start()]
    below = re.search(r"^\s*\|", tail, re.M)
    above = re.search(r"\|[^\n]*\|\s*\n?\s*$", head)
    if below or above:
        seen += 1
        order.append(re.sub(r"\s+", " ", m.group(1))[:60])
for i, c in enumerate(order, 1):
    print(f"    Table {i}: {c}…")
if not order:
    print("    (no captions found — check the caption syntax)")

# a crude topic map so a reference can be judged
TOPIC = [
    (r"(?i)axes|axis matrix|consensus axes", "the axis matrix"),
    (r"(?i)mismatch rate and coverage", "the rate/coverage grid"),
    (r"(?i)decomposition", "the provenance decomposition"),
    (r"(?i)selection rule applied to candidates", "the exclusion audit"),
]
print()
for m in re.finditer(r"Table (\d+)", tpl):
    n = int(m.group(1))
    a = max(0, m.start() - 120)
    ctx = re.sub(r"\s+", " ", tpl[a:m.end() + 120])
    if n > len(order):
        say("STALE REF", f"'Table {n}' but only {len(order)} tables exist")
        continue
    cap = order[n - 1]
    want = next((t for rx, t in TOPIC if re.search(rx, ctx)), None)
    got = next((t for rx, t in TOPIC if re.search(rx, cap)), None)
    if want and got and want != got:
        say("STALE REF", f"'Table {n}' is {got}, but the sentence is about {want}\n"
                         f"            …{ctx[max(0,len(ctx)//2-70):][:150]}…")
if problems == 0:
    print("  ok        every prose table reference points at the right table")

# ── 2. spelled-out numerals standing for engine quantities ────────────────────────────────
print("\n1c. SECTION POINTERS THAT RESOLVE TO NOTHING")
# ⛔ ADDED R10. "Section 2.1 explains why" pointed at a heading that does not exist -- the material
#    it meant renders as an unnumbered subsubsection. Nine of the paper's ten Section-N references
#    resolved; this one broke on the round it was written, and an external referee found it.
#  ★ Rounds 8, 9 and 10 each closed cleanly and each introduced exactly one new defect of this
#    same family: a hand-typed pointer attached to prose that was genuinely improving. The argument
#    and the arithmetic were never wrong. **The connective tissue was.** So check the tissue.
_heads = set()
for _m in re.finditer(r"^(#{1,6})\s+(\d+(?:\.\d+)*)", paper, re.M):
    _heads.add(_m.group(2))
_refs = sorted(set(re.findall(r"Section\s+(\d+(?:\.\d+)*)", paper)))
_dead = [r for r in _refs if r not in _heads]
for r in _dead:
    say("DEAD SECTION REF", f"the manuscript says “Section {r}” and no such numbered heading "
                           f"exists (headings present: {', '.join(sorted(_heads))})")
if not _dead:
    print(f"  ok       all {len(_refs)} Section-N references resolve to a real heading")

print("\n2. SPELLED-OUT NUMERALS WHERE THE ENGINE HAS A NUMBER")
before = problems
WORDS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
    "fifteen sixteen seventeen eighteen nineteen twenty".split())}
# A word-numeral is only a defect when it DISAGREES with the engine. Each entry pairs a phrase
# with the figures.json key that governs it, so this reports facts, not style.
import json
figs = json.loads((D / "tables" / "figures.json").read_text(encoding="utf-8"))
GOVERNED = [
    (r"\b(%s)\s+perturbations\b" % "|".join(WORDS), "n_sensitivity", 4),
    (r"dropping up to three of the (%s)\s+axes" % "|".join(WORDS), "n_axes", None),
    (r"survives all (%s)\b" % "|".join(WORDS), "n_sensitivity", 4),
    (r"printing (%s) and (%s) blank cells" % ("|".join(WORDS), "|".join(WORDS)), None, None),
]
for rx, key, fallback in GOVERNED[:3]:
    for m in re.finditer(rx, tpl, re.I):
        got = WORDS[m.group(1).lower()]
        want = figs.get(key, fallback)
        if want is not None and got != want:
            a = max(0, m.start() - 80)
            say("WORD-NUM", f"“{re.sub(chr(10),' ',tpl[a:m.end()+40])}” "
                            f"— engine says {want}, the word says {got}")
# the blank-cell count is derivable: n_axes minus what each early reference specifies
m = re.search(GOVERNED[3][0], tpl, re.I)
if m:
    got = (WORDS[m.group(1).lower()], WORDS[m.group(2).lower()])
    want = (figs["n_axes"] - 1, figs["n_axes"] - 2)
    if got != want:
        say("WORD-NUM", f"“printing {m.group(1)} and {m.group(2)} blank cells” — with "
                        f"{figs['n_axes']} axes and references specifying 1 and 2, it is "
                        f"{want[0]} and {want[1]}")

# ── 3. the engine's audit claim vs what the audit scripts actually probe ───────────────────
print("\n3. ENGINE AUDIT CLAIM vs AUDIT SCRIPT COVERAGE")
before = problems
spec = importlib.util.spec_from_file_location("obl", D / "obl_metric.py")
obl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(obl)
claimed = set(obl.AUDITED)


def checks_block(p):
    t = (D / p).read_text(encoding="utf-8")
    m = re.search(r"^CHECKS = \[.*?^\]", t, re.M | re.S)
    return m.group(0) if m else ""


probed = {("BTC", a) for a in re.findall(r'\(\s*"([a-z0-9_]+)",\s*"bip-', checks_block("audit_btc.py"))}
probed |= {(c, a) for c, a in re.findall(r'\(\s*"(BSV|BCH|XEC)",\s*"([a-z0-9_]+)"',
                                         checks_block("audit_descendants.py"))}
print(f"    probed by a script: {len(probed)}   claimed fetched by the engine: {len(claimed)}")
for c in sorted(probed - claimed):
    say("UNCOUNTED", f"{c[0]}/{c[1]} is probed and confirmed by an audit script but the engine "
                     f"classifies it as unclassified — the coverage table understates itself")
for c in sorted(claimed - probed):
    say("UNBACKED", f"{c[0]}/{c[1]} is counted as fetched but no audit script probes it")
if problems == before:
    print("  ok        the engine's audit claim matches the scripts")

print("\n" + "-" * 78)
print(f"{problems} problems.")
sys.exit(min(problems, 120))
