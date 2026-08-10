# Preservation — keeping the proof retrievable, from more than one root

The durable artifact of this project is not a running node; it is the **reproducible recipe** — the
hash-matched source, the derivation, and the checks that let anyone re-derive the earliest Bitcoin without
trusting us (see [`verify-genesis.html`](verify-genesis.html): the genesis block rebuilt from its source
bytes, offline, on any device). A recipe is only as durable as its availability. So preservation is not a
side quest here — it *is* the mission: keep the source of truth **retrievable, content-addressed, and
self-verifying**, so it survives a dead link, a lost account, or a host that disappears.

Five independent roots, so no single one is load-bearing:

| Layer | What it preserves | Status |
|---|---|---|
| **Software Heritage** | full history of all four OBL repositories, in the universal source-code archive | **live** — [`.github/workflows/preserve.yml`](../.github/workflows/preserve.yml) requests archival daily and on every release, no credentials required |
| **Content-addressed pinning (IPFS)** | the signed release bundle + `SHA256SUMS`, addressable by content hash rather than by host | **live** — every release's signed assets are pinned; CIDs per release in the table below, cross-checkable against `SHA256SUMS`, so a gateway copy either matches or does not. **⚠ Ordering matters: `preserve.yml` fires on `release: published` and downloads the release's assets. Create the release WITH its assets attached** (`gh release create … file1 file2 …`) — a release created empty and populated afterwards makes the pin job run against nothing, log `no assets to download`, and exit green. That happened to `v0.6.0-experimental` on 9 Aug 2026; fixed by re-running the workflow once the assets were up. |
| **Radicle** | a peer-to-peer git mirror, so the repository has no single hosting dependency | **live.** `rad:z4ZYBKCfJFomHvbS8d8oKzfgbR6Hg` (owned by `parthod0x`), synced by hand at each release. **Synced 9 Aug 2026 for `v0.6.0-experimental`** — `main` at `df7db95`, synced with 3 seeds. *That sync also pushed `Bitcoin-v0.1.1`, `v0.1.2` and `v0.1.3`, which had **never reached Radicle before** — the tags were on GitHub only.* Replicated by 8 public seeds at the 5 Aug 2026 sync. Synced manually rather than from CI, deliberately: the identity key is unencrypted and stays off GitHub. |


## OpenTimestamps — a date nobody here can move

Every release asset carries a `.ots` proof, submitted to four independent calendars
(`a.pool`/`b.pool.opentimestamps.org`, `a.pool.eternitywall.com`, `ots.btc.catallaxy.com`). Once the
calendars fold them into a Bitcoin block, the proof shows the file existed before that block — and
that is attested by Bitcoin's own proof-of-work rather than by us, a host, or a certificate
authority.

### Where the proofs actually landed

**A stamp is a request; an attestation is the answer.** These are the answers, and each is checkable
against any block explorer without trusting this file:

```
Bitcoin-v0.1.4   all four assets      block 961652   2026-08-09 00:16:42 UTC
Bitcoin-v0.1.5   all FIVE assets      PENDING -- stamped 2026-08-10, ots upgrade due
                 (five, not four: SHA256SUMS.slhdsa, the post-quantum counter-signature,
                  is stamped alongside the OpenPGP ones from this release onward)
                 merkle root  9f989be977da16156acd44eac5fc92a52b235b2fb7addddde766f0b35b264a86
                 block hash   00000000000000000000b286970ddbb501ced552e95c7ceda6ab92cf0f44fdbc

Bitcoin-v0.1.3   all four assets      blocks 961105, 961106, 961130
```

```
ots verify bitcoin-0.1.4.tar.gz.ots     # needs the tarball beside it; wants a local Bitcoin node
ots upgrade bitcoin-0.1.4.tar.gz.ots    # fetch the completed proof once a block confirms
```

**Without a Bitcoin node `ots verify` cannot finish**, and that is not a reason to take the anchor on
faith. The proof is self-contained: hash the file, walk the operations in the `.ots`, and the result
must equal the merkle root of the stated block. Compare that root against any explorer. Both steps
were run for the heights above.

Freshly stamped proofs read *"Pending confirmation in Bitcoin blockchain"*; that is the normal state
for the first few hours, not a failure.

> **The trap that eats attestations.** `ots upgrade` writes `<file>.ots.bak` before replacing the
> proof, and **refuses to write at all if that `.bak` already exists** — after it has already fetched
> the attestation from the calendar. The fetch is silently discarded and the file stays pending.
> Because `SHA256SUMS` is a filename every release reuses, a stale `.bak` from the previous release
> sits exactly where the next one needs to write. **Move old `.bak` files aside before upgrading**,
> and check `ots info` afterwards rather than trusting the exit output — a discarded fetch still
> prints calendar chatter that reads like progress. (`dist/` is not tracked here, so the superseded
> backups live only in the working tree.)

The hash stamped for `Bitcoin-v0.1.4` is **`3d7a7b3c…`** (`bitcoin-0.1.4.tar.gz`), the reproducible
release; `Bitcoin-v0.1.3`'s was **`d24469a4…`**. That choice is the point: stamping a binary nobody
else can regenerate would prove only that *we* had a file on a date. Stamping one that anyone can
rebuild from the published 2009 archive means the date attaches to something a stranger can
independently arrive at.

## Pinned release CIDs

| release | file | CID |
|---|---|---|
| Bitcoin-v0.1.4 | `bitcoin-0.1.4.tar.gz` | `QmVRRpDq68wMiKKBySZcCtE6Enus11YYDut52g9geXFY7Q` |
|  | `bitcoin-0.1.4.tar.gz.asc` | `QmZ3pHMbpbs3gUHWqZevm3YQJSWLXkAC41MyFRqAaTsDFr` |
|  | `SHA256SUMS` | `QmQN1W5tBW9Rxd6bjrRpJA8qhrY3SFMWTaVEyMHZ58U9Rz` |
|  | `SHA256SUMS.asc` | `QmZcdo8aa4zXzWnktzU1JH2vSog77PhbwXEXc8AXiEbxsQ` |


| release | file | CID |
|---|---|---|
| v0.6.0-experimental | `obl-genesis-0.6.0.tar.gz` | `QmT3F2PeyfobCQSqstztcS7ZcBapuYXF3Sqiwt2gwSnDNi` |
|  | `obl-genesis-0.6.0.tar.gz.asc` | `Qmdqiokepjo4TGCY92ZZkrxQoUQnWcfrpE2djr1QPFnySu` |
|  | `SHA256SUMS` | `QmdmnsHfq65Thdzdqax3K7edfNKUDHy5hAxKt7TUveLcJg` |
|  | `SHA256SUMS.asc` | `Qmd5cdEULtuJu2cxqyAPsqNgBhGSTtTkgkgQivWfJjW53r` |

*(the table below continues with earlier releases)*


Every signed asset of every Bitcoin release, by content hash. `ipfs get <CID>`, or any public
gateway — then check what comes back against `SHA256SUMS` from the release itself.

| release | file | CID |
|---|---|---|
| Bitcoin-v0.1.2 | `bitcoin-0.1.2.tar.gz` | `QmXeWBKYEJCBYJaP7N1FLjQbLxmqWtTjydyqLwBncRKUvP` |
|  | `bitcoin-0.1.2.tar.gz.asc` | `Qmcgxva1kv9SGL6EwwEoCYN8RfbB9HBbeXyPziQpfMjeXW` |
|  | `SHA256SUMS` | `QmU1JwBJ9Enw2VJwKoet1HLnpRiKWpT5yPsHavGJ1rTHXb` |
|  | `SHA256SUMS.asc` | `QmcVxjbgyQxj6KWP32MoBrYfvPfy4VRnn9ZyAeW5conQH2` |
| Bitcoin-v0.1.1 | `bitcoin-0.1.1.tar.gz` | `QmUrSdkk7fzWJtKsSzKxLCt9gXDCd4iSWDw9hRu1p1e6Kd` |
|  | `bitcoin-0.1.1.tar.gz.asc` | `QmTQRrGbexanc14C7ygRQeCGXwXnCW55wYjLNXEmy3EWS9` |
|  | `SHA256SUMS` | `QmS7cgPswk63jYJtZYbewvVwTXEMx44WciAjqEV3pzBfT4` |
|  | `SHA256SUMS.asc` | `QmQ53LWCPWwzyJmEq44pHerv2wuAA5gTfu3ofCFbWubpbF` |
| Bitcoin-v0.1.0 | `bitcoin-0.1.0.tar.gz` | `QmXGG3KsrnTqFwvbDtZgsPncoAn4hRrNxN3tGiHKiXgwsW` |
|  | `bitcoin-0.1.0.tar.gz.asc` | `Qmf5ov9Z4PNM9bTHAhcE5YpSu6wHyApXc3ptEEzca4bjuc` |
|  | `SHA256SUMS` | `Qmaf8bxgYaVRCKuPhjLYjNKsJo2w83ZLkYfSgYJzqhuw2z` |
|  | `SHA256SUMS.asc` | `QmSBaJArg2Hr1u1FBCjacbhvo2WBYU3Wp4j3vmBBjoozXp` |

`v0.5.0-experimental`: `obl-genesis-0.5.0.tar.gz` → `QmVSNMtK2yKSSyqgTQrig1zSf6qP62QuCiaMRTppQbo7BZ`.

Everything preserved is **hash-anchored**, which is what makes redundancy safe: a mirror cannot silently
drift, because the genesis, the release tarballs, and the evidence bundles all carry digests that a copy
either matches or does not. Redundancy multiplies availability without multiplying trust.

## Why this is faithful to what the lab is

This adds nothing to the *reconstruction* and attaches no value to anything — it only makes the existing,
already-verifiable proof harder to lose and easier to reach. It extends the project's own standard (source
preserved as primary evidence; behaviour independently regenerable) from "published on one host" to
"retrievable from several independent, content-addressed archives." Still **not money**: no premine, no
token, no market — a valueless research instrument, preserved.

## Enabling the two scaffolded layers

### IPFS (content-addressed pinning) — automated once a token is set
1. Create an account at a pinning service and generate an **API JWT** (e.g. Pinata → *API Keys* → *New Key*
   with `pinFileToIPFS` permission → copy the JWT).
2. In the `genesis` repo: **Settings → Secrets and variables → Actions → New repository secret**, name it
   `IPFS_TOKEN`, paste the JWT.

That is all. On the next published release the `ipfs` job downloads the signed `*.tar.gz`, `SHA256SUMS`, and
`*.asc`, pins each to IPFS, and logs the CIDs — retrievable from any gateway and cross-checkable against
`SHA256SUMS`.

### The signing key itself

Every mirror above carries the release *and* the key that signs it, which makes the check circular:
a reader who fetches both from the same place is trusting that place twice. The key is therefore
also published to **keys.openpgp.org**, fetchable by fingerprint independently of this repository:

```
gpg --keyserver hkps://keys.openpgp.org --recv-keys B128526AF85AE4A8F22B949FB0145F74B78CF1DA
```

A keyserver is a distribution point, not an authority — anyone can upload anything to most of them.
What keys.openpgp.org adds is narrower and worth stating precisely: it publishes a user ID only
after the holder proves control of that mailbox, so a key served *with* its UID carries one
independent attestation beyond this repo's say-so. That is all it carries. The fingerprint in
LICENSE, in this repo, and on bitcoin-lab.org remains the thing to compare against.

### Radicle (peer-to-peer git mirror) — a one-time local publish, then keep in sync
Radicle is published from a machine running the `rad` node, once:
1. Install: `curl -sSfL https://radicle.xyz/install | sh` (the `-L` follows the `radicle.xyz`→`radicle.dev`
   redirect; adds `rad` under `~/.radicle/bin`).
2. Create the Laboratory identity: `rad auth` (choose an alias, set a passphrase). Keys are written to
   `~/.radicle/keys/`.
3. In a clone of this repo: `rad init --public --name genesis` — this publishes the repository to Radicle
   and prints its **Repository ID** (`rad:z…`). Start the node if prompted: `rad node start`. The repo is now
   replicated across public Radicle seeds — no single host.
4. Keep it in sync: after each GitHub push, run `git push rad` (the `rad` remote is added by `rad init`), or
   `rad sync --announce`.

**Published.** The genesis repository is on Radicle as **`rad:z4ZYBKCfJFomHvbS8d8oKzfgbR6Hg`**, owned by the
`parthod0x` identity (`did:key:z6MkqZAx6fnZ3iosXhTk7K3GzyzcNC2pxy5peUAuvYL45kUA`). Fetch the decentralized
mirror with:

```
rad clone rad:z4ZYBKCfJFomHvbS8d8oKzfgbR6Hg
```

Durable public availability depends on a seed replicating the repository; keep a node online or arrange a
seed to hold `rad:z4ZYBKCfJFomHvbS8d8oKzfgbR6Hg`.

### Turning the CI mirror on

The `radicle` job in `.github/workflows/preserve.yml` installs `rad`, imports the key, starts a node, pushes
`HEAD` to the RID and announces it. It is **inert until two secrets exist**, and it says so in the run summary
rather than passing quietly:

```
gh secret set RAD_KEYPAIR   --repo original-bitcoin-laboratory/genesis   --body "$(base64 -w0 ~/.radicle/keys/radicle)"
gh secret set RAD_PASSPHRASE --repo original-bitcoin-laboratory/genesis
```

`RAD_KEYPAIR` is the OpenSSH private key base64-encoded onto one line; the passphrase is whatever protects it.
Both live in the cold backup under `01-keys-SECRET/radicle/`.

**Why this is not run from CI.** The Radicle identity key is **unencrypted**, and it is the sole thing
controlling `rad:z4ZYBKCfJFomHvbS8d8oKzfgbR6Hg`. Whoever holds it can push to that repository as `parthod0x` --
which on a p2p mirror means publishing a tampered tree that a stranger's `rad clone` would accept. Uploading it
to GitHub Actions secrets would put the only copy that matters onto third-party infrastructure, readable by any
future workflow change, and would break the invariant that **no private key of this project is on GitHub**. The
release is already signed by hand for the same reason; syncing by hand costs one command more.

**What replication does and does not guarantee.** Seeds are volunteers. Eight held the current refs at the
5 Aug sync and nine more held older ones, which is real redundancy across operators nobody here controls -- but
none of them is obliged to keep it. That is a different kind of durability from Software Heritage, not a lesser
one, and it is why the sync output is recorded with a date rather than described as permanent.

### Syncing by hand

```
export PATH="$HOME/.radicle/bin:$PATH"
rad node start
git remote add rad rad://z4ZYBKCfJFomHvbS8d8oKzfgbR6Hg/z6MkqZAx6fnZ3iosXhTk7K3GzyzcNC2pxy5peUAuvYL45kUA
git push rad HEAD:refs/heads/main
rad sync status                        # which seeds hold it, and at which refs
```

The remote URL is **not** `rad:<RID>`. Git parses that as scp-style `host:path` and tries to ssh to a host
called `rad`; the `git-remote-rad` helper is only invoked for a `scheme://` URL. It also needs the node ID
appended, or the push is rejected with *"no public key given as a remote namespace"*. *(Optional CI:* add the exported key as `RAD_KEYPAIR` and
its passphrase as `RAD_PASSPHRASE` to let the `radicle` job attempt an automated sync — but the local
`git push rad` above is the reliable path.)*

Until the secrets/identity are set, the scaffolded jobs log "skipped — not configured"; Software Heritage
archival runs regardless.

**NOT money.**
