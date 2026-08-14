# Verifying a release

Every `original-bitcoin-laboratory` release tarball is signed with the maintainer's GPG key, so you
can confirm you're running the exact bytes that were published — not a tampered copy. **This proves
authorship and integrity; it says nothing about value. NOT money.**

## The signing key

| | |
|---|---|
| **Owner** | `parthod0x <parthms.id@gmail.com>` |
| **Fingerprint** | `B128 526A F85A E4A8 F22B 949F B014 5F74 B78C F1DA` |
| **Long key id** | `B0145F74B78CF1DA` |
| **Algorithm** | Ed25519 (EdDSA), sign+certify |
| **Public key** | [`parthod0x-signing-key.asc`](parthod0x-signing-key.asc) (also attached to each GitHub release) |
| **Independently** | `gpg --keyserver hkps://keys.openpgp.org --recv-keys B128526AF85AE4A8F22B949FB0145F74B78CF1DA` |

**Always compare the fingerprint above against a second source** (the repo, the release page, this
site) before trusting a signature — a key you fetch and its own claimed identity are not
independent.

## Import the key

```bash
# from the repo/site:
# Prefer the keyserver: it is not us, so the key and the artifact no longer come from one place.
gpg --keyserver hkps://keys.openpgp.org --recv-keys B128526AF85AE4A8F22B949FB0145F74B78CF1DA

# Or from the site (same key; a fetch from here is only as trustworthy as this site):
curl -fsSL https://bitcoin-lab.org/parthod0x-signing-key.asc | gpg --import
# or from a release asset:
gpg --import parthod0x-signing-key.asc

# confirm you imported the right key:
gpg --fingerprint B0145F74B78CF1DA
# -> B128 526A F85A E4A8 F22B  949F B014 5F74 B78C F1DA
```


**Why the keyserver line is first.** Fetching the key and the release from the same host means
trusting that host twice — if it can serve you a bad tarball it can serve you the key that matches
it. keys.openpgp.org is a different party, and it publishes a user ID only after the holder proves
control of that mailbox, so the copy you get there carries one attestation that does not originate
here. It is a distribution point, not an authority: what settles it is that the fingerprint agrees
with the one in this repo's `LICENSE`, on the release pages, and on bitcoin-lab.org. Compare it.

## Verify a download

Each release carries the tarball, its detached signature (`.asc`), and a signed `SHA256SUMS`.

```bash
# 1. verify the checksum manifest is genuinely from the maintainer
gpg --verify SHA256SUMS.asc SHA256SUMS

# 2. verify the tarball matches the manifest
sha256sum -c SHA256SUMS        # -> obl-genesis-0.4.0.tar.gz: OK

# (or verify the tarball's own detached signature directly)
gpg --verify obl-genesis-0.4.0.tar.gz.asc obl-genesis-0.4.0.tar.gz
```

A good signature prints `Good signature from "parthod0x <parthms.id@gmail.com>"`. (A
`WARNING: This key is not certified with a trusted signature` line is normal — it just means you
haven't personally signed the key; the fingerprint check above is what matters.)

## Verifying the container image

The pages that tell you to `docker run` the node point at `ghcr.io/original-bitcoin-laboratory/xnode`.
**From 15 August 2026 that image is signed too**, keylessly, so there is no key for you to fetch and
none for anyone to steal:

```bash
cosign verify ghcr.io/original-bitcoin-laboratory/xnode:Bitcoin-v0.1.5   --certificate-identity-regexp '^https://github.com/original-bitcoin-laboratory/genesis/'   --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

That checks something a GPG signature cannot: it names **the workflow, in this repository, that
built the image**, rather than a person who says they did. A build-provenance attestation is pushed
alongside it and can be checked with `gh attestation verify`.

> ⚠️ **IMAGES PUBLISHED BEFORE 15 AUGUST 2026 ARE NOT SIGNED**, and no back-dating is possible — a
> signature made now would attest to a rebuild, not to what was published then. Their tags remain
> pullable and their digests remain in the registry, so **verify those the long way**: pull by
> digest and compare against the release tarball, which has always been signed. **The gap is stated
> rather than quietly closed, because a signature that claims more than it witnessed is worse than
> no signature.**

## What this does and does not mean

- **Does:** the tarball is byte‑identical to what `parthod0x` released, and hasn't been altered in
  transit or on a mirror.
- **Does not:** make the chain money, make it safe to attach value to, or make it "the real Bitcoin."
  The durable guarantee is separate and stronger — `scripts/verify_genesis.py` re‑derives both
  genesis blocks from source, so you never have to trust *us* about the chain itself. **Not money.**
