# Cutting a Bitcoin release

Written down because most of it is **not automated**, and the un-automated parts are the ones that
rot quietly: nothing fails, the release just ends up missing a mirror, a timestamp, or a signature
that still verifies against the wrong file.

Steps marked **manual** have nothing behind them but this page.

---

## 1. Build

```bash
SRC=$PWD/derivatives/bitcoin/src bash derivatives/build-reconstruction/full_build_wsl.sh
sha256sum derivatives/bitcoin/build/bitcoin-0.1.0-reconstructed.exe
```

Reproducible since v0.1.3 — the same inputs give the same bytes on any machine with the toolchain in
`docs/BUILD_NOTES.md`. Put the new hash in `derivatives/build-reconstruction/EXPECTED_SHA256`.

Pushing that file re-runs `.github/workflows/reproducible-build`, which fetches the 2009 archive,
derives the source, rebuilds on a GitHub runner and **fails if the hash does not match**. Do not skip
reading its result: it is the only step in this list that a stranger also runs.

## 2. Assemble

```bash
EXE=<path-to-new-exe> bash derivatives/bitcoin/make_release.sh
cd derivatives/bitcoin/dist && sha256sum bitcoin-0.1.N.tar.gz > SHA256SUMS
```

`EXE` is overridable so cutting a release never overwrites the previous binary. That matters:
`build/` holds `cfb59606…`, the v0.1.1 executable that mined block 1, and the evidence records for
that block are bound to its hash.

## 3. Sign — **manual**

```bash
gpg --armor --detach-sign bitcoin-0.1.N.tar.gz
gpg --armor --detach-sign SHA256SUMS
gpg --verify bitcoin-0.1.N.tar.gz.asc bitcoin-0.1.N.tar.gz
gpg --verify SHA256SUMS.asc SHA256SUMS
```

Key `B0145F74B78CF1DA`, gpg4win, passphrase cached about two hours.

**`SHA256SUMS` must be re-signed every release.** Writing the new hash into it invalidates the old
`.asc` immediately, and a stale signature does not announce itself — it simply fails for whoever
checks, long after anyone is watching.

## 4. Publish

```bash
gh release create Bitcoin-v0.1.N \
  bitcoin-0.1.N.tar.gz bitcoin-0.1.N.tar.gz.asc SHA256SUMS SHA256SUMS.asc \
  --repo original-bitcoin-laboratory/genesis --title "Bitcoin v0.1.N" \
  --notes-file bitcoin-0.1.N/RELEASE.txt
```

IPFS pinning fires automatically on release. Record the CIDs in `docs/PRESERVATION.md` — the workflow
pins them but nothing writes them down.

## 5. OpenTimestamps — **manual, and it needs a second visit**

```bash
# WSL, not Windows
for f in bitcoin-0.1.N.tar.gz bitcoin-0.1.N.tar.gz.asc SHA256SUMS SHA256SUMS.asc; do ots stamp "$f"; done
gh release upload Bitcoin-v0.1.N *.ots --repo original-bitcoin-laboratory/genesis
```

Four things that are easy to get wrong:

- **The Windows client does not work.** `ctypes.find_library` returns None and it dies with
  `LoadLibrary() argument 1 must be str, not None`. Use WSL:
  `pip install --break-system-packages opentimestamps-client`.
- **A fresh proof is incomplete.** It reads *"Pending confirmation in Bitcoin blockchain"* for a few
  hours. **Come back and `ots upgrade` each `.ots`, then re-upload.** A proof left un-upgraded never
  completes itself, and the release ships something that looks like a timestamp and is not yet one.
- **A stale `.bak` silently eats the attestation.** `ots upgrade` writes `<file>.ots.bak` before
  replacing a proof and **refuses to write if that `.bak` already exists** — but only *after* it has
  fetched the attestation, which is then thrown away. `SHA256SUMS` is a filename every release
  reuses, so the previous release's `SHA256SUMS.ots.bak` sits exactly where this one must write.
  **Move old `.bak` files aside first.** The console output is no help: it prints calendar chatter
  that reads like success. **Confirm with `ots info`** — an upgraded proof names a
  `BitcoinBlockHeaderAttestation(<height>)` and grows well past its stamped size; a pending one lists
  only `PendingAttestation` and stays put.
- **`ots verify` needs a Bitcoin node, and without one you must verify by hand.** Hash the file,
  walk the operations in the `.ots`, and check the result equals the merkle root of the stated block
  on any explorer. Record the height, the block hash and the block time in `PRESERVATION.md` — "we
  stamped it" is not the claim; "it is anchored in block N" is.
- **Stamp the reproducible hash.** A timestamp on a binary nobody else can regenerate dates a private
  artifact. On one anyone can rebuild, it dates a public fact.

## 6. Radicle — **manual, deliberately**

```bash
export PATH="$HOME/.radicle/bin:$PATH" && rad node start
git push rad HEAD:refs/heads/main
rad sync status
```

CI cannot do this and should not: the Radicle identity key is unencrypted, and it is the only thing
controlling the repository ID. Whoever holds it can push as `parthod0x` — on a peer-to-peer mirror
that means publishing a tree a stranger's `rad clone` would accept. It stays off GitHub, like the
signing key.

The remote must be `rad://<RID>/<NID>`. `rad:<RID>` is parsed by git as scp-style `host:path` and it
tries to ssh to a host called `rad`.

## 7. Site and docs — **manual**

- footer release link on all nine pages in `docs/`
- a new section in `docs/bitcoin.html`, previous release marked superseded and *why*
- `docs/ANNOUNCE.md`: the tarball name and the **verify-first sha256** — that line is the one a
  reader actually pastes, so a stale hash there is worse than none
- `docs/PRESERVATION.md`: the new CIDs

## 8. Backup

Keep an offline copy of the repository and of every published release asset, and checksum the whole
tree so the backup can be verified rather than trusted. `$BACKUP` is a path outside any checkout;
nothing under it is ever published.

```bash
git bundle create "$BACKUP/repos/genesis.bundle" --all
# copy this release's published assets into "$BACKUP/evidence/bitcoin-v0.1.N-release/"
cd "$BACKUP" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS
sha256sum -c SHA256SUMS --quiet
```

## 9. The thread — **append, never edit**

Post a new tweet; do not delete or rewrite an old one. Name which earlier tweet the new one
supersedes. A thread that visibly corrects itself can be checked; one that was never wrong cannot be
distinguished from one that never looked.

---

## What is automated, so you know what you are not doing

| | trigger | note |
|---|---|---|
| tests | push | |
| docker image | push | |
| status probe | cron `*/15` | GitHub throttles it; real gaps run 60–140 min |
| Software Heritage | daily cron | forceable via its save API |
| IPFS pin | on release | CIDs still need writing down by hand |
| reproducible rebuild | build inputs change | the only check a stranger also runs |
| **Radicle** | — | **skips with a warning unless `RAD_KEYPAIR` is set, and it deliberately is not** |
