"""Structural fingerprint of a PDF -- toolchain and document lineage, not content.

Content tells you what a file says; structure tells you what MADE it. For the whitepaper versions
this is the strongest single discriminator, because it cannot be produced by editing a file:

  PDF version / linearization / /ObjStm / /XRef   -> era and generation of the producing tool
  /ID[0] == /ID[1]                                -> never re-saved since creation
  embedded font subset prefixes, IN ORDER         -> same application, same font environment,
                                                     same document lineage

Subset prefixes (BAAAAA, CAAAAA, ...) are assigned sequentially by the producing application as it
embeds each font, so identical prefixes bound to identical faces in identical order is a far
stronger statement than "these files look similar".

Usage:  python pdf_structure.py a.pdf b.pdf [c.pdf ...]
"""
import re, sys, os

sys.stdout.reconfigure(encoding="utf-8")


def probe(path):
    d = open(path, "rb").read()
    ids = re.findall(rb"/ID\s*\[\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", d)
    cd = re.search(rb"/CreationDate\s*\(([^)]*)\)", d)
    return {
        "bytes": len(d),
        "version": d[:8].decode("latin-1", "replace"),
        "linearized": "yes" if b"/Linearized" in d[:2048] else "no",
        "ObjStm (PDF1.5+)": len(re.findall(rb"/ObjStm", d)),
        "XRef stm (1.5+)": len(re.findall(rb"/XRef", d)),
        "ID[0]==ID[1]": ("yes -- never re-saved" if ids and ids[0][0] == ids[0][1]
                         else ("no -- re-saved" if ids else "absent")),
        "XMP": "yes" if (b"<?xpacket" in d or b"Adobe XMP" in d) else "no",
        "objects": len(re.findall(rb"\n\d+ 0 obj", d)),
        "pages": len(re.findall(rb"/Type\s*/Page[^s]", d)),
        "CreationDate": cd.group(1).decode("latin-1") if cd else "(compressed)",
        "_fonts": list(dict.fromkeys(f.decode() for f in re.findall(rb"/BaseFont\s*/([A-Za-z0-9+#-]+)", d))),
    }


paths = sys.argv[1:]
if not paths:
    print(__doc__); sys.exit(2)
rows = {os.path.basename(p): probe(p) for p in paths}
fields = [k for k in next(iter(rows.values())) if not k.startswith("_")]
print(f"  {'field':18s} " + "".join(f"{n[:24]:>26s}" for n in rows))
print("  " + "-" * (18 + 26 * len(rows)))
for f in fields:
    print(f"  {f:18s} " + "".join(f"{str(r[f])[:24]:>26s}" for r in rows.values()))

print("\n  embedded font subsets, in embedding order")
names = list(rows)
maxn = max(len(r["_fonts"]) for r in rows.values())
for i in range(maxn):
    print("  " + "".join(f"{(r['_fonts'][i] if i < len(r['_fonts']) else '—')[:30]:>32s}" for r in rows.values()))
sets = [tuple(r["_fonts"]) for r in rows.values()]
print(f"\n  identical font set AND order across all inputs: {len(set(sets)) == 1}")
