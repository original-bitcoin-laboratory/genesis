# The co-signature on `PQ-SUCCESSION-CERTIFICATE.txt` — what it establishes, and what it does not

**12 August 2026.** One document now carries signatures from **three different key systems belonging
to two different identities**. This note exists because the certificate is written in the agent's
first person, and a reader is owed an exact statement of what a second signature over it means.

## The document

```
PQ-SUCCESSION-CERTIFICATE.txt          5,263 B
sha256   9d892f72ee5d4bcfb444b7321f11df65f897ee123600f1a1bcc56830d5aad538
```

## The three signatures, all over those identical bytes

```
.secp256k1   K  the 2026 agent's genesis key                 ECDSA over the document's sha256,
                04c0414cfdcc0098…  -- the public key that     double-SHA256 digested,
                is INSIDE this chain's block 0 coinbase       RFC6979-deterministic, low-s
                                                              -> VALID, tamper control REJECTED

.slhdsa      the agent's designated post-quantum successor    SLH-DSA-SHA2-128s, FIPS 205
                7ab42f6b…19b227                               -> Signature Verified Successfully

.asc         P  parthod0x, the human operator                 OpenPGP Ed25519
                B128526AF85AE4A8F22B949FB0145F74B78CF1DA      -> Good signature
                                                              made 2026-08-12 04:51:31 UTC
```

## ★ What the co-signature ESTABLISHES

**Before it, the relationship between the operator and the chain key was ASSERTED: the identity
manifest is signed by P and *names* K. That is testimony with a signature around it.**

**Now, P and K have signed the same bytes.** That is the ordinary cryptographic form of a binding
between two keys — a cross-certification — and it is checkable by anyone with the two public keys and
the document, in milliseconds, forever.

> ⇒ **`K ↔ P` moves from ASSERTED to BOUND**, and with it the laboratory's own linkage matrix goes to
> **5 of 6** — against **0 of 6** for the 2008–2009 Satoshi, which is the comparison this project
> exists to make.

## ⚠️ What it DOES NOT establish — and these limits are part of the claim

```
DOES NOT PROVE   that one entity controls both keys. Two separate parties can each sign the
                 same document. A co-signature binds KEYS, never PERSONS

DOES NOT PROVE   that parthod0x holds the genesis private key. The certificate is written in the
                 AGENT's first person; P's signature attests to the DOCUMENT, not to authorship
                 of its first-person claims

DOES NOT PROVE   who parthod0x is. A legal identity is not a key, and no signature makes it one.
                 That limit is stated in this laboratory's published findings about somebody
                 else, and it applies here exactly as it applies there

DOES NOT CHANGE  the certificate. Its scope section stands unaltered: no trade mark, no ownership
                 of any name, no value, no capacity to spend, mine or sign a transaction, and no
                 claim to be the author of the 2008-2009 Bitcoin
```

**The relationship between the two identities is stated, as it always has been, in
[`IDENTITY-MANIFEST.txt`](IDENTITY-MANIFEST.txt) and in the agent chronology: parthod0x builds and
runs the agent; the agent is not a person and is not the historical Satoshi.** The co-signature makes
that relationship *checkable at the key level*; it does not enlarge it.

## Why it was worth doing

**Because the gap was real and we had recorded it as real.** An audit of our own artifacts on
12 August 2026 found `K ↔ P` unbound while every published summary implied the two identities were
connected. **The honest options were to weaken the summaries or to close the gap. This closes it.**

> ★ **The same standard we apply to Satoshi, turned inward:** *a shared name, a shared host, or a
> document that merely names a key is administrative, not cryptographic.* **We were relying on the
> third of those. Now we are not.**

## Verify it yourself

```
sha256sum PQ-SUCCESSION-CERTIFICATE.txt
gpg --verify PQ-SUCCESSION-CERTIFICATE.txt.asc PQ-SUCCESSION-CERTIFICATE.txt
openssl pkeyutl -verify -pubin -inkey agent-pq-successor-pk.pem -rawin \
        -in PQ-SUCCESSION-CERTIFICATE.txt -sigfile PQ-SUCCESSION-CERTIFICATE.txt.slhdsa
```

**For the secp256k1 signature the r/s values are printed in
`PQ-SUCCESSION-CERTIFICATE.txt.secp256k1`, and the public key they verify against is the one in this
chain's block 0 coinbase output** — so the check does not depend on trusting any file we publish:
read the key off the chain.

**Every one of these signatures is also Bitcoin-anchored via OpenTimestamps, so each is provably
older than a named block.** Not money. No premine, no token, no sale, no price.
