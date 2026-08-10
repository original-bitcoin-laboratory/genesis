# Post-quantum counter-signatures

**Since v1.2.0, each release's `SHA256SUMS` carries a second signature under a post-quantum
algorithm, in addition to the OpenPGP one.** This page explains what it is for and how to check it.
**It changes nothing about the existing GPG signatures — it sits beside them.**

## Why

The OpenPGP release key is **Ed25519**. Elliptic-curve signatures do not survive a cryptographically
relevant quantum computer: given the public key, the private key becomes recoverable, and **anyone
could then produce signatures indistinguishable from ours.**

**SHA-256 is not in that position.** Grover's algorithm offers at most a quadratic speedup against a
hash, leaving ~128 bits of effective security. So:

```
GPG signature (Ed25519)      forgeable after a break
published SHA-256 manifests  unaffected
OpenTimestamps anchors       unaffected -- and they are what dates a release
```

**Our timestamps already outlive our signatures.** A forger who could mint a fake signature still
could not produce a **pre-break Bitcoin anchor**, so genuine releases stay distinguishable by
*precedence*. **The counter-signature closes the remaining gap: it answers *who*, where the anchor
answers *which came first*.**

## The algorithm

**SLH-DSA-SHA2-128s** — NIST FIPS 205, the standardised form of SPHINCS+. Its security rests **only
on hash functions**, so it stands in the same place SHA-256 does.

```
public key   126 bytes      parthod0x-pq-countersign.pem
signature  7,856 bytes      <release>.SHA256SUMS.slhdsa
```

**It is stateless.** LMS and XMSS were considered and rejected: they are *stateful*, and reusing a
one-time key index — restoring a backup, copying a key, rolling back a snapshot — destroys their
security. A stateless scheme has no such failure mode.

## Verify a release

**Requires OpenSSL 3.5 or later**, which ships SLH-DSA natively — no extra libraries.

```bash
openssl version                                        # must be 3.5+

# 1. the manifest still matches the tarball  (unchanged, the primary check)
sha256sum -c SHA256SUMS

# 2. the OpenPGP signature                    (unchanged)
gpg --verify SHA256SUMS.asc SHA256SUMS

# 3. the post-quantum counter-signature       (new)
openssl pkeyutl -verify -pubin -inkey parthod0x-pq-countersign.pem \
  -rawin -in SHA256SUMS -sigfile SHA256SUMS.slhdsa
#   -> Signature Verified Successfully

# 4. the counter-signature's own timestamp    (what makes it pre-dated)
ots verify SHA256SUMS.slhdsa.ots
```

**Step 4 is the one that matters most and is easiest to skip.** A counter-signature made at any time
proves authorship; a counter-signature **anchored in a Bitcoin block** proves it was made *before*
that block — which is what a forgery cannot reproduce.

## Scope, stated plainly

- **This is authenticity, not authority.** It proves who published these bytes. It proves nothing
  about any claim the bytes make. **Not money, not financial advice.**
- **The public key here is dated by its own OpenTimestamps proof.** Compare it against a second
  source before relying on it, exactly as with the OpenPGP fingerprint — a key and its own claimed
  provenance are not independent. **This page and the key are published byte-identically at three
  independently hosted domains, so the comparison costs one command:**

  ```bash
  for h in satoshioncha.in bitcoin-lab.org bitcoinwhitepaper.online; do
    curl -sL "https://$h/parthod0x-pq-countersign.pem" | sha256sum
  done
  # all three -> 0624d2c7149d4af09e25b558e76f5e6b1a8855d60723c45333829c46488ceda4
  ```

  **Three hosts agreeing is not proof** — one publisher controls all three. It rules out a single
  substituted file, not a substituted publisher. **The OpenTimestamps proof is what the compromise of
  a host cannot backdate**, and it is the reason the key was stamped at all.
- **Old releases can still be covered.** A counter-signature made today and anchored today protects a
  release published earlier, because the anchor proves it predates any break. **The deadline is
  "before a break", not "at release."**
