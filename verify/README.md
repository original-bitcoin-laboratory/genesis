# verify/ — check the whitepaper claims yourself

Four scripts. Between them they reproduce every claim this lab makes about `docs/bitcoin.pdf` and its
earlier versions, from public sources, with no API key and no trust in us.

Python 3.9+, standard library only.

```bash
python verify/whitepaper_from_chain.py  out.pdf          # carve the paper out of the block chain
python verify/pdf_text.py               docs/bitcoin.pdf out.txt
python verify/whitepaper_body_in_mail.py  <mbox-dir> <pdf>   # which of the paper survives in 2008 mail
python verify/whitepaper_quoted_passages.py <mbox-dir> <pdf>
```

The two mail scripts need a directory of gzipped monthly mboxes from
`metzdowd.com/pipermail/cryptography/`. A collector is published alongside the sister project at
[satoshi-onchain `verify/metzdowd_backup.py`](https://github.com/satoshi-onchain/satoshi-onchain/blob/main/verify/metzdowd_backup.py).

---

## `whitepaper_from_chain.py` — the strongest anchor the paper has

The canonical file is embedded in mainnet transaction
`54e48e5f5c656b26c3bca14a8c95aa583d07ebe84dde3b7dd4a78f4e4186e713` as 945 bare-multisig outputs whose
"public keys" are really file bytes, plus a 33-byte tail push. The script reassembles and hashes it:

```
block   230009        2013-04-06 20:28:10 UTC
carved  184,292 bytes  %PDF-1.4 … %%EOF
sha256  b1674191a88ec5cdd733e4240a81803105dc412d6c6708d53ab94fc248f4f553   -- matches docs/bitcoin.pdf
```

Exits non-zero if the hash does not match. Uses a public API so no node is needed; the same thing
works with `bitcoin-cli getrawtransaction`.

**Establishes:** proof-of-work cannot be backdated, so the canonical text is fixed to April 2013
independently of bitcoin.org, of the Internet Archive, and of this lab.
**Does not establish:** anything about October 2008.

*Two traps: keep the full 65-byte keys — the `0x04` prefixes are payload, not framing, and stripping
them loses ~2.8 KB while still producing a confident-looking hash. And `vout[945]` carries the
33-byte tail while `vout[946..947]` are ordinary P2PKH change, not data.*

## `whitepaper_body_in_mail.py` — how much of the paper is anchored to 2008

Word-shingle intersection between the PDF and every message in the archive, extending matches to
maximal runs, tracking quoted lines separately.

The abstract has always been checkable — it was quoted inline in the announcement. The **body** had
no known 2008 witness until the archive was searched for the paper's own sentences. It found one: on
**8 November 2008**, answering Ray Dillinger on inflation, Satoshi quoted his own Section 4:

> *"To compensate for increasing hardware speed and varying interest in running nodes over time, the
> proof-of-work difficulty is determined by a moving average targeting an average number of blocks
> per hour. If they're generated too fast, the difficulty increases."*

41 words, identical to the shipped PDF, and the **only** passage of the paper quoted anywhere in the
archive.

**Read the output carefully.** Short runs are not evidence: two 8-word hits fall inside Satoshi's own
prose rather than inside quotation marks, and an 8-word collision is expected when the same author
describes the same mechanism twice. The script reports them; counting them would inflate the result.

## `whitepaper_quoted_passages.py` — the same test, from the other direction

Extracts passages Satoshi puts in quotation marks and tests each against the PDF, reporting matches
*and* mismatches — a mismatch would locate a body revision.

*A naive `"([^"]+)"` pairs the closing quote of one thing with the opening quote of the next,
swallowing whole paragraphs plus the mailing-list footer and reporting them as near-misses. The
script guards against that; a few visibly bogus spans still survive and are left visible rather than
filtered into a cleaner-looking answer.*

## `pdf_text.py` — text extraction that actually works on this file

The whitepaper uses **per-font `ToUnicode` CMaps**. The obvious approach — merge every CMap into one
dict — fails, because subset fonts reuse glyph IDs 1,2,3… independently. Merging makes them collide
and the output is a substitution cipher: `"purely"` decodes as `"ranTBl"`. This resolves `/Font`
resources to their `ToUnicode` object and follows `/Tf` switches through the content stream, decoding
each run with the right table.

---

## What these do not establish

**No 2008 cryptographic timestamp exists for any version of the paper.** The earliest recorded hash
of the pre-revision draft is January 2015. Dating earlier than that is done by *content correlation
with dated third-party records* — a real method, and a different class from proof. See
[`docs/WHITEPAPER_PROVENANCE.md`](../docs/WHITEPAPER_PROVENANCE.md) for exactly what is and is not
anchored.

**Nothing executable in this lab depends on the paper.** The genesis re-derivation, the patched lines,
the wire format and the opcode values all rest on the two hash-verified code archives.
