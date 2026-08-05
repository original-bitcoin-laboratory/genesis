"""SourceForge's own download statistics for the Bitcoin project, back to 2008.

SourceForge still serves historical per-month download counts from a live JSON endpoint that needs
no key and no login. The series reaches back to the project's registration in November 2008, which
makes it a SERVER-DB class record of how many people actually took Satoshi's files at the time.

The result that matters:

    2008-11        0
    2008-12        1      <- the whitepaper was the ONLY file in the project that month
    2009-01      141      <- v0.1 released 8 Jan 2009
    2009-02       49

Per the agreed chronology in COPA v Wright (23.5, 23.7), Satoshi uploaded the White Paper to the
SourceForge project on 8/9 December 2008 and the Bitcoin software on 8 January 2009. So in December
2008 the project contained exactly one file, and it was downloaded exactly once.

WHAT THIS DOES NOT SAY:
  - It is a PROJECT total, not a per-file figure. The API exposes no per-file breakdown for this
    period. The inference to "the whitepaper" rests on the chronology above, not on the API.
  - Whether an uploader's own fetch is counted is not documented.
  - SourceForge does not publish what it counts as a download, or how bots were filtered in 2008.
  - Counts are bucketed by month.

Usage:  python sourceforge_download_stats.py [project] [start] [end]
"""
import json
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

PROJECT = sys.argv[1] if len(sys.argv) > 1 else "bitcoin"
START = sys.argv[2] if len(sys.argv) > 2 else "2008-11-09"
END = sys.argv[3] if len(sys.argv) > 3 else "2010-06-30"
UA = {"User-Agent": "obl-archive/1.0 (provenance check; github.com/original-bitcoin-laboratory)"}
URL = f"https://sourceforge.net/projects/{PROJECT}/files/stats/json?start_date={START}&end_date={END}"

d = json.loads(urllib.request.urlopen(urllib.request.Request(URL, headers=UA), timeout=120).read())
rows = d.get("downloads", [])
print(f"  project   {PROJECT}")
print(f"  window    {START} .. {END}")
print(f"  updated   {d.get('stats_updated')}")
print(f"  total     {d.get('total'):,}\n")
print("     month      downloads")
peak = max((r[1] for r in rows), default=1) or 1
for month, n in ((r[0][:7], r[1]) for r in rows):
    print(f"     {month}   {n:>8}  {'#' * min(58, int(58 * n / peak)) if n else ''}")

dec = next((r[1] for r in rows if r[0][:7] == "2008-12"), None)
if dec is not None:
    print(f"\n  December 2008: {dec}")
    print("  In that month the project held one file -- the whitepaper. The software came 8 Jan 2009.")
    print("  This is a project total, not a per-file figure; see the module docstring for limits.")
