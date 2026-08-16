#!/usr/bin/env python3
"""Build the MINIMAL arXiv TeX bundle, and compile it from an empty directory. NOT money.

⛔ WHY THIS IS SEPARATE FROM make_package.py. R4: *"The current zip is an excellent research
   package. It is not the zip I would upload to arXiv."* arXiv processes **TeX input**, expects the
   figures beside it, and explicitly asks authors not to include extraneous files. Our package is
   the whole laboratory — engine, five gates, audit ledger, referee correspondence — which is right
   for Zenodo and wrong for a TeX compile bundle.

   ★★ AND THE RISK IS NOT ONLY CLUTTER. Shipping the workshop ships its stale corners: an internal
   packet still saying 13 pages / 126 cells, comments recording a retracted result. **A paper whose
   argument is that documentation is part of the artifact cannot ship documentation it has
   retracted.** The two bundles have different jobs and different contents.

⇒ TWO ARTIFACTS, STATED PLAINLY:
     arxiv/    paper.tex + paper.bbl + the figure. Nothing else. Compiles standalone.
     package/  the replication laboratory, for Zenodo / the repository.

Run:  python make_arxiv.py
"""
import io
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
OUT = HERE / "arxiv"

# arXiv wants the .bbl, not the .bib + bibtex run — it does not run bibtex reliably for natbib.
NEEDED = ["paper.tex", "paper.bbl"]
FIGS = ["figures/mismatch_heatmap_v010.png"]


def check_manuscript_is_current():
    """⛔ paper.md MUST post-date the engine run, or the bundle ships yesterday's numbers.

    ★ CAUGHT LIVE, R13. The four artifacts were normalised to LF, the engine re-run to recompute
      their digests — and paper.md was not rebuilt in between. `make_arxiv.py` compiles paper.md,
      so the zip carried two digests that named bytes no longer on disk. **Every gate was green:
      they all check paper.md against the template, and the template was consistent with itself.**

    ⇒ The defect is an ORDER dependency that nothing declared. This does not repair the order —
      it refuses to build when the order was wrong, which is the part that must never be silent.
    """
    import json
    figs = json.loads((HERE / "tables" / "figures.json").read_text(encoding="utf-8"))
    md = (HERE / "paper.md").read_text(encoding="utf-8")
    # ⛔⛔ DERIVED, NOT ENUMERATED — AND THE REASON IS THAT THE ENUMERATION ALREADY WENT STALE.
    #    R13 wrote this guard over four hard-coded keys. R14 added two audit ledgers to the same
    #    verbatim block and the list had to be widened by hand. R15 added two more (the figure
    #    renderer and the PNG) and the list was silently blind to them again — one round after a
    #    comment in this very file warned that exact thing would happen.
    #
    #  ★★★ A LIST THAT MUST BE UPDATED BY HAND WHENEVER THE THING IT GUARDS GROWS IS NOT A GUARD,
    #      IT IS A SECOND COPY OF THE PROBLEM. So stop naming the digests: **every value in
    #      figures.json that IS a digest (64 hex chars) is one the paper may publish**, and any
    #      such value the manuscript declares must appear in it. New digests are covered the moment
    #      they exist, with no edit here at all.
    #
    #  ⚠️ Scope is deliberately "declared and absent", not "all digests must appear": figures.json
    #    may legitimately hold a digest the paper does not print. Only a MISSING one is a defect,
    #    and only for keys the template actually references.
    tpl = (HERE / "paper.template.md").read_text(encoding="utf-8")
    digests = {k: v for k, v in figs.items()
               if isinstance(v, str) and re.fullmatch(r"[0-9a-f]{64}", v)}
    referenced = [k for k in digests if ("{{FIG:%s}}" % k) in tpl]
    stale = [k for k in referenced if digests[k] not in md]
    print("    ok   %d digests in figures.json, %d referenced by the template"
          % (len(digests), len(referenced)))
    if stale:
        print("  ⛔ paper.md IS STALE — figures.json declares digests it does not contain: %s"
              % ", ".join(stale))
        print("     run:  python obl_metric.py && python build_paper.py    then rebuild")
        return False
    print("    ok   paper.md carries every digest figures.json declares")
    return True


def generate_tex():
    """Produce paper.tex and paper.bbl from the manuscript, here, so the bundle is end-to-end."""
    import subprocess
    steps = [(["pandoc", "paper.md", "-o", "paper.tex", "--bibliography=paper.bib",
               "--natbib", "-s"], "pandoc -> paper.tex"),
             (["pdflatex", "-interaction=nonstopmode", "paper.tex"], "pdflatex (pass 1, for .aux)"),
             (["bibtex", "paper"], "bibtex -> paper.bbl")]
    for cmd, label in steps:
        r = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        ok = (HERE / "paper.tex").exists() if "pandoc" in label else True
        print("    %s %s" % ("ok  " if r.returncode == 0 or ok else "warn", label))
    # NOTE R6: pandoc emits \bibliography{paper.bib}. That resolves only because arXiv skips
    #    BibTeX when a matching .bbl is present -- and paper.bib is deliberately NOT in the bundle.
    #    A bundle that compiles for a reason its own source contradicts is a trap for whoever
    #    rebuilds it next, so the argument is normalised to the basename BibTeX actually expects.
    #    ⛔ AND NOTE THE ESCAPING, WHICH BIT TWICE. In a Python string `"\b"` is a BACKSPACE, not
    #    backslash-b. That exact slip put a raw 0x08 byte into audit_btc.py, where it silently
    #    voided a probe until an external referee found it. Written as a raw string here so the
    #    literal says what it means.
    tex = HERE / "paper.tex"
    if tex.exists():
        t = tex.read_text(encoding="utf-8")
        old, new = r"\bibliography{paper.bib}", r"\bibliography{paper}"
        if old in t:
            tex.write_text(t.replace(old, new), encoding="utf-8")
            print("    ok   normalised the \\bibliography argument to the basename")
        # ⛔ "References" WAS PRINTED TWICE, AND IT IS A FORMAT-SPECIFIC DEFECT, NOT A TYPO.
        #    The manuscript's `# References` heading is CORRECT in markdown, where pandoc places
        #    the bibliography under whatever heading the author supplies. In LaTeX it is one
        #    heading too many, because paper.bbl opens `\begin{thebibliography}` and that
        #    environment emits its own. **The same source is right in one output format and wrong
        #    in the other**, so the fix belongs at the conversion, not in the manuscript — deleting
        #    it upstream would leave the markdown bibliography unlabelled.
        #  ★ Found by a referee rasterising page 23. Nothing in the log complains: LaTeX is
        #    perfectly happy to typeset two headings, so no compile-time gate could ever see it.
        #    ⇒ Assert the outcome instead, below, where it is countable.
        t = tex.read_text(encoding="utf-8")
        dup = r"\section{References}\label{references}"
        if dup in t:
            tex.write_text(t.replace(dup + "\n", "").replace(dup, ""), encoding="utf-8")
            print("    ok   dropped the duplicate \\section{References} (thebibliography emits it)")
        heads = tex.read_text(encoding="utf-8").count(r"\section{References}")
        print("    %s explicit References headings in paper.tex: %d (must be 0)"
              % ("ok  " if heads == 0 else "FAIL", heads))
        if heads:
            return False
    return (HERE / "paper.tex").exists() and (HERE / "paper.bbl").exists()


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "figures").mkdir(parents=True)
    missing = []
    for f in NEEDED:
        s = HERE / f
        if s.exists():
            shutil.copy2(s, OUT / Path(f).name)
        else:
            missing.append(f)
    for f in FIGS:
        s = HERE / f
        if s.exists():
            shutil.copy2(s, OUT / f)
        else:
            missing.append(f)
    return missing


def clean_compile():
    """Compile in a directory containing ONLY the bundle. Anything it needs must be inside it."""
    tmp = Path(tempfile.mkdtemp(prefix="oblmetric_arxiv_"))
    work = tmp / "sub"
    shutil.copytree(OUT, work)
    print("\n  CLEAN-ROOM TeX COMPILE in %s" % work)
    ok = True

    # ⛔⛔ ARXIV CHOOSES THE ENGINE, NOT US — AND IT CHOSE A DIFFERENT ONE.
    #    Nineteen rounds of verification ran under pdflatex and reported 0 overfull boxes. arXiv's
    #    scanner auto-selected **xelatex** (the pandoc template loads fontspec/unicode-math in its
    #    non-pdfTeX branch) and produced an overfull box we had never seen: a 13.34pt overhang on
    #    `\texttt{https://github.com/original-bitcoin-laboratory/genesis}`, which cannot line-break.
    #    Different engine, different font metrics, different line breaking.
    #
    #  ★★ THE DEFECT EXISTED ONLY IN AN OUTPUT NOBODY HAD BUILT. Every gate was green, both external
    #     referees compiled cleanly, and the first machine to try the other engine found it
    #     immediately. ⇒ **"It compiles" is a claim about a toolchain, not about a document.**
    #
    #  ⇒ So compile under BOTH and gate on both. Fixed properly at source (the URLs are now
    #    breakable \url macros rather than \texttt), so the document is engine-independent instead
    #    of merely pinned to the engine we happen to run.
    #  ⚠️ A missing engine is reported and skipped, never silently treated as a pass.
    engines = []
    for eng in ("pdflatex", "xelatex"):
        if shutil.which(eng):
            engines.append(eng)
        else:
            print("    ⚠  %s not installed here -- NOT CHECKED (arXiv may still use it)" % eng)
    for eng in engines[1:]:
        alt = tmp / ("alt_" + eng)
        shutil.copytree(OUT, alt)
        for _ in (1, 2, 3):
            subprocess.run([eng, "-interaction=batchmode", "paper.tex"], cwd=alt,
                           capture_output=True)
        alog = (alt / "paper.log").read_text(encoding="utf-8", errors="replace") \
            if (alt / "paper.log").exists() else ""
        aover = [float(x) for x in re.findall(r"Overfull .hbox \((\d+\.\d+)pt", alog)]
        apages = re.search(r"Output written .*?\((\d+) pages", alog)
        abad = [x for x in aover if x > 1.0]
        print("    %s %-9s pages %s   overfull %d %s"
              % ("ok  " if not abad else "FAIL", eng, apages.group(1) if apages else "?",
                 len(abad), ("worst %.2fpt" % max(abad)) if abad else ""))
        if abad:
            ok = False

    for i in (1, 2):
        r = subprocess.run(["pdflatex", "-interaction=nonstopmode", "paper.tex"],
                           cwd=work, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        print("    pass %d  exit %s" % (i, r.returncode))
    pdf = work / "paper.pdf"
    log = (work / "paper.log").read_text(encoding="utf-8", errors="replace") if (work / "paper.log").exists() else ""
    # ⚠️ NO `import re` HERE. `re` is imported at module level; a function-local import binds the
    #    name as a LOCAL for the WHOLE function body, so every earlier use in this same function
    #    raises UnboundLocalError -- which is exactly what the alternate-engine loop above hit.
    #    The failure appears at the FIRST use, not at the import, which is why it reads as
    #    "re is not defined" in code that plainly imports re.
    pages = re.search(r"Output written .*?\((\d+) pages", log)
    undef = len(re.findall(r"Citation .* undefined", log))
    miss = len(re.findall(r"File .* not found|LaTeX Warning: File", log))
    # ⛔⛔ TWO GATES ADDED 15 Aug 2026, AND THE REASON IS THE WORST NEAR-MISS OF THE PROJECT.
    #
    #    To fix an 8-column table colliding in the PDF, the body was wrapped in a raw
    #    \begin{landscape} … \end{landscape}. **Pandoc treats a recognised LaTeX environment as a
    #    RAW BLOCK and passes its contents through verbatim**, so the entire axis table — the
    #    paper's central exhibit — was emitted into paper.tex as literal pipe characters. The
    #    overfull-hbox count duly went from 24 to 0 and was reported as a fix.
    #
    #    ★★★ IT WENT TO ZERO BECAUSE THE TABLE HAD STOPPED EXISTING. That is the vacuous-check
    #    pattern this codebase already names, in its purest form: **an improving metric is not
    #    evidence of improvement when the measurement's subject can vanish.** Worse, every gate
    #    stayed green, because they all check paper.md — where the markdown table is intact —
    #    and nothing looked at what pandoc actually produced.
    #
    #  ⇒ So check the OUTPUT, at the stage where the damage is visible:
    tex = (work / "paper.tex").read_text(encoding="utf-8", errors="replace")
    raw_rows = len([ln for ln in tex.splitlines() if ln.startswith("| ")])
    tabulars = tex.count("\\begin{longtable}") + tex.count("\\begin{tabular}")
    hard = [ln for ln in log.splitlines() if ln.startswith("!")]
    print("    pdf produced : %s" % pdf.exists())
    print("    pages        : %s" % (pages.group(1) if pages else "?"))
    print("    undefined cites: %d" % undef)
    print("    missing files  : %d" % miss)
    # ⛔ OVERFULL BOXES ARE NOW A GATE, AND THE REASON IS THAT CONTENT CHANGES BREAK LAYOUT.
    #    Twice a substantively correct edit has produced a layout regression nothing caught:
    #    the 8-column axis table colliding, and then expanding 16-hex digest prefixes to full
    #    SHA-256 — a 64-character token TeX cannot break, which simply overhangs the margin by
    #    up to 100pt. Both were found by an external referee rasterising a page.
    #  ★ A paper whose argument is reproducibility cannot ship text running off the page, and
    #    "it compiles" was never the same claim as "it is readable".
    over = [float(x) for x in re.findall(r"Overfull .hbox \((\d+\.\d+)pt", log)]
    big = [x for x in over if x > 1.0]
    # ⛔ "References" WAS TYPESET TWICE AND EVERY GATE WAS GREEN, BECAUSE LATEX IS HAPPY TO SET TWO
    #    HEADINGS. The log has nothing to say about it; only the rendered page does. A referee
    #    found it by rasterising page 23.
    #  ★ So read the PDF, not the source and not the log. This is the same lesson as test_K in
    #    another register: **the artifact a reader receives is the only place some defects exist.**
    heads = None
    try:
        r = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
        if r.returncode == 0:
            heads = len(re.findall(r"(?m)^\s*References\s*$", r.stdout))
    except (OSError, subprocess.SubprocessError):
        heads = None          # extractor absent: report unknown, never assume good
    print("    rendered 'References' headings: %s (must be 1)"
          % ("not checked — pdftotext unavailable" if heads is None else heads))
    print("    hard TeX errors: %d %s" % (len(hard), hard[0] if hard else ""))
    print("    real tables    : %d   unconverted markdown rows: %d" % (tabulars, raw_rows))
    print("    overfull hboxes: %d %s" % (len(big),
                                          ("worst %.2fpt" % max(big)) if big else ""))
    if pdf.exists():
        shutil.copy2(pdf, OUT / "paper-arxiv-preview.pdf")
    # ⚠️ `heads is None` (no extractor) does NOT fail the build — an absent tool is not a defect —
    #    but it prints "not checked" rather than passing silently, so the gap is visible.
    # ⚠️ `ok and ...`, not `ok = ...`. The alternate-engine loop above may already have set ok
    #    False; a plain assignment here would discard that result and pass a bundle that fails
    #    under the engine arXiv actually uses.
    ok = ok and (pdf.exists() and undef == 0 and miss == 0
                 and not hard and raw_rows == 0 and tabulars >= 5 and not big
                 and heads in (None, 1))
    shutil.rmtree(tmp, ignore_errors=True)
    return ok


if __name__ == "__main__":
    print("=" * 92)
    print(" MINIMAL arXiv BUNDLE — TeX only, compiled from an empty directory")
    print("=" * 92)
    print("\n  GENERATING TeX from the manuscript (end-to-end, not assumed)")
    if not check_manuscript_is_current():
        sys.exit(1)
    if not generate_tex():
        print("  ⛔ could not generate paper.tex / paper.bbl -- is pandoc/pdflatex/bibtex present?")
        sys.exit(1)
    missing = build()
    files = sorted(p.relative_to(OUT).as_posix() for p in OUT.rglob("*") if p.is_file())
    print("\n  bundle contents (%d files):" % len(files))
    for f in files:
        print("     %s" % f)
    if missing:
        print("\n  ⛔ MISSING — build paper.tex/paper.bbl first (pandoc + bibtex):")
        for m in missing:
            print("       %s" % m)
        sys.exit(1)
    ok = clean_compile()
    if ok:
        import zipfile
        z = HERE / "arxiv-submission.zip"
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(OUT.rglob("*")):
                if f.is_file() and f.name != "paper-arxiv-preview.pdf":
                    zf.write(f, f.relative_to(OUT).as_posix())
        print("\n  wrote %s  (%s B) -- upload THIS, and inspect arXiv's generated preview"
              % (z.name, format(z.stat().st_size, ",")))
    print("\n" + "=" * 92)
    print(" arXiv bundle %s" % ("COMPILES STANDALONE" if ok else "FAILED"))
    print("=" * 92)
    if ok:
        print("""
  ⚠️ WHAT THIS PROVES AND WHAT IT DOES NOT: the bundle compiles with only its own contents, so
     no file it needs is being supplied by the working tree. It does not prove arXiv's TeX
     installation matches this one — that is environment, and no local check can settle it.""")
    sys.exit(0 if ok else 1)
