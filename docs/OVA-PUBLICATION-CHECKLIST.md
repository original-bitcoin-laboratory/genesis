# Publishing the VM image — the audit that must happen before it leaves the machine

**The `.ova` is the artifact that converts *"we ran the 2009 Bitcoin client"* into *"anyone can."***
Everything else in this laboratory is a description of an execution; the image **is** the execution,
handed over.

⚠️ **It is also the single most dangerous thing this project could publish.** A VM image captures a
whole machine: wallet files, shell history, SSH keys, browser state, saved credentials, the datadir,
deleted-but-not-overwritten disk blocks. **A published image with a private key inside it cannot be
recalled** — it will be mirrored within hours and content-addressed forever.

**So the order is: audit, then hash, then sign, then decide about distribution. Never the reverse.**

---

## STEP 0 — The scrub audit. Not optional, and not skippable because "it was a clean VM"

Run these **inside the guest** before exporting, or against a mounted copy of the disk.

```
WALLETS          wallet.dat anywhere on the disk, including
                 %APPDATA%\Bitcoin\, the Recycle Bin, and any backup/ folder
                 ⚠️ THE MINER WALLET HOLDS 64 KEYPAIRS. It must NOT ship.
KEYS             *.pem *.key *.asc *.gpg id_* .ssh/ .gnupg/ .radicle/
HISTORY          PowerShell PSReadLine history, cmd doskey, .bash_history
CREDENTIALS      Windows Credential Manager, saved RDP/SMB passwords,
                 any browser profile with saved logins
NETWORK          the seed node's address is public, but check for anything
                 that reveals the HOST network or the operator's IP
DATADIR          decide deliberately: shipping blk0001.dat is GOOD (a stranger can
                 verify the chain immediately). Shipping wallet.dat is NOT.
FREE SPACE       deleted files persist in unallocated blocks. Zero-fill free space
                 before export or the "deleted" wallet is still recoverable.
```

> ### ★ The single check that matters most
> ```
> After export, before publishing: mount the .ova's disk read-only and grep the RAW IMAGE
> for the 64-hex private key and for the first bytes of a wallet record. Not the filesystem
> -- THE RAW BYTES. A file deleted from the filesystem is still in the image.
> ```
> **If that grep finds anything, the image is destroyed and rebuilt. It is not edited.**

---

## STEP 1 — Hash it, and publish the hash whatever else happens

```
sha256sum obl-jan09-node.ova
```

**Publish that value in the repository even if the image itself never ships.** It costs nothing and
it means any copy that ever circulates — from a drive, a torrent, a colleague — is checkable against
a value we signed. **An unhashed image in circulation is worse than no image.**

## STEP 2 — Manifest what is inside

A reader must know what they are booting before they boot it.

```
OS build and locale             the guest is Windows; state which build
bitcoin.exe sha256              c3f15fc5b7bd80f4d08fe5ff356256214734eb1a3e4a7c953c9e8fc8453d2c7d
                                -- the SAME binary bound in every run since block 2
chain state at export           height, tip hash, blk0001.dat sha256
what was REMOVED                wallets, keys, history -- named explicitly, so its absence is a
                                stated fact rather than something a reader has to discover
what was KEPT and why           the datadir, so the chain verifies on first boot
how to run it                   VirtualBox version, RAM, and that it needs NO network
```

⚠️ **State that it needs no network.** The 2009 client's only peer-discovery mechanism resolves
`chat.freenode.net`, which has not existed since 2021 — a reader who expects it to sync will think
the image is broken. `addr.txt` beside `bitcoin.exe` is the supported path, and it is a v0.1.0
feature, not a modification.

## STEP 3 — Sign and anchor the manifest

Exactly as every other artifact here: GPG + SLH-DSA + OpenTimestamps.

```
gpg --armor --detach-sign OVA-MANIFEST.txt
openssl pkeyutl -sign -inkey <pq secret> -rawin -in OVA-MANIFEST.txt -out OVA-MANIFEST.txt.slhdsa
ots stamp OVA-MANIFEST.txt OVA-MANIFEST.txt.asc OVA-MANIFEST.txt.slhdsa
```

**The manifest carries the image's hash, so signing the manifest signs the image** without needing
to sign 23 GB.

## STEP 4 — Distribution `AUTHOR DECISION`

```
IPFS pin        content-addressed, already used for releases, and the CID would BE the hash.
                ⚠️ 23 GB needs a paid pinning tier or a self-hosted node kept online.
torrent         free, durable while anyone seeds, and a magnet link is content-addressed too.
                Weakest guarantee of availability; strongest cost profile.
on request      publish the hash and the manifest; hand the image to anyone who asks.
                ⚠️ Costs nothing and reaches almost nobody -- but it is honest, and it is
                strictly better than the current state, where the hash is not even published.
```

> **Recommendation: do STEPS 0–3 now, and STEP 4 later.** The audit, the hash, the manifest and the
> signature are the whole of the value that does not depend on bandwidth. **Publishing the hash
> without the image is a real improvement; publishing the image without the audit is a permanent
> mistake.**

---

**Not money.** No premine, no token, no sale, no price. The image is a laboratory instrument.
