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

## An oddity, recorded not explained

`bitcoin-0.1.0.rar` and `bitcoin-0.1.3.rar` are listed with **the same size and the same MD5**
(`2,127,418` / `9a73e0826d…`), despite different release dates. Either the same archive was published
twice under two version labels, or SourceForge's feed associated one file with two releases. **We do
not know which**, and it is recorded here as an open observation rather than resolved.

## Limits

One capture of this endpoint exists, dated 28 November 2009. There is **no pre-March-2009 capture**,
so this does not carry a fingerprint for the December 2008 whitepaper upload — that file had already
been replaced. `download-count` is cumulative to the capture date and its counting rules are
undocumented.
