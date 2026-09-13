# R5 findings — the conformance corpus against running binaries

R3 and R4 witnessed the unmodified 2009 client mining, relaying, reorganising and spending. R5 turns
the lab's conformance corpus (`derivatives/vectors/`) into transactions and blocks, submits them to a
running client over its own wire protocol, and reads the client's verdict from the client itself.

| set | binary | outcome |
|---|---|---|
| [`2026-09-13-binary-replay-release/`](2026-09-13-binary-replay-release/) | this lab's release client `c3f15fc5…` (v0.1 source + nine chain-separation substitutions, OpenSSL 1.0.2u), isolated clone of the mining node | **136/136 scripts, 17/17 signatures, 19/19 block cases agree: the 16 rejected blocks each produced their exact `main.cpp` string in `debug.log`, and the 3 expected to be accepted were accepted.** The three non-strict DER signatures are rejected by OpenSSL 1.0.2u. |
| *(pending)* | the unmodified 2009 `bitcoin.exe` `fbcac071…` (OpenSSL 0.9.8) in the R4 appliance | the only oracle for `checksig.json`'s `expected_binary` column |

Raw run bytes live under the gitignored `r5-evidence/<set>/`; each findings set commits their
SHA-256 digests (`SHA256SUMS`, `EVIDENCE_MANIFEST.json`) and a written account. The harness and
its runbook are in `derivatives/vectors/replay/`.

## Corrections (13 September 2026)

- `2026-09-13-binary-replay-release/FINDINGS.md` line 11 says "each of the 19 rejected blocks" produced its
  error string. Of the 19 block cases, 16 were rejected (each with its exact `main.cpp` string) and 3 were
  accepted, as the corpus predicts and the file's own log excerpt shows. The times in that file are the clone
  VM's local clock, not UTC; the directory it names is the guest's install path.

