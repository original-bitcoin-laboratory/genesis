# Overall review — both organisations and the three sites, 20 September 2026

*The session's findings and closing paragraphs, as received. The session was an AI session commissioned
by the operator, the same one that produced `REVIEW-adversarial-1.md` and `-2.md`, now asked to review
`original-bitcoin-laboratory` and `satoshi-onchain` together with bitcoin-lab.org, satoshioncha.in and
bitcoinwhitepaper.online. It cloned all five public repositories and `bitcoin/bitcoin`, ran every test
suite, checked every internal link and asset on the seventeen site pages, read the analytics script,
checked thirteen source-line citations against the January 2009 archive committed under
`artifacts/jan09/`, and recomputed both post-quantum notes and the full commit census. It did not audit
the Patoshi classifier's statistics, the Rust validator, the WASM verifier, or the findings sets, and
says so. Its opening survey and its list of what it verified as correct are held in the laboratory's
workspace and not reproduced here; the table and the paragraphs below are unedited. What was corrected
from each finding, and what was not and why, is in `../../REPRODUCTIONS.md`, dated.*

*One line of the opening is kept because it corrects the reviewer's own earlier finding: "Two were
disputed, and on one of them the laboratory is right and I was wrong: a 17,088-byte push needs
OP_PUSHDATA2, not OP_PUSHDATA4. My own script computed that correctly and my prose did not. That
correction stands against me."*

---

## Defects and risks

| where | issue | severity | fix |
| --- | --- | --- | --- |
| bitcoinwhitepaper.online, "What a court found" | "1,698 paragraphs" — The published counts are 1,736 (Bird & Bird) or 945 plus a 799-paragraph appendix. No source gives 1,698, and the page's own standard is that every claim names its source. | wrong | |
| all three footers | "aggregate, cookie-less analytics, no identifiers" — True about identifiers, incomplete about behaviour. analytics.js reports outbound host and path, in-page anchor jumps, scroll-depth milestones, print events, dwell buckets, JS errors, and a classification of what was copied (sha256, address, pem-or-signature, command). A visitor cannot infer that from the footer. | unsupported as written | |
| docs/analytics.js header comment | "nothing sent that a server log would not already see" — False for scroll depth, dwell time, copy shape and print. A server log sees none of these. | wrong | |
| docs/EVIDENCE_POLICY.md (revised) | scripts/revise_findings.py "exists in the workspace and is excluded on purpose: its edit tables quote the strings the revisions removed" — Resolves my original finding and creates a smaller one. The instrument whose edit table is described as the record is unauditable. | self-asserted | |
| docs/BITCOIN-GIT-HISTORY-PROVENANCE.md (rev 2) | "132 groups of two non-merge commits with the same first message line" — My independent recount gives 133. The delta is exactly the root pair e071a3f6c/4405b78d6 — the one the note features under "the doubling starts at the root". It is excluded from the count without being said. | style | |
| bitcoin-lab.org, banner | "distributed everywhere as bitcoin-0.1.0.rar" — An absolute over an unenumerated set, in the estate that removed "everyone" from the same sentence in the register. | style | |
| bitcoin-lab.org, node list | "seed.bitcoin-lab.org:18009 JAN09-X · Jan 2009 v0.1.0" — The same page's banner says the bytes are v0.1.1. The label the site exists to correct survives three screens below the correction. | style | |
| provenance/SOURCEFORGE_PUBLISHED_HASHES.md and artifacts/jan09/ | "verified against the published digests before use" — The note says plainly elsewhere that the held v0.1.0-era archive "matches no published hash anywhere." Both are true of different files, but the REPRODUCTIONS.md summary reads as if the base were hash-anchored. It is anchored by custody, internal consistency and reproduction. | unsupported as written | |
| R4 binding, fbcac071… | the digest is published by the laboratory only — Same structural limit as the source archive: no 2009-era publication to check it against. The binding now proves one uninterrupted process ran one file; it does not prove that file is the 2009 binary. | structural | |

## Structural risks, which are not defects

No independent replication exists. REPRODUCTIONS.md has four rows. All four are sessions commissioned by the operator, and the ledger labels each "Not independent replication". Mine are two of them. The laboratory is right to label them that way, and it means the entire evidential apparatus — the seals, the timestamps, the signed notes, the binding records — has never been checked by a party with its own reason to check it. The honesty of the labelling does not substitute for the thing labelled.

Everything concentrates on one person and one key. Five repositories, three domains, three live network anchors, the release signatures, the PQ succession certificate, the OpenTimestamps stamping, the analytics account. IPFS, Radicle and Software Heritage preserve artifacts against host loss. Nothing preserves the estate against the operator becoming unavailable, and the PQ-SUCCESSION-CERTIFICATE designates a successor key rather than a successor person. Mirroring is not continuity.

Named living people. satoshioncha.in and bitcoinwhitepaper.online both record that Satoshi transferred bitcoin to Nicholas Bohm, a private individual, cited to ¶771. Both decline to identify the transactions and say so. This is inside RIGHTS.md and inside the judgment, and it is handled about as carefully as it can be. It remains the single highest-risk content in the estate, because the inference a reader draws is not one the pages control. The same applies to the named coinbase address in the 2009 fee table.

The stated language discipline is not uniform across the estate. bitcoin-lab.org names no person and no jurisdiction. The other two name Adam Back, Wei Dai, Hal Finney, Perry Metzger, Ray Dillinger, Patrick Chkoreff, Dustin Trammell, Bryan Bishop, Nicholas Bohm, Craig Wright, and a court in England and Wales, extensively and by paragraph. RIGHTS.md permits all of it. But "publishes no absolutes, attributes no motive, names no jurisdiction" is a description of one site, not of the estate, and the estate presents itself as one voice under one key.

Live services on 2009-era code. Three public network anchors run a client with no resource limits in its script interpreter, by the laboratory's own finding. SECURITY.md is blunt about this and the chains carry no value. The exposure is to the hosts, not to users.

The record moves faster than anyone can check it. Between two reads three hours apart, the registers, four derivative suites, both PQ notes, two signed notes, RIGHTS.md and the evidence policy all changed, and two new directories appeared. Responsiveness is a virtue; a citable research record that is rewritten within hours of criticism is harder to cite. The signed-revision discipline (r1, r2, r3 kept beside the current file with OpenTimestamps proofs) is the right answer and is being applied. It should be applied to the registers too, which currently change in place.

## What I would do next, in order

1. Get one reproduction that is not commissioned. Post the JAN09-B specification and the corpus somewhere adversarial and wait. One uncommissioned row in REPRODUCTIONS.md is worth more than the next twenty findings.
2. Fix the paragraph count, the analytics disclosure, and the two stale labels on bitcoin-lab.org. All four are ten-minute jobs on pages that claim exactness.
3. Write down what happens if the operator stops. A successor key is a cryptographic answer to an institutional question.
4. Freeze the registers. Version them the way the signed notes are versioned, so a citation to OBL-F-0009 names a state of that row.
5. Decide whether the Bohm material earns its place. It is the only content in the estate whose downside is not borne by the laboratory.

The single strongest thing here, and the single weakest. The strongest is the discipline of stating what the evidence cannot carry: the note that the v0.1.0 archive matches no published hash, the line that no grade attests what the 2009 network enforced, the three withdrawn novelty claims, the "Not independent replication" label applied to reviews the operator paid for. Most research projects fail by overclaiming; this one repeatedly walks its own claims back, in public, with dates. The weakest is that every one of those honest statements, and every artifact that supports them, comes from the same source. The laboratory has built an unusually good apparatus for checking itself and has not yet been checked by anyone else. Until that changes, the correct description of this work is a very careful, very well-documented single-source claim — which is, to its credit, roughly what it says it is.
