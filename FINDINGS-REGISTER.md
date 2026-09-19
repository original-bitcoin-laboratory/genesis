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
| `OBL-F-0014` | the `bitcoin/bitcoin` history for 2010 carries each commit twice on parallel lineages (`s_nakamoto`, `Satoshi Nakamoto`, and the literal author string `--author=Satoshi Nakamoto`), dated one to three days apart; the SVN-derived `s_nakamoto` lineage carries the earlier dates | `DESCENDANT` | `pending: docs/BITCOIN-GIT-HISTORY-PROVENANCE.md` | — |
| `OBL-F-0015` | `MAX_BLOCK_SIGOPS = MAX_BLOCK_SIZE/50` entered in the same 7 Sep 2010 commit as the block-size rule, `f1e1fb4bd` | `DESCENDANT` | `docs/MAX-BLOCK-SIZE-RETROFITTED.md` | 2026-09-19 |
| `OBL-F-0016` | the January 2009 release enforced a block-size ceiling: `CheckBlock` rejects a block whose serialised size or transaction count exceeds `MAX_SIZE` = 0x02000000 (32 MiB); the 2010 rule narrowed it, it did not create one | `JAN09-SOURCE` | `docs/MAX-BLOCK-SIZE-RETROFITTED.md` | 2026-09-19 |

## Series

- `OBL-F-nnnn`: findings (claims about the sources, the binaries or the reconstructions).
- `OBL-C-nnnn`: consensus-rule entries of the constitution register, one per rule, each with the commit that
  introduced it, its message verbatim, whether the message describes the change (`message_match`), the argument
  the record carries for it, and an executed witness or a stated reason for its absence. Not yet started; the
  checker reports its `message_match` tally with the number of surface rows as the denominator.
