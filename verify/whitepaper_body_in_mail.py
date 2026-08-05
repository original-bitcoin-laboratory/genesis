"""Is ANY of the whitepaper's BODY text anchored to 2008 by the mail archive?

The abstract is anchored -- Satoshi quoted it inline in the announcement, and the list server dated
that message. The body (~3,000 words) has never been shown to survive in any dated third-party
record; the only copy is a PDF created 2009-03-24, months after the announcement.

But the Oct 2008 - Feb 2009 threads are technical. Satoshi answered James A. Donald, Ray Dillinger,
Hal Finney and John Levine at length. If he -- or anyone -- restated a passage of the paper, THE LIST
SERVER DATES THAT TEXT, independent of any PDF. That is the only route left to anchoring body text.

Method: word-shingle intersection, then extend hits to maximal runs. Quoted lines (">") are tracked
separately -- a reply quoting an earlier message is not an independent witness.

NOTE: pipermail obfuscates addresses as "user at host". A From_ regex requiring "@" matches nothing.
"""
import sys, os, re, gzip, subprocess, tempfile

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
# Both inputs are CLI arguments so this runs anywhere:
#   argv[1] = directory of gzipped monthly mboxes (see metzdowd_backup.py)
#   argv[2] = the whitepaper PDF to test
MBOX = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "mbox")
PDF = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "bitcoin.pdf")
N = 8

tmp = os.path.join(tempfile.gettempdir(), "wp_decoded.txt")
subprocess.run([sys.executable, os.path.join(HERE, "pdf_text.py"), PDF, tmp],
               capture_output=True, text=True)
txt = open(tmp, encoding="utf-8").read()


def norm(s):
    s = s.lower().replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    for d in "\u2014\u2013\u2010\u2011":
        s = s.replace(d, " ")
    return re.sub(r"[^a-z0-9' ]+", " ", s).split()


pw = norm(txt)
joined = " ".join(pw)
print(f"  whitepaper: {len(pw):,} words extracted")

# the abstract runs from "a purely peer to peer" to "...while they were gone" -- already anchored
try:
    a0 = len(joined[:joined.index("a purely peer to peer version")].split())
    a1 = len(joined[:joined.index("what happened while they were gone")].split()) + 7
    print(f"  abstract occupies words {a0}-{a1}; body is everything outside that")
except ValueError:
    a0 = a1 = -1
    print("  ! abstract bounds not located")

shingles = {}
for i in range(len(pw) - N + 1):
    shingles.setdefault(" ".join(pw[i:i + N]), []).append(i)
print(f"  {len(shingles):,} distinct {N}-word shingles\n")

WINDOW = ["2008-October", "2008-November", "2008-December", "2009-January", "2009-February"]
hits, scanned = [], 0
for m in WINDOW:
    p = os.path.join(MBOX, m + ".txt.gz")
    if not os.path.exists(p):
        continue
    raw = gzip.decompress(open(p, "rb").read()).decode("utf-8", "replace")
    parts = re.split(r"^(From \S+ (?:at|@) \S+  \w{3} \w{3}.*)$", raw, flags=re.M)
    for k in range(1, len(parts) - 1, 2):
        head, body = parts[k], parts[k + 1]
        scanned += 1
        sender = re.match(r"From (\S+ (?:at|@) \S+)", head).group(1)
        date = head.split("  ", 1)[1] if "  " in head else "?"
        subj = (re.search(r"^Subject: (.*)$", body, re.M) or [None, "?"])[1].strip()
        for label in ("fresh", "quoted"):
            keep = (lambda l: not l.lstrip().startswith(">")) if label == "fresh" else (lambda l: l.lstrip().startswith(">"))
            w = norm("\n".join(l for l in body.splitlines() if keep(l)))
            i = 0
            while i <= len(w) - N:
                sh = " ".join(w[i:i + N])
                if sh in shingles:
                    j, pi = i, shingles[sh][0]
                    while j + N < len(w) and pi + N < len(pw) and w[j + N] == pw[pi + N]:
                        j += 1; pi += 1
                    hits.append((j + N - i, sender, date, subj[:58], label,
                                 " ".join(w[i:j + N]), shingles[sh][0]))
                    i = j + N
                else:
                    i += 1

print(f"  scanned {scanned:,} messages across {len(WINDOW)} months")
hits.sort(key=lambda h: -h[0])
seen = set()
uniq = [h for h in hits if not (h[5] in seen or seen.add(h[5]))]
body_hits = [h for h in uniq if not (a0 <= h[6] <= a1)]
print(f"  {len(uniq)} distinct runs >= {N} words   |   {len(body_hits)} of them OUTSIDE the abstract\n")
for ln, sender, date, subj, label, run, pos in uniq[:30]:
    tag = "ABSTRACT" if a0 <= pos <= a1 else "*** BODY ***"
    print(f"  [{ln:3d}w] {tag:12s} {label:6s} {sender:32s} {date[:17]}")
    print(f"         {subj}")
    print(f"         \"{run[:260]}\"\n")
