# Findings register

One row per finding: a stable ID that is not reused, the claim in one sentence, its evidence grade
(`docs/EVIDENCE_POLICY.md`; `EXECUTED (release build)` means witnessed on this laboratory's release
client, not on the unmodified 2009 binary), the artifact the claim rests on, and the date that artifact
was first committed. Cite the ID. IDs are for claims, not documents; a document that states several
claims appears on several rows, and a claim without an artifact is marked `pending:` until it has one.
`scripts/check_register.py` runs in CI and fails on a dangling or renamed ID anywhere in the three
repositories. The `OBL-C-` series (one row per consensus rule) is reserved for the constitution register.

Experimental laboratory research, in progress. Not money, not advice, no warranty (`RIGHTS.md`).

| ID | claim | grade | artifact | recorded |
|---|---|---|---|---|
| `OBL-F-0001` | v0.1 selects the best chain by block height, not cumulative proof-of-work: on a discriminating fork the challenger at height 125 with work 250 beats the incumbent at height 122 with work 262 | `MODEL` | `paper-artifacts/height-vs-work.json` | 2026-08-01 |
| `OBL-F-0002` | v0.1 compares `nLockTime` as a block height only; the source has no `LOCKTIME_THRESHOLD`, so a wall-clock lock cannot be expressed | `JAN09-SOURCE + MODEL` | `derivatives/temporal/README.md` | 2026-07-27 |
| `OBL-F-0003` | Bitcoin's script resource limits were retrofitted in 0.3.6 on 29 Jul 2010 under a `makefile.unix wx-config` commit message; the 5000-byte element cap became 520 bytes on 15 Aug 2010 under "misc changes"; the January 2009 interpreter runs a 600-byte element and a 1500-deep stack | `DESCENDANT + JAN09-EXECUTED` | `docs/SCRIPT-LIMITS-RETROFITTED.md` | 2026-08-12 |
| `OBL-F-0004` | v0.1's `CheckTransaction` accepts the output amounts of block 74638; the 0.3.10 rule (15 Aug 2010, commit `d4c6b90ca`) rejects them | `MODEL` | `derivatives/overflow/README.md` | 2026-07-27 |
| `OBL-F-0005` | the November 2008 pre-release's genesis coinbase carries the bare integer 247422313: no headline, no external anchor to a date | `NOV08-SOURCE` | `docs/NOV08_GENESIS.md` | 2026-08-04 |
| `OBL-F-0006` | v0.1's retarget measures 2015 intervals against a 2016-interval budget; the fixed point is 600.30 s per block, 0.05% slow, not the 599.70 s a naive reading of the constants gives | `MODEL` | `derivatives/retarget/README.md` | 2026-08-01 |
| `OBL-F-0007` | v0.1 shipped a commerce subsystem that is off-chain by design: a flood pub/sub advert channel (`MSG_PRODUCT`, `MSG_TABLE`) and a local `CReviewDB`, which does not touch the transaction set | `JAN09-SOURCE` | `inventory/MARKET_AUDIT.md` | 2026-07-26 |
| `OBL-F-0008` | for post-quantum signatures on a 2009-shaped chain, size and not verification is the binding constraint: transactions grow 19× to 86× | `MODEL` | `docs/PQ-SIGNATURE-COST.md` | 2026-08-11 |
| `OBL-F-0009` | two unmodified January 2009 binaries mine, relay, reorganise and spend a matured coinbase across the wire; consensus maturity is `COINBASE_MATURITY` = 100 and the wallet withholds a generated coin 20 blocks beyond it | `JAN09-EXECUTED` | `r4-findings/2026-08-06-relayed-spend/FINDINGS.md` | 2026-08-09 |
| `OBL-F-0010` | the conformance corpus replayed over the wire against the release client (`c3f15fc5…`, OpenSSL 1.0.2u) agrees 136/136 scripts, 17/17 signature checks and 19/19 blocks; three non-strict DER encodings are rejected by that OpenSSL | `EXECUTED (release build) + MODEL` | `r5-findings/2026-09-13-binary-replay-release/FINDINGS.md` | 2026-09-13 |
| `OBL-F-0011` | v0.1 erases a block that fails `ConnectBlock` from disk and from the block index, so a rejected block is indistinguishable from one the node did not see; the best chain is chosen by height | `JAN09-SOURCE + EXECUTED (release build)` | `r5-findings/2026-09-13-binary-replay-release/FINDINGS.md` | 2026-09-13 |
| `OBL-F-0012` | the archives everyone serves as `bitcoin-0.1.0` contain v0.1.1: the byte size Satoshi gave in a 10 Jan 2009 email and a 10 Jan PE link stamp; no consensus rule differs | `JAN09-SOURCE` | `common/VERSION_LABEL.md` | 2026-08-08 |
| `OBL-F-0013` | `MAX_BLOCK_SIZE = 1000000` was defined in commit `a30b56ebe` (15 Jul 2010, 0.3.1, message about OpenSSL linkage and a tray icon) and used only by the miner; it became a block-validity rule in `f1e1fb4bd` (7 Sep 2010, message "cleanup"), gated on height > 79,400, so the first block it applies to is 79,401 (12 Sep 2010) | `DESCENDANT` | `docs/MAX-BLOCK-SIZE-RETROFITTED.md` | 2026-09-19 |
| `OBL-F-0014` | for 30 Aug 2009 to 31 Dec 2010 the `bitcoin/bitcoin` history carries 122 of its 341 non-merge commits twice, one copy with the `git-svn-id` trailer and one without, the second copy not earlier in any pair (median same day, at most 8.09 days later) and carrying the author strings `s_nakamoto`, `Satoshi Nakamoto` or the literal `--author=Satoshi Nakamoto`; 112 of 120 compared pairs are the same change, 8 differ by a few lines; the doubling starts at the root commit | `DESCENDANT` | `docs/BITCOIN-GIT-HISTORY-PROVENANCE.md` | 2026-09-19 |
| `OBL-F-0015` | `MAX_BLOCK_SIGOPS = MAX_BLOCK_SIZE/50` entered in the same 7 Sep 2010 commit as the block-size rule, `f1e1fb4bd` | `DESCENDANT` | `docs/MAX-BLOCK-SIZE-RETROFITTED.md` | 2026-09-19 |
| `OBL-F-0016` | the January 2009 release enforced a block-size ceiling: `CheckBlock` rejects a block whose serialised size or transaction count exceeds `MAX_SIZE` = 0x02000000 (32 MiB); the 2010 rule narrowed it, it did not create one | `JAN09-SOURCE` | `docs/MAX-BLOCK-SIZE-RETROFITTED.md` | 2026-09-19 |
| `OBL-F-0017` | cumulative-work chain selection replaced height in `3b7cd5d89` (25 Jul 2010, 0.3.3) under a message about JSON-RPC authentication and initial block download; the repository's first commit (30 Aug 2009, 0.1.5) selects by height | `DESCENDANT` | `docs/CONSENSUS-ATLAS.md` | 2026-09-20 |
| `OBL-F-0018` | time-based `nLockTime` (the 500,000,000 height-or-time split) entered in `dd519206a` (29 Oct 2009) with a message naming "non-final tx locktime changes" and a source comment attributing it to 0.1.6; the first commit (0.1.5) compares heights only | `DESCENDANT` | `docs/CONSENSUS-ATLAS.md` | 2026-09-20 |
| `OBL-F-0019` | the per-transaction size bound entered in two steps, 32 MiB in `401926283` (25 Aug 2010, "alert system") and 1 MB in `3df62878c` (13 Sep 2010, a message about the miner); `a790fa46f` (30 Sep 2010), cited earlier by this laboratory as the origin, moves the function unchanged | `DESCENDANT` | `docs/CONSENSUS-ATLAS.md` | 2026-09-20 |
| `OBL-F-0020` | `IsStandard` entered as node policy in `a206a2398` (7 Dec 2010, gavinandresen) with a message stating the reason; a block carrying a non-standard transaction stays valid | `DESCENDANT` | `docs/CONSENSUS-ATLAS.md` | 2026-09-20 |
| `OBL-F-0021` | the alert system entered in `401926283` (25 Aug 2010, "alert system") and left in four dated steps: removal merged 21 Mar 2016 (PR 7692, Core 0.13.0), final alert 19 Jan 2017, hard-coded in 0.14.0 (8 Mar 2017), key published 3 Jul 2018 | `DESCENDANT` | `docs/CONSENSUS-ATLAS.md` | 2026-09-20 |
| `OBL-F-0022` | the Berkeley DB lock table was a block-validity rule with no commit: block 225,430 (11 Mar 2013) forked the chain, and the written response `8bd028818` (15 Mar 2013) limited a block to 4,500 distinct transaction ids until 15 May 2013 | `DESCENDANT` | `docs/CONSENSUS-ATLAS.md` | 2026-09-20 |
| `OBL-F-0023` | OpenSSL's DER parser was a signature-validity rule with no commit until BIP 66 wrote strictness into consensus (`80ad135a5`, 13 Jan 2015; merged 3 Feb 2015; enforced from 4 Jul 2015 under the 950-of-1,000 version-3 rule) | `DESCENDANT` | `docs/CONSENSUS-ATLAS.md` | 2026-09-20 |
| `OBL-F-0024` | `CScriptNum` (PR 3965, 26 Mar to 9 May 2014) replaced OpenSSL's `BIGNUM` in script arithmetic without changing the rule; the four-byte operand cap is the 2010 rule of `4bd188c43` | `DESCENDANT` | `docs/CONSENSUS-ATLAS.md` | 2026-09-20 |
| `OBL-F-0025` | the two rules nobody wrote, executed side by side: a block referencing 4,501 distinct transaction ids passes v0.1's `CheckBlock` size and count clauses and fails the 0.8.1 clause of `8bd028818` inside its 2013 window; BIP 66's `IsValidSignatureEncoding`, ported, passes the corpus's 7 strict signatures and fails its 3 probes, which a BER-tolerant reader recovers to the same (r, s) | `MODEL` | `derivatives/emergent/README.md` | 2026-09-20 |

## Series

- `OBL-F-nnnn`: findings (claims about the sources, the binaries or the reconstructions).
- `OBL-C-nnnn`: consensus-rule entries of the constitution register, one per rule, each with the commit that
  introduced it, its message verbatim, whether the message describes the change (`message_match`), the argument
  the record carries for it, and an executed witness or a stated reason for its absence. Not yet started; the
  checker reports its `message_match` tally with the number of surface rows as the denominator, counting rules,
  with origin commits as a sub-count (a rule with several commits lists them as `sha:false,sha:true`).
