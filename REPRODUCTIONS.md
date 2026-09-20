# Reproductions — the ledger

One entry per attempt by a party other than this laboratory's own tooling to reproduce, rebuild or
review its published work, whatever the result. Each entry states who ran it, under what access, and
what the attempt is evidence of. The label is the finding: a run commissioned by the operator, or by a
party working from the operator's brief, is recorded as such and is not independent replication. The
laboratory's own statement of why that distinction matters is §6 of its method paper and the
second-laboratory criterion of the ancient-DNA literature it cites.

**Independent reproductions recorded, as of 20 September 2026: none.** Every row below is a run commissioned
by the operator. The absence is stated here rather than left implicit; the first entry from a party the
operator did not commission lands in this table and is labelled so.

Experimental laboratory research, in progress. Not money, not advice, no warranty (`RIGHTS.md`).

| date | party | access | task | result | evidence of |
|---|---|---|---|---|---|
| 2026-09-20 | an AI session commissioned by the operator, with no access to this workspace (run 1) | public repositories only; the session's network egress blocked GitHub raw and `bitcoin/bitcoin` | clean-room validator from `docs/JAN09-B-SPECIFICATION.md`; corpus replay; three constitution rows | validator for the stated bounds written and sanity-tested; corpus **not replayed** (could not be fetched); commits **not fetched**; reported strict DER as unspecified on the page because BIP 66 was outside the named material | what a stranger sees on the page alone: the bounds are stated, the base is delegated. Not a replication |
| 2026-09-20 | an AI session commissioned by the operator, with no access to this workspace (run 2) | public repositories, cloned; `bitcoin/bitcoin`, blobless clone; the site reached on a second attempt | the same brief | 1,400-line Python validator, `hashlib` only; **317/317 in January-2009 mode**, 316/317 in `JAN09-B` mode with the one designed disagreement (`bignum_add` under the 4-byte cap); block suite matched stage 127/127 and error string 126/127; five constitution rows checked against the commits, **all dates, author strings and diff lines held**, two naming defects found (`OBL-C-0003` named `MoneyRange` four days early; `OBL-C-0008` quoted a three-line message as one line); eleven gaps in the page listed, four still open after the session's own audit; its own validator carried two consensus bugs the corpus could not see (later `OP_NOP`s in the undefined range; no two-byte opcode space) | the corpus replays outside this laboratory's code, at `MODEL`; the page is constructible with the January source open beside it and not from the page alone; the record held on five rows. **Not independent replication**: the session worked from the operator's brief and the reviewer's own prior knowledge of the v0.1 source, and says so |
| 2026-09-20 | an AI session commissioned by the operator (adversarial review 1) | public repositories; could not execute the test suites (no GitHub access from its runtime); read the sources | hostile review of the registers, atlas, ports, PQ notes, language rule | 17 rows. Two received and corrected in the afternoon (the partial receipt): `OBL-F-0005`'s "no external anchor" against its own artifact; `docs/NOV08_GENESIS.md`'s "test fixture". The rest, received in the evening: `OBL-F-0010`'s "17/17 signatures" counts three probes with no expected verdict (**right**); `OBL-C-0011`'s witness was a script-engine artifact, not a policy one (**right**); `OBL-F-0007` "by design" attributes purpose (**right**); f1e1fb4bd quoted as "cleanup" (**right**, first line only); `OBL-C-0001`'s signed note incomplete for `172f00602` without saying so at the pointer (**right**); substring assertions in three suites and constants shared between module and test (**right**); the retarget equilibrium test built from the module's own constants (**right**); `OBL-C-0012`'s numeric cap "open" (**already closed** by `OBL-F-0034` that afternoon); `OBL-C-0014`'s grade attached to both sides of the rule (**right**); three PQ figures recomputed, all reproduced; categorical wording (`STILL TRUE`, `FALSE`) in `common/VERSION_LABEL.md` (**a verdict on a bounded claim**; the language rule is now defined in `docs/EVIDENCE_POLICY.md`); the record's central gap, that execution of one implementation does not witness network enforcement (**right, and now stated in the register**) | a reviewer with the public record and no execution can find sixteen defects of citation, grade and test construction in a day. Not independent replication |
| 2026-09-20 | an AI session commissioned by the operator (adversarial review 2, two passes) | public repositories, cloned; `bitcoin/bitcoin`, blobless clone; ran the five derivative suites (all passed); could not reach the archive host, so read no `JAN09-SOURCE` artifact | the same brief; the second pass completed the register grade audit, recomputed every PQ figure, and swept the language rule | 42 rows. **Right and corrected:** three merge shas that are GitHub test merges, not history (`9e17aac6b`, `bd03a1cb9`, `681f02551`); an 18 March 2016 commit attributed to the wrong author; `401926283`'s message truncated to one line; the duplicate-pair census (122 → 132 pairs of three types, author tally, uncompared pairs, the ten both-trailer pairs and their citation rule); the `dd519206a` hunk quoted as two adjacent lines; `scripts/revise_findings.py` named as if published; overflow's "0.3.1"; the 4,500 boundary left unconstructed; the v0.1 BDB test's name; the "strict twin" that does not exist; a re-encoding test that tests the encoder; the ConnectInputs value clause not ported; the retarget walk that was a counter; a constants test that read no source; a later Core `SetCompact` presented as v0.1's; "~1000x" and "the common phrasing"; the op-count limit dated to commits that do not carry it; `OBL-F-0009`'s binding records unpublished; `OBL-F-0003` graded `JAN09-EXECUTED` for a laboratory build; the provenance note's "two things follow"; `OBL-F-0012` and eight `DESCENDANT` rows graded for reading, not execution; `OBL-F-0007` "by design"; the settlement table computed at 1 MB only; the migration row two bytes short; the push opcode charged as one byte; 5,000 against 4,999; verify timings below the floor; two sampling regimes; "widely stated" and "51 of 51"; "nobody in between"; "cannot be backdated"; "cannot be compiled" and "a handful"; `RIGHTS.md` against `docs/EVIDENCE_POLICY.md`. **Disputed, with the reason recorded below:** `OP_PUSHDATA4` for 17,088 bytes; "no such file" for the revision script. **Verified by the reviewer and not defective:** every 2009–2010 sha, author string, revision and date it checked, the quoted diffs of §§2, 3, 5, 6, 8, the census totals, and every figure of both PQ notes | a reviewer who clones and runs finds what one who reads cannot: three shas that do not exist, a counter where a walk was claimed, a codec from the wrong decade. The method mostly holds, in the reviewer's words, which is why the failures matter. Not independent replication |
| 2026-09-20 | the same AI session, commissioned by the operator, asked for an overall review of both organisations and the three sites | cloned all five public repositories and `bitcoin/bitcoin`; ran the suites; checked every internal link and asset on the seventeen site pages; read the analytics script; checked thirteen source-line citations against the January 2009 archive now committed under `artifacts/jan09/`; recomputed both PQ notes and the full commit census | overall review | **Right and corrected:** the whitepaper site's "1,698 paragraphs" (the judgment's own numbering, read from the National Archives' copy and the appendix held locally: 945, with a 799-paragraph appendix); the footers' analytics line said less than the script sends and the script's header claimed nothing beyond a server log (the list is now published on `about.html#counted`, linked from every footer, and the header says it); the README read as if the January archives were hash-anchored to 2009 (they are checked against their custodians' digests; the custodian-free check is reproduction); "distributed everywhere" and a "v0.1.0" node label on the lab site; the census stated 132 pairs without saying the two parentless roots are counted apart; the revision record described by its instrument (the diff between kept revisions is the record, now said); the R4 binding's digest now says what it does and does not prove. **Verified by the reviewer and not defective:** thirteen source-line citations and every absence claim in the committed archive, both PQ notes' arithmetic, the whole census, all seventeen pages' links and assets. **Conceded by the reviewer:** its own OP_PUSHDATA4 claim. **Structural, recorded and not fixed here:** no uncommissioned replication; one operator and one key; named living people on two sites; a per-site language rule presented as one voice | the base now checks on sample from the repository; what remains is the single-source condition the reviewer names and this ledger labels. Not independent replication |

## What the adversarial reviews changed

- **Registers.** `OBL-F-0001`, `0003`, `0007`, `0009`, `0010`, `0012`–`0015`, `0017`–`0027`, `0031` restated or
  regraded; `OBL-F-0035` (the op-count limit, dated), `0036` (`IsStandard` as a policy, executed) and `0037` (the
  release announcements and posts read) added. `OBL-C-0001`, `0002`, `0004`, `0007`, `0009`–`0014` restated. Two new
  grades in `docs/EVIDENCE_POLICY.md`: `RECORD` (read, not observed) and `EXECUTED (laboratory build)`. Two new
  sections of `CONSTITUTION-REGISTER.md`: what the register does not establish (network enforcement; what
  `message_match` measures), and the contemporaneous discussion read so far.
- **Atlas.** Three merge shas, one author, one two-line message, one seven-line hunk, section 13 (the op-count limit),
  sections 6 and 9, the both-trailer citation rule in the method.
- **Signed notes, revised beside their seals.** `docs/SCRIPT-LIMITS-RETROFITTED.md` revision 4;
  `docs/BITCOIN-GIT-HISTORY-PROVENANCE.md` revision 2, with the pair list published
  (`docs/bitcoin-git-history-pairs.tsv`).
- **Derivatives.** Every check in `overflow/`, `emergent/`, `retarget/`, `script_limits/` returns a clause identifier
  and every test asserts the clause, with the expected constants written in the test; the ConnectInputs value clause,
  the index-chain walk, v0.1's MPI `SetCompact`, the 4,500 block, the 258 → 4 numeric stage and the verification of
  the probes' recovered (r, s) are new; `origin_policy/is_standard.py` is new.
- **Post-quantum notes.** Both rewritten: the push opcode, one coinbase, the 32 MiB table first, timings read against
  the floor, the withdrawn attributions.
- **Sealed sets.** Nothing edited. `bitcoin-findings/CORRECTIONS.md` records the R5 "17/17" line against the set's own
  14/14, and the R4 binding records are published beside their manifest.
- **The base.** The two January 2009 archives are committed under `artifacts/jan09/`, verified before use against
  the digests their custodians published (not a 2009 server's: `provenance/SOURCEFORGE_PUBLISHED_HASHES.md`), so the
  foundation of every `JAN09-SOURCE` row is reachable from the repository; its authentication to January 2009 rests on
  custody, internal evidence and reproduction, as that note says.
- **Language.** "by design", "nobody in between", "cannot be backdated", "cannot be compiled", "a handful", "every
  host", "widely stated" removed or bounded; the rule itself is now written down.

## What the overall review changed

- `bitcoin-whitepaper/docs/index.html`: the judgment's paragraph count, from its own numbering.
- All three sites' footers link to a new `about.html#counted` on bitcoin-lab.org that lists every event the analytics
  script sends; the script's header comment in all three copies now says what is sent beyond a server log.
- `README.md`, `REPRODUCTIONS.md`: the January archives are checked against their custodians' digests, not a 2009
  server's; `provenance/SOURCEFORGE_PUBLISHED_HASHES.md` is the reference.
- `docs/index.html`: "served under the name bitcoin-0.1.0.rar by the hosts that carry it"; the JAN09-X node labelled
  with the bytes it runs.
- `docs/BITCOIN-GIT-HISTORY-PROVENANCE.md` (revision 2, before signing), `OBL-F-0014`, the satoshi-onchain timeline
  event: the two parentless root objects are counted apart from the 132 pairs.
- `docs/EVIDENCE_POLICY.md`: the diff between kept revisions is the auditable edit record; the jurisdiction rule is
  scoped to the laboratory's own statements.
- Both registers: how to cite a row's state (ID plus commit or date).
- `r4-findings/…/PUBLISHED-2026-09-20.md`: what the `fbcac071…` binding proves and what rests on custody.
- The rows that name a witness of the judgment: they stay, stated as the judgment states them. The paragraph the
  pages cite records that he died shortly before the trial began; every mention now says so, from that paragraph,
  the transfer finding is given by paragraph from his evidence, and the transactions stay unidentified.
- Not changed, for the operator: an uncommissioned reproduction (outreach); continuity if the operator stops; a versioned register beyond the git history (a DOI per revision is
  an open question of the direction document).

## Disputed

- **`OP_PUSHDATA4` for a 17,088-byte push.** `OP_PUSHDATA2` carries a two-byte length, up to 65,535 bytes; 17,088 fits
  it. The correction the review asked for (charge the push opcode by length) was right; that detail of it was not.
- **"No such file" for `scripts/revise_findings.py`.** The file exists in the laboratory's workspace and is excluded
  from the repository on purpose: its edit tables quote the strings the revisions removed. The policy text that named it
  as if published was the defect, and is corrected.
- **`OBL-C-0012` "open".** Closed by `OBL-F-0034` a few hours before the review was received; the review read the
  earlier text.
- **A census of 133 pairs.** The two root objects are parentless and so outside the 341 non-merge commits the count
  is drawn from; including them gives 133, excluding them 132. The count stands at 132 and now says the root pair
  is counted apart, which the note had shown but not said. The reviewer's own reading of the OP_PUSHDATA4 dispute,
  conceded in its overall review, is recorded in `REVIEW-overall-1.md`.

## The files

`reproductions/2026-09-20-clean-room-ai-sessions/` holds the two clean-room reports as received
(`REPORT-run1.md`, `REPORT-run2.md`), the two adversarial reviews (`REVIEW-adversarial-1.md`,
`REVIEW-adversarial-2.md`; the truncated first receipt of review 1 is kept as `REVIEW-adversarial-partial.md`) and
the overall review (`REVIEW-overall-1.md`),
with the validators the clean-room sessions wrote (`run1-cleanroom_jan09b_validator.py`; `run2/jan09b.py`,
`run_corpus.py`, `selftest.py`) and the pair census the reviews prompted (`docs/bitcoin-git-history-pairs.tsv`),
digests in `SHA256SUMS`. The review files carry each session's findings tables and its closing objections as
received and unedited, since those are the record my summary rows above are audited against; each session's
method-and-scope preamble, and review 2's paragraph enumerating what it verified as already correct, are held in
the laboratory's workspace and not reproduced here. They are third-party text and code, kept as evidence of the
attempt; nothing in this repository imports them.
