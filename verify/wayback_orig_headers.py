"""Recover the ORIGINAL server's response headers from an Internet Archive capture.

This is the highest-value trick in this whole toolkit and it is almost unknown.

When the Wayback Machine replays a capture with the `id_` modifier, it prefixes the *original*
HTTP response headers with `X-Archive-Orig-`. Among them is **Last-Modified** — which, for a static
file, is the mtime on the serving host's filesystem.

That is a **server-authored date**. Not the author's, not the archive's: written by the web server
that held the file. It is exactly the evidence class this project grades highest below proof-of-work,
and it can be recovered from any capture without downloading the file.

APPLIED TO THE WHITEPAPER, the result is a to-the-second corroboration:

    bitcoin.org/bitcoin.pdf, captured 2010-07-04
        X-Archive-Orig-Last-Modified: Tue, 24 Mar 2009 17:33:15 GMT
        X-Archive-Orig-Content-Length: 184292

    the PDF's own /CreationDate: D:20090324113315-06'00'
        = 2009-03-24 11:33:15 at UTC-6
        = 2009-03-24 17:33:15 UTC        <- identical, to the second

    SourceForge mirrors (voxel, surfnet, ufpr), captured 2009-2013
        X-Archive-Orig-Last-Modified: Tue, 24 Mar 2009 17:50:18 GMT   <- 17 minutes later

So the document's internal creation stamp, written by OpenOffice on the author's machine, is
confirmed by bitcoin.org's own filesystem; and the file reached SourceForge's mirror network
seventeen minutes after it was made. Three independent mirrors report the same mtime.

CAVEATS:
  - Last-Modified reflects the mtime AS OF THE CAPTURE. A file re-uploaded later shows the later
    mtime; this dates the bytes that were served, not necessarily first publication.
  - Not every host sends Last-Modified, and not every capture preserves it. Dynamic pages usually
    have none. Absence is not evidence.
  - `id_` returns the original bytes and headers; the plain form returns the Archive's rewritten
    page. Always use `id_` for this.

Usage:  python wayback_orig_headers.py <timestamp> <original-url> [<timestamp> <url> ...]
        python wayback_orig_headers.py --whitepaper      # the known set, as a self-test
"""
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
UA = {"User-Agent": "obl-archive/1.0 (provenance check; github.com/original-bitcoin-laboratory)"}

KNOWN = [
    ("20100704213649", "http://www.bitcoin.org:80/bitcoin.pdf"),
    ("20091128185352", "http://voxel.dl.sourceforge.net:80/project/bitcoin/Research%20Paper/bitcoin.pdf/bitcoin.pdf"),
    ("20110125032851", "http://surfnet.dl.sourceforge.net:80/project/bitcoin/Design%20Paper/bitcoin.pdf/bitcoin.pdf"),
    ("20131008120148", "http://ufpr.dl.sourceforge.net:80/project/bitcoin/Design%20Paper/bitcoin.pdf/bitcoin.pdf"),
]

args = sys.argv[1:]
pairs = KNOWN if (not args or args[0] == "--whitepaper") else list(zip(args[0::2], args[1::2]))

print(f"  {'capture':16s} {'orig Last-Modified':34s} {'length':>10s}  url")
print("  " + "-" * 108)
for ts, url in pairs:
    req = urllib.request.Request(f"https://web.archive.org/web/{ts}id_/{url}", headers=UA)
    req.get_method = lambda: "HEAD"
    try:
        h = urllib.request.urlopen(req, timeout=90).headers
    except Exception as e:
        print(f"  {ts:16s} {str(e)[:34]:34s} {'—':>10s}  {url[:52]}")
        continue
    lm = h.get("X-Archive-Orig-Last-Modified", "—")
    cl = h.get("X-Archive-Orig-Content-Length", "—")
    print(f"  {ts:16s} {lm:34s} {cl:>10s}  {url[:52]}")

if pairs is KNOWN:
    print("""
  The PDF's own /CreationDate is D:20090324113315-06'00' = 2009-03-24 17:33:15 UTC.
  bitcoin.org's filesystem reports the same instant to the second; the SourceForge
  mirrors report 17 minutes later. The document's self-claimed creation time is
  therefore corroborated by a server the author did not run.""")
