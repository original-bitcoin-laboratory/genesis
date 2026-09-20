# Evidence Policy

## Claims must be scoped

Use one of these prefixes in reports:

- `NOV08-SOURCE:` visible in the November source witness.
- `JAN09-SOURCE:` visible in the January source release.
- `JAN09-EXECUTED:` reproduced with the historical implementation.
- `MODEL:` demonstrated only in a reimplementation or harness.
- `DERIVATIVE:` introduced by this project.
- `DESCENDANT:` observed in a later Bitcoin implementation, in execution.
- `RECORD:` read from a version-control record, a published document or a file's own header: a commit's
  message and diff, a merge date, a BIP's text, an alert page, a mailing-list message, a PE stamp. Not an
  observation of behaviour. (Added 20 September 2026; rows that carried `DESCENDANT` for such reading were
  regraded the same day.)
- `UNRESOLVED:` evidence is incomplete or contradictory.
- `EXECUTED (release build):` witnessed on this laboratory's release client (the reconstruction as shipped), not on the unmodified 2009 binary; a compound grade such as `JAN09-SOURCE + EXECUTED (release build)` lists each basis.
- `EXECUTED (laboratory build):` witnessed on a binary this laboratory compiled from the archive's source against its own compatibility shims (`derivatives/build-reconstruction/`): neither the 2009 binary nor the release client. (Added 20 September 2026 for `OBL-F-0003`, which had carried `JAN09-EXECUTED`.)

A grade attests the object it names. No grade in this list attests what the 2009 network enforced: two nodes
running one binary are one implementation, and a later commit shows what later code did
(`CONSTITUTION-REGISTER.md`, "What the register does not establish").

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
place of them. The record of a revision is the set's `REVISION.txt` and its entry in
`bitcoin-findings/CORRECTIONS.md`; and the kept manifests make the edit itself checkable, since the difference
between the files revision N-1 seals and the files revision N seals is the complete edit, which anyone holding the
set can take without any instrument of the laboratory's. The script that issued revisions 2 to 4 is kept in the laboratory's workspace
and is not published: its edit tables quote the strings the revisions removed. (An earlier text here named it as
if published; corrected 20 September 2026.)

The same rule holds for a signed note under `docs/`: it is not edited in place. A revision retires the current
text and its signature and proof files beside themselves as `<name>.rN.<ext>*`, writes the revised text with a dated
revision line at its end, and is signed and stamped afresh. An unsealed, unsigned document is corrected in place
with a dated correction line.

## The language rule

Editable public text carries no promissory or universal-temporal word (the audit
`_audit_absolutes.py` holds the list), states what is done in the present tense and facts as plain negatives,
attributes no motive to anyone, and names no jurisdiction or statute in its own statements (a judgment cited as a
source is named as such). A categorical verdict on one stated, bounded claim ("FALSE" against
a sentence this laboratory published) is a finding, not an absolute. Quoted words of others are untouched, and a
signed, sealed or frozen text is corrected forward by a dated note beside it. The workspace control that enforces
this on every editable file is the laboratory's own and is not published; what it enforces is stated here.

---

*Experimental laboratory research, in progress: what re-runnable methods find, and no conclusion beyond that. Not money — no premine, no sale, no value assigned, no token. Not financial advice. No warranty. [Rights, sourcing and corrections](https://github.com/original-bitcoin-laboratory/genesis/blob/main/RIGHTS.md).*
