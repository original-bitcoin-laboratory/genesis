# Constitution register

One row per consensus rule that Bitcoin acquired after the January 2009 release, or that the release
carried: where it came from, what the record says for it, and what has been executed. The series is
`OBL-C-nnnn`; the findings series `OBL-F-nnnn` (`FINDINGS-REGISTER.md`) is for claims, and a rule's
row cites the findings its witness rests on. Started 19 September 2026 from the rows already dated;
`scripts/check_register.py` counts the rows against `common/conformance/CONSENSUS_SURFACE.md` and
prints the `message_match` tally with that denominator, by rule and by origin commit. Rows are corrected in
place with dated notes; to cite a row's state, name its ID with the register's commit or the date, the git
history being the version record.

Experimental laboratory research, in progress. Not money, not advice, no warranty (`RIGHTS.md`).

## Fields

- **rule** — the constant or check, as named in the source.
- **kind** — `consensus` (a block or transaction is invalid without it), `anti-DoS` (a resource ceiling
  inside consensus), `policy` (node-local, not consensus), `emergent` (a rule nobody wrote: library
  behaviour that was consensus before anyone knew).
- **origin commits** — every commit that introduced or enforced the rule, on the `s_nakamoto` lineage,
  each as `sha:date:match`, where `match` is `true` when the commit message describes the change and
  `false` when it does not. The message is quoted verbatim in the note the row cites; it is not
  interpreted.
- **message_match** — the rule-level value: `true` only when every origin commit's message describes it.
- **argument** — `cited` (the record names the failure or reason the rule answers), `not-in-record` (the
  magnitude or the rule is not argued for in the commits that introduced it; an argument may exist
  elsewhere), `inherited` (carried from the origin release), `accidental` (emergent).
- **failure cited** — the incident the record names, or `none`.
- **witness** — the executed artifact, by finding ID, or `open` with what it would add.
- **grade** — the evidence grade of the row's strongest artifact (`docs/EVIDENCE_POLICY.md`). A grade attests
  the object named (a source read, a binary or build executed, a port run); no grade attests what the 2009 network
  enforced (see "What the register does not establish").
- **lineage_note** — where `bitcoin/bitcoin`'s duplicated 2010 lineages carry another copy of an origin
  commit: its sha, date and author string. Dates in this register come from the `s_nakamoto` lineage: the copy
  with the `git-svn-id` trailer, and, for SVN r148–r157 where both copies carry it, the copy on the chain the
  r158 trailer commit descends from (`docs/BITCOIN-GIT-HISTORY-PROVENANCE.md`, revision 2).

Cite; do not characterise: the rows record what the messages say against what the diffs do, and what the
record argues. They do not say why.

| ID | rule | kind | origin commits (`sha:date:match`) | message_match | argument | failure cited | witness | grade | lineage_note |
|---|---|---|---|---|---|---|---|---|---|
| `OBL-C-0001` | `MAX_BLOCK_SIZE = 1000000` | consensus | `a30b56ebe:2010-07-15:false` (constant; miner-only), `f1e1fb4bd:2010-09-07:false` (validity rule in `AcceptBlock`, heights above 79,400; message "cleanup, / catch some recoverable exceptions and continue"), `172f00602:2010-09-19:false` (the test moved into `CheckBlock` unconditionally, replacing the 32 MiB `MAX_SIZE` test; message "only accept transactions sent by IP address if -allowreceivebyip is specified") | `false` | not-in-record | none | `OBL-F-0016` for the origin side (v0.1 `CheckBlock` rejects over 32 MiB, read); `open`: a block in the 1 MB–32 MiB band submitted to the 2009 binary and to 0.3.13 would show the narrowing executed (*corrected 25 Sep 2026: this read 0.3.12, whose copy of the test is still gated at height 79,400 and which therefore accepts such a block on a low-height isolated chain; it is `172f00602`, ungating it, that makes 0.3.13 reject*) | `RECORD` + `JAN09-SOURCE` | `a30b56ebe` has no second copy in the window; `f1e1fb4bd` is duplicated as `8c9479c6b` and `172f00602` as `6aeb45187`, each same date, author string and SVN trailer (the r148–r157 run, where both copies carry the trailer: the cited copy is the one on the chain the r158 trailer commit `a790fa46f` descends from; `8c9479c6b`'s message adds a third line, "-- version 0.3.12 release"). Note: `docs/MAX-BLOCK-SIZE-RETROFITTED.md` (*corrected 25 Sep 2026: this said the note was signed on 19 September and did not record `172f00602`. Revision 1 was signed and does not record it; revision 2, which supersedes it, records the commit in its title and throughout, and is unsigned at the time of writing*) |
| `OBL-C-0002` | script resource caps: pushed element (5000 → 520 bytes), script size (20000 → 10000), stack depth (1000), numeric operand (258 → 4), op count (200, then 201 with pushes and `OP_1`–`OP_16` excluded) | anti-DoS | `757f0769d:2010-07-29:false` (installs the element, script-size, stack and numeric caps; message names `makefile.unix`), `6ff5f718b:2010-07-31:true` (op count as `nOpCount++ > 200`, script size 10000; "fixed segfault in bignum.h, / additional security limits, / refactoring / -- version 0.3.7"), `4bd188c43:2010-08-15:false` (tightens element and numeric caps, "misc changes") | `false` | not-in-record | none | `OBL-F-0003`: a 600-byte element and a 1500-deep stack run on the laboratory's build of the archive's `script.cpp` (`EXECUTED (laboratory build)`); `OBL-F-0034`: a 9-byte numeric operand accepted by v0.1, by the July cap, and rejected by the August cap (`MODEL`); `OBL-F-0035`: 201 counted opcodes pass and 202 fail on the ported rule (`MODEL`) | `EXECUTED (laboratory build)` + `MODEL` | `757f0769d` is duplicated as `a75560d82`, 2010-07-30, author string `--author=Satoshi Nakamoto`; `6ff5f718b` has no second copy within nine days; `4bd188c43` as `6ac7f9f14`, 2010-08-15, `Satoshi Nakamoto`. Note: `docs/SCRIPT-LIMITS-RETROFITTED.md` (revision 4), which leaves the op-count limit undated; atlas §13 dates it |
| `OBL-C-0003` | output value bounds in `CheckTransaction`: each output at most 21,000,000 × COIN and the running sum likewise (the check is named `MoneyRange` four days later, in `05454818d`, 2010-08-19; `d4c6b90ca` writes the bounds inline) | consensus | `d4c6b90ca:2010-08-15:true` ("fix for block 74638 overflow output transaction") | `true` | cited | block 74638, 15 Aug 2010: 184,467,440,737 BTC in two outputs | `OBL-F-0004`: v0.1 accepts the block-74638 amounts, the 0.3.10 rule rejects them (`MODEL`) | `MODEL` | `d4c6b90ca` is duplicated as `76793dc96`, 2010-08-15, `Satoshi Nakamoto`; the scanback guard `85de7d7c0` (same day) has no second copy. Note: `derivatives/overflow/README.md` |
| `OBL-C-0004` | `MAX_BLOCK_SIGOPS = MAX_BLOCK_SIZE/50`, counted by `GetSigOpCount` (`f1e1fb4bd`): one per `OP_CHECKSIG`/`OP_CHECKSIGVERIFY`, twenty per `OP_CHECKMULTISIG`/`OP_CHECKMULTISIGVERIFY` | anti-DoS | `f1e1fb4bd:2010-09-07:false`, `172f00602:2010-09-19:false` (height gate removed, same commit as the block-size move) | `false` | not-in-record | none | `open`: no artifact exercises the sigop count against the 2009 binary | `RECORD` | as `OBL-C-0001`'s second and third commits (`8c9479c6b`, `6aeb45187`). Note: `docs/MAX-BLOCK-SIZE-RETROFITTED.md` |
| `OBL-C-0005` | disabled opcodes: `OP_CAT`, `OP_SUBSTR`, `OP_LEFT`, `OP_RIGHT`, `OP_INVERT`, `OP_AND`, `OP_OR`, `OP_XOR`, `OP_2MUL`, `OP_2DIV`, `OP_MUL`, `OP_DIV`, `OP_MOD`, `OP_LSHIFT`, `OP_RSHIFT` | consensus | `4bd188c43:2010-08-15:false` ("misc changes"; a pre-switch guard that fails the script) | `false` | not-in-record | none | `OBL-F-0010`: the 2009 vocabulary executes on the release client, 136/136 script vectors (`EXECUTED (release build)`); BIP 347 documents the disabling | `EXECUTED (release build)` + `JAN09-SOURCE` | `4bd188c43` is duplicated as `6ac7f9f14`, 2010-08-15, `Satoshi Nakamoto`. BIP 347 dates this commit "Aug 25 2010"; the commit's own fields say 2010-08-15 (recorded in `docs/SCRIPT-LIMITS-RETROFITTED.md`) |
| `OBL-C-0006` | `MAX_SIZE = 0x02000000` (32 MiB): block serialised size and transaction count, `CheckBlock` | consensus | none: the January 2009 release, `main.h:17`; the `CheckBlock` test was replaced by the 1 MB test in `172f00602` (2010-09-19), after which the constant bounds only network messages and block files | — | inherited | none | `OBL-F-0016`: v0.1 `CheckBlock` rejects over 32 MiB, read from source | `JAN09-SOURCE` | not a commit; the release. `docs/CONSENSUS-ATLAS.md` §1 |
| `OBL-C-0007` | time-based `nLockTime`: values below 500,000,000 are heights, at or above are Unix times | consensus | `dd519206a:2009-10-29:true` ("addr relaying fixes, proxy option and privacy patches, detect connect to self, non-final tx locktime changes, fix hide unconfirmed generated") | `true` | not-in-record for the threshold's magnitude; the diff's comment states a reason for deferring the time-based form ("do not use time based until most 0.1.5 nodes have upgraded") | none | `OBL-F-0002`: v0.1 compares heights only; the temporal port runs that rule | `JAN09-SOURCE` + `MODEL` | `cc0b4c3b6`, same timestamp, `s_nakamoto`, no trailer. The first commit (0.1.5) is height-only; `aa496b75c` (2011-07-09) names the constant `LOCKTIME_THRESHOLD`. Atlas §2 |
| `OBL-C-0008` | best chain by cumulative work (`bnChainWork`), not height | consensus | `3b7cd5d89:2010-07-25:false` (three lines on the trailer lineage, joined here with " / ": "Gavin Andresen's JSON-RPC HTTP authentication, / faster initial block download / -- version 0.3.3") | `false` | not-in-record | none | `OBL-F-0001`: v0.1 follows height 125 with work 250 over height 122 with work 262 | `MODEL` | `40cd03694`, 2010-07-26, `Satoshi Nakamoto`, no trailer, +93/−25 against +405/−137: one of the eight differing pairs; the selection change is in both. Atlas §3 |
| `OBL-C-0009` | alert system: a network message verified by one hard-coded key, with safe mode | policy | `401926283:2010-08-25:true` ("alert system / -- version 0.3.11"); removed by PR 7692 (merge commit `29b2be6ad`, 2016-03-21, Core 0.13.0) | `true` | not-in-record in the commit; the 0.3.11 announcement states the reasons (mirror post 429, in the discussion table below) | none | none applies: not a validity rule | `RECORD` | `522dfe342`, 2010-08-28, `Satoshi Nakamoto`, no trailer. Final alert 2017-01-19; key published 2018-07-03 (bitcoin.org alert page). Atlas §4 |
| `OBL-C-0010` | transaction size: 32 MiB per transaction, then 1 MB (`CheckTransaction`) | consensus | `401926283:2010-08-25:false` (32 MiB, "alert system / -- version 0.3.11"), `3df62878c:2010-09-13:false` (1 MB, "reorganize BitcoinMiner to make it easier to add different SHA256 routines") | `false` | not-in-record | none | `open`: a transaction between 1 MB and 32 MiB submitted to the January client and to a build carrying `3df62878c` | `RECORD` | `a790fa46f` (2010-09-30), which this register cited on 19 September as the origin, moves the function unchanged: corrected 20 September. `3df62878c` has a same-timestamp copy `71cc095cb` that also carries the trailer (cited as `OBL-C-0001`'s lineage note explains). Atlas §5 |
| `OBL-C-0011` | `IsStandard`: relay and mine only template scripts | policy | `a206a2398:2010-12-07:true` ("IsStandard() check for CScripts: only relay/include in blocks CScripts we can understand.") | `true` | cited | none | `OBL-F-0036`: the January memory-pool path relays a hash-lock transaction that the `a206a2398` clause refuses as nonstandard, and `CheckTransaction` accepts it in both eras (`derivatives/origin_policy/is_standard.py`, `MODEL`). `OBL-F-0010`, cited here until 20 September 2026, shows the script engine executing non-template scripts on the release build: the consensus side, not this policy | `MODEL` | no second copy within nine days; `97ee01ad8` (2010-12-12) adds a second call. Atlas §6 |
| `OBL-C-0012` | `CScriptNum` replaces `CBigNum` in script arithmetic; the four-byte operand cap (`OBL-C-0002`) unchanged | consensus | `48d8eb184:2014-03-26:true`, `05e3ecffa:2014-03-26:true` (PR 3965 "Remove bignum dependency for scripts", merged 2014-05-09 as `1c0319bb2`) | `true` | cited | none | `OBL-F-0034` for the 2010 cap: a 9-byte operand accepted by v0.1's unbounded `CBigNum` and rejected by the 4-byte cap, operands not results (`derivatives/script_limits/test_numeric_cap.py`, `MODEL`); the 2014 representation change carries its own tests | `RECORD` + `MODEL` | post-2010, no duplicated lineage. Atlas §7 |
| `OBL-C-0013` | Berkeley DB lock table as block validity, with no commit that wrote it; the written response limits a block to 4,500 distinct transaction ids between 11 Mar and 15 May 2013 | emergent | `8bd028818:2013-03-15:true` ("CheckBlock rule until 15-May for 10,000 BDB lock compatibility"), `fc6deb521:2013-03-15:true` ("Before 15 May, limit created block size to 500K") | `true` (the written rule) | accidental | block 225,430, 11 Mar 2013 (BIP 50; bitcoin.org alert "11/12 March 2013 Chain Fork Information") | `OBL-F-0025`: a block referencing 4,501 distinct transaction ids passes v0.1's size and count clauses and fails the 0.8.1 clause inside its window, one referencing 4,500 passes both, and the 4,501 block passes after 15 May 2013 (`MODEL`) | `RECORD` + `MODEL` | post-2010. Atlas §8; `derivatives/emergent/` |
| `OBL-C-0014` | OpenSSL's DER parser as signature validity, with no commit that wrote it; the written rule is BIP 66 strict DER | emergent | `80ad135a5:2015-01-13:true` ("Change IsDERSignature to BIP66 implementation"), `5a47811da:2015-01-19:true` ("BIP66 changeover logic"; PR 5713, merged 2015-02-03 as `41e6e4cab`, enforced from 2015-07-04) | `true` (the written rule) | accidental | OpenSSL 1.0.0p and 1.0.1k rejecting encodings earlier releases accepted (BIP 66) | `OBL-F-0025`: BIP 66's function, ported, passes the corpus's 7 strict signatures and fails its 3 probes, each recovered by a tolerant reader to an (r, s) that verifies under the vector's key (`MODEL`); `OBL-F-0010`: the release build's OpenSSL 1.0.2u rejects the 3 (the rejection side, `EXECUTED (release build)`); `open`: the acceptance side, that 0.9.8 on the 2009 binary accepts them, has no artifact at any grade | `EXECUTED (release build)` + `MODEL` (rejection side only; nothing on the acceptance side) | post-2010. Atlas §9; `derivatives/emergent/` |
| `OBL-C-0015` | transaction replacement by sequence number: a newer version of a held transaction (same inputs, higher `nSequence`) replaces it in the memory pool; shipped in the release, disabled 19 Aug 2010 | policy | shipped: the January 2009 release (`main.h:408`, `main.cpp:428`); disabled: `05454818d:2010-08-19:false` ("block index checking on load, extra redundant checks, misc refactoring") | `false` | not-in-record | none | `OBL-F-0028`: v0.1 accepts the newer version and erases the old; 0.3.11 refuses every conflict (`MODEL`) | `JAN09-SOURCE` + `MODEL` | `7a37c906a`, 2010-08-28, `Satoshi Nakamoto`, no trailer. `derivatives/origin_policy/replacement.py`; Atlas §10 |
| `OBL-C-0016` | hard-coded checkpoints: a block at a named height must carry the named hash | consensus | `ae922a36a:2010-07-17:true` ("security safeguards, limited addr messages -- version 0.3.2": heights 11111, 33333, 68555); `813505cc1:2010-07-27:false` (70567; message about Crypto++ SHA-256 speed); `4bd188c43:2010-08-15:false` (74000; "misc changes") | `false` | not-in-record | none named in the commits; the author's post 370 of 15 Aug 2010 calls the 74000 checkpoint "the most recent security lockin" during the overflow incident | `OBL-F-0029`: v0.1 accepts a block at height 11111 with another hash; the 0.3.2 rule rejects it (`MODEL`) | `JAN09-SOURCE` + `MODEL` | `ae922a36a` is duplicated as `4110f33cd`, 2010-07-19, `Gavin Andresen`, no trailer. `derivatives/origin_policy/checkpoints.py`; Atlas §11 |
| `OBL-C-0017` | the fee rule: one cent per started kilobyte, free under 10 KB with the discount, applied when building and sending; from 12 Dec 2010 relay refuses a transaction below `GetMinFee(1000)` and free transactions are rate-limited to 150,000 bytes per ten minutes | policy | shipped: the January 2009 release (`main.h:504`, `main.cpp:2250`, `main.cpp:2577`); relay gate: `97ee01ad8:2010-12-12:true` ("added some DoS limits, removed safe mode") | `true` | cited (the December message names the class of change) | none | `OBL-F-0030`: v0.1 relays anything; 0.3.19 refuses a 26,500 B fee-less transaction and the 602nd free 250 B transaction in a window (`MODEL`) | `JAN09-SOURCE` + `MODEL` | post-2010 lineage not duplicated. `derivatives/origin_policy/fees.py`; Atlas §12 |

## Where a designed successor fits — decided 20 September 2026, corrected the same day

The constitution is the specification; `JAN09-B` (`docs/JAN09-B-SPECIFICATION.md`) is its expression
on paper: the January 2009 design with the rules whose argument is in the record installed, the
not-in-record ones chosen deliberately and marked, and no consensus-critical third-party library. It
is not mined, and it has no implementer. An implementation of it, if one is wanted, is a fresh
decision, and the order that would make it evidence is: an executed `JAN09-B`, by an implementer
working from the page, before any variant of it.

**Correction, 20 September 2026.** The first version of this section, published earlier the same
day, said that the laboratory's post-quantum instrument "is the implementation that takes those
bounds when its genesis is defined, adding the one delta the constitution does not contain, the
signature scheme." That was wrong, and it is withdrawn. That instrument's charter, signed and
anchored before this register existed, confines its change to the signature scheme and forbids every
rule `JAN09-B` installs, so that the cost it measures is the signature change alone against the
executed January 2009 base. The two documents answer different questions and neither implements
the other. The earlier wording is kept in this repository's history and is not rewritten here.

## What is still open

Every rule on the target list has a row, and three policies of the origin were added on 20 September 2026 (`OBL-C-0015` to `0017`). Four witness cells say `open`, and all four need the unmodified 2009 binary: the 1 MB narrowing
(`OBL-C-0001`), the sigop count (`OBL-C-0004`), the transaction-size rule (`OBL-C-0010`), and the
acceptance side of the DER rule (`OBL-C-0014`). The numeric-operand cap (`OBL-C-0002`, `OBL-C-0012`) was
executed on 20 September 2026 after a clean-room reproduction pointed out it had no case (`OBL-F-0034`); the
op-count limit was dated and executed the same day after an adversarial review found it attributed to commits that
do not carry it (`OBL-F-0035`); the `IsStandard` row's witness was replaced the same day with a port of the policy
itself (`OBL-F-0036`), the earlier witness having spoken to the script engine. Rules that entered after
2015 are not on the list.

## What the register does not establish

- **What the 2009 network enforced.** A witness shows what a named object does: the January 2009 source, read;
  the archive's binary, the laboratory's release client or its build of the archive's `script.cpp`, executed; a port,
  run. Two nodes running one binary are one implementation, and a later commit shows what later code did. The
  register carries no contemporaneous witness of enforcement by nodes this laboratory did not run, and claims none.
  What would supply one lies outside this record: the 2009–2010 block data examined at a rule's boundary, or a second
  implementation of the period.
- **Why any rule entered.** `message_match` is a property of the commit record, whether a message's text describes
  its diff, and the 2010 commits are release-batched: `757f0769d`, `3b7cd5d89` and `4bd188c43` each carry a
  release's work under one message. A batched practice scores `false` where an atomic one scores `true`, with no
  difference in how deliberate a rule was, so the tally says nothing about deliberateness and this register infers
  nothing from it; six `false` of thirteen is consistent with the batching alone. The record adjacent to the commits,
  the author's announcements and forum posts, is entered below where it has been read; it has not been read for
  every rule, and the table says which.

## Contemporaneous discussion, where read

Read on 20 September 2026 from the Satoshi Nakamoto Institute's mirror of the bitcointalk posts (`mirror post N`,
the convention the atlas uses). Quoted, not characterised; a row absent from this table has not been read.

| source | rule | what it says |
|---|---|---|
| mirror post 440, 7 Sep 2010, "Version 0.3.12" |  `OBL-C-0001` | lists four features (JSON-RPC error objects, exit codes, `backupwallet`, recovering from exceptions) and not the block-validity rule `f1e1fb4bd` carries; `OBL-F-0037`  |
| mirror posts 478 and 485, 3–4 Oct 2010, "[PATCH] increase block size limit" |  `OBL-C-0001` | "+1 theymos. Don't use this patch, it'll make you incompatible with the network, to your own detriment. We can phase in a change later if we get closer to needing it." and "It can be phased in, like: if (blocknumber > 115000) maxblocksize = largerlimit It can start being in versions way ahead, so by the time it reaches that block number and goes into effect, the older versions that don't have it are already obsolete." A method for changing the number; no argument for the number  |
| mirror posts 368–383 and 399, 15–19 Aug 2010 |  `OBL-C-0003`, `OBL-C-0016` | `docs/INCIDENT-2010-08-15.md`  |
| mirror post 429, 27 Aug 2010, "Version 0.3.11 with upgrade alerts" |  `OBL-C-0009` | "The alert system can display notifications on the status bar to alert you if you're running a version that needs to be upgraded for an important security update." and "This is an important safety improvement. For a large segment of possible problems, this can warn everyone immediately once a problem is discovered and prevent them from acting on bad information."  |
| mirror post 442, 8 Sep 2010 |  `OBL-C-0011` | "Bitcoin clients currently only create and recognize transactions that match two possible templates. Those are some quick tests that loosely check if transactions fit some general metrics that those standard transactions fit. Nodes will only work on adding those transactions to their block." Three months before `a206a2398`  |
| mirror post 543, 12 Dec 2010, "Added some DoS limits, removed safe mode (0.3.19)" |  `OBL-C-0017` | "As Gavin and I have said clearly before, the software is not at all resistant to DoS attack. This is one improvement, but there are still more ways to attack than I can count. I'm leaving the -limitfreerelay part as a switch for now and it's there if you need it."  |
| not read |  `OBL-C-0002`, `0004`, `0005`, `0007`, `0008`, `0010`, `0012`–`0015` | —  |

**Corrections, 20 September 2026, from two clean-room reproductions.** `OBL-C-0003` had named the rule `MoneyRange`; that identifier enters four days after the origin commit, so the row now names the bounds as `d4c6b90ca` writes them. `OBL-C-0008` had quoted a three-line message as one line, the form of the duplicate lineage's copy; the row now marks the line breaks. `OBL-C-0004` now states the counting method. The reproductions are recorded in `REPRODUCTIONS.md`.

**Corrections.** 20 September, later the same day: a third commit added to `OBL-C-0001` and a second to `OBL-C-0004`. `172f00602` (19 September 2010, message about `-allowreceivebyip`) moved the 1 MB test into `CheckBlock` in place of the 32 MiB `MAX_SIZE` test and removed the 79,400 height gate from both rules, twelve days after the gated rule entered. `docs/MAX-BLOCK-SIZE-RETROFITTED.md` (signed 19 September) does not mention this commit; it is recorded here and in the atlas rather than by editing the signed note.

**Corrections, 20 September 2026, from two adversarial reviews.** Three merge commits were cited by the sha GitHub's pull-request record reports (`9e17aac6b`, `bd03a1cb9`, `681f02551`); those objects are test merges GitHub computes and are not on the repository's history. The merge commits on `master` are `29b2be6ad` (PR 7692), `41e6e4cab` (PR 5713) and `1c0319bb2` (PR 3965). `401926283`'s message had been quoted as its first line only; it is two lines. `OBL-C-0002` lacked the op-count limit's commit (`6ff5f718b`, 31 July 2010) and dated the script-size cap's final value to the wrong commit. `OBL-C-0011`'s witness was a script-engine artifact, replaced by a port of the policy. `OBL-C-0014`'s grade now says which side of the rule it covers. `OBL-C-0007`'s argument cell records the reason the diff's comment gives. The grade `DESCENDANT` (behaviour observed in a later implementation) had been applied to rows that read commits, merge dates and web pages; those rows now carry `RECORD`, defined in `docs/EVIDENCE_POLICY.md` the same day. The lineage rule for the ten both-trailer pairs, which the first text of `docs/BITCOIN-GIT-HISTORY-PROVENANCE.md` did not state, is stated in that note's revision 2 and in the field definitions above. The reviews are recorded in `REPRODUCTIONS.md` and `reproductions/`.

**Corrections.** 19 September's text named `a790fa46f` (30 September 2010) as the transaction-size
rule's origin; that commit moves `CheckTransaction` without changing it. The origin is `401926283`
(25 August 2010, 32 MiB) and `3df62878c` (13 September 2010, 1 MB); recorded in `OBL-C-0010` and in
`docs/CONSENSUS-ATLAS.md` §5 on 20 September 2026.
