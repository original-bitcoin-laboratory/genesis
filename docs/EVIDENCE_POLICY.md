# Evidence Policy

## Claims must be scoped

Use one of these prefixes in reports:

- `NOV08-SOURCE:` visible in the November source witness.
- `JAN09-SOURCE:` visible in the January source release.
- `JAN09-EXECUTED:` reproduced with the historical implementation.
- `MODEL:` demonstrated only in a reimplementation or harness.
- `DERIVATIVE:` introduced by this project.
- `DESCENDANT:` observed in a later Bitcoin implementation.
- `UNRESOLVED:` evidence is incomplete or contradictory.
- `EXECUTED (release build):` witnessed on this laboratory's release client (the reconstruction as shipped), not on the unmodified 2009 binary; a compound grade such as `JAN09-SOURCE + EXECUTED (release build)` lists each basis.

## Required evidence for an opcode claim

- byte value and declaration;
- evaluator implementation;
- reachability from transaction validation;
- positive and negative script vectors;
- transaction-context behavior where relevant;
- accepted/rejected block witness if consensus-relevant.

## Required evidence for a financial construction

- economic assumptions;
- transaction graph;
- exact scripts and signature commitments;
- raw serialized transactions;
- execution trace;
- resulting UTXO state;
- failure paths and security limitations;
- explicit distinction between native rule and external coordination.

## Sealed sets and revisions

A findings set is sealed by its `SHA256SUMS`, whose OpenTimestamps proof anchors it in a Bitcoin
block. **A sealed set is not edited in place.** Two things may happen to it afterwards:

- **A correction** is recorded in `bitcoin-findings/CORRECTIONS.md`, dated, without touching the set.
  This is the default for anything that is *wrong*: the error stays visible beside its correction.
- **A revision** replaces wording that should not have been published (an internal label, a local
  clock, a provider's name) or adds a statement that every set must carry (no value, the agent's
  nature). A revision keeps the previous manifest and its proof beside the new ones
  (`SHA256SUMS.r1`, `SHA256SUMS.r1.ots`), adds a `REVISION.txt` that says what changed and why,
  re-seals the set with a new `SHA256SUMS` and a fresh proof, and lists every edit in
  `CORRECTIONS.md`. Both seals go on verifying, and the difference between them is exactly the
  recorded edit. Block data, binding records and figures are not revised; only prose is.

Revisions are numbered and dated. The direction is fixed: new seals beside old ones, not in
place of them. `scripts/revise_findings.py` is the instrument, and its edit table is the record.

---

*Experimental laboratory research, in progress: what re-runnable methods find, and no conclusion beyond that. Not money — no premine, no sale, no value assigned, no token. Not financial advice. No warranty. [Rights, sourcing and corrections](https://github.com/original-bitcoin-laboratory/genesis/blob/main/RIGHTS.md).*
