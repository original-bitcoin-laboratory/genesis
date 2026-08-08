# The whitepaper — identified here, not hosted here

**This laboratory no longer serves copies of the Bitcoin whitepaper.** It publishes the facts that
identify each version, and the tools to obtain and verify one yourself.

**That is a deliberate position, not an omission**, and it is the same standard this project applies
to every other document:

> **A SHA-256 is not a reproduction.** We publish findings *about* documents — hashes, sizes, page
> counts, metadata, provenance, searched negatives — and we point at sources other people published.

The whitepaper carries **no licence and no copyright notice**. It is not public domain and it is not
MIT. Copyright in it subsists automatically and vests in its author, who has never been identified.
**Serving a copy of a work whose owner we cannot name, while telling everyone else that a hash beats
a copy, was the weaker position.** So we stopped.

---

## Get the canonical version from the block chain

**The 24 March 2009 whitepaper is embedded in the Bitcoin block chain and cannot be taken down.**
Carve it out and hash it:

```bash
python verify/whitepaper_from_chain.py out.pdf
sha256sum out.pdf     # b1674191a88ec5cdd733e4240a81803105dc412d6c6708d53ab94fc248f4f553
```

That reads the data from **block 230009**, reassembles the file, and gives you the authentic bytes —
**from the chain itself, with nobody in between.** It is a better source than any website, including
this one, because it cannot be altered, revoked or lost.

## The versions, by hash

```
CANONICAL      24 Mar 2009   184,292 B   9 pages
  sha256  b1674191a88ec5cdd733e4240a81803105dc412d6c6708d53ab94fc248f4f553
  md5     d56d71ecadf2137be09d8b1d35c6c042      <- matches SourceForge's own published md5
  satoshin@gmx.com · "without going through a financial institution" · "provide part of the solution"

PRE-RELEASE    3 Oct 2008    183,697 B   8 pages
  sha256  427c63b364c6db914cf23072a09ffd53ee078397b7c6ab2d604e12865a982faa
  satoshi@vistomail.com · "without the burdens of" · /CreationDate D:20081003134958-07'00'
  A forensic control copy in COPA v Wright. Published by gwern at
  https://gwern.net/doc/bitcoin/20081003-nakamoto-bitcoindraft.pdf

11 NOVEMBER 2008 — NOT HELD BY ANYONE PUBLIC
  sha256  e6cc7c952c688b234f9872c3e2f50060ae6556fd27925cba503c6460048e50a9
  md5     3e5e11e1e3208d2829e887fb1c86bd05
  Larger than 182,801 bytes. Eight archives searched, all controlled — it is in none of them.
```

**Hash any copy you have and look it up.** If it matches nothing above, it is not one of the
documents this project has identified — and that is worth investigating, not assuming.

## And if you want to recognise the 11 November version by reading rather than hashing

Three sentences appear in it and in **neither** surviving public version:

```
"The incentive is also funded with transaction fees"
"The output value of every transaction is equal to the input value minus a transaction fee"
"and the incentive is increased by the total transaction fees in the block"
```

**A hash verifies; a sentence finds.** No search engine indexes a digest, and nobody can compute one
over a document they have only read.

---

**Full version-by-version record:** [bitcoinwhitepaper.online](https://bitcoinwhitepaper.online) —
which hosts no PDF either, for the same reason.
