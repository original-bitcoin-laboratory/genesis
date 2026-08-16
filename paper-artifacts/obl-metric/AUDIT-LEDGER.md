# The audit ledger — verified findings, held for ONE controlled application

**14 August 2026.** ⛔ **NOTHING HERE HAS BEEN APPLIED TO THE DATASET, DELIBERATELY.**

> ### ★★★ WHY A LEDGER INSTEAD OF EDITS
>
> Round-2 referees found that my round-1 repairs **created six regressions**, because I patched
> strings one at a time on a dataset that kept moving. `FREEZE-PLAN.md` concluded: audit → freeze →
> rerun → **regenerate**, in one pass.
>
> **Applying these findings piecemeal would repeat exactly the behaviour that caused the problem.**
> They are recorded here with their sources and quoted evidence, and applied together or not at all.

---

## ✅ VERIFIED — primary sources fetched and quoted, 14 Aug 2026

### 1. XEC element-size limit — OUR CELL IS WRONG

```
our cell        element_size_limit  XEC = "raised", cited to bch_2018
SOURCE          github.com/Bitcoin-ABC/bitcoin-abc  src/script/script.h  (master)
VERBATIM        "// Maximum number of bytes pushable to the stack
                 static const unsigned int MAX_SCRIPT_ELEMENT_SIZE = 520;"
CORRECT VALUE   520-byte  — the same as BTC, NOT "raised"
```

★ **eCash split from BCH in 2020, five years before BCH raised the limit to 10,000 in the May 2025
VM Limits upgrade.** Inheriting BCH's later value was never possible. The cell's *citation* was the
tell — `bch_2018` for a chain that did not exist under that name in 2018.

### 2. XEC script-number width — OUR CELL IS WRONG

```
our cell        script_number_width  XEC = "4-byte", cited to bch_2018
SOURCE          same file
VERBATIM        "// Maximum byte size of integers for arithmetic opcodes when interpreting Script
                 constexpr size_t MAX_SCRIPTNUM_BYTE_SIZE = 8;"
CORRECT VALUE   8-byte
```

⚠️ **This one MOVES A NUMBER.** v0.1.0 is `unbounded-openssl`, so 4-byte and 8-byte are both
mismatches — **no rate changes** — but the *label* is wrong and §5.1 shows labels are load-bearing.

### 3. BSV Chronicle activation — SETTLED, and the source conflict is NOT load-bearing

```
chronicle-spec.md (fetched)   mainnet activation height 943,835
referee, from BSV v1.2.0      943,816, "targeted for 7 April 2026"
                              ⇒ THE TWO SOURCES DISAGREE BY 19 BLOCKS
```

**Asked the chain instead of choosing a side** (WhatsOnChain):

```
height 943,816   2026-04-07 20:49:50 UTC    BEFORE the 1 Aug 2026 freeze ✓
height 943,835   2026-04-07 23:48:55 UTC    BEFORE the 1 Aug 2026 freeze ✓
```

> ★★★ **BOTH CANDIDATES PRECEDE THE FREEZE, SO THE DISAGREEMENT DOES NOT AFFECT ANY VALUE.**
> Chronicle is in force at the freeze; `script_number_width BSV = 32mb-limit` is correct **whichever
> source has the right height.** ⇒ **Record the conflict, do not resolve it — resolving it would be
> a claim we cannot support, and we do not need it.**

★ Both sources agree on the *date* (7 April 2026) while differing on the height, which is the
signature of a *targeted* height versus the block that actually triggered activation.

### 4. BCH ABLA — the CHIP located

```
SOURCE   gitlab.com/0353F40E/ebaa  (raw/main/README.md, 80,686 B)
TITLE    "CHIP-2023-04 Adaptive Blocksize Limit Algorithm for Bitcoin Cash"
OWNER    bitcoincashautist (ac-A60AB5450353F40E)   STATUS  Accepted
ACTIVATION  upgradespecs.bitcoincashnode.org/2024-05-15-upgrade/ :
            "will take effect on the main network (mainnet) once the median time past (MTP)
             of the most recent 11 blocks is >= UNIX timestamp 1715774400
             (May 15, 2024 12:00:00 UTC)"
```

⇒ **BCH's block-size limit became DYNAMIC on 15 May 2024**, so our `32mb` is wrong at the freeze
**regardless of what the correct label turns out to be.** ⚠️ The replacement value needs a reading of
the CHIP, not a guess — an algorithmically-varying cap is not a number.

### 5. The BCH upgrade index — enumerated, so nothing is missed by guessing

`upgradespecs.bitcoincashnode.org` exposes a page per upgrade. **Relevant to the freeze:**

```
2024-05-15-upgrade/    ABLA
2025-05-15-upgrade/    VM Limits + BigInt (both CHIPs already fetched, status Final)
2026-05-15-upgrade/    ⚠️ INSIDE THE FREEZE AND ENTIRELY UNREAD
```

---

## ⛔ STILL UNAUDITED — and this is the real remaining work

**Five cells were found by outsiders reading a paper. That is a SAMPLE, not a census.**

```
68 descendant cells total   (4 chains × 17 axes)
~8 examined to date
60 NOT independently verified against a primary source at the 1 Aug 2026 freeze
```

> ### ★★★ THE AUTHOR-VERIFICATION CLAIM STAYS FALSE UNTIL THIS IS A CENSUS.
>
> *"Every consensus value in the dataset was verified by the author against the primary record named
> in its cell."* **Five demonstrable errors have now been found in the cells anyone happened to
> look at.** The honest options are: complete the census, or narrow the sentence to what was
> actually done.

---

## ⇒ THE ORDER OF WORK — and step 0 is not optional

```
0  MAKE THE PAPER STOP HAND-MAINTAINING NUMBERS.
   obl_metric.py emits tables/*.md; paper.md includes them at build time.
   ★ Until this exists, every later step re-creates the propagation defects.
1  census all 68 cells against primary sources; record verbatim quotes in the cell comments
2  apply THIS LEDGER in the same pass
3  freeze; rerun; regenerate every number, table AND FIGURE 1 (never regenerated — still 18 rows)
4  sweep the whole repo for obsolete strings:
      "18 axes" · "126 cells" · "three restorations" · "0.44" · "988" · "k=4" · "0.8000"
      · 0x07 BEL bytes · U+2212 · "$pprox$" · "nothing for independent coders to disagree about"
5  run BOTH suites; the referee's revision_check.py is the gate, not stress_test.py
6  build the arXiv bundle from scratch, render, inspect every page
```

⚠️ **Do not rebuild the PDF before step 3.** A build on a moving dataset is what produced a Figure 1
showing 18 rows under a caption saying 17.

---

# ROUND 2 OF THE CENSUS — the descendant columns, 14 August 2026

**Closed the largest unverified surface in the paper.** `audit_btc.py` had censused the BTC column
(8/8) and the other three had never been fetched at all. `audit_descendants.py` now probes them
against BSV, BCH and Bitcoin ABC primary sources: **18 confirmed, 0 not found, 0 void.**

## ⛔ THE DEFECT IN MY OWN INSTRUMENT, FOUND ON THE FIRST RUN

The first run reported **18/18** — and three of those were worthless. `ASERT`, `CTOR` and `schnorr`
matched inside page navigation:

```
<link rel="next" href="../2020-11-15-asert/">        matched "ASERT"
<link rel="prev" href="../2019-11-15-minimaldata/">  sat beside one matching "schnorr"
```

> ### ★★★ THIS IS THE BOT-WALLED-200 ERROR IN A NEW COSTUME
>
> **Reading the ENVELOPE and calling it the LETTER.** A term in an `href` is the site's own
> menu, not the document making a claim. **The fix was not a better regex — it was deleting the
> envelope before reading**: `body_text()` strips tags, so no attribute can ever satisfy a probe.
>
> ⇒ **A passing audit whose pattern can match site chrome is not evidence; it is furniture.**

## ✅ TWO CITATIONS CORRECTED, ZERO VALUES CHANGED

```
bch_bigint      SAID  "BCH May 2022 upgrade: large script integers (BigInt)"
                WAS   two upgrades conflated. May 2022 = 64-BIT integers; arbitrary precision is
                      CHIP-2024-07 BigInt, activated 15 May 2025
                ⇒ still inside the 1 Aug 2026 freeze, so THE VALUE STOOD. Only the source was wrong

BSV sig_scheme  SAID  "ecdsa-only", cited to bsv_genesis
                WAS   genesis-spec.md contains ZERO occurrences of "ECDSA", "Schnorr" or
                      "signature scheme" (measured)
                ⇒ re-cited to a new `bsv_no_schnorr` ABSENCE source, confidence high -> med
```

★★ **A CELL CAN BE CORRECT AND STILL BE UNSOURCED, and only a fetch tells the difference.** Both
errors were invisible to every check that did not open the document — including three referee passes.

## ★ WHAT DID NOT MOVE, WHICH IS THE STRONGEST OUTCOME AVAILABLE

```
BTC 0.7059 · BCH 0.7647 · BSV 0.4118 · XEC 0.7647     UNCHANGED, all four
n_high 82 -> 81 · n_med 6 -> 7                        one cell, deliberately
```

**The audit corrected provenance, not results.** An audit that moves the headline numbers casts
doubt on everything upstream of it; one that moves only citations tells a reader the encoding was
sound and the paperwork was not. **That is the better of the two findings and it was not designed.**

## ⛔ THE LIMIT THAT NO AUDIT CAN CLOSE

`none` cells — segwit and Taproot on all three descendants, Schnorr on BSV — are **CLAIMS OF
ABSENCE**, and **no document establishes that a rule is absent.** They rest on chronology (BCH
forked three weeks before segwit locked in; it never had it to remove) plus the absence of any
upgrade spec introducing them. **Not remediable by further searching.** Now stated in Limitations
in the paper's own voice, rather than left for a reader to infer from what the audit skipped.
