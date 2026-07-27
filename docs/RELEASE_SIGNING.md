# Release signing — a checklist for reproducible, GPG‑signed releases

**For the maintainer.** Signed releases let operators verify **who** published a build and that it
**wasn't tampered with**. They do **not** — and cannot — prove a chain is "the real Bitcoin" or that
it is money; nothing does. This is authenticity, not authority. **Not money.**

> This uses **your** GPG key. Generating and safeguarding that key is yours to do — it is never
> managed for you. Placeholders below (`B0145F74B78CF1DA`, `B128 526A F85A E4A8 F22B  949F B014 5F74 B78C F1DA`) are for you to fill in.

## 0. One‑time: have a signing key

If you don't already have one, create a GPG key (`gpg --full-generate-key`), record its fingerprint
(`gpg --fingerprint`), and keep the private key offline/backed up. Publish only the **public** key.
Git can auto‑use it: `git config user.signingkey B0145F74B78CF1DA`.

## 1. Verify before you sign

A signature over a broken build just authenticates a broken build. Re‑run everything from a clean
checkout:

```bash
python scripts/verify_genesis.py          # both genesis blocks re-derive from source
python scripts/reproduce.py               # the whole lab — expect: ALL PASSED, 21/21 steps green
cd derivatives/validator-rs && cargo test # the Rust node — expect: 25 passed
```

Confirm the tree is clean (`git status`), the author is correct (`parthod0x`), and there are **no**
secrets, keys, or binaries staged (`git ls-files | grep -Ei 'key|secret|\.env'` returns nothing).

## 2. Tag, signed

```bash
git tag -s netnode-vX.Y.Z-experimental -m "NOV08-X / JAN09-X experimental release X.Y.Z — NOT money"
git push origin netnode-vX.Y.Z-experimental
git verify-tag netnode-vX.Y.Z-experimental   # sanity check the signature
```

(The first pre‑release, `netnode-v0.1.0-experimental`, was **unsigned**. From now on, sign every tag;
optionally cut a fresh signed tag going forward.)

## 3. A reproducible source archive + detached signature

Ship the **source** (this is a Python + dependency‑free‑ish Rust project — no opaque binaries):

```bash
git archive --format=tar.gz --prefix=obl-genesis-X.Y.Z/ \
    -o obl-genesis-X.Y.Z.tar.gz netnode-vX.Y.Z-experimental
gpg --armor --detach-sign obl-genesis-X.Y.Z.tar.gz        # -> obl-genesis-X.Y.Z.tar.gz.asc
sha256sum obl-genesis-X.Y.Z.tar.gz > SHA256SUMS
gpg --armor --detach-sign SHA256SUMS                      # sign the checksum file too
```

`git archive` from a tag is deterministic (same bytes for the same commit), so anyone can regenerate
the archive and check the hash independently.

## 4. Publish

- Attach `obl-genesis-X.Y.Z.tar.gz`, its `.asc`, and the signed `SHA256SUMS` to the GitHub release for
  the tag.
- Publish your **public key** and its **fingerprint** *out of band* (the release notes and ideally a
  keyserver): `B128 526A F85A E4A8 F22B  949F B014 5F74 B78C F1DA`. The public key is committed here at
  [`parthod0x-signing-key.asc`](parthod0x-signing-key.asc).
- Keep the release marked **pre‑release / experimental** and repeat the **NOT money** framing.

## 5. What operators run to verify

Put this in the release notes:

```bash
# 1. import the maintainer's key and confirm the fingerprint out of band
gpg --recv-keys B0145F74B78CF1DA           # or import the published key file
gpg --fingerprint B0145F74B78CF1DA         # must match B128 526A F85A E4A8 F22B  949F B014 5F74 B78C F1DA

# 2. verify the tag / archive
git verify-tag netnode-vX.Y.Z-experimental
gpg --verify obl-genesis-X.Y.Z.tar.gz.asc obl-genesis-X.Y.Z.tar.gz
gpg --verify SHA256SUMS.asc SHA256SUMS && sha256sum -c SHA256SUMS

# 3. verify the content itself — the part that truly matters
python scripts/verify_genesis.py      # re-derive the genesis from source
python scripts/reproduce.py           # 21/21
cd derivatives/validator-rs && cargo test   # 25 passed
```

## The trust model, stated plainly

- A valid signature proves the build came from **you** and is **unmodified**. That's all.
- The **durable** guarantee isn't the signature — it's the **reproducible recipe**: `verify_genesis`
  lets anyone re‑derive the exact genesis forever, with no key and no node to trust. The signature
  authenticates *a distribution*; the recipe authenticates *the artifact*.
- Nothing here — not a signature, not a tag — makes the chain money or "the real Bitcoin." **Not money.**
