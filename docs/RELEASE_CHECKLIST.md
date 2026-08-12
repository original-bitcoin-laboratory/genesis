# Cutting a Bitcoin release

Written down because most of it is **not automated**, and the un-automated parts are the ones that
rot quietly: nothing fails, the release just ends up missing a mirror, a timestamp, or a signature
that still verifies against the wrong file.

Steps marked **manual** have nothing behind them but this page.

---

## 0. Timestamps — UTC, everywhere, including git

**This project reports one clock.** Block times, OpenTimestamps attestations, findings headers and
release notes are all UTC. **Commit metadata should match**, and by default it does not — git stamps
commits in the machine's local zone.

```bash
# make the shell's git operations UTC for this session
export TZ=UTC
git commit -m "..."          # author and committer dates now +0000
```

**Why it matters and why it is not urgent.** A single-clock record is easier to check: every
timestamp in every artifact compares directly against the chain, with no conversion. It is a
research-hygiene convention.

**It does not rewrite anything.** The existing history carries a local offset and will continue to;
that is ordinary for git and true of most projects. **The point is consistency going forward, not
retrofit** — and rewriting history to change it would break the signed tags for no gain.

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

### 3b. Counter-sign with the post-quantum key — **manual**

```bash
openssl pkeyutl -sign -rawin -in SHA256SUMS \
  -inkey <OBL-BACKUP>/01-keys-SECRET/pq-counter-signing/pq-countersign-sk.pem \
  -out SHA256SUMS.slhdsa                                    # 7,856 B

openssl pkeyutl -verify -pubin -rawin -in SHA256SUMS \
  -inkey docs/parthod0x-pq-countersign.pem -sigfile SHA256SUMS.slhdsa
```

`SLH-DSA-SHA2-128s`, needs OpenSSL 3.5+ and nothing installed. **Ed25519 does not survive a quantum
break; this does, because its security rests only on hashes.** Sign the **manifest only** — it already
commits to every asset by hash, so one 7,856-byte signature covers the release. See
[`PQ-COUNTERSIGNING.md`](PQ-COUNTERSIGNING.md).

**`-rawin` is not optional.** SLH-DSA signs the message itself, not a pre-hash; without it OpenSSL
takes a different path and the signature will not verify the way the published instructions say it
should.

## 4. Publish

```bash
gh release create Bitcoin-v0.1.N \
  bitcoin-0.1.N.tar.gz bitcoin-0.1.N.tar.gz.asc SHA256SUMS SHA256SUMS.asc SHA256SUMS.slhdsa \
  --repo original-bitcoin-laboratory/genesis --title "Bitcoin v0.1.N" \
  --notes-file bitcoin-0.1.N/RELEASE.txt
```

IPFS pinning fires automatically on release. Record the CIDs in `docs/PRESERVATION.md` — the workflow
pins them but nothing writes them down.

## 5. OpenTimestamps — **manual, and it needs a second visit**

```bash
# WSL, not Windows
for f in bitcoin-0.1.N.tar.gz bitcoin-0.1.N.tar.gz.asc SHA256SUMS SHA256SUMS.asc SHA256SUMS.slhdsa
do ots stamp "$f"; done
gh release upload Bitcoin-v0.1.N *.ots --repo original-bitcoin-laboratory/genesis
```

**Stamping `SHA256SUMS.slhdsa` is the step that gives the counter-signature its value**, and it is the
one that looks skippable. A counter-signature proves *who*; only its anchor proves it was made
**before a break**, which is the whole claim. An unanchored counter-signature is indistinguishable
from one a forger made afterwards.

Four things that are easy to get wrong:

- **The Windows client does not work.** `ctypes.find_library` returns None and it dies with
  `LoadLibrary() argument 1 must be str, not None` — `ots` imports python-bitcoinlib, which loads an
  OpenSSL DLL at import time for *wallet* code an upgrade never touches. **Every subcommand dies
  before parsing its arguments.**
  > ★ **Preferred: `python _ots_upgrade.py` at the workspace root** (`--dry-run` to report only). It
  > reaches the calendars through the pure-python `opentimestamps` library, needs no WSL, and decides
  > pending-vs-anchored by **parsing the proof** rather than by reading console output or file size.
  > It also writes **no `.bak`**, so the trap two bullets down cannot arm itself.
  >
  > ⚠️ **Why this replaced the WSL workaround instead of joining it: a sweep once shelled out to the
  > Windows client, grepped its traceback for `BitcoinBlockHeaderAttestation`, found none, and
  > reported all 83 proofs pending when 74 were anchored.** A crashing tool does not answer "no" — it
  > does not answer at all. **This bullet had warned about the crash the whole time; a warning is not
  > a control.**
  >
  > WSL remains a valid fallback: `pip install --break-system-packages opentimestamps-client`.
- **A fresh proof is incomplete.** It reads *"Pending confirmation in Bitcoin blockchain"* for a few
  hours. **Come back and `ots upgrade` each `.ots`, then re-upload.** A proof left un-upgraded never
  completes itself, and the release ships something that looks like a timestamp and is not yet one.
- **A stale `.bak` silently eats the attestation.** `ots upgrade` writes `<file>.ots.bak` before
  replacing a proof and **refuses to write if that `.bak` already exists** — but only *after* it has
  fetched the attestation, which is then thrown away. `SHA256SUMS` is a filename every release
  reuses, so the previous release's `SHA256SUMS.ots.bak` sits exactly where this one must write.
  **Move old `.bak` files aside first** — and sweep for them again *after* every upgrade, including
  a re-run on proofs that are already complete: **`ots upgrade` writes a `.bak` every time it runs,
  finished or not**, so simply re-checking a release arms this trap for the next one.
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

**⚠️ Do this AFTER step 5's `ots upgrade`, never between the stamp and the upgrade.** A backup sealed
in that gap stores **pending** proofs — promises that can never complete on their own — and the
filename is identical either way, so nothing about the archive looks wrong.

```bash
# check the proof INSIDE the archive, not the one on disk
tar -xzOf "$BACKUP/<bundle>.tar.gz" '*/SHA256SUMS.ots' | wc -c     # ~1,900 anchored / ~800 pending
```

### ⏳ One dated file that rots on its own: `security.txt`

**`.well-known/security.txt` carries a mandatory `Expires:` field (RFC 9116), currently
`2027-08-11T00:00:00.000Z` on all three sites.** After that date the file is **not merely stale — it
is invalid**, and a scanner is entitled to treat it as absent.

```bash
# any release after mid-2027, or any time you think of it:
for h in bitcoin-lab.org satoshioncha.in bitcoinwhitepaper.online; do
  curl -s "https://$h/.well-known/security.txt" | grep Expires
done
```

**Push the date out by a year and redeploy all three.** It is the only file this project publishes
that becomes wrong by the passage of time alone — everything else is a hash, a signature or an
anchor, and none of those expire.

### ★ This is no longer your job to remember

**Run `python _verify_self_sufficient.py`.** Section 4 walks every `.ots` in the workspace, and
**FAILS** on any proof inside `OBL-BACKUP/` or `archives/` that carries no
`BitcoinBlockHeaderAttestation`. It also reports stray `.ots.bak` files, which are the other half of
the same hazard.

It classifies by **reading the attestation marker**, not by file size. The old sweep here used
`-size -1k`; that happened to catch every real case, but a pending proof is not required to be
small and an anchored one is not required to be large. **Size was a proxy that worked until it
didn't.**

**Why this moved out of the checklist and into the verifier:** on 10 Aug 2026 four of eight proofs
in the cold backup were pending, and it was found only because an unrelated mistake caused someone
to look. This warning was then written, in detail, with a working command. **On 11 Aug 2026 it
happened again** — twelve pending proofs plus one release missing entirely — and the warning did not
stop it, because a checklist step only fires when a human remembers to read the checklist.

> **A warning is not a control. A check that runs whether or not anyone remembers it is.**
> The published releases were fine both times. The backup was not, and the backup is the copy that
> matters if GitHub does not survive.

**Refresh stale proofs from the PUBLISHED release, not the working tree.** The published copy is the
authoritative one, and re-downloading also catches assets the backup never had.

**This happened on 10 Aug 2026** with the post-quantum bundle: sealed at 05:52, upgraded at 06:49, so
the cold copy held 735-byte promises until it was rebuilt. **The routine already warned about this for
published releases; nobody had thought to look for it in the backup path.**

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
