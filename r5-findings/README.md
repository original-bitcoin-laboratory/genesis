# R5 findings — the conformance corpus against running binaries

R3 and R4 witnessed the unmodified 2009 client mining, relaying, reorganising and spending. R5 turns
the lab's conformance corpus (`derivatives/vectors/`) into transactions and blocks, submits them to a
running client over its own wire protocol, and reads the client's verdict from the client itself.

| set | binary | outcome |
|---|---|---|
| [`2026-09-13-binary-replay-release/`](2026-09-13-binary-replay-release/) | this lab's release client `c3f15fc5…` (v0.1 source + nine chain-separation substitutions, OpenSSL 1.0.2u), isolated clone of the mining node | **136/136 scripts, 17/17 signatures, 19/19 blocks agree; all 19 rejection strings found in `debug.log`.** The three non-strict DER signatures are rejected by OpenSSL 1.0.2u. |
| *(pending)* | the unmodified 2009 `bitcoin.exe` `fbcac071…` (OpenSSL 0.9.8) in the R4 appliance | the only oracle for `checksig.json`'s `expected_binary` column |

Raw run bytes live under the gitignored `r5-evidence/<set>/`; each findings set commits their
SHA-256 digests (`SHA256SUMS`, `EVIDENCE_MANIFEST.json`) and a written account. The harness and
its runbook are in `derivatives/vectors/replay/`.
