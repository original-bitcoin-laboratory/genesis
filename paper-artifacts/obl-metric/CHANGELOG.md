# Changelog — the forensic history the paper no longer carries

**R4 asked for the manuscript to read like a scientific article rather than a merged
referee-response letter, and it was right.** The methodological admissions stay in the paper,
compressed to a sentence each. The account of *how* each one was found lives here.

★ **Nothing is deleted, only relocated.** A finding that cost something to learn is worth keeping;
it is simply not what a reader of the paper came for.

## Round 18 (16 Aug 2026) — the last unpinned link, and a self-healing test suite

Both referees returned **GO** with no defects. R18-#2: *"Eighteen rounds; the instrument hasn't been
broken."* Two optional items were taken, one of them not as proposed.

- **The tables manifest closes the last link between `comparison.json` and a printed table.**
  R18-#2 recorded `tables/*.md` as unhashed and explicitly did *not* recommend fixing it, on the
  grounds that Data and Code is already 9.4% of the document. **Both parts of that are right**, so
  it is closed the cheap way: **one SHA-256 over each emitted file's name and digest — a single
  line covering eight files.** ⇒ *`figures.json` remains the only presentation artifact outside the
  list, and for a reason that cannot be engineered away: it is the file every digest is recorded
  in, so it cannot contain its own.*

- **One proposed wording change was declined and replaced.** R18-#1 read *"not `figures.json`,
  which contains them"* as an ambiguous pronoun — correct — and proposed *"which contains
  presentation-layer scalar values used during manuscript generation."* **That removes the
  ambiguity and the reason at the same time.** The exclusion is not because the file is
  presentation-layer; it is because it is where the digests live. Rewritten to say exactly that.
  The other tweak — *"Every numerical figure"*, distinguishing text figures from Figure 1 — was
  adopted verbatim.

> ### ⛔ THE TEST SUITE HEALS THE DEFECTS ITS OWN CHECKS LOOK FOR
> Perturbing a table file and deleting one both failed to trip the new manifest gate. Corrupting
> `comparison.json` failed to trip `test_M` last round. The cause is the same in all three:
> **`test_B` runs the engine as a subprocess early in the suite, regenerating every artifact before
> the later checks read it.**
>
> ★★ That is not a flaw to remove — regenerating is what makes the later checks describe *current*
> engine output rather than whatever was lying on disk. But it means **a control that corrupts an
> artifact proves nothing about these gates.** The only controls that work break the *producer*:
> removing `newline=` from the engine (test_M failed correctly), and making the manifest hash
> on-disk bytes instead of the bytes about to be written (the manifest gate failed correctly, with
> exactly the stale-directory signature it exists to catch).
>
> ⇒ **Know which side of a self-healing boundary your control is on, or you will conclude a gate is
> stuck-green when it is merely being fed a repaired input.**

- **The manifest is computed from the bytes about to be written, never from disk** — at that moment
  the `.md` files are still the previous run's, the same trap that made the engine-output digests
  read a stale directory in round 16. Verified by round trip: recomputing from what was actually
  written reproduces the declared value.

- ⚠️ **The first version of the round-trip check swept all of `tables/`** and reported a mismatch —
  which was the check's error, not the manifest's: that directory also holds the two audit ledgers,
  written by the audit scripts and hashed separately. Scoped to `table*.md`. *Same shape as the
  substring search that matched the wrong writer last round: **a check must name its subject as
  precisely as the claim it is testing.***

## Round 17 (16 Aug 2026) -- a digest that was a property of the machine

R17-#1 returned a micro NO-GO on the provenance paragraph alone; R17-#2 found a latent defect that
sixteen rounds had treated as cosmetic. Both were right, and the paragraph was rewritten to claim
only what the hashes establish.

- **CRLF made a published digest platform-dependent.** `comparison.json` was written with
  `write_text` and no `newline=` argument, so Python applied platform translation. A reader
  regenerating it on Linux gets **identical content, different bytes, different SHA-256** -- and,
  under the rule this paper now states, would have to read that as a changed result. ★★ **Cosmetic
  for sixteen rounds; material the instant the hash became a verification target.** Fixed at the
  writer, where `.gitattributes` cannot reach because the bytes are made at run time.
  ⚠️ **The two CSVs were deliberately NOT touched**: `csv.writer` with `newline=""` emits CRLF on
  every platform per RFC 4180, so they were already byte-stable. *Normalising them to match would
  have changed two correct digests to make three files look alike -- uniformity is not the property
  being protected, platform-independence is.*

- **Four overclaims in the new paragraph, all removed.**
  *"The last two are the audit ledgers"* -- they were positions 7 and 8 once the outputs were added;
  the entries are now **named**, not counted. **Fifth positional pointer to go stale as a list
  grew.**
  *"The digests name the exact outputs they were interpolated from"* -- false: interpolation runs
  through `figures.json`, which cannot be hashed inside itself.
  *"If any of them changes, a number in this paper changed"* -- false: `comparison.json` carries
  criteria, sources and confidence, so a citation-only correction moves the digest while every
  number holds. **This work has made exactly such corrections.**
  *"Every table is built from `comparison.json`"* -- a data-flow claim, and checking the code
  settled it: `emit_tables` builds from in-memory state and never reads that file.

- **`test_M` gates the line-ending property, and proving it fires took three attempts.** Corrupting
  the file on disk proved nothing -- `test_B` re-runs the engine earlier in the suite and silently
  repaired it. **The only true control was breaking the ENGINE**, after which the byte check failed
  correctly. ⛔ *And the source check kept passing, because a bare substring search for the newline
  argument also matches the TABLES writer, which carries the same argument.* **A substring search
  over a whole file answers "does this text exist somewhere", never "is this call correct".**
  Scoped to the `comparison.json` statement, both halves now fail together.

  ⚠️ **This entry was itself written through a shell heredoc that ate the escape** — the eighth
  occurrence of that bug in this project, and the first that `test_I` could not catch, because the
  mangled result was a legitimate newline rather than a control byte. *An instrument built for one
  failure mode does not cover its neighbours.*

> ### THE SHAPE OF THE LAST FIVE ROUNDS
> R13 published digests with no address. R14 gave the audits an execution record. R15 found a
> correct count concealing a wrong attribution. R16 gave the engine the pair the audits had. R17
> found that one of those digests described **this machine** rather than the data.
> ⇒ *Each fix was sound and each created the surface for the next. The referees could see the
> paragraph; only running the code could see what the paragraph was about.*

## Round 16 (16 Aug 2026) — the engine gets the pair the audits had

R16-#2 withdrew the round-15 blocker unprompted, and both referees converged on one structural gap
plus one visible typesetting defect.

- **"References" was typeset twice.** The manuscript's `# References` heading is *correct in
  markdown*, where pandoc places the bibliography under the heading the author supplies, and *wrong
  in LaTeX*, where `paper.bbl` opens a `thebibliography` environment and that environment emits its
  own.
  **The same source is right in one output format and wrong in the other**, so the fix belongs at
  the conversion — deleting it upstream would leave the markdown bibliography unlabelled.
  ⛔ **No compile-time gate could ever have caught it: LaTeX is perfectly happy to set two
  headings, and the log says nothing.** Found by a referee rasterising page 23.
  ⇒ Now gated twice — zero explicit `\section{References}` in the generated TeX, and **exactly one
  rendered heading read back out of the compiled PDF with `pdftotext`**. Both were exercised on a
  failing input: with the removal disabled the TeX gate reads 1 and, with both disabled, the PDF
  gate reads 2 and the bundle FAILS.

- **★★ The engine had no output to pair its digest against, and the audit scripts did.** The engine
  digest moved in three consecutive bundles while every reported number stayed identical. For an
  audit script that is legible — script digest moves, ledger digest and timestamp do not, therefore
  the output was not regenerated under the new bytes. **Tables 2–9 rested on one unhashed sentence
  naming a date three engine revisions old.** `artifacts/comparison.json`, `axis_matrix.csv` and
  `comparison.csv` are now hashed and published: eleven digests.

- **★★★ And deliberately WITHOUT the generation timestamps the referee asked for.** These outputs
  are **deterministic** — two consecutive runs are byte-identical, and nothing in them is a wall
  clock, both verified. **Embedding one would change the digest on every run and convert "the
  output changed" into "time passed", destroying exactly the legibility the pairing exists to
  provide.** The audit ledgers carry timestamps because they record *network fetches*, which are
  not reproducible; these record *computations*, which are. ⇒ *The stronger artifact was the one
  that recorded less.*

- **⚠️ THREE CLAIMS WRITTEN THIS ROUND WERE FALSE AND WERE CAUGHT BY TESTING THEM, NOT BY READING
  THEM.** *"The build fails if any figure disagrees with the engine's output"* — it does not; a
  wrong literal that matches no figure passes. Narrowed to *"the build rejects a retyped literal
  that duplicates one"* — **also false**: that rule fires only for a key interpolated *nowhere*
  whose value exceeds two characters. The surviving sentence claims only what is demonstrable:
  every figure is *interpolated* from the engine's output rather than typed.
  ★ **A claim about one's own instrument is not privileged evidence about it.**

- **The digest-block staleness guard needed no edit**, because R15 rewrote it to derive its subject.
  It went from 8 to 11 the moment the keys existed. ⇒ *That is what the derived form bought.*

## Round 15 (16 Aug 2026) — ★★★ a correct count concealing a wrong attribution

R15-#2 returned **NO-GO** on the new provenance paragraph. Both referees identified the same
blocker: the block hashes two ledgers, there is no `tables/audit_btg.json`, therefore Bitcoin
Gold's five probes are unrecorded — and both prescribed emitting a third ledger.

**Checking the data rather than the filenames showed the blocker does not exist, and something
worse does.**

```
tables/audit_descendants.json   23 records   BSV 7 · BCH 7 · XEC 4 · BTG 5   22 distinct cells
tables/audit_btc.json            8 records   BTC 8                            7 distinct cells
                                31 records                                    29 distinct cells
```

⇒ **Bitcoin Gold's five probes were in a hashed ledger all along** — including `pow_function`, the
axis BTG was added to expose. The sentence *"the 31 probes over 29 cells are the contents of these
two files"* was true, and `test_L` had already verified it by counting.

- **⛔ THE REAL DEFECT, which the counting could never see.** Section 7 said *"A third script,
  `audit_btg.py`, probes Bitcoin Gold's own `chainparams.cpp` for the 5 cells that distinguish
  it."* **It does not, and never did.** `audit_btg.py` tests chain-selection criterion (2) — was
  BTG producing blocks at the freeze — and emits no citation ledger because it verifies no cell.
  Those five probes are run by `audit_descendants.py`. The engine splits them out **by chain**
  (`r["chain"] == "BTG"`), never by script; the prose had read that split as a script boundary.
  ★★ **The count was right, so every numeric gate passed, for rounds.**

- **★★★ And the prescribed fix would have broken the number that was already correct.** Emitting
  `audit_btg.json` would have duplicated five records that already exist, taking the ledger total
  to 36 against a reported 31. ⇒ *Two independent referees reasoned correctly from the artifact
  list to the wrong conclusion, because the missing file was evidence of a naming assumption, not
  of a missing execution.* **The remedy for a symptom is only safe once the cause is known.**

- **MAJOR, accepted in full: a digest cannot prove an execution occurred.** *"If a ledger digest
  moves, the audit was re-run"* claims more than SHA-256 supplies — bytes can be regenerated,
  edited or copied, and an embedded timestamp is a recorded claim, not proof. Replaced with the
  narrower statement: a changed ledger digest means the recorded **output** changed; a changed
  script digest with an unchanged ledger digest and timestamp means the output **has not been
  regenerated** under those bytes. Scientifically stronger for saying only what is established.

- **"The artifacts that produced this paper" was broader than its list.** Figure 1 is rendered by a
  separate program, which the same section says — and neither `figures/mismatch_heatmap.py` nor the
  PNG was hashed. Both added; the sentence now reads "the scoring, audit and figure artifacts
  underlying every reported result". Eight digests.

- **`test_L` now checks attribution, not just arithmetic**, against each ledger's own `script`
  field — the only record of who actually ran a probe. Negative-controlled by the defect itself: it
  failed on the old sentence and passes on the corrected one.

> ### ⛔ THE STALENESS GUARD HAD TO BE REWRITTEN, ONE ROUND AFTER PREDICTING ITS OWN FAILURE
> R13 wrote it over four hard-coded digest keys. R14 added two ledgers and widened the list by
> hand, with a comment warning that a guard covering only what existed when it was written goes
> blind to the new half. **R15 added two more and it was blind to them again.** It now derives its
> subject: every 64-hex value in `figures.json` that the template references must appear in the
> built manuscript — 8 of 8 today, and new digests are covered the moment they exist.
> ⇒ **A list that must be updated by hand whenever the thing it guards grows is not a guard; it is
> a second copy of the problem.**

## Round 14 (16 Aug 2026) — what the code IS versus what the code DID

Both referees returned **GO** again. R14-#1 found the one thing the previous round's fix had left
ambiguous, and it is a genuinely new class of objection.

- **★★ Two digests moved and the paper gave no way to read the change.** `audit_descendants.py`
  and `audit_btc.py` changed between revisions 8 and 9. Two readings fit: *the scripts were
  reformatted and the results still hold* (true — it was the LF normalisation of Round 13), or
  *the probes changed and the reported figures were never refreshed*. **Nothing in the manuscript
  distinguished them, and a hostile reader takes the second.** ⇒ *"The paper commits to what the
  code is, not to what it did."*

- **The fix: publish the ledgers, not only the scripts.** `tables/audit_descendants.json` and
  `tables/audit_btc.json` now appear in the same verbatim block, each with its SHA-256 **and its
  run timestamp**. Each holds, per probe, the URL fetched, the HTTP status, the control outcome and
  the **SHA-256 of the retrieved body**. The reported 31 probes over 29 cells is now the content of
  two dated artifacts rather than a property of source files that merely existed. **A future digest
  change becomes legible**: a ledger digest moving means the audit was re-run and the figures
  follow it; only a script digest moving means the code changed without a re-run, and the dates
  say so.

- **Both new facts are computed, never typed.** The engine hashes the ledgers and lifts their
  `generated_utc` into `figures.json`, so they cannot go stale the way a hand-written digest would.
  No circularity: the ledgers are written by the audit scripts, not by the engine.

- **`test_L` verifies the claim rather than asserting it.** Counting the records, requiring a
  `body_sha256` on every one, and requiring the total to equal the figure the paper prints — 31 of
  31, all with body digests. ⛔ *Asserting in prose that the ledgers back the number is the same
  unverified pointer that produced every defect since round 6.* The paper may say it because the
  number is read out of them.

- **The Round 13 staleness guard was extended in the same edit.** It covered the four script
  digests; the ledgers had just doubled the block. ⚠️ **A guard that covers only what existed when
  it was written goes blind to exactly the half most likely to be wrong** — the new half.

## Round 13 (16 Aug 2026) — ★★★ the two defects no referee could have found

Both referees returned **GO**. R13-#2 named the one check it could not run itself: *"the only
remaining operational check on your side is that the immutable release you intend readers to use
contains exactly the full SHA-256 values printed in the manuscript."* **Running it failed, twice,
for two independent reasons.**

- **⛔ D1 — the address contained none of the artifacts.** *Data and Code* stated the code and data
  were available at `github.com/original-bitcoin-laboratory/genesis`. That repository tracks none
  of the four declared files, has never mentioned obl-metric, and its `paper-artifacts/` directory
  belongs to a different paper. All twelve repositories in the workspace were checked: **zero.**
  ⇒ The paper printed four full digests and said *"Any copy that does not hash to these is not the
  copy this paper reports on"* — pointing at a place with no copy to hash. **A commitment with no
  address is not weaker than no commitment; it is a promise a reader cannot redeem, in the one
  section whose entire purpose is redeeming it.**

- **⛔ D2 — the digests were not reproducible from any clone, on any platform, including this one.**
  Found by writing the *negative control* for the gate built for D1: the four artifacts were
  **mixed line endings** — two stored LF, two CRLF — and the declared digests were of those exact
  mixed bytes. Git normalises text blobs to LF and checks out the platform convention, so a reader
  cloning on Windows would hash CRLF and get a different answer **from the correct file**, and a
  reader on Linux would get a different answer for the other two. ★★ **D2 would have silently
  defeated the fix for D1**: publish the files, add a commit hash, and readers still mismatch.
  Fixed by normalising all four to LF, regenerating the digests, and pinning `-text` in
  `.gitattributes` so git stores and checks out the bytes verbatim.

- **⚠️ An ordering trap, caught by the new gate within the hour.** After normalisation the engine
  was re-run but `paper.md` was not rebuilt, so `arxiv-submission.zip` briefly carried two digests
  naming bytes no longer on disk — **with every gate green**, because they all compare paper.md to
  the template and the template was consistent with itself. `make_arxiv.py` now refuses to build a
  manuscript that lacks a digest `figures.json` declares.

- Two checks downgraded from failure to **warning** where they genuinely cannot apply (no clone
  visible / no nested `package/` inside the built package). **A check that always fails is a check
  the operator learns to skip** — which is how the defect it exists for gets through again.

- R13-#2's optional wording adopted: *"the chain-selection criteria **were fixed before application
  to the candidate audit**"*, matching Section 2's language exactly.

> ### ★★★ WHY EVERY GATE WAS GREEN FOR THIRTEEN ROUNDS
> `test_J` proved `package/` ships the declared bytes, and it passed every round. Every other check
> compared local things to other local things: template to paper, package to figures.json, tex to
> log. **The claim was about the outside world, and nothing in the harness ever looked outside.**
> The referees could not see it either — they hold only the minimal three-file arXiv bundle, where
> those bytes are absent *by design*, so their absence proves nothing. R13-#1 could see *"no DOI,
> no commit hash"*; it could not see *"no files"*.
> ⇒ **A green gate is evidence about what it measures, never about what it was assumed to cover.**
> Now `test_K`.

## Round 4 (14 Aug 2026)

- **Bitcoin Gold was measured, not excluded.** Testing our own chain-selection rule against a
  candidate it should reject found that BTG satisfies all three criteria — block 958,305, header
  time 2026-08-01T21:01:04Z, from a primary chain endpoint. It became a fifth chain.
- **That forced an axis into existence.** BTG changed the proof-of-work function and no axis
  covered it: the axis set had been shaped, invisibly, by the chains already chosen. With BIP34
  (identified by a referee), the enumeration went 17 -> 19 and every rate moved. **The ordering
  did not.** The paper now claims the axis list is admissible, not exhaustive.
- **The audits became gates.** Both exited 0 while reporting every probe void. They now exit
  nonzero on any failure or void, and emit `tables/audit_*.json` carrying each document's
  SHA-256; the engine reads that instead of a hand-maintained dict, which had drifted one cell
  behind (BSV/block_size_rule was fetched and reported unfetched).
- **eCash Heartbeat re-scoped.** It had been parked on fork-choice "to avoid double-counting".
  eCash's own description is a second difficulty on top of the base DAA with non-conforming
  blocks *rejected* — an acceptance rule, not a tip-selection rule. The difficulty axis was
  widened to say so.
- **The `$-$` minus, third form.** R1 literal -> R2 U+2212 (pdfTeX drops it) -> R3 the ASCII guard
  forbade U+2212 and the engine reverted to `$-$`, which the guard allowed. **A guard that bans one
  spelling of a defect selects for the others.** Now a plain hyphen, with the guard banning the
  shape `$...$<digit>` rather than a character.
- **Two four-round-old figure defects** — a title overprinting the disclaimer, and column labels
  printed twice — fixed. No gate could see either.

## Rounds 1-3

- **R2:** the manuscript stopped hand-carrying numbers the engine computes; `paper.md` became a
  build artifact and `revision_check_live.py` began reading it.
- **R3:** the captions stopped hand-carrying which table they labelled. All five `{{TABLE:}}`
  placeholders were shifted by one and the provenance table was generated and inserted nowhere,
  while a gate that checked only for a *missing* table stayed green.
- **The pattern across all four rounds:** each layer that stops hand-carrying exposes the next one
  that still does — manuscript, then captions, then the engine's own audit dict. **A check on
  presence reads as a check on correctness until something is present and wrong.**
