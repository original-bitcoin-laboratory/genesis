# SourceForge's own published hashes for the earliest Bitcoin releases

A **server-published** record of what SourceForge was distributing, with MD5 and byte size written by
SourceForge's own file API — not by the author, and not by us.

Source: the Wayback Machine's capture of SourceForge's file-index RSS endpoint for project
`244765` (Bitcoin), `2009-11-28 20:30:45 UTC`. Held at
[`sourceforge-fileapi-rss_2009-11-28.xml`](sourceforge-fileapi-rss_2009-11-28.xml).

```
file                        bytes       md5                               released (SourceForge)   dls
-------------------------------------------------------------------------------------------------------
bitcoin-0.1.0.rar       2,127,418   9a73e0826d5c069091600ca295c6d224   Mon, 12 Jan 2009 20:44:25    57
bitcoin-0.1.2.rar       2,129,310   8f1231bed01a36c0a32d8763c03224f1   Sun, 11 Jan 2009 21:19:11    26
bitcoin-0.1.3.rar       2,127,418   9a73e0826d5c069091600ca295c6d224   Tue, 13 Jan 2009 16:58:39   116
bitcoin-0.1.5.rar       2,139,348   8d5c12b3b52eb03dbc9ebad08ab91816   Wed, 04 Feb 2009 17:47:07   424
bitcoin.pdf               184,292   d56d71ecadf2137be09d8b1d35c6c042   Tue, 24 Mar 2009 17:50:18    83
```

## Why this matters to the Laboratory

This Laboratory reconstructs and executes **v0.1.0 of January 2009**. Until now its provenance chain
rested on the source tree and on our own hashing. **This is SourceForge's own statement of what it
served**, recovered from a third-party archive of a machine-generated feed — an independent check on
the release the Laboratory rebuilds.

It also corroborates two figures published elsewhere in this project from unrelated routes:

- **`bitcoin.pdf` = 184,292 bytes, MD5 `d56d71ec…`** — identical to the canonical whitepaper, and to
  the MD5 a High Court expert published for the court's own control copy.
- **`pubDate 24 Mar 2009 17:50:18`** — the same instant the SourceForge mirrors report as their
  `Last-Modified`, seventeen minutes after bitcoin.org's own filesystem timestamp of `17:33:15`.
- **`download-count 83`** — the figure this project has published as the upper bound on the Research
  Paper package's lifetime downloads.

## ★ RESOLVED — this was recorded as an unexplained oddity; it is not unexplained

`bitcoin-0.1.0.rar` and `bitcoin-0.1.3.rar` are listed with **the same size and the same MD5**
(`2,127,418` / `9a73e0826d…`) despite different release dates. **An earlier version of this file said
"we do not know which". We do know, and the discriminator is inside the bytes.**

**We hold an archive matching that exact digest and size.** Its `serialize.h` declares:

```
held bitcoin-0.1.3.rar    md5 9a73e0826d…  2,127,418 B    serialize.h VERSION = 103
held bitcoin-0.1.0.rar    md5 91e2dfa2af…  2,132,686 B    serialize.h VERSION = 101
                          (the SNI archive -- and see the note below on its real label)
```

**VERSION 103 is v0.1.3's wire version; v0.1.0 and v0.1.1 carry 101.** So the bytes SourceForge
published under the **`bitcoin-0.1.0.rar`** row are **v0.1.3's code**, not v0.1.0's. The feed
associated one later file with two releases.

### ⚠️ The consequence, stated plainly

> **There is no server-published hash for the actual v0.1.0 code.** The digest published beside that
> filename belongs to different bytes, and the v0.1.0-era archive we hold matches **no** published
> hash anywhere.

**That is not a gap in the searching — it is a property of the record**, and it matters because it
removes a custodian-free link we might otherwise have assumed we had. **For v0.1.0 the only
custodian-free check is reproduction**: derive the source, rebuild, and compare the bytes you get.
That is exactly what `derivatives/build-reconstruction/` exists to make possible, and why the
laboratory anchors to reproduction rather than to a published digest.

### And a second label problem in the same neighbourhood

**The archive circulated as `bitcoin-0.1.0.rar` is v0.1.1.** Its size, 2,132,686 bytes, is precisely
the figure Satoshi states for **`bitcoin-0.1.1.rar`** in a 10 January 2009 message; its shipped
`bitcoin.exe` carries a PE `TimeDateStamp` of 2009-01-10, two days after v0.1.0 was announced. See
[`../../common/VERSION_LABEL.md`](../../common/VERSION_LABEL.md).

**Neither correction changes any consensus result** — the v0.1.0→v0.1.1 delta is confined to
`irc.cpp` and `serialize.h`, and `main.cpp` is untouched. **What changes is what may be claimed about
provenance**, which is the whole point of this file.

## Limits

One capture of this endpoint exists, dated 28 November 2009. There is **no pre-March-2009 capture**,
so this does not carry a fingerprint for the December 2008 whitepaper upload — that file had already
been replaced. `download-count` is cumulative to the capture date and its counting rules are
undocumented.
