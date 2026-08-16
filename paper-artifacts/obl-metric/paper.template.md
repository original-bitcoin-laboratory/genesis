---
title: "Reference-Relative Protocol-Profile Comparison: A Reproducible, Source-Anchored Method for Situating Bitcoin's Descendant Chains Against Historical References"
author: "Parth Mauria Saxena"
date: "15 August 2026. Chain values evaluated at the evidence freeze, 1 August 2026."
bibliography: paper.bib
header-includes:
  # THE AUTHOR BLOCK, AND WHY IT IS SET HERE RATHER THAN LEFT TO THE `author:` FIELD.
  # Pandoc renders `author:` as a bare name. Every other paper in this corpus carries name +
  # affiliation + the canonical contact address, and obl-metric was the only one that did not --
  # an inconsistency visible the moment two of them sit side by side under one ORCID.
  # `before_genesis.tex`, the closest sibling and already permanent on a Zenodo DOI, uses exactly
  # this form, so this matches it rather than inventing a seventh style.
  # And it is not only consistency: this paper's claim is that any cell can be CONTESTED against
  # its source. A contestability claim with no contact route is weaker than it needs to be, on a
  # preprint that is permanent and indexed.
  # ASCII ONLY here -- check_template.py fails the build on non-ASCII in the output.
  # NO ORCID LINE. It is carried by the arXiv author profile, which is where a reader follows it
  # from; repeating it on the title page adds a second place for it to be wrong and none for it to
  # be useful. This matches `before_genesis.tex`, whose Zenodo record shows the iD beside the
  # author name while the PDF title block does not.
  - \AtBeginDocument{\author{Parth Mauria Saxena\\ \small Independent Researcher \\ \small \texttt{parthms.id@gmail.com}}}
  - \usepackage{etoolbox}
  # Table 1 is 7 columns of consensus-value labels and overflows \textwidth at full size.
  # Shrinking the table is right where shortening the labels would not be: the labels ARE the data.
  # NOTE scriptsize, not footnotesize: at footnotesize two rows still ran 24pt and 44pt over.
  #    And note WHERE this must live — an outer \begingroup\scriptsize does NOT work, because
  #    this hook fires INSIDE the environment and overrides it. The wrapper looked like a fix
  #    and changed nothing; the log said so and the eye would not have.
  - \AtBeginEnvironment{longtable}{\scriptsize}
  # NOTE R6: with BTG the axis table became 8 columns of consensus labels and its cells physically
  #    COLLIDED in the compiled PDF -- "ecdsa+schnorr" running into its neighbour. scriptsize was
  #    no longer enough. Landscape returns the width without shortening a single machine label,
  #    which matters because the labels ARE the data: abbreviating them would be a data change
  #    dressed as typesetting.
  - \usepackage{pdflscape}
  # NOT a raw landscape environment DIRECTLY IN THE BODY. Pandoc treats a recognised LaTeX
  #    environment as a RAW BLOCK and passes its contents through VERBATIM -- which
  #    silently turned the whole axis table into a wall of literal pipe characters and
  #    took the overfull-hbox count to zero by DESTROYING the table. These one-word
  #    macros are inline commands, so pandoc keeps parsing markdown around them.
  # Row spacing is tightened ONLY inside the landscape block, so the 19-row axis table fits on
  # one page instead of spilling a handful of rows onto a second. It must not be global: the
  # portrait tables are already comfortable and would look cramped.
  - \newcommand{\blandscape}{\begin{landscape}\renewcommand{\arraystretch}{0.72}}
  - \newcommand{\elandscape}{\end{landscape}}
---

# Abstract

"Which chain is closest to the original Bitcoin?" is usually answered as narrative or advocacy. We give a
*reproducible* answer to a *narrower, well-posed* question: across a fixed set of consensus-protocol axes,
how far do each descendant chain's rules sit from a chosen historical reference? Every cell of the
comparison is a **source-anchored encoding** — a consensus value decided by a stated criterion against a
primary source (a BIP, an upgrade specification, or a self-describing commit), at a frozen evaluation date, with
**{{FIG:aud_fetched}} of the {{FIG:aud_specified}} cells additionally verified by fetching that source
mechanically** (Section 7) — so
the whole table is **machine-recomputable** from that encoding. **We are careful not to claim more.**
Reproducibility guarantees that anyone scoring the same encoding gets the same number; it does not make
the encoding the uniquely correct reading of the protocol. **Judgement is not eliminated, it is relocated
to individuation** — which axes exist, how finely they are cut, and what each state is called — where it
is visible and can be perturbed on purpose, and we perturb it (Section 5). We report a
**mismatch rate** and an explicit **coverage** for each reference$\rightarrow$chain pair (the mismatch rate is
undefined where coverage is zero), and four sensitivity analyses over axis choice and label granularity. Applied to BTC, BCH, BSV, XEC and BTG under three references (the 2008 whitepaper, the November 2008 pre-release, and the January 2009
v0.1.0 client), the method shows that the comparison is *degenerate* under the whitepaper (coverage 1/{{FIG:n_axes}} $\approx$ {{FIG:wp_cov}}), *low-coverage* under the preview, and only well-posed under v0.1.0 — where, on the enumerated axes,
BSV carries the fewest mismatches, a result that is source-anchored yet, we stress, *reference-relative and
individuation-sensitive*, and not a claim about which chain "is" Bitcoin. Two further results sharpen that
caution into measurement rather than hedging. First, decomposing each chain's *agreements* with v0.1.0
shows that **BSV is the only chain in the set that agrees with the reference on any axis it had
previously diverged from and reverted** — {{FIG:rest_BSV}} of its {{FIG:match_BSV}}, against zero for every other chain: a
displacement measure cannot distinguish agreement preserved from agreement re-created. Second, the
three references **do not describe one ruleset**: the whitepaper and the November pre-release share no
axis at all; the whitepaper and v0.1.0 share exactly one and **disagree on it**; and the pre-release and
v0.1.0 share {{FIG:nov_spec}}, agreeing on the proof-of-work function and differing on the other {{FIG:nov_diff}}. The single consensus axis the whitepaper
specifies is one the released client does not implement as described. So "the origin" is not one object. The contribution is the method and its
reproducible engine; the numbers are its worked demonstration. **These artifacts carry no monetary
value.**

# 1. Introduction

Bitcoin's descendant chains — BTC, Bitcoin Cash (BCH), Bitcoin SV (BSV), eCash (XEC), Bitcoin Gold (BTG) — each present
themselves, explicitly or implicitly, in relation to an origin. Comparisons of how far each has moved from
that origin are common but almost always *rhetorical*: a list of favoured changes, weighted by the author's
priorities, concluding with the author's preferred chain. Such comparisons are unreproducible and
unfalsifiable; a reader cannot re-derive them or locate where a disagreement lies.
We take the opposite stance. Rather than argue *which* chain is closest, we build a **measurement
instrument** that (i) makes the axes of comparison explicit, and fixed, before any run is scored,
drawing them from documented change logs, (ii) records
each chain's value on each axis as a fact tied to a primary source, and (iii) computes displacement from a
reference by a stated rule, exposing coverage and sensitivity. The instrument does not decide the
contested question of protocol identity; it makes one *bounded, well-posed* component of that question
— consensus-rule displacement — reproducible.
The design principle is that **reproducibility relocates inter-rater disagreement rather than removing
it**. In content analysis and empirical software engineering, subjective codings are made credible by
multiple independent coders reporting their agreement [@krippendorff; @easterbrook]. Here each cell is a
consensus value determined by a stated criterion against a cited primary record, and the scoring step is
mechanical — so two coders working from the *same encoding* cannot disagree about the result.
 **They can still disagree about the encoding, and an earlier draft of this paper wrongly claimed they
could not.** The shipped dataset contains the counterexample: v0.1.0's block-size state is labelled
`no-dedicated-cap` and BSV's `no-consensus-cap`, which name the same condition and are scored a *mismatch*
because the match rule is string equality. **Section 5 measures what that costs.** The defensible claim is
that the locus of judgement moves from scoring, where it is invisible, to individuation, where it is
explicit and testable. This is the
same move the surrounding project makes elsewhere — replacing narrative about the earliest Bitcoin with
regenerable computation [@saxena_ledger; @saxena_beforegenesis] — applied to cross-chain comparison.

# 2. Method

**Profiles.** A *profile* is a set of consensus-rule values. Three are **references**: the 2008 whitepaper
[@nakamoto2008] (design intent); the 15 November 2008 pre-release [@sni_code] (a partial, source-bounded
snapshot); and v0.1.0 [@sni_code] (the January 2009 client, the only complete early ruleset). Five are
**chains** evaluated at a frozen date: BTC, BCH, BSV, XEC, BTG. All comparisons are reference$\rightarrow$chain.

**Chain selection.** Which chains enter the comparison is itself a judgement, so the rule is stated
before the results and does not depend on them. A chain is **eligible for inclusion if** it satisfies all three of:
**(1) direct ledger ancestry** — its ledger continues Bitcoin's genesis block, so no reissued or
re-genesised chain qualifies however it is named; **(2) an active mainnet at the freeze** — producing
blocks on 1 August 2026; and **(3) a public, dated primary record that explicitly identifies the
relevant consensus divergences** — a BIP, an upgrade specification, or a self-describing commit.
*Raw source diffs carrying no explicit statement of the consensus change fall outside this study's
audit boundary, which is a scope decision and not a claim that they cannot be measured; the
subsection below explains why.* *(We say "eligible for inclusion if", not "included iff": the criteria decide which
chains qualify, and the candidate audit below applies them outside the set -- but a hand-built
candidate list cannot certify that every qualifying descendant has been enumerated.)*

**An inclusion rule only ever applied to the chains one already chose is a description, not a rule**,
so we applied it to candidates outside the set. **Doing so changed this study.**

Bitcoin Gold satisfies all three criteria: it duplicated Bitcoin's ledger through block 491,406, it
publishes dated hard-fork specifications, and it was producing blocks at the freeze — we queried a
primary chain endpoint and block 958,305 carries header time 2026-08-01T21:01:04Z. **It is therefore
measured here as a fifth chain rather than argued away.** The alternative was to add a fourth
criterion, and **a criterion invented after seeing which chain it removes is not a criterion**; the
three criteria were fixed before being applied to the candidate audit, and keeping them fixed when
they produced an inconvenient answer is the only thing that makes fixing them beforehand mean
anything.

Including it had a consequence we did not anticipate and report because it is the more interesting
finding: **Bitcoin Gold changed the proof-of-work function, and no axis existed for that.** The axis
set had been shaped, invisibly, by the chains already chosen. Adding `pow_function` — and
`coinbase_height` (BIP34), which a referee identified independently — takes the enumeration to
{{FIG:n_axes}} axes and changes every reported rate. **The ordering is unchanged.**

: The selection rule applied to candidates outside the set, with each verdict's evidence. A
candidate excluded for a reason we have not checked is one we cannot defend, so unverified
criteria are marked as such rather than assumed.

{{TABLE:table8_exclusions}}

**Criterion (1) does most of the excluding, and does it on substantive grounds:**
{{FIG:n_excl_by_1}} of the {{FIG:n_excl_total}} candidates fail it because their ledger does not continue Bitcoin's
genesis block. **Criterion (3) excludes exactly {{FIG:n_excl_by_3}}** — and that is worth saying
plainly, because the paragraph that follows defends criterion (3) at length and would otherwise read
as a defence of the rule that did the work. It is not; it is a defence of the rule that has barely
been used, which is a different and weaker thing.

Criterion (3) nonetheless excludes for a methodological reason rather than a substantive one. **An earlier draft justified it too strongly**, saying that a chain whose consensus
changes exist only as source diffs *"cannot have a single source-anchored cell and so cannot be
measured by this instrument at all."*

> ### That was false, and the paper itself is the counter-example
>
> Criterion (3) admits *"a BIP, an upgrade specification, **or a self-describing commit**"*, and the
> v0.1.0 reference profile is anchored to **source files**, not to any prose specification. **A
> dated, content-addressed commit can source-anchor a consensus value** — we do it throughout.
>
> $\Rightarrow$ **So this is a scope decision, not a technical impossibility, and it is restated as
> one.** What criterion (3) actually requires is a record from which the *relevant consensus
> divergences can be identified without our reading the diff and deciding for ourselves what
> changed.* A specification says which rule moved and when; a commit history obliges the analyst to
> infer it, and **that inference is exactly the unsourced judgement this method exists to remove.**
>
> **The cost is stated rather than hidden:** the boundary is drawn where auditability becomes
> expensive, not where measurement becomes impossible, and a different study could legitimately draw
> it further out. A reader who supplies the missing record — or who does the diff-reading and cites
> it — can add a column, and the engine will accept it. **Found by an external referee, who noticed
> that criterion (3) contradicted our own source model.**  An earlier draft described these as *"large"
descendant chains without defining "large"*; the word is removed, because **size was never the
criterion and using it would have made the population a popularity judgement.**

*A note on that label.* The archive distributed as `bitcoin-0.1.0.rar` **contains v0.1.1, not the 8 January 2009 release** — its size matches the figure Satoshi states for `bitcoin-0.1.1.rar` in a 10 January 2009 message, and the shipped executable's PE `TimeDateStamp` is 2009-01-10, two days after v0.1.0 was announced. Prior archival analysis reached this first [@chainbulletin]. **It does not affect anything reported here:** the v0.1.0-to-v0.1.1 delta is confined to `irc.cpp` and `serialize.h`, neither of which carries a consensus rule, so no axis or behaviour below changes. We retain the conventional filename because the published digests are recorded under it.

**Axis selection — two classes.** An axis is a *consensus-relevant* rule: one that can render a block
or transaction valid on one profile and invalid on another. *Implementation-only* differences (for
example, the ECDSA library) are excluded: we compare consensus behaviour, not code lineage. Axes are
admitted under one of two stated classes, enumerated from documented change logs — the Bitcoin BIPs
and release history, and the published Bitcoin Cash [@bch_upgrades; @bch_abla], Bitcoin SV [@bsv_genesis; @bsv_chronicle],
eCash [@abc_src; @xec_rtt] and Bitcoin Gold [@btg_spec] specifications, together with the relevant
Bitcoin Improvement Proposals [@bip16; @bip34; @bip65; @bip66; @bip112; @bip141; @bip340; @bip341]
— the axes for P2SH, strict-DER signature encoding and Schnorr are anchored to BIP 16, BIP 66
and BIP 340 respectively, and the paper discusses all three:

**(i) Changed on a descendant** — the rule changed on at least one included chain since January
2009. **{{FIG:n_class_i}} axes.**

**(ii) Reference-discriminating** — an early *reference* specifies the rule, and no descendant has
ever changed it. **{{FIG:n_class_ii}} axes: the initial block subsidy and the target block spacing.**

> ### The second class is a revision, reported as one
>
>An earlier draft stated only class (i). **That rule contradicted its own dataset** — the subsidy,
> spacing and supply axes changed on no included chain — and an external referee found the
> contradiction. Enforced literally, those three axes leave the dataset.
>
> **We retained the subsidy and spacing axes under class (ii) — and dropped the supply axis, for the
> reason given below.** The reason for retaining the two is not convenience: how the choice of
> reference changes what can be said is the paper's subject, and deleting them would be cutting the
> instrument to fit one sentence of the rule.
>
> > #### THE ORIGINAL JUSTIFICATION FOR THIS CLASS NO LONGER HOLDS, AND IS REPLACED RATHER THAN REPAIRED
> >
> > This passage used to argue that without class (ii) the November 2008 reference would be left
> > with **zero jointly specified axes and no result at all**, and that the subsidy and spacing were
> > **the only axes that profile specifies**. Both statements were true when written and **both were
> > falsified by our own later revision**: adding `pow_function` for Bitcoin Gold created a
> > *class-(i)* axis that the November pre-release also specifies. Enforcing class (i) alone would
> > now leave that reference with **one** jointly specified axis, not none.
> >
> > $\Rightarrow$ **The correct claim is weaker and we state the weaker one: class (ii) buys additional
> > reference coverage, not chain discrimination.** It raises November's coverage from
> > 1 axis to {{FIG:nov_spec}}; it cannot separate the chains, because every chain agrees on both.
> >
> > **The dependency ran the wrong way round and that is the lesson.** A justification for a
> > *design* rule was resting on a *dataset* fact, so extending the dataset silently invalidated the
> > rationale while every number stayed correct. Found by an external referee in round 7, three
> > rounds after the axis that broke it was added.
>
> ### The cost of that revision, stated here rather than discovered later
>
> **{{FIG:n_constant}} axes carry a single value across all five chains and therefore cannot separate
> them at all.** {{FIG:n_const_match}} of those agree with v0.1.0 ({{FIG:const_match_names}}) and
> {{FIG:n_const_mismatch}} differ from it ({{FIG:const_mismatch_names}}), so every chain receives the
> same fixed {{FIG:n_const_match}} matches and the same fixed {{FIG:n_const_mismatch}} mismatches
> before any comparison begins. **Every mismatch rate reported under the v0.1.0 reference contains
> that constant component**, and only the remaining **{{FIG:n_discriminating}} of {{FIG:n_axes}}** do
> any comparative work — {{FIG:n_constant}} + {{FIG:n_discriminating}} = {{FIG:n_axes}}, which a
> reader should be able to check on the page rather than take on trust. A fact we return to in
> Section 5 and which should be carried through every number below.
>
> ### A third axis was removed because the rule, once stated, excluded it
>
>An earlier draft carried an eighteenth axis, the **monetary supply schedule** (210,000-block
> halving, 21-million cap). It qualifies under neither class: no descendant has ever changed it,
> and no early reference specifies it. **The engine's own class validator caught this within a
> minute of the rule being written.** Its presence had been an unstated judgement that the
> 21-million cap is too famous to omit — and there is no principled reason it was included while,
> say, BIP34's coinbase-height rule was not. **The finding survives without the axis and is stated
> here instead: the halving interval and asymptotic cap are identical on v0.1.0 and on all five
> descendants.** An axis on which every profile agrees carries no comparative information.
>
> $\Rightarrow$ **Class (ii) buys reference coverage, not chain discrimination.** It is stated before the
> results so that its effect on every reported number is visible rather than absorbed. **We do not
> claim it was fixed before the analysis began — Section 2 records that it was not, and why.**
The engine validates that the declared classes are **consistent with the frozen states** — a
class-(ii) axis must be one on which every profile agrees *and* which an early reference specifies —
**and the validator fails if a cell edit ever breaks that.** What it cannot check is the historical
*never changed* condition, which is a separately sourced assertion: **the single-state schema cannot
derive it**, for the same reason Section 4.1 gives — a chain that changed a rule and later restored
it is indistinguishable, at the freeze, from one that never touched it.
The enumeration yields {{FIG:n_axes}} axes (Table 2), spanning best-chain selection, the block-size rule, the
script opcode vocabulary and its numeric/element limits, signature encoding and scheme, the
output-value range check, P2SH, segwit, Taproot, timelock opcodes, the difficulty algorithm, replay
protection, transaction ordering, and the early monetary parameters.

> ### The axis list is admissible, not exhaustive
>
> The two classes state **when an axis may qualify**. They do **not generate the set**, and this
> revision is the demonstration: a referee identified BIP34's coinbase-height rule as an obvious
> class-(i) axis we had simply not listed, and testing our own chain-selection rule surfaced a
> proof-of-work axis that existed only because every chain we had chosen shared one value.
> **Two axes, added under two different external checks rather than by our own enumeration.**
>
> Therefore we claim only that these are **{{FIG:n_axes}} explicitly specified macro-axes in the
> frozen instrument, drawn from documented consensus changes, admissible under the stated classes
> and not asserted complete.** **Not *pre-registered*:** two of them were added under external
> review after earlier results existed, which Section 2 states in full. *The instrument is frozen
> before each reported run; it was not frozen before the project began, and claiming otherwise
> would contradict our own revision history.*
> Omitted-axis choice remains an unbounded source of model uncertainty, and the honest bound on it
> is that two omissions were found in one round. A future revision that wanted completeness would
> need a sourced consensus-change event ledger mapped onto axes, which this schema does not have.

> ### One cell was reversed after a referee falsified a claim that depended on it, and that is disclosed here rather than absorbed
>
> A previous revision encoded the **whitepaper's proof-of-work function as `sha256d`, sourced to the
> whitepaper, at high confidence.** A referee falsified two claims resting on it. Re-reading the
> source, the encoding was wrong on two independent grounds: the paper says the work is *"scanning
> for a value that when hashed, **such as with SHA-256**, ..."* — illustrative, not normative — and
> that it *"can be verified by executing **a single hash**"*, which is not double-SHA-256 at all.
> **The cell is now unspecified.**
>
> **What that edit moved:** whitepaper coverage {{FIG:wp_spec}}/{{FIG:n_axes}}; the whitepaper and
> the November pre-release returned to sharing no axis; and one chain's whitepaper rate moved from
> 0.50 to 0.00. **It also restored a sentence the same referee had falsified**, which is exactly why
> it is flagged rather than quietly banked.
>
> **Section 2 already holds that "a criterion invented after seeing which chain it removes is not
> a criterion." A cell reversed after seeing which claim it falsifies is the same shape**, and it
> earns the same treatment: state what it said, why it changed, and what it moved. **We think the
> new value is right. The reader is entitled to check that judgement against the old one rather
> than only against the corrected result.**

**Cell schema.** Each cell is `{value, criterion, source, confidence}`, where *source* is one or more
primary records. Cells do **not** carry an activation height or date, which is why the instrument
evaluates at a single frozen date and refuses any other (Section 7).
The *value* is a canonical label; two profiles *match* on an axis iff their labels
are equal. The *criterion* is the objective question the value answers ("is P2SH a consensus rule?"). The
*source* is a primary record a reader can check. *Confidence* is `high` (unambiguous primary source) or
`med` (documented but nuanced, and flagged). **Of the {{FIG:n_cells}} cells, {{FIG:n_unspecified}} are unspecified (`None`); of the
{{FIG:n_specified}} that carry a value, {{FIG:n_high}} are high-confidence and {{FIG:n_med}} are medium**, and the medium cells do not affect
the ordering (Section 5). *An earlier draft reported "117 of {{FIG:n_cells}} high-confidence", which silently
counted every unspecified cell as a high-confidence value.* `None` marks that a profile does not specify
an axis — kept distinct from "specified and equal."

**Mismatch rate and coverage.** For a reference$\rightarrow$chain pair, over the axes both specify (*jointly
specified*): the **mismatch rate** is differing / jointly-specified, and is *undefined* where nothing is
jointly specified; **coverage** is jointly-specified / total. We report both, always. A single "distance"
number is rejected precisely because the three references have very different coverage, and a mismatch rate
read without its coverage misleads.

**Sensitivity.** Because any such comparison depends on which axes are chosen and how finely they are
individuated, the engine reports, per pair, four perturbations: the leave-one-axis-out range of the
mismatch rate; a *merged-cluster* variant that collapses the post-2017 witness/signature upgrades
(segwit, Taproot, Schnorr) into a single axis; and the range over *every* subset obtained by dropping
up to three of the {{FIG:n_axes}} axes, and a re-scoring under alternative labels. We report a conclusion only to the extent it survives all four perturbations.

**Evaluation date.** All chain values are asserted as of the evidence freeze, **1 August 2026**, and
the engine refuses to evaluate any other date (Section 7).
Table 2 gives the axes and the value each profile takes; the machine-readable artifact records the criterion and the primary source for every cell. **The two earlier references are omitted from its body because they are almost entirely empty** — the whitepaper specifies one of these axes, the November 2008 pre-release {{FIG:nov_spec}} — and mostly blank cells would misrepresent them as sparse data rather than as documents that do not legislate consensus rules. Their values follow the table.

\blandscape

{{TABLE:table1_axes}}

: The {{FIG:n_axes}} consensus axes, with the v0.1.0 reference and the five chains.

\elandscape

**The two earlier references, in full.** The **2008 whitepaper** specifies axis 1 only, as
*most-work*. The **15 November 2008 pre-release** specifies {{FIG:nov_spec}}: axis 16 as *100*,
axis 17 as *15 min*, and axis 19 as *SHA-256d*, and nothing else. Axis 19 is the one cell on which
that pre-release and v0.1.0 both speak **and agree**; on the other {{FIG:nov_diff}} they differ. Every other cell for both is *missing* — the profile does not address
that rule — which is kept strictly distinct from "specified and equal", and is what produces
the low coverage reported for both in Table 3. A rate computed over one or {{FIG:nov_spec}} jointly specified
rules is not comparable with one computed over all of them, which is why coverage is printed beside
every rate rather than in a footnote.

**How much of the table discriminates.** {{FIG:n_constant}} axes ({{FIG:constant_names}}) carry the
*same* value on every chain in the set. {{FIG:n_const_mismatch}} of those disagree with v0.1.0 and
{{FIG:n_const_match}} agree with it, so they contribute a fixed offset of
{{FIG:n_const_mismatch}} mismatches and {{FIG:n_const_match}} matches to every chain and **cannot
affect the ordering**. The comparison between chains is therefore carried by
**{{FIG:n_discriminating}} of the {{FIG:n_axes}} axes** — a fact we state rather than leave a reader
to derive, since it bears directly on how much separation the reported rates express.

# 3. Reproducibility

The method is one program plus one renderer. `obl_metric.py` produces every numerical result and
table; `figures/mismatch_heatmap.py` renders Figure 1 deterministically from that engine's
axis-matrix output. The engine holds the axis table (with every value, its
criterion, its primary source, and its confidence) and the computation of mismatch rate, coverage, and
sensitivity. Running it prints the reference$\times$chain table and writes `comparison.json` (the full cell-level
record, including per-cell sources), `comparison.csv` (the summary), and `axis_matrix.csv` (the raw axis
values). The figure regenerates from the same engine. Updating a chain's rule after a future upgrade is a
one-cell edit with a new source, after which the entire table and figure recompute. **Once the encoding is fixed there is no manual scoring step: the
artifact performs the derivation deterministically.** The encoding itself is a human judgement —
axis individuation, label choice and source interpretation — which Section 5 measures rather than
denies.

# 4. Results

: Mismatch rate and coverage for every reference$\rightarrow$chain pair, evaluated 1 August 2026.
The mismatch rate is *undefined* where coverage is zero; a rate must never be read without the
coverage beside it.

{{TABLE:table2_rates}}

*Under the whitepaper*, coverage is {{FIG:wp_spec}}/{{FIG:n_axes}} $\approx$ {{FIG:wp_cov}} — a single jointly-specified consensus axis (best-chain
selection). We print the row in full **because it is the row most easily quoted out of context**:
four of the five chains score 0.00 against the whitepaper, which sounds like a strong result and is not one. It
means only that those four agree with the whitepaper on the one axis both specify. A ranking built
on one axis is degenerate: the whitepaper simply does not constrain enough of the protocol to situate
chains against it, which is itself a useful and often-overlooked finding. *Under the November 2008
pre-release*, coverage is {{FIG:nov_spec}}/{{FIG:n_axes}} $\approx$ {{FIG:nov_cov}} ({{FIG:nov_spec}} specified parameters — the 100-coin subsidy, the 15-minute
spacing, and the proof-of-work function). **The subsidy and spacing differ from every descendant.
The proof-of-work function agrees with four of the five — and differs on Bitcoin Gold, which
replaced it** — which is exactly why the November rate is 0.6667 against BTC, BCH, BSV and XEC and
still 1.00 against BTG. *A single axis separating one chain's rate from four others is the clearest
illustration in the paper of how much a low-coverage reference rests on.*

*Under v0.1.0* (full coverage), the comparison is well-posed. On the {{FIG:n_axes}} axes the mismatch rates are BSV
{{FIG:rate_BSV}}, BTC {{FIG:rate_BTC}}, and BCH = XEC = BTG {{FIG:rate_BCH}}. The axis-level structure is shown in Figure 1.

![Axis-level agreement with the v0.1.0 reference. Each row is one of the {{FIG:n_axes}} consensus
axes and each column one chain. **Every cell is filled; the colour, not the fill, carries the
meaning** — one shade marks a value differing from v0.1.0 and the other a value matching it.
Regenerated by `figures/mismatch_heatmap.py` from the same engine that produces the tables.
](figures/mismatch_heatmap_v010.png){width=90%}

## 4.1 Why BSV is lowest, measured rather than asserted

A chain can agree with the reference for two very different reasons: it never changed the rule
(**retention**), or it adopted a change and later removed it (**restoration**). A bare mismatch rate
cannot tell these apart, and the distinction is the whole of the caution this method must carry. We
therefore report it as a count.

: Decomposition of each chain's agreement with v0.1.0. A match counts as a
*restoration* only where the chain demonstrably **held a different value and later removed it**,
with the introducing and removing change both named; every other match is a retention.

{{TABLE:table3_provenance}}

**BSV is the only chain in the set with any restorations at all**, and it has four: the script opcode
vocabulary and the element-size limit (both restricted by the August 2010 commit and re-enabled by the
2020 "Genesis" upgrade [@bsv_genesis]); P2SH (a consensus rule on its lineage from 2012, removed by
Genesis); and the **timelock opcodes** — CLTV and CSV reached its lineage through BIP65 and BIP112 in
2015--16 and Genesis sunsets them, the specification stating that the operations *revert to NOPs, which
have no effect*, which is v0.1.0's value. **Its other {{FIG:ret_BSV}} agreements — including the absence of
segwit, Taproot and CTOR — are retentions: BSV forked from Bitcoin Cash in November 2018 and never
held any of them.**

$\Rightarrow$ The caution is therefore narrower than a bare mismatch rate suggests, and sharper:
**{{FIG:rest_BSV}} of BSV's {{FIG:match_BSV}} agreements are restorations: axes on which the chain
diverged from v0.1.0 and later returned to the reference value.** A low mismatch rate can arise from removing later additions as readily as from
preserving original ones, and it is not a verdict of authenticity, continuity, or intent.

> **A note on how this table was arrived at, because it bears on the method.** An earlier version of
> this analysis inferred restoration from *which source a cell cites*, on the reasoning that a cell
> citing a chain's own upgrade specification marks a rule that chain legislated. **That inference is
> false and the numbers it produced were wrong** — it reported BSV at 7 restorations and gave BCH and
>XEC two apiece. A citation records where a value is *documented*, not what the chain previously
> did: BCH forked three weeks before segwit activated and so never had segwit to remove, yet its
> segwit cell cites the fork specification. **The table is now an explicit list in which every
> restoration names the change that introduced the rule and the change that removed it**, and
> nothing is inferred. *A citation is not a history.*

## 4.2 The references do not agree with each other

The engine compares references to chains. Asking it to compare the references *to each other* yields
the result we consider most important in the paper:

: Reference-against-reference disagreement. Every pair of candidate origins, over the axes both
specify. **They partly agree and partly disagree** — the whitepaper and the November pre-release share
no axis at all; the November pre-release and v0.1.0 share {{FIG:nov_spec}} and differ on {{FIG:nov_diff}} — so the choice of reference is not
a technical preliminary to the question but the substance of it.

{{TABLE:table6_refdis}}

**The single consensus axis the whitepaper specifies is one the released client does not implement as
described.** The paper describes best-chain selection by accumulated proof-of-work; the January 2009
client selects by height. **Of the {{FIG:nov_spec}} axes the November pre-release shares with v0.1.0,
{{FIG:nov_diff}} differ and one agrees** — the subsidy and the block spacing changed between the
preview and the release; the proof-of-work function did not.

$\Rightarrow$ **"The origin" is not one object.** Displacement is measured from whichever origin is chosen, and
the available origins do not describe one ruleset: {{FIG:ref_summary}}. This is the strongest
available argument for the paper's own insistence that its output is *reference-relative*, and we
would rather state it than have a reader discover it.

# 5. Robustness

**Leave-one-axis-out.** The v0.1.0 mismatch rates stay within BSV {{FIG:loo_BSV}}, BTC {{FIG:loo_BTC}}, and BCH, XEC and BTG {{FIG:loo_BCH}}; no single axis drives the ordering.

**Dropping up to three axes — and why this is weaker than it looks.** Over all {{FIG:subsets}} subsets obtained by
dropping up to three of the {{FIG:n_axes}} axes the ranges are BSV {{FIG:sub_BSV}}, BTC {{FIG:sub_BTC}}, and BCH, XEC and BTG {{FIG:sub_BCH}}, and the lowest-mismatch chain is BSV in {{FIG:subsets}} of {{FIG:subsets}}. **But
that is arithmetic, not a finding.** All five chains share the denominator {{FIG:n_axes}}, so the mismatch
*counts* ({{FIG:cnt_BSV}}, {{FIG:cnt_BTC}}, {{FIG:cnt_BCH}}, {{FIG:cnt_XEC}}, {{FIG:cnt_BTG}}) order the rates, and the gap from BSV to the runner-up is {{FIG:gap}}. Dropping $k$
axes moves any count by at most $k$, so the ordering *cannot* change for $k<{{FIG:gap}}$: invariance up to
{{FIG:invariance_k}} dropped axes is a theorem. Exhaustively, the first ties appear at $k=5$ ({{FIG:kscan_k5_ties}} of {{FIG:kscan_k5_total}} subsets)
and the first strict reversal at $k=6$ ({{FIG:kscan_k6_reversals}} of {{FIG:kscan_k6_total}}). **We report this because a referee found it, and because a robustness claim that
is secretly a tautology is worse than none at all.**

**Individuation.** Collapsing segwit, Taproot and Schnorr into one axis moves every chain, and we
report all five rather than the two that suit the argument:

: Merged individuation. The post-2017 witness and signature-scheme axes are collapsed into a single
axis, and every rate recomputed. **Every chain moves, and they do not move in the same
direction** — which is the point: individuation is not a neutral bookkeeping choice.

{{TABLE:table4_merged}}

*(Rates are given to four places with the exact fraction beside them. `0.625` and `0.8125` are exact
binary values on a rounding tie, and two-place rounding of them is convention-dependent — an earlier
draft printed `0.63`, which is not a number the engine emits under any rounding mode.)*
An earlier draft described this cluster as "BTC-only" and reported only BTC and BSV. That was wrong
in both respects: Schnorr is a divergence for BCH and XEC as well, and **the merge moves those two
chains further than it moves BTC**. The merge moves **every** chain and not in one direction: BTC {{FIG:merged_BTC}}, BSV {{FIG:merged_BSV}}, and BCH, XEC and BTG {{FIG:merged_BCH}} each — reported in full rather than for the two that suit the argument. BSV remains lowest under the merged individuation.

**Confidence.** The {{FIG:conf_k}} medium-confidence cells (script-limit, signature-scheme and timelock
details on BCH, BSV and XEC) lie inside all of these ranges and do not change the ordering.
**Exhaustively, and now computed rather than asserted: `confidence_sensitivity()` enumerates all
{{FIG:conf_assignments}} assignments of those cells to match or mismatch, and BSV is uniquely lowest
in {{FIG:conf_holds_in}} of them.** This result was previously stated in the text and produced by no
code; it is emitted to `figures.json` so that it follows a cell edit instead of outliving one.

## 5.1  Label granularity — the sensitivity of the encoding itself

Two profiles match iff their labels are **equal as strings**. The choice of label is therefore itself
a coding decision, and the shipped dataset contains a case where two labels name the same condition:

```
v0.1.0  block_size_rule = "no-dedicated-cap"
BSV     block_size_rule = "no-consensus-cap"
```
Both mean *no consensus rule caps the block size*. **Scored as a mismatch purely because the strings
differ.** The same applies to `unbounded-openssl` versus `unbounded` on script-number width.
Conversely, a coder could reasonably argue the opposite way on `script_opcodes`: BSV's post-Genesis
vocabulary is not v0.1's, since it adds `OP_CHECKDATASIG`, `OP_SPLIT` and `NUM2BIN`/`BIN2NUM` while
still disabling `OP_2MUL`, `OP_2DIV`, `OP_VERIF` and `OP_VERNOTIF`.

: Label granularity. Each row re-scores the whole comparison under one defensible alternative
*labelling* of states that are already agreed as facts. **Only BSV moves.** Relabelling shifts it
{{FIG:bsv_move_label}} from its base rate against {{FIG:bsv_move_loo}} for removing any single axis
— **one cell's individuation can matter more than an entire axis** — though dropping up to three
axes moves it further still, {{FIG:bsv_move_subset}}.

{{TABLE:table5_labels}}

> ### $\Rightarrow$ BSV SPANS {{FIG:lab_BSV}} UNDER RELABELLING — WIDER THAN LEAVE-ONE-OUT {{FIG:loo_BSV}}.
>
> **None of these is a correction.** Each is a labelling a competent coder could have chosen from the
> same primary sources. **The spread is the result**, and it is the honest answer to what an earlier
> draft of this paper claimed when it said there was *"nothing for two independent coders to disagree
> about"*. There is: they can disagree about individuation, and that disagreement moves the score
> {{FIG:bsv_move_label}} — more than removing any single axis does ({{FIG:bsv_move_loo}}), though
> less than dropping up to three ({{FIG:bsv_move_subset}}).
>
> **This does not weaken the instrument; it locates its soft joint.** A displacement measure
> defined by label equality inherits every judgement embedded in the labels. Reporting that
> explicitly is the difference between a measurement and an assertion. **The soft joint was
> identified in review, not in construction** — which is itself evidence about where a
> label-equality measure is weakest.

# 6. Interpretation

The output is **reference-relative consensus-rule displacement**, nothing more. It is *not a metric*, and the reason is stronger than an
earlier draft stated. That draft said identity-of-indiscernibles fails because *"distinct profiles can
share a mismatch rate"* — but sharing a value is not a failure of that axiom. **The real failure is
that distinct profiles can sit at distance ZERO.** Take two axes and profiles
$A=(0,\emptyset)$, $B=(0,1)$, $C=(1,1)$. Under skip-unspecified $d(A,B)=0$ although $A \neq B$; and
$d(A,C)=1$ while $d(A,B)+d(B,C)=0+\tfrac{1}{2}$, so the triangle inequality fails too. We therefore
do not call it a metric. It is *not a quality score* and *not a ranking of
which chain "is" Bitcoin*: protocol identity also involves naming, continuity, adoption, and governance,
none of which this instrument measures or should. What the instrument does provide is a way to state — and
have anyone re-derive — that, on a fixed, source-anchored set of consensus axes, chain X's rules differ
from reference Y on a specific fraction of the jointly-specified axes, with the sensitivity of that
fraction made explicit.

# 7. Limitations

**Granularity.** The axis enumeration, though rule-governed, still embodies a choice of granularity;
the four sensitivity analyses bound but do not eliminate its influence. Relatedly, only {{FIG:n_discriminating}} of the {{FIG:n_axes}}
axes discriminate between chains at all (Section 2), so the reported rates contain a fixed component
that carries no comparative information.

**Coverage.** Coverage is intrinsically low for the two earlier references, which limits what can be
said against them — a limit we report rather than paper over, and which Section 4.2 shows to be more
than a technicality: **the only axis on which any two references agree is the proof-of-work
function, and they differ on every other axis they share.**

**No historical evaluation.** Values are asserted at a single frozen date, 1 August 2026. The engine
accepts an `--at` argument and **refuses** any earlier date. It previously accepted one and returned
byte-identical output, because no cell records when its rule activated; that silent no-op has been
replaced by an explicit refusal naming what is missing. Making the instrument answer historically
would require replacing each chain cell's single value with a sourced timeline — roughly {{FIG:aud_specified}} cells,
each needing the activation date its primary source states. That is real work, it is not done, and we
prefer to say so than to ship a flag that appears to do it. **We note this because a paper whose
claim is reproducibility is exactly the paper in which an inert control is most damaging: a reader
who finds one has no way to judge which other capability is also decorative.**

**A population that is eligible, not proven closed.** The chain-selection criteria were fixed before
application to the candidate audit, and that audit applies them to candidates outside the set —
which is how Bitcoin Gold was found to qualify and became a fifth measured chain rather than a
fourth criterion. **But
passing that test on a hand-built candidate list does not prove the list is complete.** The criteria
say which chains are *eligible*; they do not certify that every eligible descendant has been
enumerated. We therefore claim only that **these five qualifying chains were identified by the
candidate audit**, and not that they are every chain the rule admits. This is the same posture as
the axis set: **admissible, not exhaustive** — and both weakenings were forced by external checks
rather than found internally, which is itself the honest thing to report about the method.

**Scope.** The method is deliberately confined to consensus rules; it says nothing about the economic,
social, or governance dimensions of the chains it compares, and must not be read as if it did. It
generalises beyond Bitcoin to any protocol lineage with documented change logs, which is its intended
contribution.

**Source attribution, and what a census of it found.** The method's premise is that a reader may
contest any cell against its cited source, which requires the citation to be the *right* one. We
therefore audited the citations mechanically rather than asserting them: `audit_btc.py` fetches the
BIPs repository and confirms **8 of 8** BIP-backed BTC cells, and `audit_descendants.py` fetches the
Bitcoin SV, Bitcoin Cash and Bitcoin ABC primary specifications and confirms **18 of 18** probes
across BCH, BSV and XEC. Each fetch carries a control requiring the document to name itself, so a
challenge or error page cannot be read as an answer. **The same script also probes Bitcoin Gold's
own `chainparams.cpp` for the {{FIG:aud_probes_btg}} cells that distinguish it**, so all
{{FIG:aud_probes_btg}} are recorded in `tables/audit_descendants.json` alongside the others. *(A
third script, `audit_btg.py`, is not a citation audit at all: it tests chain-selection criterion (2)
— whether Bitcoin Gold was producing blocks at the freeze — and it is why Bitcoin Gold is measured
here rather than excluded. It emits no citation ledger because it verifies no cell.)*
**Two units are in play here and they must not be added across.** The non-BTG probes number
{{FIG:aud_probes_first2}} over {{FIG:aud_cells_first2}} distinct *cells* — a cell can be probed more
than once. Adding Bitcoin Gold's {{FIG:aud_probes_btg}} probes, none of which repeats an earlier
cell, gives **{{FIG:aud_probes_total}} probes over {{FIG:aud_fetched}} cells**. The fetched figure
quoted throughout this paper is the *cell* count. **The split is by chain, not by script**, because
Bitcoin Gold's cells were the ones added last.

**Three denominators appear in this paper and they are not interchangeable:**
**{{FIG:n_cells}}** total profile cells, **{{FIG:n_specified}}** of them carrying a value across all
profiles, and **{{FIG:aud_specified}}** specified cells on the five *chains* — which is the
denominator the audit partition uses, because that partition is defined over the descendant-chain
cells; the three historical reference profiles are source-anchored separately and are not part of it.

**Those are pass rates on the probes that were run, and a pass rate is not a coverage figure.** The
denominator matters more than the numerator, so the engine partitions all
{{FIG:aud_specified}} specified cells by *what each one's warrant actually is*:

: Audit coverage, partitioned by what each cell's warrant actually is. **A pass rate on the probes
that were run is not a coverage figure; this is the denominator.**

{{TABLE:table7_audit}}

The unclassified group is the honest residue and it is not empty; several of its cells are also the
medium-confidence ones, which is why the confidence sensitivity in Section 5 matters. **We state
this partition rather than the two pass rates alone, because the pass rates read as a census and are
not one.**

The census changed two citations and **no values**. BCH's script-integer cell cited the May 2022
upgrade, which delivered 64-bit integers; arbitrary precision arrived with CHIP-2024-07 BigInt,
activated 15 May 2025 — still before the freeze, so the value stood and only the source was wrong.
BSV's signature-scheme cell cited the Genesis specification, which contains no occurrence of *ECDSA*
or *Schnorr*; it is an absence, and is now cited and scored as one. Separately, three attributions
warrant a reader's attention without being errors: strict-DER encoding on BCH, BSV and XEC is
inherited from BIP66 (2015) rather than originating at the 2017 fork, and BSV's CW-144 difficulty
algorithm originates in the November 2017 Bitcoin Cash upgrade rather than the August 2017 fork.

**Claims of absence are the dataset's weakest footing, and they are structurally so.** The `none`
cells — {{FIG:aud_absence}} of them: **segwit on BCH, BSV and XEC** (Bitcoin Gold forked after
segwit activated and therefore has it), **Taproot on BCH, BSV, XEC and BTG**, and **the Schnorr
signature scheme on BSV and BTG** — cannot be confirmed by any
audit, because **no document establishes that a rule is absent**. They rest on chronology, a fork
cannot remove what it never had, together with the absence of any upgrade specification introducing
them. This is weaker than a positive citation, it is not remediable by further searching, and it is
reported here rather than left for a reader to infer from the fact that the audit did not cover it.

# 8. Conclusion

Situating chains against a historical reference need not be advocacy. By making the axes explicit
and fixing them before scoring,
anchoring every value to a primary source, reporting coverage alongside mismatch, and exposing sensitivity,
the comparison becomes a computation a reader can rerun and contest cell by cell — reproducibility standing
in for the inter-rater machinery a subjective coding would need. The worked result is itself instructive:
the "distance from the origin" question is degenerate against the whitepaper, low-coverage against the
preview, and, against v0.1.0, yields an ordering that is source-anchored yet reference-relative and
individuation-sensitive — which is precisely why it should be read as a measurement, not a verdict.
Two of the instrument's own outputs make that case better than the argument does. The chain with the
fewest mismatches is also the only one that reaches *any* of its agreement by removal rather than
preservation — {{FIG:rest_BSV}} axes of {{FIG:match_BSV}}, with the other {{FIG:ret_BSV}} preserved throughout — and a displacement
measure is constitutionally unable to tell the two apart; and the three candidate origins do not
describe one ruleset — {{FIG:ref_summary}} — so the choice of reference is not a technical preliminary but
the substance of the question. **A measurement that discloses what it cannot see is more useful than one
that does not, and building the disclosure into the engine is the only way to keep it from being
forgotten.**

# Data and Code Availability

Every numerical result and table in this paper regenerates from `obl_metric.py`, and
`figures/mismatch_heatmap.py` renders Figure 1 deterministically from the engine's axis-matrix
output. The engine carries the axis dataset it embeds. Running it writes `comparison.json` (the
full cell-level record, including the criterion, primary source and confidence for each of the {{FIG:n_cells}}
cells), `comparison.csv` (the summary), and `axis_matrix.csv` (the raw axis values); the figure
regenerates from the same engine. The code, data and this paper's source are available at
`https://github.com/original-bitcoin-laboratory/genesis`. **Every numerical figure quoted in this
paper is interpolated from the engine's output when the manuscript is built, not typed**, so the
reported
values are re-derived on every build rather than compared against the engine as of a date. The
digests below identify the engine outputs from which the reported results can be independently
reconstructed.

**The bytes, not just the address.** A repository URL is a promise: it can be edited after
publication and a reader cannot tell. So the scoring, audit and figure artifacts underlying every
reported result name themselves, by full SHA-256:

```
obl_metric.py ({{FIG:engine_bytes}} bytes)
{{FIG:engine_sha}}
audit_descendants.py
{{FIG:sha_descendants}}
audit_btc.py
{{FIG:sha_btc}}
audit_btg.py
{{FIG:sha_btg}}
figures/mismatch_heatmap.py
{{FIG:sha_figscript}}
figures/mismatch_heatmap_v010.png
{{FIG:sha_figpng}}

tables/audit_descendants.json   run {{FIG:ledger_run_descendants}}
{{FIG:sha_ledger_descendants}}
tables/audit_btc.json           run {{FIG:ledger_run_btc}}
{{FIG:sha_ledger_btc}}

artifacts/comparison.json
{{FIG:sha_out_comparison}}
artifacts/axis_matrix.csv
{{FIG:sha_out_axismatrix}}
artifacts/comparison.csv
{{FIG:sha_out_comparisoncsv}}

tables/table*.md   manifest over the {{FIG:n_tables_manifest}} engine-emitted table files
{{FIG:sha_tables_manifest}}
```

Any copy that does not hash to these is not the copy this paper reports on.
**The two `tables/audit_*.json` entries are the audit ledgers, and they are what tie the reported
audit figures to recorded output rather than to source files that merely existed.** Each records its
own run timestamp and, per probe, the URL fetched, the HTTP status, the control outcome and the
SHA-256 of the retrieved body; the {{FIG:aud_probes_total}} probe records over
{{FIG:aud_fetched}} distinct cells reported in Section 7 are the contents of those two files —
Bitcoin Gold's {{FIG:aud_probes_btg}} included, since `audit_descendants.py` performs them.

*A digest change is therefore legible, within what a digest can establish.* **If a ledger digest
changes, the recorded audit output changed, and the embedded run timestamp identifies the execution
that the ledger records. If only a script digest changes while its ledger digest and run timestamp
do not, the published audit output has not been regenerated under those new script bytes.**
*A digest proves which bytes exist, not how they came to exist: the timestamp is a recorded claim
about an execution, not proof that one occurred. The narrower statement is the one the evidence
supports.*

**The three `artifacts/` entries are the engine's principal serialised outputs**, and they give the
engine the counterpart the ledgers give the audit scripts. `comparison.json` pins the full
cell-level comparison record, `axis_matrix.csv` pins the canonical axis matrix, and
`comparison.csv` pins the summary rates. Every numerical table in this paper is emitted by the same
engine run whose comparison state those files serialise.

**Their digests establish byte identity, not the semantic reason for a change.** A changed digest
means that artifact changed; a diff identifies whether the change touched values, sources,
confidence, criteria or serialisation. *`comparison.json` records criteria, primary sources and
confidence alongside values, so a citation-only correction moves its digest while every number in
this paper stays the same — this work has made exactly such corrections.* Conversely, if the engine
digest changes while these three remain byte-identical, what is established is that the serialised
comparison state and summary outputs are unchanged.

**The final entry closes the remaining link between that state and a printed table.** The
manuscript's numerical tables are substituted from files the engine emits, and the manifest is a
single SHA-256 over each emitted file's name and digest, so those {{FIG:n_tables_manifest}} files
are pinned without adding {{FIG:n_tables_manifest}} lines. *One presentation artifact remains
deliberately outside the list: `figures.json`, which carries the scalar substitutions — it is the
file every digest above is recorded in, so it cannot contain its own.*

*A generation timestamp was deliberately not embedded, and the distinction is the point: it would
change the digest on every run and convert "the output changed" into "time passed", destroying the
property the pairing exists to provide. The audit ledgers carry timestamps because they record
network fetches, which are not reproducible; these record computations, which are.* **The writers
disable platform line-ending translation, so these digests are properties of the data rather than
of the machine that produced them.**
*The digests cover those files only — not the fetched upstream sources, whose own hashes are
recorded per-probe inside the ledgers, and not `figures.json`, which cannot be listed here because
it is the file these digests are recorded in.*
Updating any chain's rule after a future upgrade is a one-cell edit carrying a new primary source,
after which the entire table, the sensitivity analysis and the figure recompute. **Once the encoding is fixed there is no manual scoring
step: the artifact performs the derivation deterministically**, and a reader who disagrees with a
value can contest it cell by cell against the cited source. *That is not a claim that no human
judgement is present — it is present in the encoding, and Section 5.1 measures how much the result
moves when a defensible alternative labelling is substituted.*

**Scope statement.** The experimental chains and artifacts associated with this work carry no
monetary value: there is no premine, no sale, no token, and no price. Nothing in this paper is
financial advice, and the instrument takes no position on whether any chain should change anything.
**The instrument compares five chains that do carry a market price; it measures none of it, and a
mismatch rate must not be read as a statement about any of them as an asset.**

# References
