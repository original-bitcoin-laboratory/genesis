# Notary — hashes anchored in public, with dates

A hash published here is fixed by this file's commit history, and by the mirrors that copy it
(IPFS, Software Heritage, Radicle). That establishes an **upper bound**: the document existed no
later than this commit. It does not prove the document existed earlier — nothing can — but it means
the record cannot be quietly rewritten afterwards.

Why this is needed: a GPG signature carries the signer's own clock, which is self-asserted and can
be set. This lab has said as much about the `satoshin@gmx.com` key, whose 2008 creation date is
period-plausible but forgeable. The same limit applies to our signatures, so we anchor rather than
rely on them for time.

## 4 August 2026

Provenance of the chain `00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a` — a
GPG-signed statement recording who built the agent that authored it. The statement is **not
published**; only its hash is, so its existence and integrity are fixed without disclosing it.

```
sha256  d84a8c1acaf1e5f088b292d1c39c6d86e5503cb84c981537648c5694310d6dcf   PROVENANCE-STATEMENT.txt
sha256  98b30c08a3ad44a011d64da5290011214193923c6fe927bfc7021297aaa658eb   PROVENANCE-STATEMENT.txt.asc
```

Signed with `B128 526A F85A E4A8 F22B  949F B014 5F74 B78C F1DA` — the key named in this repo's
LICENSE, and the key that signs its releases.

**To check, if the statement is ever produced:** `sha256sum` it and compare with the line above. A
match means it is byte-identical to the document that existed on this date. Then
`gpg --verify PROVENANCE-STATEMENT.txt.asc PROVENANCE-STATEMENT.txt`.

## What is anchored, and what is claimed

Anchored: **that these bytes existed by this date**, and that they have not changed since.

Not anchored, and not claimed: that the statement is *true*. It is testimony. What it attests to —
that a particular agent was built and run — is a claim by its signer, exactly as such claims always
are. The part of the lineage that needs no trust is the other one: the agent signs a challenge with
the key the genesis pays to, and anyone can check that against the chain.
