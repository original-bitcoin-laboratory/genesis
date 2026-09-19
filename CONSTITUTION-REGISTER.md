# Constitution register

One row per consensus rule that Bitcoin acquired after the January 2009 release, or that the release
carried: where it came from, what the record says for it, and what has been executed. The series is
`OBL-C-nnnn`; the findings series `OBL-F-nnnn` (`FINDINGS-REGISTER.md`) is for claims, and a rule's
row cites the findings its witness rests on. Started 19 September 2026 from the rows already dated;
`scripts/check_register.py` counts the rows against `common/conformance/CONSENSUS_SURFACE.md` and
prints the `message_match` tally with that denominator, by rule and by origin commit.

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
- **grade** — the evidence grade of the row's strongest artifact (`docs/EVIDENCE_POLICY.md`).
- **lineage_note** — where `bitcoin/bitcoin`'s duplicated 2010 lineages carry another copy of an origin
  commit: its sha, date and author string. Dates in this register come from the `s_nakamoto` lineage.

Cite; do not characterise: the rows record what the messages say against what the diffs do, and what the
record argues. They do not say why.

| ID | rule | kind | origin commits (`sha:date:match`) | message_match | argument | failure cited | witness | grade | lineage_note |
|---|---|---|---|---|---|---|---|---|---|
| `OBL-C-0001` | `MAX_BLOCK_SIZE = 1000000` | consensus | `a30b56ebe:2010-07-15:false` (constant; miner-only), `f1e1fb4bd:2010-09-07:false` (validity rule in `AcceptBlock`, heights above 79,400), `172f00602:2010-09-19:false` (the test moved into `CheckBlock` unconditionally, replacing the 32 MiB `MAX_SIZE` test; message "only accept transactions sent by IP address if -allowreceivebyip is specified") | `false` | not-in-record | none | `OBL-F-0016` for the origin side (v0.1 `CheckBlock` rejects over 32 MiB, read); `open`: a block in the 1 MB–32 MiB band submitted to the 2009 binary and to 0.3.12 would show the narrowing executed | `DESCENDANT` + `JAN09-SOURCE` | `a30b56ebe` has no second copy in the window; `f1e1fb4bd` is duplicated as `8c9479c6b`, same date, author string and SVN trailer. Note: `docs/MAX-BLOCK-SIZE-RETROFITTED.md` |
| `OBL-C-0002` | script resource caps: pushed element (5000 → 520 bytes), script size (20000), stack depth (1000), numeric operand (258 → 4) | anti-DoS | `757f0769d:2010-07-29:false` (installs all four, message names `makefile.unix`), `4bd188c43:2010-08-15:false` (tightens element and numeric caps, "misc changes") | `false` | not-in-record | none | `OBL-F-0003`: the January 2009 interpreter runs a 600-byte element and a 1500-deep stack (`JAN09-EXECUTED`) | `JAN09-EXECUTED` | `757f0769d` is duplicated as `a75560d82`, 2010-07-30, author string `--author=Satoshi Nakamoto`; `4bd188c43` as `6ac7f9f14`, 2010-08-15, `Satoshi Nakamoto`. Note: `docs/SCRIPT-LIMITS-RETROFITTED.md` |
| `OBL-C-0003` | `MoneyRange` and the output-sum overflow check in `CheckTransaction` | consensus | `d4c6b90ca:2010-08-15:true` ("fix for block 74638 overflow output transaction") | `true` | cited | block 74638, 15 Aug 2010: 184,467,440,737 BTC in two outputs | `OBL-F-0004`: v0.1 accepts the block-74638 amounts, the 0.3.10 rule rejects them (`MODEL`) | `MODEL` | `d4c6b90ca` is duplicated as `76793dc96`, 2010-08-15, `Satoshi Nakamoto`; the scanback guard `85de7d7c0` (same day) has no second copy. Note: `derivatives/overflow/README.md` |
| `OBL-C-0004` | `MAX_BLOCK_SIGOPS = MAX_BLOCK_SIZE/50` | anti-DoS | `f1e1fb4bd:2010-09-07:false`, `172f00602:2010-09-19:false` (height gate removed, same commit as the block-size move) | `false` | not-in-record | none | `open`: no artifact exercises the sigop count against the 2009 binary | `DESCENDANT` | as `OBL-C-0001`'s second commit. Note: `docs/MAX-BLOCK-SIZE-RETROFITTED.md` |
| `OBL-C-0005` | disabled opcodes: `OP_CAT`, `OP_SUBSTR`, `OP_LEFT`, `OP_RIGHT`, `OP_INVERT`, `OP_AND`, `OP_OR`, `OP_XOR`, `OP_2MUL`, `OP_2DIV`, `OP_MUL`, `OP_DIV`, `OP_MOD`, `OP_LSHIFT`, `OP_RSHIFT` | consensus | `4bd188c43:2010-08-15:false` ("misc changes"; a pre-switch guard that fails the script) | `false` | not-in-record | none | `OBL-F-0010`: the 2009 vocabulary executes on the release client, 136/136 script vectors (`EXECUTED (release build)`); BIP 347 documents the disabling | `EXECUTED (release build)` + `JAN09-SOURCE` | `4bd188c43` is duplicated as `6ac7f9f14`, 2010-08-15, `Satoshi Nakamoto`. BIP 347 dates this commit "Aug 25 2010"; the commit's own fields say 2010-08-15 (recorded in `docs/SCRIPT-LIMITS-RETROFITTED.md`) |
| `OBL-C-0006` | `MAX_SIZE = 0x02000000` (32 MiB): block serialised size and transaction count, `CheckBlock` | consensus | none: the January 2009 release, `main.h:17`; the `CheckBlock` test was replaced by the 1 MB test in `172f00602` (2010-09-19), after which the constant bounds only network messages and block files | — | inherited | none | `OBL-F-0016`: v0.1 `CheckBlock` rejects over 32 MiB, read from source | `JAN09-SOURCE` | not a commit; the release. `docs/CONSENSUS-ATLAS.md` §1 |
| `OBL-C-0007` | time-based `nLockTime`: values below 500,000,000 are heights, at or above are Unix times | consensus | `dd519206a:2009-10-29:true` ("addr relaying fixes, proxy option and privacy patches, detect connect to self, non-final tx locktime changes, fix hide unconfirmed generated") | `true` | not-in-record (the threshold's magnitude) | none | `OBL-F-0002`: v0.1 compares heights only; the temporal port runs that rule | `JAN09-SOURCE` + `MODEL` | `cc0b4c3b6`, same timestamp, `s_nakamoto`, no trailer. The first commit (0.1.5) is height-only; `aa496b75c` (2011-07-09) names the constant `LOCKTIME_THRESHOLD`. Atlas §2 |
| `OBL-C-0008` | best chain by cumulative work (`bnChainWork`), not height | consensus | `3b7cd5d89:2010-07-25:false` ("Gavin Andresen's JSON-RPC HTTP authentication, faster initial block download -- version 0.3.3") | `false` | not-in-record | none | `OBL-F-0001`: v0.1 follows height 125 with work 250 over height 122 with work 262 | `MODEL` | `40cd03694`, 2010-07-26, `Satoshi Nakamoto`, no trailer, +93/−25 against +405/−137: one of the eight differing pairs; the selection change is in both. Atlas §3 |
| `OBL-C-0009` | alert system: a network message verified by one hard-coded key, with safe mode | policy | `401926283:2010-08-25:true` ("alert system"); removed by PR 7692 (`9e17aac6b`, 2016-03-21, Core 0.13.0) | `true` | not-in-record | none | none applies: not a validity rule | `DESCENDANT` | `522dfe342`, 2010-08-28, `Satoshi Nakamoto`, no trailer. Final alert 2017-01-19; key published 2018-07-03 (bitcoin.org alert page). Atlas §4 |
| `OBL-C-0010` | transaction size: 32 MiB per transaction, then 1 MB (`CheckTransaction`) | consensus | `401926283:2010-08-25:false` (32 MiB, "alert system"), `3df62878c:2010-09-13:false` (1 MB, "reorganize BitcoinMiner to make it easier to add different SHA256 routines") | `false` | not-in-record | none | `open`: a transaction between 1 MB and 32 MiB submitted to the January client and to a build carrying `3df62878c` | `DESCENDANT` | `a790fa46f` (2010-09-30), which this register cited on 19 September as the origin, moves the function unchanged: corrected 20 September. `3df62878c` has a same-timestamp copy `71cc095cb` that also carries the trailer. Atlas §5 |
| `OBL-C-0011` | `IsStandard`: relay and mine only template scripts | policy | `a206a2398:2010-12-07:true` ("IsStandard() check for CScripts: only relay/include in blocks CScripts we can understand.") | `true` | cited | none | `OBL-F-0010`: the release build executes 136/136 script vectors over the wire, among them non-template constructions | `EXECUTED (release build)` | no second copy within nine days; `97ee01ad8` (2010-12-12) adds a second call. Atlas §6 |
| `OBL-C-0012` | `CScriptNum` replaces `CBigNum` in script arithmetic; the four-byte operand cap (`OBL-C-0002`) unchanged | consensus | `48d8eb184:2014-03-26:true`, `05e3ecffa:2014-03-26:true` (PR 3965 "Remove bignum dependency for scripts", merged 2014-05-09) | `true` | cited | none | `open` for the numeric cap: `derivatives/script_limits/` has no numeric-operand case; the representation change carries its own tests | `DESCENDANT` + `JAN09-SOURCE` | post-2010, no duplicated lineage. Atlas §7 |
| `OBL-C-0013` | Berkeley DB lock table as block validity, with no commit that wrote it; the written response limits a block to 4,500 distinct transaction ids between 11 Mar and 15 May 2013 | emergent | `8bd028818:2013-03-15:true` ("CheckBlock rule until 15-May for 10,000 BDB lock compatibility"), `fc6deb521:2013-03-15:true` ("Before 15 May, limit created block size to 500K") | `true` (the written rule) | accidental | block 225,430, 11 Mar 2013 (BIP 50; bitcoin.org alert "11/12 March 2013 Chain Fork Information") | `OBL-F-0025`: a block referencing 4,501 distinct transaction ids passes v0.1's size and count clauses and fails the 0.8.1 clause inside its window, passes it after 15 May 2013 (`MODEL`) | `DESCENDANT` + `MODEL` | post-2010. Atlas §8; `derivatives/emergent/` |
| `OBL-C-0014` | OpenSSL's DER parser as signature validity, with no commit that wrote it; the written rule is BIP 66 strict DER | emergent | `80ad135a5:2015-01-13:true` ("Change IsDERSignature to BIP66 implementation"), `5a47811da:2015-01-19:true` ("BIP66 changeover logic"; PR 5713, merged 2015-02-03, enforced from 2015-07-04) | `true` (the written rule) | accidental | OpenSSL 1.0.0p and 1.0.1k rejecting encodings earlier releases accepted (BIP 66) | `OBL-F-0025`: BIP 66's function, ported, passes the corpus's 7 strict signatures and fails its 3 probes, which a tolerant reader recovers (`MODEL`); `OBL-F-0010`: the release build's OpenSSL 1.0.2u rejects the 3; `open`: acceptance by 0.9.8 on the 2009 binary | `EXECUTED (release build)` + `MODEL` | post-2010. Atlas §9; `derivatives/emergent/` |

## Where a designed successor fits — decided 20 September 2026, corrected the same day

The constitution is the specification; `JAN09-B` (`docs/JAN09-B-SPECIFICATION.md`) is its expression
on paper: the January 2009 design with the rules whose argument is in the record installed, the
not-in-record ones chosen deliberately and marked, and no consensus-critical third-party library. It
is not mined, and it has no implementer. An implementation of it, if one is ever wanted, is a fresh
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

Every rule on the target list has a row. Five witness cells say `open`: the 1 MB narrowing against
the 2009 binary (`OBL-C-0001`), the sigop count (`OBL-C-0004`), the transaction-size rule
(`OBL-C-0010`), the acceptance side of the DER rule (`OBL-C-0014`), and the numeric-operand cap under
`OBL-C-0002` and `OBL-C-0012`, which is read from source and not yet executed. Four of the five need
the unmodified 2009 binary. Rules that entered after
2015 are not on the list.

**Corrections.** 20 September, later the same day: a third commit added to `OBL-C-0001` and a second to `OBL-C-0004`. `172f00602` (19 September 2010, message about `-allowreceivebyip`) moved the 1 MB test into `CheckBlock` in place of the 32 MiB `MAX_SIZE` test and removed the 79,400 height gate from both rules, twelve days after the gated rule entered. `docs/MAX-BLOCK-SIZE-RETROFITTED.md` (signed 19 September) does not mention this commit; it is recorded here and in the atlas rather than by editing the signed note.

**Corrections.** 19 September's text named `a790fa46f` (30 September 2010) as the transaction-size
rule's origin; that commit moves `CheckTransaction` without changing it. The origin is `401926283`
(25 August 2010, 32 MiB) and `3df62878c` (13 September 2010, 1 MB); recorded in `OBL-C-0010` and in
`docs/CONSENSUS-ATLAS.md` §5 on 20 September 2026.
