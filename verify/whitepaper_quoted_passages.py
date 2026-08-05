"""Every passage Satoshi quotes in his own words, tested against the March 2009 PDF.

Two directions, and the second matters more:
  MATCH    -> that text existed in the paper on the list server's date. Body text, ANCHORED.
  MISMATCH -> the paper said something different then. A body revision, LOCATED.

The abstract was already anchored (quoted inline in the announcement). This asks whether any of the
~3,000-word body is too.
"""
import sys, os, re, gzip, subprocess, tempfile, difflib

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
# Both inputs are CLI arguments so this runs anywhere:
#   argv[1] = directory of gzipped monthly mboxes (see metzdowd_backup.py)
#   argv[2] = the whitepaper PDF to test
MBOX = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "mbox")
PDF = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "bitcoin.pdf")

tmp = os.path.join(tempfile.gettempdir(), "wp_decoded.txt")
subprocess.run([sys.executable, os.path.join(HERE, "pdf_text.py"), PDF, tmp], capture_output=True)
paper_raw = open(tmp, encoding="utf-8").read()


def norm(s):
    s = s.lower().replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    for d in "\u2014\u2013\u2010\u2011":
        s = s.replace(d, " ")
    return " ".join(re.sub(r"[^a-z0-9' ]+", " ", s).split())


paper = norm(paper_raw)
ABS_END = paper.index("what happened while they were gone") + 34

MONTHS = ["2008-October", "2008-November", "2008-December", "2009-January", "2009-February"]
msgs = []
for m in MONTHS:
    p = os.path.join(MBOX, m + ".txt.gz")
    if not os.path.exists(p):
        continue
    raw = gzip.decompress(open(p, "rb").read()).decode("utf-8", "replace")
    parts = re.split(r"^(From \S+ (?:at|@) \S+  \w{3} \w{3}.*)$", raw, flags=re.M)
    for k in range(1, len(parts) - 1, 2):
        if "satoshi at vistomail" in parts[k]:
            msgs.append((parts[k].split("  ", 1)[1].strip(), parts[k + 1]))
print(f"  {len(msgs)} Satoshi messages in window\n")

found = []
for date, body in msgs:
    text = body.split("\n\n", 1)[1] if "\n\n" in body else body
    text = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith(">"))
    text = re.sub(r"\s+", " ", text)
    # A naive '"([^"]+)"' pairs the CLOSING quote of one thing with the OPENING quote of the next,
    # swallowing whole paragraphs plus the list footer and reporting them as bogus near-misses.
    # Require the span to look like a real inline quotation: no sentence-final gap, bounded length.
    cands = [c for c in re.findall(r'"([^"]{40,600})"', text)
             if not re.search(r"(Cryptography Mailing List|Unsubscribe by sending|Satoshi Nakamoto\s*$)", c)]
    for q in cands:
        nq = norm(q)
        if len(nq.split()) < 8:
            continue
        if nq in paper:
            where = "ABSTRACT" if paper.index(nq) < ABS_END else "*** BODY ***"
            found.append((date, "EXACT", where, q, None))
        else:
            # locate the closest passage and show what differs
            best, bs = None, 0.0
            w = nq.split()
            for i in range(0, len(paper.split()) - len(w) + 1):
                cand = " ".join(paper.split()[i:i + len(w)])
                r = difflib.SequenceMatcher(None, nq, cand).ratio()
                if r > bs:
                    bs, best = r, cand
            found.append((date, f"DIFFERS {bs:.0%}", "?", q, best))

print(f"  {len(found)} quoted passages of >=8 words\n" + "=" * 96)
for date, verdict, where, q, best in found:
    print(f"\n  {date}   [{verdict}]  {where}")
    print(f"  quoted : \"{q}\"")
    if best:
        print(f"  paper  : \"{best}\"")
