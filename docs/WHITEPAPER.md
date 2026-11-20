# The whitepaper — identified here, not hosted here

**This laboratory no longer serves copies of the Bitcoin whitepaper.** It publishes the facts that
identify each version, and the tools to obtain and verify one yourself.

**That is a deliberate position, not an omission**, and it is the same standard this project applies
to every other document:

> **A SHA-256 is not a reproduction.** We publish findings *about* documents — hashes, sizes, page
> counts, metadata, provenance, searched negatives — and we point at sources other people published.

The whitepaper carries **no licence and no copyright notice**, and its author has not been
identified. This laboratory does not redistribute it; it identifies it by hash and points at copies others publish.
**Serving a copy of a work whose owner we cannot name, while telling everyone else that a hash beats
a copy, was the weaker position.** So we stopped.

---

## Get the canonical version from the block chain

**The 24 March 2009 whitepaper is embedded in the 2009 Bitcoin block chain, where no host can withdraw it.**
Carve it out and hash it:

```bash
python verify/whitepaper_from_chain.py out.pdf
sha256sum out.pdf     # b1674191a88ec5cdd733e4240a81803105dc412d6c6708d53ab94fc248f4f553
```

That reads the data from **block 230009**, reassembles the file, and gives you the authentic bytes —
**from a public API's copy of the chain, checked against the published digest.** It is a better source than any
website, including this one, because the bytes have not changed since block 230009 and a changed copy fails the digest.

## The versions, by hash

```
CANONICAL      24 Mar 2009   184,292 B   9 pages
  sha256  b1674191a88ec5cdd733e4240a81803105dc412d6c6708d53ab94fc248f4f553
  md5     d56d71ecadf2137be09d8b1d35c6c042      <- matches SourceForge's own published md5
  satoshin@gmx.com · "without going through a financial institution" · "provide part of the solution"

PRE-RELEASE    3 Oct 2008    183,697 B   8 pages
  sha256  427c63b364c6db914cf23072a09ffd53ee078397b7c6ab2d604e12865a982faa
  satoshi@vistomail.com · "without the burdens of" · /CreationDate D:20081003134958-07'00'
  A control copy in COPA v Wright. Published by gwern at
  https://gwern.net/doc/bitcoin/20081003-nakamoto-bitcoindraft.pdf

A JANUARY 2009 DOWNLOAD — IN THE COURT RECORD, NOT IN PUBLIC HANDS
  The judgment in COPA v Wright [2024] EWHC 1198 (Ch) records (¶271.9) that Nicholas Bohm, who died shortly before the trial began, provided
  a version he downloaded in January 2009, authenticated in evidence (¶271.9) and used as a control
  copy. Its hashes and text are not published by the court or the parties and are not reproduced here.
```

**Hash any copy you have and look it up.** If it matches nothing above, it is not one of the
documents this project has identified — and that is worth investigating, not assuming.

## Court material

This project cites the published judgment by paragraph and nothing else from the proceedings. The
expert appendices and the exhibits it refers to are not published by the court or the parties, and this
project does not reproduce, re-host or rely on copies of them in circulation. A party, COPA, published
some witness statements and expert reports; this project does not draw on them either, so that each
statement here can be checked against the judgment alone. Until 14 September 2026 this note carried the
court-record version's hashes and three sentences of its text from an expert appendix; that material was
removed.

*Corrected 21 Nov 2026.* This section previously said that the witness statements the judgment refers to were not published by the court or the parties, and the January 2009 version's date was listed as unpublished. COPA published Mr Bohm's witness statement, which gives that version's download date and the creation date in its metadata (¶19; [archived copy](https://web.archive.org/web/20240519201158/https://bitcoindefense.org/wp-content/uploads/2024/03/Witness-Statement-of-Nicholas-Bohm.pdf)).

---

**Full version-by-version record:** [bitcoinwhitepaper.online](https://bitcoinwhitepaper.online) —
which hosts no PDF either, for the same reason.

---

*Experimental laboratory research, in progress: what re-runnable methods find, and no conclusion beyond that. Not money — no premine, no sale, no value assigned, no token. Not financial advice. No warranty. [Rights, sourcing and corrections](https://github.com/original-bitcoin-laboratory/genesis/blob/main/RIGHTS.md).*
