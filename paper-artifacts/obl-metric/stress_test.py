#!/usr/bin/env python3
"""Adversarial stress test of the obl-metric engine and paper. Run before submission. NOT money.

WHAT THIS IS FOR
------------------
The paper's whole claim is that its result is *reproducible and contestable cell by cell*. That
claim invites exactly one kind of reader: **someone trying to break it.** This file is that reader,
written by the authors, run before anyone else gets the chance.

It does not check that the engine agrees with itself — it checks the things a referee would attack:

    A  do the paper's stated numbers match the engine, digit for digit
    B  does the advertised `--at` flag actually do anything
    C  do the paper's structural claims (cell counts, confidence counts) hold
    D  does the merged-cluster sensitivity affect chains the paper does not mention
    E  how far can the ORDERING be moved by an adversarially-chosen axis subset
    F  which matches are RETENTIONS and which are RESTORATIONS — the paper's central caution,
       stated in prose and never quantified
    G  do the references agree with EACH OTHER where they overlap
    H  are the paper's own tables and figure actually present in the manuscript

⚠️ A FAILING CHECK HERE IS A GOOD OUTCOME. Every one found before submission is one not found by a
   referee, and the method's credibility rests on the authors having looked hardest.

Run:  python stress_test.py
"""
from __future__ import annotations

import itertools
import json
import re
import subprocess
import sys
import hashlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import obl_metric as M  # noqa: E402

HERE = Path(__file__).resolve().parent
FAILS: list[str] = []
WARNS: list[str] = []


def hdr(t):
    print("\n" + "=" * 96)
    print(" " + t)
    print("=" * 96)


def check(name, ok, detail="", warn=False):
    tag = "ok  " if ok else ("WARN" if warn else "FAIL")
    print("  [%s] %-58s %s" % (tag, name, detail))
    if not ok:
        (WARNS if warn else FAILS).append("%s — %s" % (name, detail))
    return ok


# ── A ── the paper's numbers against the engine ──────────────────────────────────────────────
# ⛔ MIGRATED 14 Aug 2026 (R4): 17 axes/4 chains -> 19 axes/5 chains. Bitcoin Gold was measured
#    (it satisfied the stated selection rule), which forced a `pow_function` axis into existence,
#    and BIP34's coinbase-height rule was added after a referee identified it. **Every constant
#    below moved because the DATASET moved, and all 15 of them failed loudly first** — which is
#    the only reason this file is worth having. ★ A tripwire that silently follows the engine
#    catches nothing; these are re-pinned deliberately, once, with the reason.
# ⚠️ BSV's figures changed on 13 Aug 2026 when two of its cells were corrected against the primary
#    source (timelock -> nops; script-number -> 32 MB per chronicle-spec). Updated because REALITY
#    changed, not to make the suite green — the engine is the authority and these track it.
PAPER_V010 = {'BTC': 0.68, 'BCH': 0.74, 'BSV': 0.42, 'XEC': 0.74, 'BTG': 0.74}
PAPER_LOO = {'BTC': (0.67, 0.72), 'BCH': (0.72, 0.78), 'BSV': (0.39, 0.44), 'XEC': (0.72, 0.78), 'BTG': (0.72, 0.78)}
PAPER_MERGED = {"BTC": 0.6471, "BSV": 0.4706}


def test_A():
    hdr("A. THE PAPER'S NUMBERS vs THE ENGINE")
    tbl = M.table(M.AXES)
    for ch, want in PAPER_V010.items():
        got = tbl["v0.1.0"][ch]["mismatch_rate"]
        check("v0.1.0 -> %s mismatch = %.2f" % (ch, want), round(got, 2) == want,
              "engine %.4f" % got)
    check("whitepaper coverage 0.05", round(tbl["whitepaper"]["BTC"]["coverage"], 2) == 0.05,
          "engine %.4f" % tbl["whitepaper"]["BTC"]["coverage"])
    check("nov08 coverage 3/19", round(tbl["nov08"]["BTC"]["coverage"], 4) == 0.1579,
          "engine %.4f" % tbl["nov08"]["BTC"]["coverage"])
    sens = M.sensitivity(M.AXES)
    for ch, (lo, hi) in PAPER_LOO.items():
        s = sens["v0.1.0|%s" % ch]
        check("LOO range %s = [%.2f, %.2f]" % (ch, lo, hi),
              round(s["leave_one_out_min"], 2) == lo and round(s["leave_one_out_max"], 2) == hi,
              "engine [%.4f, %.4f]" % (s["leave_one_out_min"], s["leave_one_out_max"]))
    for ch, want in PAPER_MERGED.items():
        got = sens["v0.1.0|%s" % ch]["merged_cluster"]
        # ⚠️ NOT round(got, 2) == want. round(0.625, 2) is 0.62 in Python — binary floats plus
        #    banker's rounding — so a 2dp comparison silently fails on an exactly-correct value.
        #    This test asserted the paper was wrong when the TEST was. Compare exactly.
        check("merged-cluster %s = %s" % (ch, want), abs(got - want) < 1e-9, "engine %.4f" % got)


# ── B ── the flag the paper and METHOD.md both advertise ─────────────────────────────────────
def test_B():
    hdr("B. DOES `--at` DO ANYTHING? (METHOD.md: \"--at YYYY-MM-DD evaluates at an earlier date\")")
    outs = {}
    for d in ["2026-08-01", "2013-01-01", "2010-01-01"]:
        r = subprocess.run([sys.executable, str(HERE / "obl_metric.py"), "--at", d,
                            "--out", str(HERE / "artifacts")],
                           capture_output=True, text=True, cwd=str(HERE))
        # ⚠️ A SystemExit message goes to STDERR. Reading only stdout made a loud, correct refusal
        #    look like silence — the test reported the exact defect it was written to detect,
        #    against an engine that had already been fixed. Read both streams.
        # ⚠️ Either stream can be None. An earlier version assumed both were strings and the test
        #    itself crashed — a test that cannot run is worse than a test that fails.
        body = "\n".join(ln for ln in ((r.stdout or "") + "\n" + (r.stderr or "")).splitlines()
                         if "evaluated" not in ln and "wrote" not in ln)
        outs[d] = body
        nums = re.findall(r"\d\.\d\d \(cov \d\.\d\d\)", body)
        print("   --at %s -> %s" % (d, " ".join(nums[:4]) or "(no table parsed)"))
    # ⚠️ THE PASS CONDITION CHANGED, AND FOR A REASON, NOT TO GO GREEN.
    #    Historical evaluation is NOT implemented — implementing it would mean inventing ~72
    #    activation dates that no primary source in this dataset currently states, in a paper whose
    #    entire premise is that every value is source-anchored. The defect was never "the flag
    #    returns the same numbers"; it was "the flag CLAIMS to do something it does not".
    #    ⇒ So the correct test is not "does --at vary" but "does the artifact tell the truth about
    #      what --at does". An honest refusal passes; a silent no-op fails.
    refused = [d for d in ("2013-01-01", "2010-01-01") if "REFUSED" in outs[d]]
    check("--at refuses dates it cannot actually evaluate", len(refused) == 2,
          "silently accepted and returned identical numbers for: %s"
          % [d for d in ("2013-01-01", "2010-01-01") if d not in refused])
    doc = (HERE / "paper.md").read_text(encoding="utf-8") + \
          (HERE / "METHOD.md").read_text(encoding="utf-8")
    check("the absence of historical evaluation is DISCLOSED, not hidden",
          "refuses" in doc.lower() and "activation date" in doc.lower(),
          "neither paper.md nor METHOD.md tells a reader the engine cannot evaluate a past date")


# ── C ── structural claims made in prose ─────────────────────────────────────────────────────
def test_C():
    hdr("C. THE PAPER'S STRUCTURAL CLAIMS")
    # ⚠️ 17 axes since 13 Aug 2026: `supply_cap` qualified under neither class of the stated
    #    axis-selection rule and the engine's own validator caught it. See paper §2.
    n_cells = len(M.AXES) * len(M.PROFILES)
    check("152 cells (19 axes x 8 profiles)", n_cells == 152, "engine %d" % n_cells)
    # ★ Count only SPECIFIED cells. Counting `None` cells as high-confidence values is the error a
    #   referee found in "117 of 126"; the honest figures are over the cells that carry a value.
    spec = [a["p"][p] for a in M.AXES for p in M.PROFILES if a["p"][p]["value"] is not None]
    hi = sum(1 for c in spec if c["confidence"] == "high")
    med = sum(1 for c in spec if c["confidence"] == "med")
    check("118 specified cells", len(spec) == 118, "engine %d" % len(spec))
    # ⚠️ UPDATED 14 Aug 2026: 79/9 -> 82/6. These are DELIBERATE hardcodes, not a moving target —
    #    a tripwire that silently follows the engine catches nothing. They changed because six cells
    #    were re-sourced during the descendant audit (BSV timelock, BSV/BCH/XEC script-number and
    #    element-size, BCH block-size), each moving med -> high on a primary specification.
    #    ⇒ If this fails again, the question is WHICH CELL MOVED, not what number to write here.
    #    ⛔ MOVED AGAIN 15 Aug (R5): the whitepaper's pow_function cell became UNSPECIFIED, because
#    the paper says "such as with SHA-256" (illustrative) and "verified by executing a single
#    hash" (not sha256d). One cell left the specified set, so 119->118 and 112->111, and the
#    whitepaper's coverage fell to 1/19. ★ A referee found the encoding, not a gate: no check
#    here can read a PDF and ask whether "such as" is normative.
#    ⛔ MOVED AGAIN 14 Aug: 82/6 -> 81/7. ONE cell, and the tripwire did its job — BSV's
    #    sig_scheme was cited to genesis-spec.md, which contains ZERO occurrences of 'ECDSA' or
    #    'Schnorr'. audit_descendants.py found it; the value is right, the citation was not, and
    #    an absence cited as a positive is now cited as an absence at medium confidence.
    #    ★ NOTE WHAT DID NOT MOVE: all four mismatch rates are unchanged. The audit corrected
    #      provenance, not results — which is the strongest outcome an audit can have.
    check("111 high-confidence (of specified)", hi == 111, "engine %d" % hi)
    check("7 medium-confidence", med == 7, "engine %d" % med)
    check("confidence labels exhaustive", hi + med == len(spec),
          "%d unlabelled" % (len(spec) - hi - med))
    # every cited source key must exist
    cited = {k for a in M.AXES for p in M.PROFILES for k in M.src_keys(a["p"][p])}
    missing = sorted(cited - set(M.SOURCES))
    check("every cell's source key resolves", not missing, "dangling: %s" % missing)
    # ⚠️ An unused SOURCES entry is not tidiness — it is a cell that should have cited it and did
    #    not. This warning is what found BTC's block-size and timelock cells under-citing.
    unused = sorted(set(M.SOURCES) - cited)
    check("no unused source entries (an unused one = an UNDER-CITED cell)", not unused,
          "unused: %s" % unused, warn=True)


# ── D ── the merged-cluster variant, for EVERY chain ─────────────────────────────────────────
def test_D():
    hdr("D. MERGED-CLUSTER SENSITIVITY — the paper reports BTC and BSV only")
    sens = M.sensitivity(M.AXES)
    print("   %-6s %8s %8s %8s" % ("chain", "base", "merged", "delta"))
    moved = []
    for ch in M.CHAINS:
        s = sens["v0.1.0|%s" % ch]
        d = s["merged_cluster"] - s["base"]
        print("   %-6s %8.4f %8.4f %+8.4f" % (ch, s["base"], s["merged_cluster"], d))
        # Reported = its merged value actually appears in the manuscript, not = it is in a constant
        # in this file. The earlier version tested the test's own expectations, which is circular.
        paper_txt = (HERE / "paper.md").read_text(encoding="utf-8")
        # ⚠️ NOT "%.3f": 0.8125 is an exact binary tie and "%.3f" gives 0.812 while the paper
        #    prints 0.8125. Match the 4-place form the paper actually uses.
        if abs(d) > 0.005 and ("%.4f" % s["merged_cluster"]) not in paper_txt:
            moved.append("%s %+0.2f" % (ch, d))
    check("every chain the merge moves is reported in the paper", not moved,
          "MOVES BUT IS NOT REPORTED: %s" % ", ".join(moved), warn=True)
    cl = M.WITNESS_SIG_CLUSTER
    nonbtc = [ax for ax in M.AXES if ax["id"] in cl
              and any(M.val(ax, c) != M.val(ax, "v0.1.0") for c in ("BCH", "XEC"))]
    src = Path(M.__file__).read_text(encoding="utf-8")
    # The cluster genuinely is NOT BTC-only. The defect was the CLAIM, so that is what is tested.
    check("nothing still calls this cluster \"BTC-only\" without correcting it",
          ("BTC-only" not in src) or ("CORRECTED" in src),
          "the cluster contains %s, which BCH and XEC also diverge on"
          % ", ".join(a["id"] for a in nonbtc))
    paper = (HERE / "paper.md").read_text(encoding="utf-8")
    # ⛔ MIGRATED R4: this pinned three LITERAL merged values ("0.8667", "0.6667", "0.4667") that
    #    the 19-axis dataset no longer produces, so it failed against a paper that was correct.
    #    ★ The invariant it was written to protect is "every chain the merge MOVES is reported",
    #    not "these three strings are present" — so assert the invariant, derived from the engine.
    _sens = M.sensitivity(M.AXES)
    _moved = [c for c in M.CHAINS
              if abs(_sens["v0.1.0|%s" % c]["merged_cluster"]
                     - M.table(M.AXES)["v0.1.0"][c]["mismatch_rate"]) > 1e-9]
    _missing = [c for c in _moved if ("%.4f" % _sens["v0.1.0|%s" % c]["merged_cluster"]) not in paper
                and c not in paper.split("merge moves")[-1][:400]]
    check("every chain the merge moves is named in the paper", not _missing,
          "moved but unreported: %s" % ", ".join(_missing))


# ── E ── how far can an adversary move the ordering? ─────────────────────────────────────────
def test_E():
    hdr("E. ADVERSARIAL AXIS SUBSETS — can a defensible axis set reverse the ordering?")
    n = len(M.AXES)
    best = {c: (1.1, None) for c in M.CHAINS}
    worst = {c: (-0.1, None) for c in M.CHAINS}
    bsv_not_lowest = 0
    total = 0
    # all subsets of size n-3 .. n  (a referee arguing three axes are wrong is entirely ordinary)
    for k in range(n - 3, n + 1):
        for combo in itertools.combinations(range(n), k):
            sub = [M.AXES[i] for i in combo]
            rates = {c: M.compare("v0.1.0", c, sub)["mismatch_rate"] for c in M.CHAINS}
            if any(v is None for v in rates.values()):
                continue
            total += 1
            lo = min(rates.values())
            if rates["BSV"] > lo + 1e-9:
                bsv_not_lowest += 1
            for c in M.CHAINS:
                if rates[c] < best[c][0]:
                    best[c] = (rates[c], combo)
                if rates[c] > worst[c][0]:
                    worst[c] = (rates[c], combo)
    print("   subsets tested (dropping up to 3 of %d axes): %d" % (len(M.AXES), total))
    print("   %-6s %10s %10s" % ("chain", "min", "max"))
    for c in M.CHAINS:
        print("   %-6s %10.4f %10.4f" % (c, best[c][0], worst[c][0]))
    pct = 100.0 * bsv_not_lowest / total if total else 0
    check("BSV is lowest in EVERY 3-axis-drop subset", bsv_not_lowest == 0,
          "BSV is not strictly lowest in %d/%d (%.1f%%) of subsets" % (bsv_not_lowest, total, pct),
          warn=True)
    print("""
   ⇒ This is a STRONGER robustness statement than leave-one-out and belongs in the paper:
     leave-one-out drops one axis; a referee who disputes three is entirely ordinary.""")


# ── F ── the caution the paper states but never measures ─────────────────────────────────────
def test_F():
    hdr("F. RETENTION vs RESTORATION — the paper's central caution, quantified")
    print("""   A chain MATCHES v0.1.0 on an axis either because it never changed the rule
   (RETENTION) or because it adopted the change and later removed it (RESTORATION).
   The paper says in prose that these are different; it never counts them.\n""")
    # ⛔⛔ THIS BLOCK REIMPLEMENTED THE HERESY IT WAS WRITTEN TO CATCH, AND CERTIFIED IT GREEN.
    #     It classified a match as a RESTORATION when the cell's cited source happened to be a
    #     later upgrade spec — the exact source-key proxy the project retracted after finding that
    #     BCH forked three weeks BEFORE segwit and so never had it to remove. The engine has used
    #     an explicit RESTORATIONS table with reasons ever since. The stress test did not, so it
    #     printed BSV 3 retentions / 7 restorations against the engine's 6 / 4 — **the retracted
    #     result, inside the instrument whose job is to catch retracted results, passing 0/0.**
    #
    #     ★★★ A CITATION IS NOT A HISTORY — the paper's own methodological lesson, and the hostile
    #     test was the last place in the repo still disobeying it. A test must INTERROGATE the
    #     engine, never re-derive the answer by a shortcut the engine already rejected.
    print("   %-6s %9s %11s %13s" % ("chain", "matches", "retentions", "restorations"))
    rows = {}
    for c in M.CHAINS:
        pv = M.match_provenance(c)          # <- the engine's explicit table, with reasons
        rows[c] = (pv["matches"], len(pv["retentions"]), len(pv["restorations"]),
                   pv["restorations"])
        print("   %-6s %9d %11d %13d" % (c, pv["matches"], len(pv["retentions"]),
                                         len(pv["restorations"])))
    check("only BSV has restorations", all(not M.match_provenance(c)["restorations"]
                                           for c in M.CHAINS if c != "BSV"),
          "a chain other than BSV is credited with a restoration")
    check("BSV restorations match the engine's explicit table",
          len(M.match_provenance("BSV")["restorations"]) == len(
              [k for k in M.RESTORATIONS if k[0] == "BSV"]),
          "the count disagrees with RESTORATIONS itself")
    print("\n   BSV's matches that are RESTORATIONS, not retentions — with the engine's reason:")
    for nm, why in M.match_provenance("BSV")["reasons"].items():
        print("      %-22s %s" % (nm, why))
    check("restoration/retention split is reported in the paper",
          "restoration" in (HERE / "paper.md").read_text(encoding="utf-8").lower(),
          "the paper argues this in prose but publishes no counts", warn=True)


# ── G ── do the references agree with each other? ────────────────────────────────────────────
def test_G():
    hdr("G. DO THE REFERENCES AGREE WITH EACH OTHER? (the engine never asks)")
    for r1, r2 in itertools.combinations(M.REFERENCES, 2):
        cmp = M.compare(r1, r2, M.AXES)
        mr = cmp["mismatch_rate"]
        print("   %-11s -> %-11s jointly %2d  differing %2d  mismatch %s"
              % (r1, r2, cmp["jointly_specified"], cmp["differing"],
                 "undef" if mr is None else "%.2f" % mr))
        for row in cmp["rows"]:
            if row["verdict"] == "mismatch":
                print("        %-22s %-24s vs %s"
                      % (row["axis"], row["ref_value"], row["chain_value"]))
    paper = (HERE / "paper.md").read_text(encoding="utf-8")
    check("reference-to-reference disagreement appears in the paper",
          "most-work vs height" in paper or "do not agree with each other" in paper.lower(),
          "the ONE axis the whitepaper specifies is one the released client does NOT match — "
          "a finding the paper does not report", warn=True)


# ── H ── is the manuscript actually complete? ────────────────────────────────────────────────
def test_H():
    hdr("H. IS THE MANUSCRIPT BUILDABLE? (arXiv takes LaTeX; pandoc must have something to build)")
    p = (HERE / "paper.md").read_text(encoding="utf-8")
    for label, rx in [("Table 1 referenced", r"Table 1"), ("Table 2 referenced", r"Table 2"),
                      ("Figure 1 referenced", r"Figure 1")]:
        print("   %-24s %s" % (label, "yes" if re.search(rx, p) else "no"))
    has_table = bool(re.search(r"(?m)^\s*\|.*\|\s*$", p)) or "\\begin{table}" in p
    has_fig = bool(re.search(r"!\[", p)) or "\\includegraphics" in p
    check("a table is actually present in paper.md", has_table,
          "paper.md cites Table 1 and Table 2 and contains NO table markup")
    check("a figure is actually present in paper.md", has_fig,
          "paper.md cites Figure 1 and contains NO image include")
    check("the evaluation date appears in the paper", "2026-08-01" in p or "1 August 2026" in p,
          "the paper says 'a frozen evaluation date' and never states WHICH — the engine uses "
          "%s" % M.EVIDENCE_FREEZE)
    # citation keys used vs defined
    # ⛔ AN EMAIL ADDRESS IS NOT A CITATION, AND THIS CHECK SAID IT WAS.
    #    Adding `parthms.id@gmail.com` to the author block made `@gmail` look like a citation key
    #    and the gate reported an undefined reference in a paper whose LaTeX compiled with ZERO
    #    undefined citations. **Pandoc has never treated `x@y` as a citation** -- a citation key
    #    must not be preceded by a word character -- so the manuscript was right and the extractor
    #    was wrong.
    #  ★ Same boundary error this suite has now made three times: matching a number without its
    #    edges, matching a substring in the wrong writer, and now matching `@` without its left
    #    edge. **A pattern that ignores what precedes its anchor is not matching the thing it
    #    names.**
    used = set(re.findall(r"(?<![\w.])@([A-Za-z][A-Za-z0-9_:-]*)", p))
    bib = (HERE / "paper.bib").read_text(encoding="utf-8")
    defined = set(re.findall(r"@\w+\{([^,]+),", bib))
    missing = sorted(used - defined - {"a"})
    check("every \\cite key is in paper.bib", not missing, "undefined: %s" % missing)
    unused = sorted(defined - used)
    check("no orphan bib entries", not unused, "unused: %s" % unused, warn=True)


def test_I():
    """⛔ CONTROL BYTES IN SOURCE — the defect class that got through to a referee.

    In a Python or shell string, `\\b` is a BACKSPACE (0x08), not backslash-b. Writing a regex or a
    TeX macro through a shell heredoc silently converts it. That put a raw 0x08 into audit_btc.py,
    where it voided a probe **while the script still exited 0** — found by an external referee, and
    then it happened a second time in make_arxiv.py.

    ★★★ TWICE IS A PATTERN, AND A PATTERN DESERVES AN INSTRUMENT, NOT MORE CARE. The bug is
    invisible in every editor and every diff: the byte renders as nothing. So check the bytes.
    """
    hdr("I. control bytes in source files (the \\b -> 0x08 class)")
    bad = []
    for p in sorted(HERE.glob("*.py")) + sorted(HERE.glob("*.md")) + sorted(HERE.glob("*.bib")):
        if p.name == Path(__file__).name:
            continue
        raw = p.read_bytes()
        for i, b in enumerate(raw):
            # tab, LF, CR are legitimate; everything else below 0x20 is a mangled escape
            if b < 0x20 and b not in (0x09, 0x0A, 0x0D):
                bad.append("%s: 0x%02X at byte %d" % (p.name, b, i))
    check("no stray control bytes in any source file", not bad,
          "; ".join(bad[:4]) + (" (+%d more)" % (len(bad) - 4) if len(bad) > 4 else ""))


def test_J():
    """The package must SHIP the exact bytes the paper DECLARES.

    ⛔ CAUGHT BY AN EXTERNAL REFEREE AT ROUND 10, AND IT WAS REAL. The paper publishes the SHA-256
    of the engine so a reader can tell whether their copy is the right one. Editing the engine
    changes that digest and the manuscript follows automatically -- but `package/` does not, unless
    make_package.py is re-run. It was not, so the replication bundle shipped `ced7ba2b...` while the
    paper declared `3230c4d2...`.

    ★★ THE FAILURE IS WORSE THAN A STALE FILE. A digest that does not match the artifact it names
    turns a verification aid into a false negative: a reader checking honestly concludes they have
    the wrong copy, or that the paper is wrong. **A hash that disagrees with its subject is more
    damaging than no hash at all**, which is exactly the argument the paper makes for publishing it.
    """
    hdr("J. the shipped package == the digests the paper declares")
    import json as _j
    figs = _j.loads((HERE / "tables" / "figures.json").read_text(encoding="utf-8"))
    want = {"obl_metric.py": figs.get("engine_sha"),
            "audit_descendants.py": figs.get("sha_descendants"),
            "audit_btc.py": figs.get("sha_btc"),
            "audit_btg.py": figs.get("sha_btg")}
    pkg = HERE / "package"
    if not pkg.is_dir():
        # ⚠️ WARNING, NOT FAILURE — for the same reason as test_K. make_package.py runs this file
        #    from INSIDE the built package, where there is no nested package/ to inspect, so a
        #    hard failure here fires on every clean-room build and says nothing about the artifact.
        #  ★ The clean room is the one context where this check cannot apply; make it say so,
        #    rather than emit a red line the operator has to learn to disregard.
        check("package/ present to be checked", False,
              "no package/ here (expected when running inside the built package); "
              "run make_package.py from the source tree to exercise this", warn=True)
        return
    for fn, w in want.items():
        f = pkg / fn
        if not f.exists():
            check("package ships %s" % fn, False, "absent from package/")
            continue
        # ⚠️ FULL digest: the paper widened from a 16-hex prefix to the whole hash in R11, and a
        #    gate comparing a truncation against it fails on four correct files. Compare like
        #    for like, or the check reports the artifact wrong when the CHECK is wrong.
        got = hashlib.sha256(f.read_bytes()).hexdigest()
        check("package/%s == declared digest" % fn, got == w,
              "package has %s, paper declares %s -- re-run make_package.py" % (got, w))


def test_K():
    """⛔⛔ THE ADDRESS THE PAPER GIVES MUST CONTAIN THE ARTIFACTS THE PAPER NAMES.

    ★★★ THIS IS THE DEFECT test_J CANNOT SEE, AND IT SURVIVED THIRTEEN REVIEW ROUNDS.
    test_J proves `package/` ships the declared bytes. It passed every round. But *Data and Code*
    tells a reader those artifacts are "available at github.com/original-bitcoin-laboratory/genesis"
    — and that repository tracked **none of the four**, has never mentioned obl-metric, and its
    `paper-artifacts/` directory belongs to a different paper.

    ⇒ So the paper printed four full SHA-256 digests, said *"Any copy that does not hash to these is
      not the copy this paper reports on"*, and pointed at a place with no copy to hash. **A
      commitment with no address is not weaker than no commitment — it is a promise a reader cannot
      redeem, in the one section whose entire purpose is redeeming it.**

    ⛔ WHY NO EXISTING GATE CAUGHT IT, WHICH IS THE REAL LESSON. Every check compared local things
       to other local things: template to paper, package to figures.json, tex to log. **The claim
       was about the outside world, and nothing in the harness ever looked outside.** Two referees
       could not catch it either — they hold only the minimal three-file arXiv bundle, so the bytes
       are absent by design and its absence there proves nothing. R13 could see "no DOI, no commit
       hash"; it could not see "no files".

    ★ Same shape as the landscape-table regression this file already records: **a green gate is
      evidence about what it measures, never about what it was assumed to cover.**
    """
    hdr("K. the repository the paper names actually tracks the artifacts it declares")
    import json as _j
    import subprocess as _sp
    text = (HERE / "paper.md").read_text(encoding="utf-8")
    urls = set(re.findall(r"https://github\.com/([\w.-]+/[\w.-]+)", text))
    figs = _j.loads((HERE / "tables" / "figures.json").read_text(encoding="utf-8"))
    named = ["obl_metric.py", "audit_descendants.py", "audit_btc.py", "audit_btg.py"]
    check("paper.md names at least one artifact repository", bool(urls),
          "Data and Code cites no repository at all")
    # Map "org/repo" -> a local clone, if this workspace holds one. Absent clone = unverifiable
    # here, which is reported as such rather than passed.
    ws = HERE.parent.parent
    clones = {}
    for gitdir in ws.rglob(".git"):
        if not gitdir.is_dir() or "OBL-BACKUP" in gitdir.parts:
            continue
        r = _sp.run(["git", "remote", "get-url", "origin"], cwd=gitdir.parent,
                    capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode == 0:
            slug = re.sub(r"^.*github\.com[:/]|\.git\s*$", "", r.stdout.strip())
            clones[slug] = gitdir.parent
    for slug in sorted(urls):
        repo = clones.get(slug)
        if repo is None:
            # ⚠️ WARNING, NOT FAILURE, AND THE DISTINCTION IS THE WHOLE POINT OF THE CHECK.
            #    "The artifacts are missing from the published repo" and "I cannot see the
            #    published repo from here" are different facts, and only the first is a defect.
            #    make_package.py runs this file inside a clean room with no sibling clones, so
            #    treating absence-of-clone as failure would make the package's own hostile test
            #    fail every single time — and **a check that always fails is a check the operator
            #    learns to skip**, which is how the defect it exists for gets through again.
            check("%s — reachable from here to check" % slug, False,
                  "no clone in this workspace (expected inside package/): verify by hand that it "
                  "tracks %s" % ", ".join(named), warn=True)
            continue
        tracked = _sp.run(["git", "ls-files"], cwd=repo, capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout
        # ⛔ RESOLVE THE REAL PATH. The artifacts live under `paper-artifacts/obl-metric/`, not at
        #    the repository root, so `git show HEAD:obl_metric.py` resolves to nothing and the
        #    digest comparison would hash an EMPTY buffer and report a mismatch -- against a
        #    correctly published file. **A check that finds a file by basename must then read it
        #    by path**, or it verifies one thing and reports on another.
        paths = {}
        for n in named:
            m = re.search(r"(?m)^(\S*(?:^|/)?%s)$" % re.escape(n), tracked)
            if not m:
                m = next((re.match(r"(.*%s)$" % re.escape(n), ln)
                          for ln in tracked.splitlines() if ln.endswith(n)), None)
            if m:
                paths[n] = m.group(1)
        have = set(paths)
        check("%s tracks all %d declared artifacts" % (slug, len(named)), have == set(named),
              "missing from the published repo: %s -- the paper's digests name bytes that are not "
              "at the address it gives" % ", ".join(sorted(set(named) - have)))
        # ⚠️ Tracked is not enough: a tracked file whose bytes differ from the declared digest is
        #    the false-negative test_J exists to prevent, just relocated to the public copy.
        for n in sorted(have):
            want = figs.get({"obl_metric.py": "engine_sha", "audit_descendants.py":
                             "sha_descendants", "audit_btc.py": "sha_btc",
                             "audit_btg.py": "sha_btg"}[n])
            blob = _sp.run(["git", "show", "HEAD:%s" % paths[n]], cwd=repo, capture_output=True)
            raw = blob.stdout if blob.returncode == 0 else b""
            got = hashlib.sha256(raw).hexdigest()
            # ⛔⛔ LINE ENDINGS, AND THIS IS NOT PEDANTRY — IT DECIDES WHETHER THE DIGEST WORKS.
            #    A digest is computed over BYTES. Git stores a text blob with LF and checks it out
            #    with the platform's convention, so a reader cloning on Windows hashes CRLF bytes
            #    and gets a different answer FROM THE CORRECT FILE. They would conclude the paper
            #    is wrong, or that they have the wrong copy -- the precise false negative the
            #    digests exist to prevent.
            #  ★★ Found by the negative control for this very test: hashing the committed blob
            #     against a CRLF working copy disagreed on 2 of 4 files. This corpus has already
            #     recorded that mistake once, in the opposite direction, during the collateral
            #     audit. ⇒ **A published digest needs its line endings pinned (.gitattributes
            #     `-text`) or it is only reproducible on the platform that computed it.**
            if got != want and hashlib.sha256(raw.replace(b"\n", b"\r\n")).hexdigest() == want:
                check("%s:%s -- LINE ENDINGS, not content" % (slug, n), False,
                      "the blob is LF and the declared digest is of the CRLF form. Commit these "
                      "with `*.py -text` in .gitattributes, or the digest is unverifiable on any "
                      "platform but the one that produced it")
            else:
                check("%s@HEAD:%s == the declared digest" % (slug, n), got == want,
                      "published %s, paper declares %s" % (got, want))


def test_L():
    """The audit LEDGERS must actually contain what the paper says they contain.

    ★★ R14: *"the paper commits to what the code is, not to what it did."* Two audit-script digests
       moved between revisions and two readings fit — reformatted-but-valid, or re-probed-and-not-
       refreshed — with nothing in the paper to separate them. The fix was to publish the ledgers
       with their run dates, so the reported probe count is bound to a dated execution.

    ⛔ BUT A CLAIM ABOUT AN ARTIFACT IS ONLY AS GOOD AS THE CHECK BEHIND IT. Asserting in prose
       that the ledgers hold N probes, each with the SHA-256 of the fetched body, is the same kind
       of unverified pointer that produced every defect since round 6. So verify it: count the
       records, require a body digest on each, and require the total to equal the figure the paper
       prints. ⇒ *The paper may now say the ledgers back the number, because the number is read
       out of them.*
    """
    hdr("L. the audit ledgers back the probe count the paper reports")
    import json as _j
    figs = _j.loads((HERE / "tables" / "figures.json").read_text(encoding="utf-8"))
    total = 0
    for name, key in (("audit_descendants", "descendants"), ("audit_btc", "btc")):
        p = HERE / "tables" / ("%s.json" % name)
        if not p.exists():
            check("ledger %s.json exists" % name, False, "the paper publishes its digest")
            continue
        led = _j.loads(p.read_text(encoding="utf-8"))
        check("%s.json digest == the declared one" % name,
              hashlib.sha256(p.read_bytes()).hexdigest() == figs.get("sha_ledger_" + key),
              "re-run obl_metric.py so figures.json follows the ledger")
        check("%s.json records its run timestamp" % name,
              led.get("generated_utc") == figs.get("ledger_run_" + key),
              "declared %s, ledger says %s" % (figs.get("ledger_run_" + key),
                                               led.get("generated_utc")))
        recs = led.get("records", [])
        total += len(recs)
        missing = [r for r in recs if not r.get("body_sha256")]
        # ⚠️ The per-probe body digest is the whole reason the ledger is evidence rather than a
        #    log: without it a record says a URL was visited, not what came back.
        check("%s.json: every probe carries body_sha256" % name, not missing,
              "%d of %d records have no digest of the fetched body" % (len(missing), len(recs)))
    check("ledger records == the probe count the paper prints",
          total == figs.get("aud_probes_total"),
          "ledgers hold %d, paper reports %s" % (total, figs.get("aud_probes_total")))

    # ⛔ THE TABLES MANIFEST MUST DESCRIBE THE FILES ON DISK, NOT THE PREVIOUS RUN'S.
    #    It is computed inside emit_tables from the bytes about to be written, because at that
    #    moment the .md files on disk are still the LAST run's -- the exact staleness trap that
    #    made the engine-output digests read a stale directory two rounds earlier. So the check
    #    that matters is the round trip: recompute the manifest from what was actually written.
    #  ⚠️ Scope is `table*.md`. `tables/` also holds the two audit ledgers, which the audit scripts
    #    write and which are hashed separately -- a first attempt at this check swept the whole
    #    directory and reported a mismatch that was the CHECK's error, not the manifest's.
    tfiles = sorted(p.name for p in (HERE / "tables").glob("table*.md"))
    man = hashlib.sha256()
    for n in tfiles:
        man.update(n.encode("utf-8"))
        man.update(hashlib.sha256((HERE / "tables" / n).read_bytes()).digest())
    check("tables manifest covers %s files, as declared" % figs.get("n_tables_manifest"),
          str(len(tfiles)) == str(figs.get("n_tables_manifest")),
          "found %d table files, figures.json declares %s"
          % (len(tfiles), figs.get("n_tables_manifest")))
    check("tables manifest == the files actually written",
          man.hexdigest() == figs.get("sha_tables_manifest"),
          "recomputed %s, declared %s -- the manifest describes a different set of bytes"
          % (man.hexdigest()[:24], str(figs.get("sha_tables_manifest"))[:24]))

    # ⛔⛔ WHICH SCRIPT DID WHICH PROBES — THE DEFECT R15 CAME WITHIN ONE INFERENCE OF FINDING.
    #    The paper claimed "a third script, audit_btg.py, probes Bitcoin Gold's own chainparams.cpp
    #    for the 5 cells that distinguish it." **It does not.** audit_btg.py tests chain-selection
    #    criterion (2) — was BTG producing blocks at the freeze — and writes no citation ledger at
    #    all. Those 5 cells are probed by audit_descendants.py and have always been recorded in
    #    audit_descendants.json, which is why the counts were right while the attribution was wrong.
    #
    #  ★★ BOTH REFEREES REACHED THE OPPOSITE CONCLUSION FROM THE SAME EVIDENCE: seeing no
    #     audit_btg.json, they inferred BTG's probes were unrecorded and asked for a third ledger.
    #     Emitting one would have DUPLICATED five records that already exist and pushed the total to
    #     36 against a reported 31. ⇒ *A correct count concealed an incorrect attribution, and the
    #     obvious fix for the symptom would have broken the number that was already right.*
    #
    #  ⚠️ So check attribution against the ledgers' own `script` field, which is the only place that
    #     records who actually ran a probe. Counting alone cannot see this — it never could.
    paper = (HERE / "paper.md").read_text(encoding="utf-8")
    btg_in = [n for n, _ in (("audit_descendants", "d"), ("audit_btc", "b"))
              if any(r.get("chain") == "BTG"
                     for r in _j.loads((HERE / "tables" / ("%s.json" % n))
                                       .read_text(encoding="utf-8")).get("records", []))]
    for name in btg_in:
        led = _j.loads((HERE / "tables" / ("%s.json" % name)).read_text(encoding="utf-8"))
        owner = led.get("script", "")
        # The paper must not credit BTG's axis probes to a script that did not run them.
        wrong = re.search(r"`audit_btg\.py`[^.]{0,120}(?:probes|fetches)[^.]{0,120}"
                          r"chainparams", paper)
        check("paper credits BTG's axis probes to %s, which ran them" % owner, not wrong,
              "paper says audit_btg.py probes chainparams.cpp; the ledger records those "
              "%d probes under %s" % (sum(1 for r in led["records"] if r.get("chain") == "BTG"),
                                      owner))


def test_M():
    """⛔ THE PUBLISHED ENGINE-OUTPUT DIGESTS MUST NOT BE PROPERTIES OF THE MACHINE.

    ★★ R17, and it had been latent since round 1. `comparison.json` was written with `write_text`
       and no `newline=` argument, so Python applied platform translation: CRLF on Windows, LF on
       Linux. **Identical content, different bytes, different SHA-256.** A referee regenerating it
       on Linux got exactly that in round 1, when it was cosmetic. **Publishing the digest as a
       verification target made it material** — a reader on another platform would compute a
       different hash from correct output and, under the rule this paper now states, would have to
       read it as a changed result.

    ⇒ The check has two halves, because the two file types are correct in DIFFERENT ways:
        comparison.json   must contain NO CR at all — written with newline="\\n"
        the two CSVs      must be CRLF throughout — csv.writer with newline="" emits \\r\\n on
                          every platform per RFC 4180, so they are already byte-stable
      ⚠️ Normalising the CSVs to match the JSON would change two correct digests to make three
        files look alike. **Uniformity is not the property being protected; platform-independence
        is.**
    """
    hdr("M. published engine outputs are byte-stable across platforms")
    art = HERE / "artifacts"
    j = art / "comparison.json"
    if j.exists():
        raw = j.read_bytes()
        check("comparison.json has no CR (written with newline='\\n')", b"\r" not in raw,
              "%d CRLF present -- this digest is a Windows digest, not a data digest"
              % raw.count(b"\r\n"))
    for n in ("axis_matrix.csv", "comparison.csv"):
        p = art / n
        if p.exists():
            raw = p.read_bytes()
            lone = raw.count(b"\n") - raw.count(b"\r\n")
            check("%s is uniformly CRLF (RFC 4180, platform-independent)" % n, lone == 0,
                  "%d bare LF -- mixed terminators are stable on no platform" % lone)
    # ⛔⛔ EVERY PUBLISHED PYTHON DIGEST MUST BE OF LF BYTES, AND THIS CHECK EXISTS BECAUSE THE
    #    ONE FILE IT DOES NOT COVER IS THE ONE THAT WAS WRONG.
    #    R13 normalised the four audit/engine scripts to LF and pinned them. R16 added
    #    `figures/mismatch_heatmap.py` to the digest block and nobody normalised it -- it was still
    #    108 CRLF lines. The repository's `.gitattributes` says `*.py text eol=lf`, so **git stored
    #    the LF form while the paper published the CRLF digest**: a reader cloning the repo would
    #    compute 2406483e... against a printed d828e48f... and conclude the paper was wrong.
    #
    #  ★★ IT WAS CAUGHT BY STAGING THE FILES AND RE-HASHING THE BLOBS OUT OF GIT'S INDEX --
    #     not by any check that read the working tree. **The question "what will a reader get?"
    #     is answered by the object store, never by the directory the author is looking at.**
    #  ⇒ Cover them all, derived from the digest keys rather than listed, so a NEW published
    #    artifact is covered the moment it exists. That is the same lesson as the staleness guard.
    pyfiles = {"engine_sha": "obl_metric.py", "sha_descendants": "audit_descendants.py",
               "sha_btc": "audit_btc.py", "sha_btg": "audit_btg.py",
               "sha_figscript": "figures/mismatch_heatmap.py"}
    for key, rel in sorted(pyfiles.items()):
        p = HERE / rel
        if not p.exists():
            continue
        raw = p.read_bytes()
        check("%s is LF (its digest is published)" % rel, b"\r\n" not in raw,
              "%d CRLF lines -- git stores *.py as LF, so the published digest would not "
              "reproduce from a clone" % raw.count(b"\r\n"))

    # The engine must not have been changed to write this through a translating path again.
    # ⚠️ SCOPED TO THE comparison.json STATEMENT, and it has to be. A bare `'newline="\\n"' in src`
    #    passes on the TABLES writer, which carries the same argument — so it went green against an
    #    engine deliberately broken to prove it would go red. **A substring search over a whole
    #    file answers "does this text exist somewhere", never "is this call correct".** Same
    #    boundary error as matching a number without its edges, which this suite already records.
    src = (HERE / "obl_metric.py").read_text(encoding="utf-8")
    stmt = re.search(r'comparison\.json"\)\.write_text\((?:[^()]|\([^()]*\))*\)', src)
    check("the engine still pins comparison.json's newline",
          bool(stmt) and "newline=" in stmt.group(0),
          "the comparison.json write no longer passes newline=, so its digest becomes a property "
          "of the platform that produced it")


def main():
    print(__doc__.split("Run:")[0])
    for t in (test_A, test_B, test_C, test_D, test_E, test_F, test_G, test_H, test_I, test_J,
              test_K, test_L, test_M):
        t()
    hdr("SUMMARY")
    print("  FAILURES (%d)" % len(FAILS))
    for f in FAILS:
        print("    ⛔ %s" % f)
    print("\n  WARNINGS (%d)" % len(WARNS))
    for w in WARNS:
        print("    ⚠  %s" % w)
    print("\n  ⇒ Every item above is something a referee could have found first.")
    return 1 if FAILS else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
