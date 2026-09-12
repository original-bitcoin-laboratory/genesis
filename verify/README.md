# verify/ — check this lab's claims yourself

Two groups of scripts, and between them they let you re-derive what this lab asserts without
trusting us: the **whitepaper** claims about the canonical PDF (sha256 `b1674191…`; carve it from the chain with `whitepaper_from_chain.py`, or fetch it from bitcoin.org), and the **signatures** over the
documents and releases.

Python 3.9+, standard library only. No API key, no network for the signature checks.

```bash
python verify/whitepaper_from_chain.py  out.pdf          # carve the paper out of the block chain
python verify/pdf_text.py               out.pdf out.txt
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
sha256  b1674191a88ec5cdd733e4240a81803105dc412d6c6708d53ab94fc248f4f553   -- matches the canonical PDF
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
**8 November 2008**, answering Ray Dillinger on inflation, Satoshi quoted their own Section 4:

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

## `verify_slhdsa.py` — the post-quantum signature, without OpenSSL

Every release manifest and several protocol documents in `docs/` carry a **second** signature under
**SLH-DSA-SHA2-128s** (FIPS 205), beside the OpenPGP one. The reason is stated in
[`docs/PQ-COUNTERSIGNING.md`](../docs/PQ-COUNTERSIGNING.md): elliptic-curve signatures do not
survive a cryptographically relevant quantum computer, and SHA-256 does. So the post-quantum
signature is the one intended to still mean something long after the other kind stops meaning
anything.

⛔ **The published way to check it needed OpenSSL 3.5 or later** — a specific version of one
program, standing behind the signature whose whole purpose is to outlast the software around it.
This script removes that dependency:

```bash
python verify/verify_slhdsa.py docs/agent-pq-successor-pk.pem \
                               docs/PQ-SUCCESSION-CERTIFICATE.txt \
                               docs/PQ-SUCCESSION-CERTIFICATE.txt.slhdsa
```

**Pure Python, `hashlib` only.** No OpenSSL, no build step, no package, no network. It runs from a
bare directory containing the script, a public key, a signed file and its signature.

### Check the checker

```bash
python verify/verify_slhdsa.py --selftest --corpus docs
```

Every SLH-DSA signature in `docs/` must verify under exactly one of the public keys there, every
other key must refuse it, and eight deliberate mutations must all be rejected — including the bare
message *without* the FIPS 205 context prefix, which is what proves the domain separator is
load-bearing rather than decorative.

```bash
python verify/verify_slhdsa.py --crosscheck --corpus docs     # if you have OpenSSL 3.5+
```

Runs both implementations over the same inputs and requires them to agree on **every** verdict,
accepts and rejects alike. Agreement on accepts alone would be satisfied by two permissive
implementations, which is why the rejects are counted too.

⚠️ **What this has not been checked against: NIST ACVP / FIPS 205 official test vectors.** They were
not available offline when it was written. The residual risk is a misreading of FIPS 205 that
OpenSSL also makes — unlikely, since the two were written independently in different languages, but
that is the gap and it is stated rather than left for a reader to discover.

⚠️ **It verifies; it never signs.** There is no signing path in the file, it needs no secret, and it
refuses a private key rather than reading one.

## What these do not establish

**No 2008 cryptographic timestamp exists for any version of the paper.** The earliest recorded hash
of the pre-revision draft is January 2015. Dating earlier than that is done by *content correlation
with dated third-party records* — a real method, and a different class from proof. See
[`docs/WHITEPAPER_PROVENANCE.md`](../docs/WHITEPAPER_PROVENANCE.md) for exactly what is and is not
anchored.

**Nothing executable in this lab depends on the paper.** The genesis re-derivation, the patched lines,
the wire format and the opcode values all rest on the two hash-verified code archives.

**A signature answers WHO, never WHEN.** `verify_slhdsa.py` tells you a key signed those bytes. It
says nothing about when, and a signature is only as good as the scheme behind it. What dates these
artifacts is the OpenTimestamps proof (`.ots`) beside each one, anchored in Bitcoin — and an anchor
made before a scheme breaks keeps its meaning after, which is the whole reason the two are kept
together.
