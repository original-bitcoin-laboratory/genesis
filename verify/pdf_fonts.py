"""Compare the EMBEDDED FONT PROGRAMS of two or more PDFs.

The deepest structural test available on these files, and the one hardest to fake.

OpenOffice embeds a SUBSET of each font, containing only the glyphs the document uses. Two exports
of the same document from the same machine therefore share byte-identical subsets for every font
whose glyph coverage did not change -- and differ, in the glyph tables only, where the text did.

For the whitepaper: 6 of 7 font programs are byte-identical between the 3 Oct 2008 draft and the
24 Mar 2009 canonical. The seventh is the body text font, and it differs only in glyf/hmtx/loca
(which glyphs are included), not in cmap/cvt/fpgm/maxp/name/post/prep (the font machinery). Both
carry the same source-font creation timestamp of 1990-08-06.

Usage:  python pdf_fonts.py a.pdf b.pdf [...]
"""
import hashlib, os, re, struct, sys, zlib, datetime

sys.stdout.reconfigure(encoding="utf-8")


def font_programs(path):
    d = open(path, "rb").read()
    out = {}
    for m in re.finditer(rb"/BaseFont\s*/([A-Za-z0-9+#-]+)(.{0,400}?)/FontDescriptor\s+(\d+)\s+0\s+R", d, re.S):
        name = m.group(1).decode()
        fdm = re.search(rb"(?<![0-9])" + m.group(3) + rb"\s+0\s+obj(.{0,900}?)endobj", d, re.S)
        if not fdm:
            continue
        ff = re.search(rb"/FontFile2\s+(\d+)\s+0\s+R", fdm.group(1))
        if not ff:
            continue
        om = re.search(rb"(?<![0-9])" + ff.group(1) + rb"\s+0\s+obj(.{0,200}?)stream\r?\n", d, re.S)
        if not om:
            continue
        raw = d[om.end():d.find(b"endstream", om.end())]
        try:
            out[name] = zlib.decompress(raw)
        except Exception:
            out[name] = raw
    return out


def tables(prog):
    n = struct.unpack(">H", prog[4:6])[0]
    t = {}
    for i in range(n):
        o = 12 + i * 16
        tag = prog[o:o + 4].decode("latin-1")
        _, off, ln = struct.unpack(">III", prog[o + 4:o + 16])
        t[tag] = (off, ln)
    return t


paths = sys.argv[1:]
if len(paths) < 2:
    print(__doc__); sys.exit(2)
sets = {os.path.basename(p): font_programs(p) for p in paths}
names = sorted(set().union(*[set(v) for v in sets.values()]))
print(f"  {'font':34s} " + "".join(f"{n[:20]:>22s}" for n in sets))
print("  " + "-" * (34 + 22 * len(sets)))
ident = 0
for f in names:
    row = ""
    progs = []
    for s in sets.values():
        p = s.get(f)
        progs.append(p)
        row += f"{(str(len(p)) + ' ' + hashlib.sha256(p).hexdigest()[:8]) if p else '—':>22s}"
    same = all(p is not None and p == progs[0] for p in progs)
    ident += same
    print(f"  {f[:34]:34s} {row}  {'IDENTICAL' if same else 'differ'}")
print(f"\n  byte-identical font programs: {ident}/{len(names)}")

# for any font that differs, show WHERE -- machinery vs glyph data
for f in names:
    progs = [s.get(f) for s in sets.values()]
    if any(p is None for p in progs) or all(p == progs[0] for p in progs):
        continue
    a, b = progs[0], progs[1]
    diffs = [i for i in range(min(len(a), len(b))) if a[i] != b[i]]
    print(f"\n  {f}: {len(a)} vs {len(b)} bytes, {len(diffs)} differing")
    for tag, (o, l) in sorted(tables(a).items()):
        n = sum(1 for d in diffs if o <= d < o + l)
        print(f"     {tag:6s} len={l:<7} differing: {n}")
    o, l = tables(a).get("head", (0, 0))
    if l:
        ep = datetime.datetime(1904, 1, 1)
        for lbl, blob in zip(sets, progs):
            c, mo = struct.unpack(">qq", blob[o + 20:o + 36])
            print(f"     head created={ep+datetime.timedelta(seconds=c)}  modified={ep+datetime.timedelta(seconds=mo)}  ({lbl})")
