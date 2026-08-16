#!/usr/bin/env python3
"""check_template.py — the gate build_paper.py's docstring promises and the repo does not have.

`build_paper.py` refuses to write a paper with a MISSING table. It does not check that the table
it inserted is the one the caption above it promises, that every generated table is used at all,
or that a number the engine emits was interpolated rather than retyped. Those are the three ways
the current draft is wrong, and no existing script looks at any of them.

    python3 check_template.py [paper.template.md] [tables/]

Exit status is the number of problems found.
"""
import json, re, sys
from pathlib import Path

TPL = Path(sys.argv[1] if len(sys.argv) > 1 else "paper.template.md")
TABLES = Path(sys.argv[2] if len(sys.argv) > 2 else "tables")
tpl = TPL.read_text(encoding="utf-8")
figs = json.loads((TABLES / "figures.json").read_text(encoding="utf-8"))
problems = []


def say(kind, msg):
    problems.append(kind)
    print(f"  {kind:8} {msg}")


# What each generated table is, identified by its header row rather than its filename, so a
# renamed or reordered file cannot pass by looking familiar.
SHAPE = {
    "| # | Axis |": "axis matrix (one row per axis, one column per profile)",
    "| reference |": "mismatch rate and coverage grid (one row per reference)",
    "| chain | matches |": "retention/restoration decomposition",
    "| chain | base |": "merged-cluster individuation",
    "| relabelling |": "label-granularity re-scoring",
    # added 14 Aug 2026 with the two tables that were hand-typed until this checker found them
    "| pair |": "reference-against-reference disagreement",
    "| warrant |": "audit-coverage partition",
    "| candidate |": "exclusion audit of non-included chains",
}
# Words in a caption that demand a particular shape.
CAPTION_WANTS = [
    (r"(?i)consensus axes, with the .* reference", "axis matrix"),
    (r"(?i)mismatch rate and coverage", "mismatch rate and coverage grid"),
    (r"(?i)decomposition of each chain", "retention/restoration decomposition"),
    (r"(?i)collapsing|merged", "merged-cluster individuation"),
    (r"(?i)relabelling|label granularity", "label-granularity re-scoring"),
    (r"(?i)reference-against-reference|pair of candidate origins",
     "reference-against-reference disagreement"),
    (r"(?i)audit coverage, partitioned", "audit-coverage partition"),
    (r"(?i)selection rule applied to candidates", "exclusion audit of non-included chains"),
]


def shape_of(key):
    p = TABLES / (key + ".md")
    if not p.exists():
        return None
    head = p.read_text(encoding="utf-8").splitlines()[0]
    for sig, name in SHAPE.items():
        if head.startswith(sig):
            return name
    return "unrecognised (%s)" % head[:40]


print("\n1. CAPTION <-> TABLE BINDING")
# A caption is a block starting with ': '. Pandoc's table_captions extension binds such a block to
# the table on EITHER side of it, and this check originally assumed "above" only.
#
# ⛔ THAT ASSUMPTION BROKE A CAPTION AND THIS CHECK IS WHY IT WAS FOUND. Wrapping the axis table in
#    \blandscape…\elandscape to fix its width put a RAW LATEX BLOCK between the caption and the
#    table, so pandoc could no longer bind them: the caption rendered as a literal ": The 19
#    consensus axes…" paragraph, the table lost its number, and **every downstream table silently
#    shifted by one against the prose's hard-coded "Table 2"**. An external referee found it.
#
#  ⇒ The fix is to put the caption INSIDE the landscape block, immediately AFTER the table — so
#    this check must accept below-binding too. It still fails when a table has no caption on
#    either side, which is its actual job.
#    ★ Widened deliberately, once, with the reason. A gate loosened without one is a gate deleted.
included = re.findall(r"\{\{TABLE:([a-z0-9_]+)\}\}", tpl)
blocks = re.split(r"\n(?=: )", tpl)
seen = []
for b in blocks[1:]:
    cap = b.split("\n\n")[0].replace("\n", " ")
    m = re.search(r"\{\{TABLE:([a-z0-9_]+)\}\}", b)
    if not m:
        # No table AFTER this caption — look immediately BEFORE it, which is the landscape case.
        idx = tpl.find(cap.replace(" ", "")[:24].replace("\n", "")) if cap else -1
        before = tpl[:tpl.find(cap[:40])] if cap[:40] and cap[:40] in tpl else ""
        m2 = re.search(r"\{\{TABLE:([a-z0-9_]+)\}\}\s*$", before.rstrip())
        if not m2:
            continue
        m = m2
    key = m.group(1)
    seen.append(key)
    got = shape_of(key)
    want = next((w for rx, w in CAPTION_WANTS if re.search(rx, cap)), None)
    label = cap[2:90].strip()
    if want is None:
        say("?", f"caption not recognised: \u201c{label}…\u201d")
    # ⚠️ PREFIX, not equality. SHAPE names carry a parenthetical gloss ("axis matrix (one row per
    #    axis, one column per profile)") while CAPTION_WANTS names the shape ("axis matrix"), so
    #    exact equality reported a MISMATCH between a string and itself-plus-a-comment. The two
    #    tables it flagged were correctly bound. **Loosened deliberately, and only here** — the
    #    binding check still fails on any genuinely different shape, which is its whole job.
    elif not (got or "").startswith(want):
        say("MISMATCH", f"caption promises {want!r}\n           but {key}.md is the {got!r}\n"
                        f"           caption: \u201c{label}…\u201d")
    else:
        print(f"  ok       {key:20} = {got}")

for k in included:
    if k not in seen:
        say("NO CAPTION", f"{k} is inserted with no caption above it")

print("\n1b. HARD-WRAPPED HEADINGS")
# ⛔ A markdown heading wrapped onto a second line that ALSO starts with #s emits TWO headings, with
#    a paragraph of white space between them. It happened to the disclosure paragraph on p.8 — the
#    one passage that best demonstrates the paper's integrity — and an external referee met the
#    break before the argument.
#  ★ Nothing numeric could have caught it: both halves were correct prose. This checks SHAPE.
# ⚠️ BODY ONLY. The YAML front matter carries comment lines that begin with '#', and the first
#    version of this check reported one of them as a split heading — a gate whose first act is a
#    false positive is a gate that gets ignored.
_all = tpl.splitlines()
_body_start = 0
if _all and _all[0].strip() == "---":
    for _i in range(1, len(_all)):
        if _all[_i].strip() == "---":
            _body_start = _i + 1
            break
_lines = [(i + 1, ln) for i, ln in enumerate(_all) if i >= _body_start]
_split = []
_DANGLING = ("and that is", "and", "the", "of", "is", "a", "to", "that", "with", "for", "in")
for (i, ln), (j, nx) in zip(_lines, _lines[1:]):
    a = ln.lstrip("> ").rstrip()
    b = nx.lstrip("> ").rstrip()
    if a.startswith("#") and b.startswith("#") and a.endswith(_DANGLING):
        _split.append((i, a[:64]))
for i, txt in _split:
    say("SPLIT HEADING", f"line {i} is a heading continued onto the next heading line: "
                         f"“{txt}…”")
if not _split:
    print("  ok       no heading is wrapped onto a second heading line")

print("\n2. GENERATED TABLES NEVER INCLUDED")
for p in sorted(TABLES.glob("table*.md")):
    if p.stem not in included:
        say("ORPHAN", f"{p.name} is generated and never appears in the manuscript "
                      f"({shape_of(p.stem)})")
if not any(k == "ORPHAN" for k in problems):
    print("  ok       every generated table is included")

print("\n3. LITERAL TABLES IN THE TEMPLATE (hand-maintained, cannot track the engine)")
stripped = re.sub(r"\{\{TABLE:[a-z0-9_]+\}\}", "", tpl)
for m in re.finditer(r"^\|[^\n]*\|\n\|[-:| ]+\|\n(?:\|[^\n]*\|\n)+", stripped, re.M):
    rows = m.group(0).count("\n") - 2
    say("LITERAL", f"a {rows}-row table is typed into the template at line "
                   f"{stripped[:m.start()].count(chr(10))+1} — it cannot follow a cell edit")
if not any(k == "LITERAL" for k in problems):
    print("  ok       no hand-typed tables")

print("\n4. ENGINE NUMBERS RETYPED INSTEAD OF INTERPOLATED")
used = set(re.findall(r"\{\{FIG:([a-zA-Z0-9_]+)\}\}", tpl))
prose = re.sub(r"\{\{(TABLE|FIG):[a-zA-Z0-9_]+\}\}", "", tpl)
for k, v in sorted(figs.items()):
    s = str(v)
    # ⚠️ `s in prose` is a SUBSTRING test, and it convicted "210,000-block" of retyping
    #    kscan_k6_ties=210. The value is real, the match was inside a longer numeral.
    #    ★ Same boundary error as `liar` inside `familiar` and `satoshi@` inside `_satoshi@`:
    #      a number needs edges as much as a word does.
    if k not in used and len(s) > 2 and re.search(r"(?<![\d,.])%s(?![\d,.])" % re.escape(s), prose):
        say("RETYPED", f"figures.json['{k}'] = {s}  appears as a literal; use {{{{FIG:{k}}}}}")
if not any(k == "RETYPED" for k in problems):
    print("  ok       no engine-emitted number is retyped")

print("\n5. MARKUP TRAPS THAT HAVE SHIPPED BEFORE")
for path in [TPL] + sorted(TABLES.glob("*.md")):
    t = path.read_text(encoding="utf-8")
    for rx, why in [
        (r"\$[^$\n]*\$\d", "pandoc will not close a math span before a digit — this renders literally"),
        (r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "control byte (a \\a in a replacement string produces BEL)"),
        (r"\u2212", "U+2212 has no glyph in the default pdfTeX font and is dropped silently"),
    ]:
        for m in re.finditer(rx, t):
            say("MARKUP", f"{path.name}: {m.group(0)!r} — {why}")
if not any(k == "MARKUP" for k in problems):
    print("  ok       no known markup traps")

print("\n" + "-" * 78)
print(f"{len(problems)} problems.")
sys.exit(min(len(problems), 120))
