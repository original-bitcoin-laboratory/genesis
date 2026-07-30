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

**Always compare the fingerprint above against a second source** (the repo, the release page, this
site) before trusting a signature — a key you fetch and its own claimed identity are not
independent.

## Import the key

```bash
# from the repo/site:
curl -fsSL https://bitcoin-lab.org/parthod0x-signing-key.asc | gpg --import
# or from a release asset:
gpg --import parthod0x-signing-key.asc

# confirm you imported the right key:
gpg --fingerprint B0145F74B78CF1DA
# -> B128 526A F85A E4A8 F22B  949F B014 5F74 B78C F1DA
```

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

## What this does and does not mean

- **Does:** the tarball is byte‑identical to what `parthod0x` released, and hasn't been altered in
  transit or on a mirror.
- **Does not:** make the chain money, make it safe to attach value to, or make it "the real Bitcoin."
  The durable guarantee is separate and stronger — `scripts/verify_genesis.py` re‑derives both
  genesis blocks from source, so you never have to trust *us* about the chain itself. **Not money.**
