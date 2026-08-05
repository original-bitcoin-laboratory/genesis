# The whitepaper: what is established, and what is not

**5 August 2026**

This lab ships `docs/bitcoin.pdf`. This note records exactly what that file is, because the ordinary
label — *"the Bitcoin whitepaper, 2008"* — is not accurate about the file, and this project does not
get to be imprecise about its own artifacts.

Every claim below is checkable by anyone, from public sources, without trusting us.

---

## The file we ship

```
bitcoin.pdf   184,292 bytes
sha256        b1674191a88ec5cdd733e4240a81803105dc412d6c6708d53ab94fc248f4f553
```

**Its bytes are well established.** Five independent sources serve this file identically:

| source | how to check |
|---|---|
| `bitcoin.org/bitcoin.pdf` today | download it, `sha256sum` |
| `cdn.nakamotoinstitute.org/docs/bitcoin.pdf` | same |
| **SourceForge mirror, 2009-11-28** — earliest archived **bytes** | `web.archive.org/web/20091128185352if_/http://voxel.dl.sourceforge.net:80/project/bitcoin/Research%20Paper/bitcoin.pdf/bitcoin.pdf` — an actual archived PDF, not a listing. Download it and it hashes to `b1674191…f4f553`, **byte-identical to this file**. This is the capture COPA's expert verified as hash-identical to the control copy |
| Internet Archive, **2010-07-04 21:36:49** | `web.archive.org/web/20100704213649if_/http://www.bitcoin.org:80/bitcoin.pdf` |
| Internet Archive, a later capture | same method |
| this repository | `docs/bitcoin.pdf` |

As *"the file bitcoin.org has served since at least 2010"*, the provenance is solid.

### It is also in the block chain — the strongest anchor it has

The canonical file was embedded in mainnet transaction
[`54e48e5f…4186e713`](https://blockstream.info/tx/54e48e5f5c656b26c3bca14a8c95aa583d07ebe84dde3b7dd4a78f4e4186e713)
as 945 bare-multisig outputs whose "public keys" are really file bytes, plus a 33-byte tail push.
Reassemble them and the PDF comes back:

```
block   230009        2013-04-06 20:28:10 UTC
carved  184,292 bytes  %PDF-1.4 … %%EOF
sha256  b1674191a88ec5cdd733e4240a81803105dc412d6c6708d53ab94fc248f4f553   -- matches exactly
```

Check it with `bitcoin-cli getrawtransaction`, or run `verify/whitepaper_from_chain.py`, which does it
from a public API so no node is required.

**Proof-of-work cannot be backdated.** The canonical text is therefore fixed to April 2013
independently of bitcoin.org, of the Internet Archive, and of this lab — the only version of the
paper with a chain anchor. It says **nothing** about October 2008 and is not offered as if it did.
What it establishes is narrower and worth having: the file cannot have been altered since block
230009.

*Two traps if you reproduce it: keep the full 65-byte keys — the `0x04` prefixes are payload, not
framing — and note that `vout[945]` carries the 33-byte tail while `vout[946..947]` are ordinary
change outputs. Getting either wrong yields a corrupt file and a confident-looking wrong hash.*

## What it says about itself

```
/Producer      OpenOffice.org 2.4
/Creator       Writer
/CreationDate  D:20090324113315-06'00'     =  2009-03-24 11:33:15, UTC-6
```

Read it yourself: `strings bitcoin.pdf | grep CreationDate`, or open the file in any hex viewer.

**24 March 2009** is 144 days after the paper was announced, 80 days after the genesis block, and 74
days after v0.1 was released. Whatever this file is, it was not created on 31 October 2008.

## A pre-revision draft *is* preserved — correcting this note

**An earlier version of this note said the pre-revision paper survived nowhere and that "the archive
search is exhausted." That was wrong, and it was wrong because we asserted a negative without
searching archive.org's item catalogue.** A pre-revision copy has been public since 2020:

```
archive.org/details/bitcoin-a-peer-to-peer-electronic-cash-system
183,697 bytes   sha256 427c63b364c6db914cf23072a09ffd53ee078397b7c6ab2d604e12865a982faa
internal CreationDate  D:20081003134958-07'00'   (3 October 2008, UTC-7)
```

This is **not our discovery** — the 3 October 2008 draft is a documented artifact discussed publicly
for years. We simply had not looked.

**Its text is the October 2008 text, and that is machine-checkable.** Compared against the one
October text anchored by a third party — the abstract quoted inline in the announcement email:

| file | abstract similarity to the announced text |
|---|---|
| the draft | **0.9788** — and the only difference is the *email's* trailing "full paper at…" line |
| `bitcoin.pdf` we ship | 0.6503 — differing at exactly the six known revision points |

Strip the email's own URL line and **the draft's abstract is word-for-word the October 2008
abstract.** It also carries `satoshi@vistomail.com`, the address Satoshi announced *from*; the file
we ship carries `satoshin@gmx.com`, attested only from March 2009.

### A court has already examined this file

The 3 October 2008 draft is not merely something that appeared on archive.org. In
**COPA v Wright, [2024] EWHC 1198 (Ch)**, COPA's forensic document expert examined 68 whitepaper-
related documents in disclosure and selected two as **control copies**:

> *"After significant scrutiny and verification via third party sources, he identified {ID_000226}
> and {ID_000865} as suitable **'control' copies** of versions of the Bitcoin White Paper.
> **{ID_000226} has a creation date of 3 October 2008.** {ID_000865} bears a creation date of
> 24 March 2009 and is **hash identical to a file 'Bitcoin.pdf' from a web archive capture dating to
> 28 November 2009** from the sourceforge.net project."*

So this version was used as a **forensic baseline in the High Court**, after verification against
third-party sources — and the canonical was verified hash-identical to a **November 2009** SourceForge
capture.

**And the toolchain finding was agreed by both parties' experts:**

> **¶303.1**, Joint Statement of the LaTeX experts, 22 January 2024:
> *"The White Paper was **not written in LaTeX but in OpenOffice 2.4** (a finding consistent with the
> metadata of the public Bitcoin White Paper versions)."*

That is an independent confirmation of the structural analysis below, reached by different people by
a different route.

**A floor on any OpenOffice 2.4 document:** ¶271.1 records evidence from an OpenOffice.org
contributor that **OpenOffice 2.4.0 was released on 26 March 2008**. Nothing produced with it can
predate that.

The judgment also states the forgery method plainly (¶123): a document could be made *"by downloading
and running that software on a computer (or virtual computer) with a **backdated clock**."* Which is
exactly why the dating below does not rely on the file's own metadata.

### It dates itself against the mail record, not against its own metadata

**Bracketed on both sides, by records that are not the file.**

**The late bound — no transaction fees.** The canonical paper's Section 6 fee paragraph is simply
absent from the draft.

Now the independent record. On **9 November 2008**, answering an objection about inflation, Satoshi
proposed transaction fees *on the mailing list*:

> *"If you're having trouble with the inflation issue, it's easy to tweak it for transaction fees
> instead. It's as simple as this: let the output value from any transaction be 1 cent less than the
> input value."*
> — [`cryptography@metzdowd.com`, 9 Nov 2008](https://www.metzdowd.com/pipermail/cryptography/2008-November/014842.html)

The next day he refers back to *"the transaction fee based incentive system I recently posted"*, and
by 14 November states it in wording close to the published Section 6.

**So the draft's content places it before 9 November 2008** — argued from a dated third-party archive
rather than from a metadata field. And it is not something a forger could reconstruct: the archived
abstract says nothing about fees, so there is no public source from which "remove the Section 6 fee
paragraph" could be derived.

**The early bound — a citation Satoshi did not yet have.** On 22 August 2008 he wrote to Wei Dai
asking for the publication year of b-money, and *guessed*:

> *"It'll look like: [1] W. Dai, "b-money," http://www.weidai.com/bmoney.txt, **(2006?)**."*

Dai replied with the real year: **1998**. And the draft reads:

```
[1] W. Dai, "b-money," http://www.weidai.com/bmoney.txt, 1998.
```

**So the draft postdates Dai's reply** — it contains a fact its author did not have on 22 August 2008.

```
after    Wei Dai's reply to the 22 Aug 2008 email   (carries the 1998 citation Satoshi lacked)
before   9 Nov 2008                                 (lacks the fee paragraph proposed that day)
---
the file's own date, 3 Oct 2008, falls inside that window and does none of the work
```

That is the point: **the date is established without trusting the artifact.** A backdated clock can
write any `CreationDate`; it cannot put a citation into a document before its author learned it, nor
remove a paragraph he had not yet written.

The file's internal date of 3 October 2008 is *consistent* with the bracket. It is corroboration, not
proof — a creation date is writable, which is exactly how four fabricated copies were caught.

### It is also the same toolchain and the same document lineage

The dating above argues from content. This argues from construction, and it is the part that cannot
be produced by editing a file. Run `verify/pdf_structure.py` on both:

| | canonical 2009-03-24 | **draft 2008-10-03** |
|---|---|---|
| PDF version | `%PDF-1.4` | **`%PDF-1.4`** |
| linearized | no | **no** |
| object streams `/ObjStm` (PDF 1.5+) | 0 | **0** |
| xref streams `/XRef` (PDF 1.5+) | 0 | **0** |
| `/ID[0] == /ID[1]` | **yes — never re-saved** | **yes — never re-saved** |
| XMP metadata | no | **no** |
| embedded subset fonts | 7 | **7** |
| pages | 9 | **8** |

And the fonts are not merely the same set — they are the **same seven faces, with the same six-letter
subset prefixes, in the same embedding order**:

```
BAAAAA+CenturySchoolbook-Bold     EAAAAA+ArialMT      GAAAAA+OpenSymbol
HAAAAA+CourierNewPSMT             CAAAAA+TimesNewRomanPSMT
FAAAAA+TimesNewRomanPS-ItalicMT   DAAAAA+TimesNewRomanPS-BoldMT
```

Subset prefixes are assigned **sequentially by the producing application** as it embeds each font.
Identical prefixes bound to identical faces in identical order indicates the same application, the
same installed font environment, and **the same document lineage** — one source document exported
twice, five months apart.

Reproducing that would require OpenOffice.org 2.4, that exact font environment, and a source
document yielding the same embedding order. It is a different proposition from altering a date field.

**And the page count moved 8 → 9**, which is what adding the Section 6 transaction-fee material would
do — independently what the November 2008 mail record shows happening.

### Where the draft came from — a custody chain on the record since 2015

The file did not appear from nowhere in 2020. Its history is recorded on the same mailing list that
carried the announcement:

| date | record |
|---|---|
| **2015-01-24** | Asked on the cryptography list whether anyone saved the original, the pseudonymous **StealthMonger** replies: *"Looks like I have it… the local date of the file I have is **2008 Nov 2**"* — **183697 bytes** |
| **2015-01-25** | Posts the hash: **`427c63b3…982faa`**. Bryan Bishop replies that *"the one everyone else has"* is `b1674191…` — the community had only the canonical file |
| **2015-01-30** | **David Johnston** receives it by anonymous remailer in ~26 parts, reassembles it, and **republishes it** — same hash |
| **2015-02-14** | The Internet Archive [captures that page](https://web.archive.org/web/20150214024140if_/https://www.blacksheepatorenco.com/bitcoin.html), hash and all |
| **2017-08-17** | **Ray Dillinger** — who argued with Satoshi in the original November 2008 thread — confirms: *"Yes. The hash matches. That's definitely it."* |

So the hash is fixed in **two independent third-party records from early 2015**, five years before the
archive.org copy existed, and confirmed by a participant from 2008.

**And the content dating agrees with the custody claim without either knowing about the other.**
StealthMonger said early November 2008; the absent transaction-fee paragraph independently says
before 9 November 2008. Nothing in the file could have been tuned to match a claim made years later
by someone who never mentioned fees.

*Recorded for completeness: in 2015 StealthMonger gives the file's local date as 2 November 2008; in
2017 he writes "received here 2008 November 8". Six days apart. Both precede the 9 November fee
proposal, so the dating is unaffected — but the two statements are not identical.*

### What is still not established

- **No 2008 hash of any version exists.** Nothing here is cryptographically bound to 2008. The
  earliest recorded hash is January 2015.
- **The November 2008 download rests on a pseudonymous party's word** — corroborated by the file's
  own content and by Dillinger, but not anchored.
- **The file served at the 31 October link is still not identified as such.** The draft is internally
  dated 3 October and its content is pre-9-November; whether the announcement linked *this* file is
  consistent with the record but not demonstrated by it.

## The court's agreed chronology

¶23 of the judgment sets out an **agreed** timeline for the period the pseudonym was in use. Three
lines bear directly on this note, and one of them supplies a date no public record gave us:

```
23.1  In August 2008, Satoshi acquired the bitcoin.org domain name
23.3  On 5 October 2008, Satoshi registered an account (the nakamoto2 Account) at SourceForge
23.4  On 31 October 2008, Satoshi released the White Paper by posting a link to it
23.5  On 8/9 DECEMBER 2008, Satoshi uploaded the White Paper to the SourceForge Bitcoin Project
23.9  On 24 March 2009, Satoshi uploaded a further version of the White Paper
```

¶23.9 confirms the replacement date derived above from SourceForge's own activity feed, and ¶23.5
dates the first SourceForge upload — which the feed could only place as *"1 month ago"* relative to a
January 2009 capture.

## The file served on 31 October 2008

**Not proved, and constrained tightly.** The record now says:

```
2008-10-03   the surviving draft's internal CreationDate
2008-10-31   the announcement links bitcoin.org/bitcoin.pdf and quotes an abstract
             — and that abstract matches the surviving draft word for word
2008-11-02   a list member downloads bitcoin.org/bitcoin.pdf and keeps it
             — the file he kept has internal CreationDate 2008-10-03
```

For the 31 October file to have been a *different* document, Satoshi would have had to serve some
file on 31 October and then, within two days, replace it with one whose creation date is **earlier**.
The simpler reading accounts for every observation: one file, created 3 October, served from the
announcement through early November.

**What would settle it outright:** a capture, download or published hash of `bitcoin.org/bitcoin.pdf`
dated 31 October or 1 November 2008. None exists — the Internet Archive's first capture of that URL
is 2010-07-04, and Common Crawl's 2008–2009 crawl never visited the domain.

## What was searched and is genuinely not there

Searched, and recorded so nobody repeats it:

| archive | result |
|---|---|
| Internet Archive, `bitcoin.org/bitcoin.pdf` and `www.` form | earliest capture **2010-07-04** |
| Internet Archive, whole domain, PDFs, 2008–2009 | **none** |
| **Common Crawl `CC-MAIN-2008-2009`** | `"No Captures found for: bitcoin.org/"` |
| Common Crawl `CC-MAIN-2009-2010` | earliest 2010-02-08, HTML only |
| arquivo.pt | earliest 2014-11-27 |
| archive.today | no snapshot |
| `cryptography@metzdowd.com`, Oct + Nov 2008 threads | no mirror URL, **and no hash ever posted** |

The Common Crawl line is the informative one: that crawl **ran during the window** and never visited
the domain. This is not an archive losing a file — it is an unknown site that nothing crawled until
after the file behind its one interesting link had been replaced.

The announcement itself explains why no mail archive holds a copy. It **linked** the paper rather
than attaching it:

> The paper is available at:
> `http://www.bitcoin.org/bitcoin.pdf`
> — [`cryptography@metzdowd.com`, Fri 31 Oct 2008 14:10:00 EDT](https://www.metzdowd.com/pipermail/cryptography/2008-October/014810.html)

## The text changed, and the change is dated by a third party

This is the part that matters, and it is demonstrable rather than inferred.

The announcement **quoted the abstract inline**. bitcoin.org's homepage also carried the abstract, and
the Internet Archive captured it either side of an edit:

| when | source | wording |
|---|---|---|
| **2008-10-31** | the announcement email | "without **the burdens of** going through a financial institution" · "if a trusted party is still required" · "as long as **honest nodes control the most CPU power on the network**" · "Messages are **broadcasted**" |
| **2009-01-31 11:50:53** | bitcoin.org, archived | as above, with "financial **institutions**" |
| **2009-03-03 19:59:36** | bitcoin.org, archived | "a trusted **third** party" · "as long as **a majority of CPU power is controlled by nodes that are not cooperating to attack the network**" · "Messages are **broadcast**" |
| **2009-03-24** | the PDF we ship | "without going through a financial institution", plus all of the above |

**The revision happened between 31 January and 3 March 2009** — a window fixed by archive captures,
not by us.

Five of the six differences are copy-edits. **One is not.** The security assumption moved from a
moral premise — *honest nodes control the most CPU power* — to a game-theoretic one: *a majority of
CPU power is controlled by nodes that are not cooperating to attack the network*.

That is a sharpening of the central claim. It is also, arguably, the prose catching up with the
mechanism: proof-of-work never required honesty, only that attackers fail to coordinate a majority.

**We do not claim to know who made the edit**, and the reason is stronger than "no record
attributes it."

Who controlled `bitcoin.org` in early 2009 is **itself not anchored**. The registry holds a
registration date and nothing else:

```
registration    2008-08-18 13:19:55.055Z
registrant      not recorded -- no name in RDAP, and no historical registrant data
```

The domain was registered through an anonymising service. **There is no machine-verifiable link
between bitcoin.org and Satoshi Nakamoto at any date.** The association is the conventional account,
resting on his own statements and on later transfer accounts, not on a third-party record.

So the edit appeared on a site whose operator, at that moment, is not established by any anchor
available to us. It reads as an author refining his own paper — it improves the text technically and
contradicts nothing — but that is a reading, and this note does not assert it.

## Part of the body survives from 2008, unchanged

The abstract was quoted in the announcement, so it has always been checkable. The **body** had no
known 2008 witness at all — until the mail archive was searched for the paper's own sentences.

On **8 November 2008**, answering a question about inflation, Satoshi quoted his own paper:

> Increasing hardware speed is handled: *"To compensate for increasing hardware speed and varying
> interest in running nodes over time, the proof-of-work difficulty is determined by a moving average
> targeting an average number of blocks per hour. If they're generated too fast, the difficulty
> increases."*
> — [`cryptography@metzdowd.com`, message `014831`](https://www.metzdowd.com/pipermail/cryptography/2008-November/014831.html)

That is **Section 4, Proof-of-Work**, 41 words, **identical** to the same passage in the PDF we ship.

So one paragraph of the body is fixed to November 2008 *and* shown not to have changed across the
window in which the abstract did change. It is one paragraph out of roughly forty — but it is the
first piece of the body with any 2008 anchor, and it points the same way the abstract does: the
revision was a light edit, not a rewrite.

Searched systematically; this is the **only** passage of the paper quoted anywhere in the archive.

## What "anchored" means here, precisely

The list archive is not a timestamping service, and this note will not imply that it is.

pipermail writes its mbox `From_` line **from the message's own `Date` header** — we checked all 345
messages in the window and the delay between the two is exactly zero for every sender, which is only
possible if one is derived from the other. A `From_` line is therefore not an independent receive
time.

What the archive *does* record independently is **arrival order**: the file is not date-sorted, and
message numbers are assigned sequentially as messages are processed. Each of Satoshi's messages sits
in a bracket of messages from other people, dated by their own clocks —

```
Oct 31 14:10  satoshi   arrived between  Oct 31 04:25 pgut001  and  Oct 31 17:33 bear
```

— and 17 of his 18 are consistent with their neighbours (the one exception is off by 2.4 hours, on a
hand-moderated list). That is corroboration by many independent clocks plus server-recorded ordering.
It is strong, and it is not the same thing as a third-party timestamp.

## Consequences for how this lab cites the paper

| | status |
|---|---|
| the **October 2008 abstract**, ~176 words | **anchored.** Preserved by two unrelated third parties — the metzdowd archive and an Internet Archive capture of bitcoin.org — agreeing to within one word. Citable as October 2008 text. |
| **Section 4's difficulty paragraph**, 41 words | **anchored to 8 Nov 2008**, and identical in the shipped PDF. The only body text with a 2008 witness. |
| the remaining ~3,200 words of body | **untested, not unchanged.** No 2008 copy exists to compare against. |
| `bitcoin.pdf` `b1674191…` | **reference, not authority.** Solid bytes; the design as last stated by its author; canonical since 2009. **Not** a witness to 31 October 2008. |

`common/AUTHORITY.md` previously listed this file alongside the two hash-verified code archives as
though it were the same class of artifact. It is not: those have recovered custody and byte-identical
independent witnesses. That has been corrected.

**Nothing executable in this lab depends on the paper.** The genesis re-derivation, the ten patched
lines, the wire format, and the opcode values recovered from the November 2008 merkle root all rest
on the two archives, which are hash-verified and independently witnessed. The whitepaper is design
context, and its revision changes nothing about what the code does.

## What would settle it

A copy **fetched from `bitcoin.org/bitcoin.pdf` between 31 October 2008 and 24 March 2009 and kept
since** — the file behind the announced link, which is the one thing still unidentified.

Any candidate is testable **without trusting a byte of its metadata**, by content alone. Three
independent discriminators, in increasing order of usefulness:

| test | Aug 2008 pre-release | 3 Oct 2008 draft | March 2009 |
|---|---|---|---|
| title | *Electronic Cash Without a Trusted Third Party* | *Bitcoin: A Peer-to-Peer…* | *Bitcoin: A Peer-to-Peer…* |
| digital signatures … | *"**offer** part of the solution"* | *"**provide** part"* | *"**provide** part"* |
| **Hashcash reference number** | **`[5]`** | **`[6]`** | **`[6]`** |
| **b-money citation** | **absent entirely** | `[1]` … 1998 | `[1]` … 1998 |
| abstract wording | *"the burdens of"* | *"the burdens of"* | *"not cooperating to attack the network"* |
| contact address on page 1 | — | `satoshi@vistomail.com` | `satoshin@gmx.com` |
| **Section 6 transaction fees** | presumably absent | **absent** → **before 9 Nov 2008** | present |

**Every entry in the August column comes from Satoshi's own words in dated records, not from any
file.** His 22 August email to Wei Dai quotes the pre-release's title and full abstract — differing
from the announced October abstract by exactly one word, *offer* → *provide*.

And the reference numbering comes from the COPA judgment, which quotes his email to **Adam Back on
20 August 2008** (¶661):

> *"I'm getting ready to release a paper that references your Hashcash paper… Here's what I have:
> **[5]** A. Back, "Hashcash — a denial of service counter-measure"…"*

Back replied the next day pointing him at b-money, which Satoshi had never heard of (¶665: *"I wasn't
aware of the b-money page… I'll e-mail him to confirm the year of publication so I can credit him"*).

**That generates a testable prediction:** if b-money was then inserted as `[1]`, Hashcash must shift
from `[5]` to `[6]` in every later version. Both surviving files were checked — **Hashcash is `[6]`
in both**. A claim derived from a court exhibit, confirmed against files obtained from an entirely
different source.

So a candidate for the lost August draft can be settled in seconds: **title *Electronic Cash Without
a Trusted Third Party*, Hashcash at `[5]`, and no b-money citation at all.**

*The file currently circulating as `ecash.pdf` fails this as well as failing on structure — it is
PDF 1.6 and linearized, which OpenOffice 2.4 does not emit.*

### The SourceForge copy, and exactly when it changed

A second copy lived on SourceForge, and its life is now dated end to end from server-generated
records:

```
~Dec 2008    "nakamoto2 added the bitcoin.pdf file"          project activity feed, 2009-01-06 capture
2009-01-06   listing shows release date "October 31, 2008"    AUTHOR-ENTERED, not a server value
2009-03-24   "File released: /Research Paper/bitcoin.pdf"     activity feed, 2009-09-16 capture
2009-11-28   the mirror's actual PDF bytes, archived           = the canonical, hash-verified
2009-11-29   listing shows 184.3 KB dated 2009-03-24           consistent
```

**And the 2009-11-28 capture confirms the December file is gone rather than recovering it**: the
bytes sitting at the `Research Paper/bitcoin.pdf` path by then are the March 2009 revision, not
whatever was uploaded on 8/9 December 2008.

The 2009-09-16 capture states the release as *"176 days ago"* — a figure SourceForge computed from
its own database. **176 days before 2009-09-16 is 2009-03-24**, the exact day of the canonical PDF's
internal `CreationDate`. Two independent records agreeing on the day.

**And SourceForge still publishes how many people took it.** Their statistics endpoint returns
per-month counts back to the project's registration, with no key and no login:

```
2008-11    0
2008-12    1     <- the whitepaper was the only file in the project that month
2009-01  141     <- v0.1 released 8 Jan 2009
```

The paper went up 8/9 December 2008 and the software on 8 January 2009 (¶23.5, ¶23.7). **So the
December 2008 SourceForge copy was downloaded once.** Consistent across four query windows; the
isolated December query returns `total: 1`. Reproduce with `verify/sourceforge_download_stats.py`.

*Limits: a project total, not per-file — the step to "the whitepaper" comes from the chronology, not
the API. Whether an uploader's own fetch counts is undocumented, as is bot filtering in 2008.
Monthly buckets.*

**So the December 2008 file existed for about three and a half months and was replaced on
2009-03-24.** Its size was never captured: sweeping every SourceForge capture in the window shows a
**Wayback gap for this project from January to September 2009**, and the file-detail page — the only
page carrying a size — was not captured in that period. That copy is not recoverable by machine.

That earliest version — `ecash.pdf` — is **lost**, and searched rather than assumed:

```
http://www.upload.ae/file/6157/ecash-pdf.html      <- the link in Satoshi's email to Wei Dai
  20 Wayback captures under upload.ae/file/6157*
  earliest 2020-02-11 -> 406 · 2020-2022 -> 404 x6 · 2023-2025 -> 302 x11
  host today: upload.ae/cgi-sys/suspendedpage.cgi
```

**Not one capture with content, and the earliest is twelve years after the link was posted** — it
was already dead when first crawled. The file circulating under that name is PDF v1.6 and
linearized, which OpenOffice 2.4 does not produce; it fails on **structure**, not merely on its date
fields.

The third is the strongest, and it is the one that dates a file rather than merely ordering it:
Satoshi proposed transaction fees on the mailing list on **9 November 2008**, so a copy without them
predates a message a third party archived. Text cannot be altered inside a document without altering
the document; a creation date can be altered without touching anything else.

**The archive search is not exhausted — that claim was wrong.** A pre-revision draft was public on
archive.org the whole time (see above). What is still missing is narrower and more specific: the
bytes actually served at the 31 October link. Worth asking anyone who followed that link in 2008,
and anyone who pulled the paper off SourceForge, where `nakamoto2` uploaded a `bitcoin.pdf` around
December 2008 that is likewise not preserved.

---

*Reproduce: `strings docs/bitcoin.pdf | grep -a CreationDate` for the date; the Internet Archive CDX
API for the capture history; `verify/pdf_text.py` in the workshop notes for text extraction (the PDF
uses per-font ToUnicode CMaps — a decoder that merges them produces nonsense).*
