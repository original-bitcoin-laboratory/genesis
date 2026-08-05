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
sha256        b1674191a88ec5cdd733e4240a818031e83a5da0328e9cc0b2683bda8f0a1a4c
```

**Its bytes are well established.** Five independent sources serve this file identically:

| source | how to check |
|---|---|
| `bitcoin.org/bitcoin.pdf` today | download it, `sha256sum` |
| `cdn.nakamotoinstitute.org/docs/bitcoin.pdf` | same |
| Internet Archive, **2010-07-04 21:36:49** | `web.archive.org/web/20100704213649if_/http://www.bitcoin.org:80/bitcoin.pdf` |
| Internet Archive, a later capture | same method |
| this repository | `docs/bitcoin.pdf` |

As *"the file bitcoin.org has served since at least 2010"*, the provenance is solid.

## What it says about itself

```
/Producer      OpenOffice.org 2.4
/Creator       Writer
/CreationDate  D:20090324113315-06'00'     =  2009-03-24 11:33:15, UTC-6
```

Read it yourself: `strings bitcoin.pdf | grep CreationDate`, or open the file in any hex viewer.

**24 March 2009** is 144 days after the paper was announced, 80 days after the genesis block, and 74
days after v0.1 was released. Whatever this file is, it was not created on 31 October 2008.

## The October 2008 file is not preserved

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

A copy fetched between **31 October 2008 and 24 March 2009** and kept since.

It would be identifiable **without trusting a byte of its metadata**, by the text alone:

- contains *"the burdens of"* and *"honest nodes control the most CPU power"* → **pre-revision**
- contains *"not cooperating to attack the network"* → **March 2009 or later**

That test is stronger than any timestamp such a file could carry, because text cannot be altered
inside a document without altering the document, whereas a creation date can be altered without
touching anything else.

The archive search is exhausted. What remains is a person's old drive.

---

*Reproduce: `strings docs/bitcoin.pdf | grep -a CreationDate` for the date; the Internet Archive CDX
API for the capture history; `verify/pdf_text.py` in the workshop notes for text extraction (the PDF
uses per-font ToUnicode CMaps — a decoder that merges them produces nonsense).*
