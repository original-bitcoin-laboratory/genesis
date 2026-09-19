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
| `OBL-C-0001` | `MAX_BLOCK_SIZE = 1000000` | consensus | `a30b56ebe:2010-07-15:false` (constant; miner-only), `f1e1fb4bd:2010-09-07:false` (validity rule in `AcceptBlock`, heights above 79,400) | `false` | not-in-record | none | `OBL-F-0016` for the origin side (v0.1 `CheckBlock` rejects over 32 MiB, read); `open`: a block in the 1 MB–32 MiB band submitted to the 2009 binary and to 0.3.12 would show the narrowing executed | `DESCENDANT` + `JAN09-SOURCE` | `a30b56ebe` has no second copy in the window; `f1e1fb4bd` is duplicated as `8c9479c6b`, same date, author string and SVN trailer. Note: `docs/MAX-BLOCK-SIZE-RETROFITTED.md` |
| `OBL-C-0002` | script resource caps: pushed element (5000 → 520 bytes), script size (20000), stack depth (1000), numeric operand (258 → 4) | anti-DoS | `757f0769d:2010-07-29:false` (installs all four, message names `makefile.unix`), `4bd188c43:2010-08-15:false` (tightens element and numeric caps, "misc changes") | `false` | not-in-record | none | `OBL-F-0003`: the January 2009 interpreter runs a 600-byte element and a 1500-deep stack (`JAN09-EXECUTED`) | `JAN09-EXECUTED` | `757f0769d` is duplicated as `a75560d82`, 2010-07-30, author string `--author=Satoshi Nakamoto`; `4bd188c43` as `6ac7f9f14`, 2010-08-15, `Satoshi Nakamoto`. Note: `docs/SCRIPT-LIMITS-RETROFITTED.md` |
| `OBL-C-0003` | `MoneyRange` and the output-sum overflow check in `CheckTransaction` | consensus | `d4c6b90ca:2010-08-15:true` ("fix for block 74638 overflow output transaction") | `true` | cited | block 74638, 15 Aug 2010: 184,467,440,737 BTC in two outputs | `OBL-F-0004`: v0.1 accepts the block-74638 amounts, the 0.3.10 rule rejects them (`MODEL`) | `MODEL` | `d4c6b90ca` is duplicated as `76793dc96`, 2010-08-15, `Satoshi Nakamoto`; the scanback guard `85de7d7c0` (same day) has no second copy. Note: `derivatives/overflow/README.md` |
| `OBL-C-0004` | `MAX_BLOCK_SIGOPS = MAX_BLOCK_SIZE/50` | anti-DoS | `f1e1fb4bd:2010-09-07:false` | `false` | not-in-record | none | `open`: no artifact exercises the sigop count against the 2009 binary | `DESCENDANT` | as `OBL-C-0001`'s second commit. Note: `docs/MAX-BLOCK-SIZE-RETROFITTED.md` |
| `OBL-C-0005` | disabled opcodes: `OP_CAT`, `OP_SUBSTR`, `OP_LEFT`, `OP_RIGHT`, `OP_INVERT`, `OP_AND`, `OP_OR`, `OP_XOR`, `OP_2MUL`, `OP_2DIV`, `OP_MUL`, `OP_DIV`, `OP_MOD`, `OP_LSHIFT`, `OP_RSHIFT` | consensus | `4bd188c43:2010-08-15:false` ("misc changes"; a pre-switch guard that fails the script) | `false` | not-in-record | none | `OBL-F-0010`: the 2009 vocabulary executes on the release client, 136/136 script vectors (`EXECUTED (release build)`); BIP 347 documents the disabling | `EXECUTED (release build)` + `JAN09-SOURCE` | `4bd188c43` is duplicated as `6ac7f9f14`, 2010-08-15, `Satoshi Nakamoto`. BIP 347 dates this commit "Aug 25 2010"; the commit's own fields say 2010-08-15 (recorded in `docs/SCRIPT-LIMITS-RETROFITTED.md`) |

## Where a designed successor fits — decided 20 September 2026

The constitution is the specification; a chain built from it is its executable expression. Only one
designed successor is kept. `JAN09-B` is that expression on paper: the January 2009 design with the
rules whose argument is in the record installed, the not-in-record ones chosen deliberately and marked,
and no consensus-critical third-party library. It is written as a profile specification when the register
is complete, and it is not mined. The laboratory's post-quantum successor (`pqBitcoin`, its own repository)
is the implementation that takes those bounds when its genesis is defined, adding the one delta the
constitution does not contain, the signature scheme. Two chains with two rule sets would split the
argument; one specification and one implementation do not.

## Rows still to enter

From `CONSENSUS_SURFACE.md` and `CONSENSUS_BEHAVIORS.md`: the 32 MiB `MAX_SIZE` ceiling as the
inherited rule the 1 MB limit narrowed; `IsStandard` (policy); the transaction-size rule
(`a790fa46f`, 30 Sep 2010); `LOCKTIME_THRESHOLD` (witness `OBL-F-0002`, commit not yet identified);
cumulative-work chain selection replacing height (witness `OBL-F-0001`, commit not yet identified);
`CScriptNum` replacing unbounded `BIGNUM`; the alert key; and the two emergent rules, Berkeley DB lock
limits (the March 2013 fork) and OpenSSL DER parsing (closed by BIP 66). A row that cannot be witnessed
is entered as `open` with the reason, not left out.
