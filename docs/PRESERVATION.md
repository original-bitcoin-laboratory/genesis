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


## The identity manifest — one signed answer for the whole periphery

Preservation spreads the work across hosts nobody here controls, which raises a question the mirrors
themselves cannot answer: **who says this Radicle repository, this organisation, this domain is
ours?** Until 12 August 2026 the answer was prose in this file — worth nothing to a reader with a
reason to doubt it.

[`IDENTITY-MANIFEST.txt`](IDENTITY-MANIFEST.txt) replaces that prose with one signature. It lists
every identity that *publishes* — the OpenPGP key, the post-quantum counter-signing key, the GitHub
account and both organisations, the three sites, the Radicle identity and repository IDs, and the
2026 chain's genesis and agent key — and it is **GPG-signed, SLH-DSA counter-signed, and
Bitcoin-anchored**, so the assertion provably predates any dispute about it.

```
IDENTITY-MANIFEST.txt          12,930 B   sha256 4825c4c0984209bf64c478d011a1933dd28d186ad1659101aa4098f77deb72b7
IDENTITY-MANIFEST.txt.asc         273 B   OpenPGP, B128526AF85AE4A8F22B949FB0145F74B78CF1DA
IDENTITY-MANIFEST.txt.slhdsa    7,856 B   SLH-DSA-SHA2-128s, verified against the published pk
  + a .ots proof over each of the three
```

> **Revision 2, 12 August 2026.** The manifest now also carries the agent's **post-quantum successor
> key** (§5) — published, with its succession certificate and both signatures, because *a successor
> key that first appears after a break is indistinguishable from one a forger made*. The exclusion
> clause in §6 was narrowed accordingly: it had been withholding a key on a rule whose own reason —
> *never cite a hash a reader cannot fetch* — was better answered by publishing it.
>
> **Revision 1** was `11b3f7db…`, 11,394 B, **anchored in Bitcoin block 962049** (block hash
> `00000000000000000000b1914635ada20cd0992856ebba4ba21b5ea4815eda1b`, merkle root
> `cf62d5d80f9e0a2fecdba1c129eff6fb42ce259572649c163e42e8641ea90864`, 2026-08-11 20:03:25 UTC).
> **That anchor stands and is not withdrawn** — it proves revision 1 existed before that block.
> Revision 2's proofs are freshly stamped and pending.

## Proof of domain control — a DNS TXT record on each of the three domains

Each domain answers a TXT query at its apex with the same record, so control of the domain is
demonstrated by the one party who can set it:

```
parthod0x-pgp=B128526AF85AE4A8F22B949FB0145F74B78CF1DA; manifest=https://bitcoin-lab.org/IDENTITY-MANIFEST.txt https://satoshioncha.in/IDENTITY-MANIFEST.txt
```

```
$ dig +short TXT bitcoin-lab.org
$ dig +short TXT satoshioncha.in
$ dig +short TXT bitcoinwhitepaper.online
```

> ★ **It pins the KEY FINGERPRINT, not a manifest hash — and that is a correction, not a preference.**
> The first version of these records carried `parthod0x-manifest=<sha256>`, which went stale within a
> day when the manifest was revised. **A binding that breaks whenever the thing it binds is improved
> is the wrong binding.** The fingerprint does not change; the manifest is expected to.
>
> **The record proves domain control, and nothing else.** It publishes a fingerprint, which is
> already public — never a key. That is why `bitcoinwhitepaper.online` carries it while still hosting
> no release material of any kind.
>
> ⚠️ **Verify against the authoritative nameservers, not a public resolver.** When these were set,
> `1.1.1.1` and `8.8.8.8` both still served the previous record for one domain with 1,755 s of TTL
> left, while `dns1`/`dns2.registrar-servers.com` already had the new one. **A cached answer is not
> the zone** — reading the resolver would have reported a correct change as a failed one.

> **The merkle root was read off the chain and compared, not taken from the `ots` output.** That is
> the whole point of an anchor: it is checkable against Bitcoin by anyone, without trusting this
> file, the calendars, or us. Compare it against any block explorer.
>
> ⇒ **The manifest now carries all three: a signature saying WHO, a post-quantum counter-signature
> saying WHO STILL after an elliptic-curve break, and a Bitcoin anchor saying BEFORE WHEN.**

**It is deliberately not a list of every key the project holds, and says so in its own text.** Server
access keys and machine-identifying node keys are excluded: they authenticate infrastructure rather
than statements, and publishing them would expose the machines they belong to while proving nothing
a reader could check. A signed inventory that said *"every"* while quietly omitting things would be
the exact failure this project exists not to make.

Mirrored byte-identically to `satoshioncha.in`, since it speaks for that site too.

## The post-quantum designations — one for each identity that publishes

Two keys can outlive a break of elliptic-curve signatures, and each is now designated **in writing,
in advance, with its limits stated**:

```
PQ-SUCCESSION-CERTIFICATE.txt      the 2026 agent's successor        10 Aug 2026
                                   signed by the chain key AND the successor AND (12 Aug) the
                                   OpenPGP key -- three signatures, two identities, one document
PQ-COUNTERSIGN-DESIGNATION.txt     parthod0x's counter-signing key   12 Aug 2026
                                   7,629 B, sha256 51c69df077f6150e04e97c9128dbe2919282879ceed107ebcfd464e8fa7c6246
                                   signed by the OpenPGP key AND by the designated key itself
```

**Both are OpenTimestamped, and that is the part that carries the weight.** A designation made
BEFORE a break proves it was made while the root key was still trustworthy; one made after is
indistinguishable from a forger's, and worth nothing.

> ⚠️ **Each states what its key may NOT do, and those limits are part of the designation.** Neither
> proves the identity of any person — a legal identity is not a key. Neither confers power over the
> chain: `parthod0x` publishes the software and did not author the chain, and the agent's successor
> cannot spend, mine or sign a transaction. Neither asserts any name or trade mark. Neither says
> anything about value.
>
> ★ **The designation for `parthod0x` was written last, and only because an audit noticed the
> asymmetry:** the agent had one from 10 August and the publishing identity did not. The two keys
> were already cryptographically bound — both sign `IDENTITY-MANIFEST.txt` over identical bytes —
> but **the scope of the second key's authority was nowhere stated.** An unstated scope is the
> difference between a tool with known limits and a key whose holder can later claim what suits them.

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
Bitcoin-v0.1.5   all FIVE assets      block 961885   2026-08-10 14:28:15 UTC
                 (five, not four: SHA256SUMS.slhdsa, the post-quantum counter-signature,
                  is stamped alongside the OpenPGP ones from this release onward)
                 merkle root 7c8fd92d03b2bb5c247182268bd5bab9351ac3c29844775d20995141efd5a234
                 -- read off the chain and compared, not taken from the ots output

                 Also anchored the same day, retroactively: the post-quantum
                 counter-signature over EVERY earlier published manifest, in block 961879.
                 Eight of those releases had no timestamp of any kind before this.
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

> **Every CID below was verified by FETCHING it from a public gateway and hashing the bytes**, not by
> reading the workflow log. The log prints CIDs without saying which file each belongs to, so
> recording them from it would be guesswork — and a mislabelled CID is worse than none, because it
> looks checkable and fails only for whoever tries.
>
> **✅ Fixed 11 Aug 2026 — the pin workflow now covers every signed asset.** It previously fetched
> only `*.tar.gz`, `SHA256SUMS` and `*.asc`, so a release survived on IPFS *without* the two
> artifacts built specifically to outlive it: `SHA256SUMS.slhdsa`, the post-quantum
> counter-signature, and the `.ots` proofs. A content-addressed copy carrying neither is a copy of
> the thing we can no longer prove anything about. `preserve.yml` now also passes `-p '*.slhdsa'`
> and `-p '*.ots'` — **4 of 10 `v0.1.5` assets were pinned under the old patterns, 10 of 10 under
> the new ones.**
>
> **⚠️ The CID table below predates that fix**, so its rows list four assets per release. Those CIDs
> remain correct for the files they name; the missing ones are on the GitHub release and in the cold
> backup, and will be pinned from the next release onward.


| release | file | CID |
|---|---|---|
| Bitcoin-v0.1.5 | `bitcoin-0.1.5.tar.gz` | `Qmf3gedtsL5oaWXaWLwWqjNNjxC2qwDNGguWT6y1CwoPAu` |
|  | `bitcoin-0.1.5.tar.gz.asc` | `QmeoomwgPrJ1zdrY81wfZuxFUfuvcXMRb1afQvh1tgXT2D` |
|  | `SHA256SUMS` | `QmdguWZuoNEkmxSN5CLZhXJZWg7FsxFxf5u9Qy8rNTSYUW` |
|  | `SHA256SUMS.asc` | `QmbNRBoVwYTU4H3jkXdWtrGGecq525ai5hfi1DbzurhEpc` |
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

> ### ⚠️ A push to Radicle is not a push to the seeds, and the difference is measurable
>
> **Measured 12 Aug 2026.** `git push rad` updated the canonical reference in LOCAL storage
> immediately and reported **`✓ Synced with 0 seed(s)`**; `rad sync --announce` then returned
> **`✗ All seeds timed out`**. Meanwhile `rad sync status` showed eleven seeds holding the
> repository at refs one to two days old.
>
> **Nothing was broken.** This node runs behind NAT and is *"not configured to listen for inbound
> connections"*, so a seed that hears the announcement cannot open a connection back to fetch. The
> seeds converge on their own polling schedule instead of on ours.
>
> ⇒ **`git push rad` succeeding means the local canonical ref moved. It does not mean any seed has
> the commit.** Read `rad sync status` for that, and read the per-seed timestamps rather than the
> summary line. Recorded here because the summary line is the one that looks like an answer.

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
