# Preservation — keeping the proof retrievable, from more than one root

The durable artifact of this project is not a running node; it is the **reproducible recipe** — the
hash-matched source, the derivation, and the checks that let anyone re-derive the earliest Bitcoin without
trusting us (see [`verify-genesis.html`](verify-genesis.html): the genesis block rebuilt from its source
bytes, offline, on any device). A recipe is only as durable as its availability. So preservation is not a
side quest here — it *is* the mission: keep the source of truth **retrievable, content-addressed, and
self-verifying**, so it survives a dead link, a lost account, or a host that disappears.

Three independent roots, so no single one is load-bearing:

| Layer | What it preserves | Status |
|---|---|---|
| **Software Heritage** | full history of all four OBL repositories, in the universal source-code archive | **live** — [`.github/workflows/preserve.yml`](../.github/workflows/preserve.yml) requests archival daily and on every release, no credentials required |
| **Content-addressed pinning (IPFS)** | the signed release bundle + `SHA256SUMS`, addressable by content hash rather than by host | scaffolded — enable with an `IPFS_TOKEN` secret |
| **Radicle** | a peer-to-peer git mirror, so the repository has no single hosting dependency | scaffolded — enable with a `RAD_KEYPAIR` secret |

Everything preserved is **hash-anchored**, which is what makes redundancy safe: a mirror cannot silently
drift, because the genesis, the release tarballs, and the evidence bundles all carry digests that a copy
either matches or does not. Redundancy multiplies availability without multiplying trust.

## Why this is faithful to what the lab is

This adds nothing to the *reconstruction* and attaches no value to anything — it only makes the existing,
already-verifiable proof harder to lose and easier to reach. It extends the project's own standard (source
preserved as primary evidence; behaviour independently regenerable) from "published on one host" to
"retrievable from several independent, content-addressed archives." Still **not money**: no premine, no
token, no market — a valueless research instrument, preserved.

## Enabling the two scaffolded layers (one-time)

**Radicle (peer-to-peer git mirror).** Install `rad`, create a dedicated Laboratory identity, and bind the
repository to its Radicle Identifier (`rid`). Export the keypair and add it as the repository secret
`RAD_KEYPAIR`; the `radicle` job in `preserve.yml` then syncs on each run. For hourly mirroring once it is
configured, add `- cron: '0 * * * *'` to the workflow's `schedule`.

**IPFS (content-addressed pinning).** Obtain a token from any pinning service (or run a self-hosted node),
add it as the secret `IPFS_TOKEN`, and the `ipfs` job pins the signed release bundle whenever a release is
published, recording the resulting CID so anyone can retrieve the exact bytes by hash.

Until those secrets are set, the two jobs log a clear "skipped — not configured" and do nothing; Software
Heritage archival runs regardless.

**NOT money.**
