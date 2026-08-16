# The controlled freeze — and why more patching would make it worse

**14 August 2026. Round-2 referees: NO-GO, both.** This file answers the two questions actually
asked: *what to do about the unaudited cells*, and *what to do about the paper*.

> ### ★★★ THE FINDING THAT OUTRANKS EVERY INDIVIDUAL DEFECT
>
> Referee 2: *"the revision reproduced its own diagnosed failure four more times, twice inside the
> file it was repairing."*
>
> **That is correct, and it is the whole problem.** Round 1 found propagation failures. My round-2
> repairs *created six more*:
>
> ```
> fixed the --at claim          left the SAME docstring asserting "nothing for independent
>                               coders to disagree about" — the retracted claim, 4 lines above
> fixed "$-$0.0417"             introduced U+2212, which pdfTeX SILENTLY DROPS. The minus is now
>                               absent from the merged table, so -0.0392 reads as positive.
>                               ⇒ WORSE THAN THE DEFECT IT REPLACED.
> fixed "≈"                     introduced THREE LITERAL BEL BYTES — my replacement string
>                               contained \a, which Python read as the bell escape. Verified:
>                               `paper.md` contains 0x07 three times. Renders as "$pprox$".
> updated the gap to 5          left "first ties at k=4" hardcoded in the engine's own banner
> corrected BSV script-number   silently gutted a label perturbation, which now moves nothing
> claimed captions were fixed   the rebuilt PDF still renders "Figure 1: Figure 1."
> ```
>
> ⇒ **THE ROOT CAUSE IS NOT CARELESSNESS. IT IS THAT THE PAPER HAND-MAINTAINS NUMBERS THE ENGINE
> COMPUTES.** Tables 1, 2 and 3, the §5 ranges and the §5.1 table are prose I edit with string
> surgery every time a cell moves — and a cell has moved on three consecutive days. **No amount of
> care fixes a pipeline where the authority and the presentation are separate documents.**

---

## 1. ⇒ WHAT TO DO ABOUT THE UNAUDITED CELLS

**It is no longer a search. Referee 1 named the sources.** That converts an open-ended hunt into a
bounded fetch of five documents:

```
BCH ABLA (May 2024)        Bitcoin Cash Node documentation — block size becomes DYNAMIC,
                           so our "32mb" is wrong regardless of what replaces it
BCH May 2026 upgrade       upgradespecs.bitcoincashnode.org (index already confirmed reachable)
XEC script numbers         Bitcoin ABC docs: MAX_SCRIPTNUM_BYTE_SIZE = 8
XEC element size           Bitcoin ABC docs: MAX_SCRIPT_ELEMENT_SIZE = 520
XEC difficulty             e.cash: Heartbeat / Real-Time Targeting enforced via Avalanche,
                           so "asert" alone is incomplete
BSV Chronicle height       ⚠️ referee says v1.2.0 release states 943,816, targeted 7 Apr 2026.
                           OUR FETCHED SPEC SAYS 943,835. THE TWO DISAGREE.
```

> ### ⚠️ AND THE REFEREE'S VALUES ARE CLAIMS UNTIL FETCHED.
>
> The discipline that has worked all week is *verify, do not accept* — it caught three of my own
> greps being wrong, and it cleared the SHA-1 question when I expected it to convict. **A referee
> gets the same treatment as anyone else.** ★ The Chronicle disagreement (943,816 vs 943,835) is
> the proof of why: two sources, one number, and we currently have no basis to prefer either.
>
> ⇒ **Fetch all five, quote each verbatim into the cell comment, and where two sources disagree,
> record the disagreement rather than picking.**

⚠️ **And the audit must cover all 68 descendant cells, not the six named.** Six were found by
outsiders reading a paper; that is a sample, not a census. **The claim certifying author
verification stays false until the census is done.**

## 2. ⇒ WHAT TO DO ABOUT THE PAPER: one freeze, no more patches

Referee 1's prescription is right and I adopt it without amendment:

```
1  primary-source re-audit of all 68 descendant cells
2  FREEZE the 17-axis dataset
3  rerun the engine
4  REGENERATE every number, table and figure — do not edit them
5  mechanically sweep every repository file for obsolete strings
   (18 axes · 126 cells · three restorations · 0.44 · 988 · k=4 · 0.8000)
6  build the arXiv bundle from scratch
7  render it and inspect EVERY page
```

### ★★★ The one structural change that makes step 4 possible

**The engine must emit the tables, and the paper must include them.** Not "the engine computes and I
transcribe" — **`obl_metric.py` writes `tables/*.md`, and `paper.md` includes those files at build
time.** Then a cell change propagates by construction and cannot be forgotten.

⇒ **Until that exists, every future correction will regenerate this same list.** Six regressions in
one round is not bad luck; it is the predicted output of hand-maintaining derived numbers.

### And `revision_check.py` goes in the loop, not at the end

The referee supplied a mechanical diff of manuscript-vs-engine: **34 checks, 9 mismatches.** It is a
better instrument than my own `stress_test.py`, which passes at 0/0 while those 9 mismatches stand —
because mine tests what I thought to encode and theirs tests what the paper actually says.

> ★★ **A test written by the artifact's author validates the author's model of the artifact.** That
> was the round-1 lesson and I did not act on it structurally. **Both suites now run, and the
> external one is the gate.**

## 3. ⛔ What NOT to do next

```
do not add analysis          the method is at ~85%; the artifact is at ~55%. More analysis
                             widens the gap the referees are actually complaining about.
do not patch strings         six regressions came from exactly that.
do not rebuild the PDF       until the dataset is frozen and the tables are generated. A build
                             on a moving dataset is what produced a Figure 1 showing 18 rows
                             under a caption saying 17.
do not submit                neither referee's blocker list is closed.
```

## 4. Status, stated plainly

```
conceptual / methodological   ~85%  — the two-class rule, §5.1, the metric counterexample and
                                      the bilateral OpenOffice finding are all sound
artifact / data               ~55%  — dataset currency unverified, numbers hand-maintained,
                                      figure stale, three files at different revision states
arXiv today                   NO-GO
```

★ **The honest summary: the science got better and the engineering got worse.** The next round
should contain no new ideas at all.
