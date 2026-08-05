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
| **Content-addressed pinning (IPFS)** | the signed release bundle + `SHA256SUMS`, addressable by content hash rather than by host | **live** — every release's signed assets are pinned. CIDs are listed per release in the table below; retrievable from any gateway and cross-checkable against `SHA256SUMS`, so a gateway copy either matches or does not. |
| **Radicle** | a peer-to-peer git mirror, so the repository has no single hosting dependency | **published once, not continuously mirrored.** `rad:z4ZYBKCfJFomHvbS8d8oKzfgbR6Hg` (owned by `parthod0x`) holds whatever was last pushed by hand. CI can now sync it, but only once `RAD_KEYPAIR` and `RAD_PASSPHRASE` are set; until then the job skips with a warning. Not counted among the live roots. |


## Pinned release CIDs

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

**What that does and does not buy.** With the secrets set, every release pushes the current commit to the RID
and announces it to the network. Announcing is not the same as being held: Radicle replication depends on some
seed choosing to keep a copy, and no CI job can compel that. So even when green, this is a mirror whose
durability rests on a peer, which is why it is documented separately from the three roots that do not. *(Optional CI:* add the exported key as `RAD_KEYPAIR` and
its passphrase as `RAD_PASSPHRASE` to let the `radicle` job attempt an automated sync — but the local
`git push rad` above is the reliable path.)*

Until the secrets/identity are set, the scaffolded jobs log "skipped — not configured"; Software Heritage
archival runs regardless.

**NOT money.**
