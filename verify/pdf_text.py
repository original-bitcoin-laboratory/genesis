"""Extract text from a PDF that uses subset fonts with PER-FONT ToUnicode CMaps.

The naive approach -- merge every CMap into one dict -- fails, because subset fonts reuse glyph
IDs 1,2,3... independently. Merging makes them collide and the output is a substitution cipher
('purely' -> 'ranTBl'). The fix is to resolve /Font resources to their ToUnicode object, then
follow /Tf switches through the content stream and decode each run with the right table.
"""
import re, sys, zlib

sys.stdout.reconfigure(encoding="utf-8")
PATH = sys.argv[1]
d = open(PATH, "rb").read()


def inflate(b):
    for attempt in (b, b.strip()):
        try:
            return zlib.decompress(attempt)
        except Exception:
            pass
    return None


# ---- 1. index every object: num -> raw body -------------------------------------------------
objs = {}
for m in re.finditer(rb"(\d+)\s+0\s+obj(.*?)endobj", d, re.S):
    objs[int(m.group(1))] = m.group(2)

# objects living inside object streams (PDF 1.5+)
for num, body in list(objs.items()):
    if b"/ObjStm" not in body:
        continue
    sm = re.search(rb"stream\r?\n(.*?)\r?\nendstream", body, re.S)
    if not sm:
        continue
    data = inflate(sm.group(1))
    n = re.search(rb"/N\s+(\d+)", body)
    first = re.search(rb"/First\s+(\d+)", body)
    if not (data and n and first):
        continue
    n, first = int(n.group(1)), int(first.group(1))
    header = data[:first].split()
    for i in range(n):
        try:
            onum = int(header[2 * i])
            off = int(header[2 * i + 1])
            end = int(header[2 * i + 3]) + first if 2 * i + 3 < len(header) else len(data)
            objs[onum] = data[first + off:end]
        except Exception:
            pass


def stream_of(num):
    b = objs.get(num, b"")
    m = re.search(rb"stream\r?\n(.*?)\r?\nendstream", b, re.S)
    return inflate(m.group(1)) if m else None


# ---- 2. parse one ToUnicode CMap ------------------------------------------------------------
def parse_cmap(raw):
    t = {}
    if not raw:
        return t
    for blk in re.findall(rb"beginbfchar(.*?)endbfchar", raw, re.S):
        for a, b in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", blk):
            t[int(a, 16)] = "".join(chr(int(b[i:i + 4], 16)) for i in range(0, len(b), 4))
    for blk in re.findall(rb"beginbfrange(.*?)endbfrange", raw, re.S):
        for a, b, c in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", blk):
            lo, hi, dst = int(a, 16), int(b, 16), int(c, 16)
            for k in range(lo, hi + 1):
                t[k] = chr(dst + k - lo)
    return t


# ---- 3. font resource name -> its CMap ------------------------------------------------------
fontmaps = {}
for num, body in objs.items():
    if b"/Type" not in body or b"/Font" not in body:
        continue
    tu = re.search(rb"/ToUnicode\s+(\d+)\s+0\s+R", body)
    if not tu:
        continue
    fontmaps[num] = parse_cmap(stream_of(int(tu.group(1))))

# map /Fn names to font objects.  The /Font value may be an inline dictionary OR an indirect
# reference (/Font 64 0 R) pointing at a dictionary object -- this PDF uses the latter, which is
# why a pattern that only handles the inline form silently resolves nothing.
name_to_obj = {}


def harvest(blob):
    for nm, ref in re.findall(rb"/(\w+)\s+(\d+)\s+0\s+R", blob):
        name_to_obj[nm.decode()] = int(ref)


for num, body in objs.items():
    for fm in re.finditer(rb"/Font\s*<<(.*?)>>", body, re.S):
        harvest(fm.group(1))
    for fr in re.finditer(rb"/Font\s+(\d+)\s+0\s+R", body):
        harvest(objs.get(int(fr.group(1)), b""))

print(f"  fonts with ToUnicode: {len(fontmaps)}   /Fn names resolved: {len(name_to_obj)}")

# ---- 4. walk content streams, honouring /Tf --------------------------------------------------
out = []
for num, body in objs.items():
    raw = stream_of(num)
    if not raw or b"BT" not in raw:
        continue
    cur = {}
    for tok in re.finditer(rb"/(\w+)\s+[\d.]+\s+Tf|\[(.*?)\]\s*TJ|\((?:[^()\\]|\\.)*\)\s*Tj", raw, re.S):
        if tok.group(1):
            cur = fontmaps.get(name_to_obj.get(tok.group(1).decode(), -1), {})
        elif tok.group(2) is not None:
            s = ""
            for hm in re.finditer(rb"<([0-9A-Fa-f]+)>|(-?\d+)", tok.group(2)):
                if hm.group(1):
                    h = hm.group(1).decode()
                    for i in range(0, len(h), 2):
                        s += cur.get(int(h[i:i + 2], 16), "")
                elif int(hm.group(2)) < -120:
                    s += " "
            out.append(s)
print(f"  text runs decoded: {len(out)}")
text = re.sub(r"\s+", " ", " ".join(out))
OUT = sys.argv[2] if len(sys.argv) > 2 else "decoded.txt"
open(OUT, "w", encoding="utf-8").write(text)
print(f"  chars: {len(text)}")
print("\n  --- first 700 chars ---")
print("   ", text[:700])
