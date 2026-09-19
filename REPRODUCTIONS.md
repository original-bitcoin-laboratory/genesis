# Reproductions — the ledger

One entry per attempt by a party other than this laboratory's own tooling to reproduce, rebuild or
review its published work, whatever the result. Each entry states who ran it, under what access, and
what the attempt is evidence of. The label is the finding: a run commissioned by the operator, or by a
party working from the operator's brief, is recorded as such and is not independent replication. The
laboratory's own statement of why that distinction matters is §6 of its method paper and the
second-laboratory criterion of the ancient-DNA literature it cites.

Experimental laboratory research, in progress. Not money, not advice, no warranty (`RIGHTS.md`).

| date | party | access | task | result | evidence of |
|---|---|---|---|---|---|
| 2026-09-20 | an AI session commissioned by the operator, with no access to this workspace (run 1) | public repositories only; the session's network egress blocked GitHub raw and `bitcoin/bitcoin` | clean-room validator from `docs/JAN09-B-SPECIFICATION.md`; corpus replay; three constitution rows | validator for the stated bounds written and sanity-tested; corpus **not replayed** (could not be fetched); commits **not fetched**; reported strict DER as unspecified on the page because BIP 66 was outside the named material | what a stranger sees on the page alone: the bounds are stated, the base is delegated. Not a replication |
| 2026-09-20 | an AI session commissioned by the operator, with no access to this workspace (run 2) | public repositories, cloned; `bitcoin/bitcoin`, blobless clone; the site reached on a second attempt | the same brief | 1,400-line Python validator, `hashlib` only; **317/317 in January-2009 mode**, 316/317 in `JAN09-B` mode with the one designed disagreement (`bignum_add` under the 4-byte cap); block suite matched stage 127/127 and error string 126/127; five constitution rows checked against the commits, **all dates, author strings and diff lines held**, two naming defects found (`OBL-C-0003` named `MoneyRange` four days early; `OBL-C-0008` quoted a three-line message as one line); eleven gaps in the page listed, four still open after the session's own audit; its own validator carried two consensus bugs the corpus could not see (later `OP_NOP`s in the undefined range; no two-byte opcode space) | the corpus replays outside this laboratory's code, at `MODEL`; the page is constructible with the January source open beside it and not from the page alone; the record held on five rows. **Not independent replication**: the session worked from the operator's brief and the reviewer's own prior knowledge of the v0.1 source, and says so |
| 2026-09-20 | an AI session commissioned by the operator (adversarial review, partial receipt) | public repositories; could not execute the test suites (no GitHub access from its runtime); read the sources | hostile review of the registers, atlas, ports, PQ notes, language rule | two findings received before the transcript was cut: `OBL-F-0005`'s "no external anchor to a date" contradicted by its own artifact's 17 Nov 2008 email (an anchor for an artifact of that description, not for the bytes); `docs/NOV08_GENESIS.md` calling the genesis "a developer's test fixture" characterises purpose | both corrected the same day (rows above; the note's correction line). The rest of the review was not received |

## What each session's findings changed

- `OBL-C-0003`, `OBL-C-0004`, `OBL-C-0008`, `OBL-F-0005`, `OBL-F-0009`: corrected in place, dated.
- `common/conformance/CONSENSUS_BEHAVIORS.md`: rows 6 (the `OP_VERIFY`/`OP_RETURN` stop; undefined and
  two-byte opcodes; `OP_SUBSTR`'s arguments) and 7 (coinbase maturity, executed depth 99) added
  (`OBL-F-0032`, `OBL-F-0033`).
- `derivatives/script_limits/test_numeric_cap.py`: the numeric-operand cap executed (`OBL-F-0034`),
  closing an `open` cell in two constitution rows.
- `docs/JAN09-B-SPECIFICATION.md`: the cross-references a builder needs (`inventory/OPCODES.json`, the
  monetary constants, the behaviours, `JAN09-X`'s `OP_NOTEQUAL`), the sigop counting method, the cap's
  failure mode and where locks are consulted.
- `derivatives/vectors/README.md`: what the corpus does not cover, stated.

## The files

`reproductions/2026-09-20-clean-room-ai-sessions/` holds the two sessions' reports as received and the
validators they wrote (`run1-cleanroom_jan09b_validator.py`; `run2/jan09b.py`, `run_corpus.py`,
`selftest.py`), with their digests in `SHA256SUMS`. They are third-party code, kept as evidence of the
attempt; nothing in this repository imports them.
