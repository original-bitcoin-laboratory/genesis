# obl-metric — internal review packet

**13 August 2026. These are the files to send, and nothing else.** Everything below regenerates
from the two source files; the rest is derived and is included only so a reviewer need not build it.

---

## ⇒ SEND THESE FIVE

```
1  paper.pdf                  THE DOCUMENT UNDER REVIEW. 19 pages, 1 figure, 8 tables.
2  REVIEW-2026-08-13.md       what the stress test found and what was changed. READ SECOND --
                              it tells a reviewer where the paper was weakest and why.
3  obl_metric.py              the engine. Every number in the paper comes from running this.
4  METHOD.md                  the method, standalone, with the corrections marked in place.
5  paper.md                   the source, for anyone who would rather comment inline than on a PDF.
```

⚠️ **Do NOT send `stress_test.py` as a headline item.** It is in the repo and a reviewer may run it,
but leading with it invites review of the test rather than of the paper.

## Optional, if the reviewer asks "show me the data"

```
artifacts/comparison.json     all 152 cells with criterion, source and confidence, plus the four
                              analyses (reference disagreement, match provenance, subset
                              robustness, constant axes)
artifacts/axis_matrix.csv     the raw 18 x 7 value grid
artifacts/comparison.csv      the summary table
figures/mismatch_heatmap_v010.png
```

---

## ★ THE COVERING NOTE — paste this, so the reviewer knows what kind of read you want

> This is a method paper heading for arXiv `cs.DC`. It builds a reproducible instrument for a
> question usually answered by advocacy: **how far do BTC, BCH, BSV and XEC sit from a chosen
> historical Bitcoin reference, across 18 consensus axes, with every cell tied to a primary source?**
>
> **I have already run a hostile pass on it myself** — `REVIEW-2026-08-13.md` records six failures
> and four warnings found and fixed before this reached you, including one substantive error in the
> paper's own headline analysis. **So please do not spend your time on whether the arithmetic
> reproduces; it does, and there is a script that checks it.**
>
> **What I actually need from you is the reading a referee will give it:**
>
> 1. **Is the central claim over-stated anywhere?** The result is *reference-relative consensus-rule
>    displacement*. It is not a claim about which chain "is" Bitcoin, and every sentence is supposed
>    to hold that line. **Tell me where a sentence slips.**
> 2. **Section 4.1 (retention vs restoration) is the newest material and was WRONG in an earlier
>    draft.** It now says BSV is the only chain with any restorations — three of ten. **Is the
>    reasoning airtight, and is the correction note in the right place?**
> 3. **Section 4.2 says the three references disagree with each other**, and that the one axis the
>    whitepaper specifies is one the January 2009 client does not implement as described.
>    **Is that as significant as I think, or am I over-reading a labelling choice?**
> 4. **Section 7 admits the engine cannot evaluate a historical date and refuses to try.** Is that
>    the right call, or does it read as a hole a referee will push on?
> 5. **Does the BSV result read as advocacy?** It should not, and Section 4.1 exists to stop it.
>    **If it reads that way to you, it will to a reviewer, and that is the single biggest risk in
>    the paper.**

---

## What is already checked, so nobody re-does it

```
[x] every number in the paper matches the engine, verified digit for digit
[x] LOO ranges, merged-cluster values, coverage figures, cell and confidence counts
[x] 0 undefined citations, 0 orphan bib entries
[x] figure renders and is captioned; Table 1 fits the page
[x] 3 source attributions corrected (BIP66 inheritance; cw-144 dated to Nov 2017; commit day)
[x] stress_test.py: 0 failures, 0 warnings
```

## ⚠️ Still open, and a reviewer should know

```
- the licence on the arXiv form is not yet chosen (non-exclusive is the default and is fine)
- the paper carries the author's legal name; arXiv is permanent and indexed. Decided KEPT,
  because three sibling papers carry it and pseudonymising one achieves only inconsistency.
- no external falsification attempt has ever been made on ANY of this project's findings.
  ★ That is the reason for submitting at all, and the reviewer should feel free to be the first.
```
