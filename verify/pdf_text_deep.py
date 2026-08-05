"""Third-approach PDF text extraction: per-font ToUnicode resolution.

WHY THIS EXISTS. Two earlier extractors failed on the same class of document for two DIFFERENT
reasons, and each failure nearly produced a false negative:

  1. A naive "pull the literal strings" pass on Rosendahl's expert report returned 41,957
     characters of DocuSign envelope stamps and page numbers. Searching it for `AR3` gave ZERO
     hits. The conclusion "the fourth whitepaper version does not exist" was one step away -- and
     it would have been wrong. That body was HEX-encoded: 35,868 hex tokens against 356 literal
     strings.

  2. `pdf_text.py`, written to fix case 1, returned ONE CHARACTER on Madden's report. Also not a
     data problem: that file has 425 inflatable streams, 199 of them carrying Tj/TJ operators,
     457 font references and 27 ToUnicode CMaps.

The lesson both times is the same. A PDF does not store "the text" in one place or one encoding.
It stores glyph codes plus a per-font map from those codes to Unicode. Skip the map and you get
either nothing or a substitution cipher. (On the 3 October 2008 draft, merging CMaps across fonts
instead of resolving them per font turned the word "purely" into "ranTBl". That artifact is what
taught this project to resolve fonts individually.)

So this extractor does the whole job:
  - expands EVERY stream, including object streams (/ObjStm), which hold objects in PDF 1.5+
  - resolves the font -> /ToUnicode chain per font object
  - parses bfchar and bfrange CMap sections, including the [dst dst dst] array form
  - decodes BOTH literal (...) and hex <...> strings, tracking the current font via Tf
  - handles Identity-H / Type0 two-byte codes separately from single-byte simple fonts
  - falls back to raw bytes when a font carries no ToUnicode, rather than dropping the text

Deliberately dependency-free: this project's tools must still run in twenty years from a bare
Python, not from whatever PDF library happens to be fashionable then.

Usage:  python pdf_text_deep.py <file.pdf> [--search TERM ...] [--out out.txt]
"""
import re
import sys
import zlib
import argparse

sys.stdout.reconfigure(encoding="utf-8")


def inflate(raw):
    """Flate streams in the wild have stray leading whitespace; try the usual offsets."""
    for attempt in (raw, raw.lstrip(b"\r\n"), raw[1:], raw[2:]):
        try:
            return zlib.decompress(attempt)
        except Exception:
            pass
    try:
        return zlib.decompressobj().decompress(raw)
    except Exception:
        return None


def objects(data):
    """obj number -> (header bytes, decoded stream bytes or None), including objects in /ObjStm."""
    out = {}
    for m in re.finditer(rb"(\d+)\s+(\d+)\s+obj\b", data):
        num = int(m.group(1))
        end = data.find(b"endobj", m.end())
        body = data[m.end():end if end != -1 else len(data)]
        sm = re.search(rb"stream\r?\n", body)
        head = body[:sm.start()] if sm else body
        blob = None
        if sm:
            se = body.find(b"endstream", sm.end())
            raw = body[sm.end():se if se != -1 else len(body)]
            blob = inflate(raw) if b"FlateDecode" in head else raw
        out[num] = (head, blob)

    # PDF 1.5+ hides most objects inside object streams: /N objects, offsets in a leading table
    for num, (head, blob) in list(out.items()):
        if b"/ObjStm" not in head or not blob:
            continue
        n = re.search(rb"/N\s+(\d+)", head)
        first = re.search(rb"/First\s+(\d+)", head)
        if not (n and first):
            continue
        n, first = int(n.group(1)), int(first.group(1))
        nums = re.findall(rb"(\d+)\s+(\d+)", blob[:first])[:n]
        for i, (onum, off) in enumerate(nums):
            onum, off = int(onum), int(off)
            nxt = int(nums[i + 1][1]) if i + 1 < len(nums) else len(blob) - first
            out.setdefault(onum, (blob[first + off:first + nxt], None))
    return out


def utf16(h):
    """CMap destinations are UTF-16BE hex; single bytes appear in malformed files."""
    try:
        b = bytes.fromhex(h.decode())
    except Exception:
        return ""
    if len(b) >= 2:
        return b.decode("utf-16-be", "replace")
    return chr(b[0]) if b else ""


def parse_cmap(txt):
    """ToUnicode CMap -> {glyph code: str}. Handles bfchar and both bfrange forms."""
    cmap = {}
    for blk in re.findall(rb"beginbfchar(.*?)endbfchar", txt, re.S):
        for src, dst in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]*)>", blk):
            cmap[int(src, 16)] = utf16(dst)
    for blk in re.findall(rb"beginbfrange(.*?)endbfrange", txt, re.S):
        for lo, hi, dst in re.findall(
                rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]*)>", blk):
            lo_i, hi_i = int(lo, 16), int(hi, 16)
            base = int(dst, 16) if dst else 0
            for i in range(min(hi_i - lo_i + 1, 65536)):
                try:
                    cmap[lo_i + i] = chr(base + i)
                except ValueError:
                    pass
        for lo, hi, arr in re.findall(
                rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*\[(.*?)\]", blk, re.S):
            lo_i = int(lo, 16)
            for i, d in enumerate(re.findall(rb"<([0-9A-Fa-f]*)>", arr)):
                cmap[lo_i + i] = utf16(d)
    return cmap


def unescape(s):
    """PDF literal string escapes, including 1-3 digit octal."""
    esc = {b"n": 10, b"r": 13, b"t": 9, b"b": 8, b"f": 12, b"(": 40, b")": 41, b"\\": 92}
    out, i = bytearray(), 0
    while i < len(s):
        c = s[i:i + 1]
        if c == b"\\" and i + 1 < len(s):
            nxt = s[i + 1:i + 2]
            if nxt in esc:
                out.append(esc[nxt])
                i += 2
                continue
            octm = re.match(rb"[0-7]{1,3}", s[i + 1:i + 4])
            if octm:
                out.append(int(octm.group(), 8) & 0xFF)
                i += 1 + len(octm.group())
                continue
            i += 2
            continue
        out.append(s[i])
        i += 1
    return bytes(out)


def decode(raw, cmap, two_byte):
    if not cmap:
        return raw.decode("latin-1", "replace")
    if two_byte:
        return "".join(cmap.get(int.from_bytes(raw[i:i + 2], "big"), "")
                       for i in range(0, len(raw) - 1, 2))
    return "".join(cmap.get(b, chr(b) if 32 <= b < 127 else "") for b in raw)


TOKENS = (rb"/(\w+)\s+[\d.-]+\s+Tf"
          rb"|\((?:[^()\\]|\\.)*\)"
          rb"|<([0-9A-Fa-f\s]+)>"
          rb"|\bTd\b|\bTD\b|\bT\*\b")


def extract(path):
    data = open(path, "rb").read()
    objs = objects(data)

    cmaps, wide = {}, {}
    for num, (head, _blob) in objs.items():
        if b"/ToUnicode" not in head:
            continue
        tu = re.search(rb"/ToUnicode\s+(\d+)\s+\d+\s+R", head)
        if not tu:
            continue
        ref = int(tu.group(1))
        if ref in objs and objs[ref][1]:
            cmaps[num] = parse_cmap(objs[ref][1])
            wide[num] = b"/Type0" in head or b"Identity-H" in head

    # resource name (/F13) -> font object number, gathered from every /Resources /Font dict
    resmap = {}
    for _num, (head, _blob) in objs.items():
        for name, ref in re.findall(rb"/(\w+)\s+(\d+)\s+0\s+R", head):
            if int(ref) in cmaps:
                resmap[name] = int(ref)

    chunks = []
    for _num, (_head, blob) in objs.items():
        if not blob or (b"Tj" not in blob and b"TJ" not in blob):
            continue
        cur = None
        for m in re.finditer(TOKENS, blob):
            tok = m.group(0)
            if tok.endswith(b"Tf"):
                cur = resmap.get(m.group(1), cur)
            elif tok.startswith(b"("):
                chunks.append(decode(unescape(tok[1:-1]), cmaps.get(cur, {}), wide.get(cur)))
            elif tok.startswith(b"<"):
                h = re.sub(rb"\s", b"", m.group(2))
                if len(h) % 2:
                    h += b"0"
                try:
                    chunks.append(decode(bytes.fromhex(h.decode()), cmaps.get(cur, {}),
                                         wide.get(cur)))
                except Exception:
                    pass
            else:
                chunks.append("\n")
    return "".join(chunks), len(objs), len(cmaps)


ap = argparse.ArgumentParser()
ap.add_argument("pdf")
ap.add_argument("--search", nargs="*", default=[])
ap.add_argument("--out")
a = ap.parse_args()

text, nobj, ncmap = extract(a.pdf)
print("  " + a.pdf.replace("\\", "/").split("/")[-1])
print(f"  objects {nobj}   fonts with ToUnicode {ncmap}   extracted {len(text):,} chars")
if a.out:
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"  written -> {a.out}")
for term in a.search:
    hits = [mm.start() for mm in re.finditer(re.escape(term), text, re.I)]
    print(f"\n  '{term}': {len(hits)} hits")
    for h in hits[:6]:
        print("     ..." + re.sub(r"\s+", " ", text[max(0, h - 170):h + 240]) + "...")
