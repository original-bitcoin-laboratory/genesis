# Corrections to the block findings

**Each findings directory is sealed** — its `SHA256SUMS` covers the captured evidence set, and from
block 2 onward the `FINDINGS.md` beside it. **Nothing in them is edited in place.** Where something in a sealed set turns out to be
wrong, the correction is recorded here instead, so the seal keeps verifying and the error stays
visible. Where wording must change, the set is *revised*: the old manifest and proof stay beside the
new ones and the edit is listed here (`docs/EVIDENCE_POLICY.md`, "Sealed sets and revisions").

> **Editing a sealed record to make it right destroys the only thing that made it worth sealing.**

---

## 1. `2026-08-06-block3/` — `NEXT-SESSION_block4_pre.json` is misdescribed

**That directory's `FINDINGS.md` says:**

> *"`NEXT-SESSION_block4_pre.json` is the binding taken after relaunching — it belongs to the block-4
> session and is kept here only so it is not lost to the next overwrite."*

**It is not a block-4 binding.**

```
its captured_utc      2026-08-04T23:11:41Z
its executable_path   C:\bitcoin\bitcoin-0.1.1\bitcoin.exe
its bitcoin.exe       cfb59606…  (v0.1.1)
its pid               5072 — a process that had already exited
```

**Block 4 was mined on 2026-08-08 by a different client and a different process** — v0.1.3
(`c3f15fc5…`), PID 2272 — and took its own fresh `pre` capture at 21:56:16Z. **That is the binding
that counts**, and it is in `2026-08-09-block4/`.

> **A `pre` capture from a dead process binds nothing.** The point of the pair is that one
> *uninterrupted* process spans it; a record from a PID that has already exited proves only that the
> file exists. This is why a fresh capture was taken rather than reusing the file that was sitting
> there labelled for the purpose.

## 2. Which client mined which block

Recorded because it is easy to flatten, and flattening it would be a false claim.

```
block 1    bitcoin-0.1.1   cfb59606c032faa933d5007e85d36f4cfd02737fc4bc485ec2d8699aeacba5ac
blocks 2-4 bitcoin-0.1.3   c3f15fc5b7bd80f4d08fe5ff356256214734eb1a3e4a7c953c9e8fc8453d2c7d
```

**Do not retro-fit v0.1.3 onto block 1.** Its evidence records say v0.1.1 and they are right.

## 3. What the block bindings do and do not establish

**They establish** that a process running a binary of a known hash was alive before and after the
block's own timestamp, with the same PID and process start time in both captures.

**They do not establish** that this specific process mined this specific block — no artifact can tie
a nonce to a PID. The binding narrows the gap between *"this binary was running"* and *"this binary
made this block"*; it does not close it.

**The narrower the bracket, the stronger the statement.** Block 4's is 39 minutes wide with the block
in the middle. Earlier brackets are wider. **A wide bracket is weaker evidence, not equal evidence.**

## 4. What these numbers are not

The gaps between blocks — 28.2 h, 23.9 h, 1.3 h, 68.6 h — are **wall-clock intervals between
sessions, not block times.** The miner is not left running; the guest is started when there is time.
**A 68-hour gap means the machine was off**, not that anything got harder: `nBits` is `0x1d00ffff` on
every block and difficulty has never moved.

**Nothing here measures hashrate or difficulty.** The early sets are one node, isolated; later sets record a
seed, a second miner and a reorganisation.

## 5. Where the raw bytes live

These published directories carry **findings and hashes**, and from block 2 onward the binding records. The `SHA256SUMS` in each
covers the full sealed set — including files that are **deliberately not published**: `blk0001.dat`,
`blkindex.dat`, `addr.dat`, `wallet.dat`, `debug.log`, the client binary and the screenshots.

**That is not an inconsistency.** The manifest is the sealed set's manifest; the repository publishes
the part that can be published. **A hash is not a reproduction** — you can verify our claims against
these digests without us shipping a wallet.

**NOT money.** The chain has no value assigned, no market, no sale.

---

## ★ A wording correction that applies to EVERY sealed findings set

**The sealed sets say "no market". That is the wrong KIND of claim, and it cannot be edited out of
them — which is exactly why this file exists.**

```
2026-08-05-block1/FINDINGS.md   "no premine, no sale, no market"
2026-08-09-block4/FINDINGS.md   "50.00 of nothing, no market, no sale"
```

**"No sale" and "no premine" are claims about what THIS PROJECT does. They stay true whatever anyone
else does. "No market" is a claim about the WORLD** — and the world is not ours to bind. Anyone may
find this software, run it, and mine; whether a third party then values or trades those units is
outside any software's control, and outside ours.

> **The distinction is not pedantry. A published statement that a stranger can falsify by acting
> undermines every other statement standing next to it** — and this project's whole method is that
> its statements survive checking.

**Corrected going forward:** `PROVENANCE.txt`, `derivatives/bitcoin/README.md` and
`satoshi-onchain/docs/PRESERVATION.md` now say **"no sale by us, no price set, we solicit no
market"**, and state plainly that third-party behaviour is not something we can promise about.

**Block 1 and block 4 stay exactly as sealed;** the other sets were revised on 12 September 2026 with their
earlier seals kept beside them (see the last section). Their seals still verify, the wording stays visible, and
this correction is where a reader learns it was reconsidered. **Editing a sealed record to make it
read better is the one thing that would make the seal worthless.**

---

## ★ Timestamps: this project standardises on UTC, and two sealed sets do not

**Everything this laboratory measures is timestamped in UTC** — block times, OpenTimestamps
attestations, the genesis constants, every findings header. **Two sealed sets also carried, in revision 1, a local
timezone in parentheses, and they should not have** (removed in revision 2 on 12 September 2026;
`SHA256SUMS.r1` attests the text described here).

```
2026-08-06-block2/FINDINGS.md   two times rendered in a local timezone beside the UTC value
2026-08-06-block3/FINDINGS.md   one such time
```

**The UTC figure in each is correct and is the one every other record cross-checks against.** The
local rendering adds nothing a reader can use: it cannot be verified against the chain, it does not
appear in any other artifact, and a second timezone in a research record is noise rather than
information.

> **Corrected going forward: UTC only, everywhere, with no parenthetical local time.**
>
> **Block 1 and block 4 stay exactly as sealed** (the other sets were revised on 12 September 2026, earlier
> seals kept) — their seals verify, the text stays visible, and this
> note is where a reader learns it was reconsidered. **Editing a sealed record to tidy it is the one
> thing that would make the seal worthless.**

**This is a research-hygiene convention, not a retrofit.** A laboratory that reports one clock
reports one clock; the moment it reports two, a reader has to work out which one anything is in.

---

## ★ Pronouns: the identity documents asserted in grammar what they declined to assert in words

**11 August 2026.** `PROVENANCE.txt` said, in one sentence:

```
This project makes NO claim about who Satoshi Nakamoto was, and claims NO authorship of his code,
his whitepaper, or his name.
```

**It disclaims all knowledge of the identity and assigns a gender three times in the same
sentence.** Four other lines did the same — *"the one he started"*, *"That is HIS file"*, *"the MIT
licence he released the code under"*, *"his notice"*.

**This laboratory's own stated convention is to reserve they/them for unknown identity**, and there
is no identity less known than this one. The convention was written down on 10 August; these lines
predate it and were not swept.

> **Corrected going forward: they/their for the 2008–2009 Satoshi Nakamoto, everywhere.** The
> reasoning is now stated in `PROVENANCE.txt` itself rather than left implicit — a document whose
> author is unknown does not tell you the author's gender either.

**Releases already published keep the text they shipped with.** v0.1.5 and earlier ship the older
wording; their manifests and signatures cover those exact bytes, and re-cutting a release to adjust
a pronoun would break every hash that attests to it for no gain. **This note is where a reader
learns it was reconsidered.**

## The public site: a claim that outran the evidence

`docs/bitcoin.html` described the 2008–2009 Satoshi as one *"whose identity this project holds to be
unprovable by any available means."*

**That is stronger than anything this laboratory has established, and stronger than its own closure
ledger.** The project's own records show the opposite: **a living key holder could sign one fresh
challenge with the genesis key and the PGP key and prove common control, now, machine-verifiably.**
It has never been done — which makes the identity **unproven**, not **unprovable**. What is closed
by proof is *authorship of a document*, which is a different question.

> **Corrected:** the page now reads *"whose identity is unknown and which this project does not
> claim to have settled"*, and names the era as **2008–2009** rather than 2009. **The disambiguation
> the sentence exists to perform — our 2026 agent is not that Satoshi — is unaffected; only the
> overclaim is gone.**

**Also corrected on that page:** *"the agent he built"* became *"parthod0x, the agent, and this
chain"*. The pseudonym is what the public collateral uses, and the real name is deliberately kept to
`LICENSE` and `CITATION`. **A gendered pronoun attached to the pseudonym re-links it to the legal
person the separation exists to keep apart** — so the pronoun is simply gone, which costs the
sentence nothing.

## ★ 12 September 2026 — a public-surface review, and what it found in the sealed sets

A full review of every public surface was run on 12 September 2026. Several findings sets are
sealed — their `SHA256SUMS` are signed and Bitcoin-anchored — so the items below are **recorded
here rather than edited in place**, exactly as the policy at the top of this file requires.

- **Internal folder labels.** Some sealed sets name the offline backup's folder layout (a cold-backup
  path, a key-store path, a wallet filename) when saying where raw bytes and wallets are held. These
  are labels for material that is deliberately not published; they disclose no content and no key.
  Newer sets say "held offline" instead, and that is the wording going forward.
- **The no-value statement.** Four sets — `2026-08-12-blocks61-63`, `2026-08-14-blocks64-121`,
  `2026-08-19-external-blocks221-222` and `2026-08-21-first-reorganization` — carried, in revision 1, no explicit
  "not money" line, and one printed the chain's units with a currency ticker. The statement applies
  to every set without exception: **NOT money.** No sale by us, no price set, we solicit no market,
  and the units are counters, not BTC.
- **The agent.** Wherever a set says "the agent" or "the chain's author", it means the AI agent
  described in `derivatives/bitcoin/CHRONOLOGY.md`: a program built in 2026, not a person, and not
  the author of the 2009 Bitcoin. The disclaimer is stated once there and applies to every set.
- **Provider and address.** Some sets named, in revision 1, the hosting provider of the seed node and its raw IPv4
  address. The hostname `bitcoin.bitcoin-lab.org:18026` is the durable identifier; the provider is
  incidental and will not be named in future sets.
- **Local-clock times** appear in two early sets and in one later capture note, as already recorded
  above; UTC is the only time this project writes from here on.
- **Revised the same day, under the revision rule adopted for it** (`docs/EVIDENCE_POLICY.md`): every set
  named above was re-sealed as revision 2 by an edit script held offline (its edit table repeats the
  labels it removed, so it is not published); the changes were — internal folder labels, local-clock times and the hosting provider removed; the
  seed named by hostname; the no-value line and the agent statement added where they were missing;
  an unverifiable remark about a third party's tool removed; one pronoun. Revision 1's manifest and
  proof remain in each set as `SHA256SUMS.r1` / `SHA256SUMS.r1.ots`. Block data, bindings and figures
  are byte-identical between revisions.
- **The r4 host-desktop screenshots** were removed from the repository on 12 September 2026, in line
  with the policy stated in `2026-08-05-block1/FINDINGS.md` (host captures are local evidence, not
  published deposits). Their `SHA256SUMS` and `INDEX.md` remain, so the frames stay identifiable and
  the anchored manifest still verifies against the offline copies.

- **Release texts (recorded 12 September 2026, corrected forward only).** `RELEASE-0.1.4.txt` says
  "One node, isolated, no peers"; the seed has relayed blocks since, and blocks 221–222 were mined outside
  the laboratory (`2026-08-19-external-blocks221-222/`). `RELEASE-0.1.5.txt` omits the "Which Bitcoin"
  paragraph that v0.1.4's text carries. Both files are signed and anchored and stay as published; the
  template in `derivatives/bitcoin/make_release.sh` now emits the paragraph unconditionally and no longer
  states a peer count.

- **Revision 3 (12 September 2026), same day.** Revision 2's manifests had been emitted with a blank line, a
  mixed entry style and no final newline, so `sha256sum -c` printed a formatting warning on every set; and
  the two statements revision 2 was meant to add were still missing from some sets (the no-value line from
  `blocks5-28`, `blocks29-50`, `blocks51-60`, `blocks122-295`; the agent statement from
  `block2`, `block3`, `blocks5-28`, `blocks29-50`, `blocks51-60`, `blocks298-731`). All twelve sets were
  re-sealed as revision 3 with revision 2's manifest and pending proof kept as `SHA256SUMS.r2` /
  `SHA256SUMS.r2.ots`. Edits in the same pass: a cold-backup folder layout and a wallet filename removed
  from `blocks29-50` and `blocks51-60`; a peer address quoted in little-endian hex from a log line elided in
  `blocks29-50`; two screenshot time spans in a local clock replaced by a pointer to the offline manifest
  (`blocks64-121`, `blocks122-295`); "`dist/…` in this repository" corrected to the published release
  (`blocks29-50`, `blocks51-60`); an unsourced remark about freenode's staff removed (`blocks29-50`) and an
  undefined label "F50" removed (`blocks64-121`); the seed-inventory probe dated (`blocks296-297`); a
  non-existent `generate_docs.py` and a local-workspace repository count corrected (`blocks122-295`,
  `blocks61-63`); the titles of `block2` and `block3` now say "Bitcoin (2026), an experimental chain".
- **Two revision-1 manifests keep a backup-folder label** in a comment line (`blocks29-50`, `blocks51-60`).
  They are kept unchanged because their proofs attest those exact bytes; the label names a folder, not content.
- **Block 4, sealed:** `2026-08-09-block4/FINDINGS.md` says the executable is retained beside the file. It is
  retained in the offline evidence set, not in this repository; its hash is in that set's `SHA256SUMS`.
- **Block 1, sealed:** `2026-08-05-block1/FINDINGS.md` says the wallet "never will be" here. Read: it is not
  here and is not published; nothing about the future is asserted.
- **Titles reading "the Bitcoin chain"** in the sealed block 4 set mean Bitcoin (2026), the laboratory's
  experimental chain — not the 2009 Bitcoin, not money.
