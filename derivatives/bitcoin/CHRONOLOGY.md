# Chronology

Every dated fact about this chain and the agent that authored it, with what each timestamp is
actually worth. Assembled from artifacts.

**Not money. Experimental. No warranty.**

---

## The three parties

```
Parth Mauria Saxena          a person. Real name on this repository's LICENSE.
  pseudonym  parthod0x
  GPG        B128 526A F85A E4A8 F22B  949F B014 5F74 B78C F1DA
  his acts   building and running the agent, signing releases, publishing,
             registering the domains, operating the seed node
        |
        |  built and ran
        v
"Satoshi Nakamoto"           an AI agent. Not a person, and not the author of the
                             2009 Bitcoin. It generated its own key and holds it.
  key        04c0414cfdcc009830708543b06e43a03570dc1ffa45ddf98657045e594a815eba7
             94ca0602e8527d7ba3197e53c0c2f226892212aa99b827e8e2fd95fcea2f834
  its acts   generating that key, mining this genesis, signing challenges
        |
        |  created
        v
"Bitcoin"                    this chain.
  genesis    00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a
```

**Publishing the software is Parth's act. Authoring the chain is not.**

---

## The timeline

All times UTC.

```
2026-08-03 18:20:30   the agent generates its own secp256k1 key
2026-08-03 18:22:55   ★ mint time fixed: 1785781375. This becomes the genesis nTime.
                        2 minutes 25 seconds after the key existed.
2026-08-03 20:33-20:54  coinbase headline fixed, miner written, nonce found
                        nNonce 33394338 -> 00000000ad12f3ec…
2026-08-03 23:34:17   Bitcoin-v0.1.0 released and GPG-signed        7da79f8e…
2026-08-04 11:54:00   Bitcoin-v0.1.1 released and GPG-signed        135134d6…
2026-08-04 22:36:53   ★ BLOCK 1 mined at difficulty-1               000000007beb32b8…
                        nNonce 895691393 — 28h 14m after the genesis
2026-08-05            Bitcoin-v0.1.2  099c011d…   ·  v0.1.3  d24469a4…
                        SHA256SUMS signed and OpenTimestamped, then upgraded
```

### The genesis header, in full

```
hash      00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a
merkle    aaa5bdfd6c4075a646db9975aab8515781c67fdd73b02df1773a4e1e21a38085
nTime     1785781375  =  2026-08-03 18:22:55 UTC
nBits     0x1d00ffff  (difficulty-1, real work)      nNonce  33394338
coinbase  "The Times 03/Aug/2026 Toll of schooling 'straitjacket'"
output    50 -> P2PK 04c0414c…   no value assigned
```

**The coinbase is a proof of time, not homage.** It is *The Times* front-page splash of the morning
the block was mined — the same page slot Satoshi used, and a different headline because copying his
would keep the words and lose the function. **This block cannot have been mined before that paper was
printed.**

---

## ★ What each timestamp is worth

The distinction that matters, and it is the same one this laboratory applies to everyone else.

```
STRONGEST   the genesis and block-1 nTime
            Bound into headers that satisfy difficulty-1 proof-of-work, and paired
            with a newspaper published that morning. Cannot be backdated.

STRONG      OpenTimestamps proofs, upgraded
            Anchored into the Bitcoin blockchain by a third party. Independent of
            any clock of ours.

MODERATE    GPG signature times · git tagger times
            SELF-ASSERTED. A signer's clock can be set to anything.
            ★ This lab says exactly that about the satoshin@gmx.com key's 2008 date.
              The same limit applies to ours, and we will not cite a GPG time as
              proof of when something happened.

WEAKEST     file modification times
            A local clock. Useful for ordering events on one machine; worth nothing
            as absolute proof to anyone else.
```

**`nTime` is a field the miner chooses, not a clock reading.** Satoshi's own genesis carries an
`nTime` six days before block 1. Ours happens to coincide with the moment the mint time was fixed,
which is why the two agree to the second — but that is a fact about how it was made, not a property
of the format.

---

## The ordering

Each of these would be a problem if it came out the other way round.

```
the Times headline existed before the block that quotes it        PASS
the key existed before the genesis that pays to it                PASS   (2m 25s)
the genesis precedes block 1                                      PASS   (28h 14m)
the coinbase was fixed before mining began                        PASS
the genesis was mined before the client was released              PASS   (5h 11m)
```

**Only the first and third stand against a determined sceptic** — a third party's publication, and
proof-of-work. The rest rest on local filesystem times and establish internal consistency, not
independent proof. **Said plainly because the alternative is to imply more than the evidence carries.**

---

## What anyone can check, without trusting us

```
the chain exists and its genesis is what we say     read it from any node
the genesis cannot predate 3 August 2026            the headline + the proof-of-work
the agent holds the genesis key                     issue a challenge; it signs
the releases are Parth's                            gpg --verify against the published key
this is NOT the 2009 Bitcoin                        genesis 00000000ad12f3ec…
                                                    vs Bitcoin's 000000000019d668…
                                                    -- one comparison, seconds
```

**And one thing nobody can check:** that the agent is a machine rather than a person. **No chain can
establish that.** It authenticates keys, not natures.

That is not a hole in this design — it is the finding the rest of this laboratory's research rests
on. Across the entire authenticated record of the 2009 Satoshi Nakamoto, no artifact ever leaked
species either. **The position here is identical in kind, and stated rather than hidden.**

---

## A signed statement exists, and only its hash is published

A GPG-signed statement recording who built the agent is held privately. **Its hash was published in
[`NOTARY.md`](NOTARY.md) on 5 August 2026**, so its existence and integrity are fixed and dated
without disclosing its contents. If it is ever produced, anyone can verify it is byte-identical to
the document that existed then.

```
sha256  d84a8c1acaf1e5f088b292d1c39c6d86e5503cb84c981537648c5694310d6dcf   PROVENANCE-STATEMENT.txt
sha256  98b30c08a3ad44a011d64da5290011214193923c6fe927bfc7021297aaa658eb   PROVENANCE-STATEMENT.txt.asc
```

---

## Known gaps in this record

Listed here rather than left to be discovered.

- **`Bitcoin-v0.1.2` and `v0.1.3` are lightweight git tags, not signed tag objects.** All four
  release tarballs *are* GPG-signed, and `SHA256SUMS` is signed and OpenTimestamped, so nothing is
  unattested — but the tags themselves are not, and history will not be rewritten to hide that.
- **Only v0.1.3's tarball is individually OpenTimestamped.** The earlier three are covered
  transitively through the stamped `SHA256SUMS`.
- **Blocks 2 and 3 have no evidence directory.** Block 1 was the witness; later blocks are routine
  and were not captured with the same ceremony.

MIT. `license.txt` in every release is the 2009 source's own and is unmodified.
