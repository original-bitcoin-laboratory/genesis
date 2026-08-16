# Reference-relative protocol-profile comparison — method

**Regenerated 14 August 2026.** ⚠️ **This file had drifted badly** — it still described a one-class
axis rule and an 18-axis enumeration after both were replaced, and carried retracted provenance
figures and a `988 of 988` result. **A correction not propagated to every file that states the
number is not a correction**, and this file was the standing example of that.

A reproducible way to state **how far a chain's consensus rules sit from a historical reference**, so
the comparison is a computation anyone can re-derive rather than a judgement. Engine:
[`obl_metric.py`](obl_metric.py). Figure: [`figures/mismatch_heatmap.py`](figures/mismatch_heatmap.py).
**NOT money.**

---

## 1. Profiles

Three **references**: the 2008 whitepaper (design intent), the 15 November 2008 pre-release (a
partial, source-bounded snapshot), and v0.1.0 (the January 2009 client, the only complete early
ruleset). Four **chains** at a frozen date: **BTC, BCH, BSV, XEC**. Comparisons are always
*reference → chain*.

> **The label `v0.1.0` is retained deliberately.** The archive distributed as `bitcoin-0.1.0.rar` is
> by its own bytes **v0.1.1, built 10 January 2009**. **No axis value changes** — the 0.1.0 → 0.1.1
> delta is `irc.cpp` and `serialize.h`, both networking. The correction is *recorded rather than
> applied*, because renaming a column would churn every published artifact's provenance to fix a
> label that changes no number.

## 2. ★ Chain selection — stated, because it is a judgement too

Referees asked twice why these four chains. The rule, **independent of any result**:

```
1  DIRECT LEDGER ANCESTRY    the chain's ledger continues Bitcoin's genesis block; no
                             reissued or re-genesised chain qualifies, however named
2  ACTIVE MAINNET AT FREEZE  producing blocks on 1 August 2026
3  A DOCUMENTED CONSENSUS    a public, dated specification record for its divergences.
   CHANGE HISTORY            Without one, no cell can be source-anchored and the chain
                             cannot be measured by this instrument AT ALL
```

⇒ **BTC, BCH, BSV and XEC satisfy all three.** Chains excluded by rule 3 rather than by obscurity
include forks whose consensus changes are recorded only in source diffs without dated
specifications — **they are excluded because the method cannot see them, not because they are
unimportant**, and a reader who supplies such a record can add a column.

⚠️ **The abstract previously called these "large descendant chains" without defining "large".**
Removed: **size was never the criterion, and using it would have made the population a popularity
judgement.**

## 3. Axis selection — two classes

An axis is a **consensus-relevant** rule: one that can render a block or transaction valid on one
profile and invalid on another. *Implementation-only* differences (e.g. the ECDSA library) are
excluded — we compare consensus behaviour, not code lineage.

```
class i    changed on at least one included chain since January 2009           15 axes
class ii   an early REFERENCE specifies it, and no descendant ever changed it    2 axes
           (initial block subsidy · target block spacing)
```

⚠️ **Class ii is a revision, and it is stated as one.** The original rule was class (i) only; that
contradicted its own dataset and an external referee found it. Enforced literally, the subsidy and
spacing axes leave — and **the November 2008 reference is then left with zero jointly specified axes
and no result at all.** They were kept because they are the only axes that profile specifies.

> ⛔ **AND THE COST IS STATED HERE, NOT DISCOVERED LATER.** The 2 class-ii axes carry the same value
> on v0.1.0 and all four chains, contributing a fixed 2 matches to every chain. With the 2 further
> axes on which all four chains agree while differing from v0.1.0, **only 13 of the 17 axes do any
> comparative work.** **Class ii buys a reference, not a ranking.**

★ **A third axis was removed once the rule was written.** The monetary supply schedule qualified
under neither class — no descendant changed it, and no early reference specifies it. **The engine's
own class validator caught it within a minute.** The finding survives in prose: the halving interval
and 21e6 cap are identical on v0.1.0 and all four descendants, so the axis carried no comparative
information.

**The classification is enforced, not asserted:** `validate_axis_classes()` re-derives each axis's
class from the data and fails if a cell edit breaks it.

## 4. Cell schema

`{value, criterion, source, confidence}`, where *source* is one or more primary records.
**Cells do NOT carry an activation height or date** — which is why the engine evaluates at a single
frozen date and refuses any other.

> ⚠️ **CORRECTED, TWICE.** This section previously claimed cells carry an activation height, and
> claimed *"there is nothing for two independent coders to disagree about"*. **Both were false.**
> The counterexample is in the shipped CSV: `no-dedicated-cap` (v0.1.0) and `no-consensus-cap` (BSV)
> name the same state and score a **mismatch**, because matching is string equality on labels.
>
> ★★ **Reproducibility does not eliminate coder judgement — it RELOCATES it from scoring to
> individuation**, where it is visible and can be perturbed. `label_sensitivity()` perturbs it.

## 5. Mismatch rate and coverage

For a `(reference, chain)` pair, over the axes where **both** specify a value:

- **mismatch rate** = differing / jointly-specified — **undefined** where nothing is jointly specified
- **coverage** = jointly-specified / total axes

Both are always reported. The three references have very different coverage (whitepaper 1 axis;
November 2 axes; v0.1.0 all 17), and **a mismatch rate read without its coverage is meaningless.**

## 6. Four sensitivity analyses

```
leave-one-axis-out    the range when any single axis is dropped
merged individuation  collapses the post-2017 witness/signature upgrades into one axis
subset robustness     every subset dropping up to three axes
label granularity     re-scores under defensible alternative LABELS
```

⚠️ **The subset result is arithmetic, not a finding.** All four chains share a denominator, so the
counts order the rates, and the gap from the lowest to the runner-up is 5 — so invariance up to four
dropped axes is a **theorem**. Exhaustively: first ties at k=5, first strict reversal at k=6.

★★ **Label granularity is the one that bites: BSV spans a wider range under relabelling than under
any axis-dropping perturbation.**

## 7. What the result means — and does not

**Reference-relative consensus-rule displacement.** It is **not a metric**: under skip-unspecified,
distinct profiles can sit at distance zero (take axes $A=(0,\emptyset)$, $B=(0,1)$: $d(A,B)=0$ with
$A \neq B$), and the triangle inequality fails. It is **not a quality score** and **not a claim about
which chain "is" Bitcoin** — that involves naming, continuity, adoption and governance, all out of
scope.

**A low mismatch rate can arise from a chain REMOVING post-2009 additions as readily as from
preserving originals**, and `match_provenance()` separates the two.

## 8. Reproduce

```
python obl_metric.py                 # table + artifacts + tables/
python figures/mismatch_heatmap.py   # the figure, from the same engine
python build_paper.py                # assembles paper.md from paper.template.md
python revision_check_live.py        # manuscript-vs-engine gate; must be 0
python audit_btc.py                  # BTC column vs the BIPs repo          -> 8/8
python audit_descendants.py          # BCH/BSV/XEC vs their primary specs   -> 18/18
python stress_test.py                # the hostile referee                  -> 0 failures
```

> ### ★ THE CITATION CENSUS, AND THE TWO THINGS IT FOUND (14 Aug 2026)
>
> Both audit scripts fetch **primary** documents and apply a **self-naming control** — the document
> must identify itself or the probe is **void, not negative**. ⚠️ **A first run "confirmed" three
> BCH cells by matching `ASERT`, `CTOR` and `schnorr` inside `<link rel="next" href="…">` navigation
> chrome.** That is the bot-walled-200 error wearing a new costume: **reading the envelope and
> calling it the letter.** The fix was not a cleverer regex but deleting the envelope — `body_text()`
> strips tags before matching.
>
> **It corrected two citations and zero values:**
> `bch_bigint` conflated two upgrades (May 2022 gave 64-bit integers; arbitrary precision is
> CHIP-2024-07, activated 15 May 2025 — still inside the freeze, so the value stood); and BSV's
> `sig_scheme` cited a specification containing **no occurrence of *ECDSA* or *Schnorr***.
> ★★ **A cell can be correct and still be unsourced, and only a fetch can tell the difference.**
>
> ⛔ **And the limit that cannot be audited away: `none` cells are CLAIMS OF ABSENCE.** No document
> establishes that a rule is absent. They rest on chronology plus the absence of a spec introducing
> them — **the weakest footing in the dataset, not remediable by more searching**, and stated in
> Limitations rather than left for a reader to infer.

> ### ⛔ `paper.md` IS A BUILD ARTIFACT. DO NOT EDIT IT.
>
> Two referee rounds found the same defect class repeatedly: **the manuscript hand-maintained
> numbers the engine computes.** Repairs then introduced six further regressions — including a
> minus sign pdfTeX silently dropped and three literal BEL bytes from a `\a` in a replacement
> string. The engine now emits `tables/*.md` and `figures.json`; the paper includes them, and the
> builder refuses any non-ASCII output. **A cell change propagates by construction.**

`--at` accepts only the evidence freeze (**1 August 2026**) and refuses any other date; historical
evaluation is not implemented and is reported as a limitation. **NOT money.**
