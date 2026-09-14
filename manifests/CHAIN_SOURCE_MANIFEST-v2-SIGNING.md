# CHAIN_SOURCE_MANIFEST schema 2 — prepared, verified, awaiting the chain key

**Prepared 14 September 2026. ⛔ Not yet signed.** The chain key's private half is held by the
operator alone; nothing below can be done by anyone else, and nothing below has been done yet.

```
staged      manifests/CHAIN_SOURCE_MANIFEST.v2-UNSIGNED.json
sha256      ab2783c708cb6c26d0e5b9b69b07a5ef8f6f9d27f7b0fb3bc778cc06cfc71db2
size        9,451 B · 44 files pinned by bytes · 28 carrying Satoshi's 2009 notice
identity    magic f00ba726 · port 18026 · genesis 00000000ad12f3ec…  pinned BY VALUE,
            cross-checked against the patch on 8 constants
built by    verify/build_chain_source_manifest.py   (deterministic: a rebuild reproduces these bytes)
```

## Why a schema 2 exists

The schema-1 manifest signed on 12 August 2026 (`62ba1cee…`) pinned 45 files by their bytes,
including `PROVENANCE.txt`. On 12 September a language pass corrected that file — prose only; no
constant moved — and the signed manifest stopped describing the tree. The signature was still valid
over the manifest; the manifest was no longer true of the source.

Two scope errors, in opposite directions, and one fix that corrects both:

| | schema 1 | schema 2 |
|---|---|---|
| `PROVENANCE.txt` — a note for a reader; the compiler never reads it | pinned by bytes | excluded, by class (`*.txt`, `*.md` at the root) |
| `net.py` — magic, port, coinbase headline, genesis hash/time/nonce/bits, public key, the genesis block itself | **not pinned at all** | pinned **by value**: the constants are read out and recorded; a verifier re-reads `net.py` *and* the patch and requires all three to agree |
| `src/**`, `bitcoin-v0.1.0.patch` — what was compiled into the binary that mined block 0 | pinned by bytes | pinned by bytes (unchanged) |

⇒ The signature now breaks only when **the program or the chain** changes — never when a sentence
does. That is the rule `docs/PRESERVATION.md` already states for the DNS record: *a binding that
breaks whenever the thing it binds is improved is the wrong binding.*

**On 29 → 28.** Schema 1 reported 29 files carrying Satoshi's copyright notice. Twenty-eight of
those *carry* it; the 29th was `PROVENANCE.txt`, which *quotes* it. The count is now the honest one.

## What was verified before this note was written

```
generator, --schema 1, given the tree AS IT WAS at the signing commit (8f0bcea)
    -> reproduces the signed 62ba1cee… byte-for-byte      (the generator is faithful)
generator, --schema 1, given today's tree
    -> differs                                             (the finding, reproduced)
generator, schema 2, run twice
    -> identical bytes both times                          (deterministic)
generator, with an unclassified decoy file at the root
    -> REFUSED                                             (fail-closed; a list cannot do this)
net.py GENESIS_RAW (270 B)
    -> double-SHA-256 of its header equals BITCOIN_GENESIS_HASH; the coinbase message is inside it;
       its merkle equals the patch's assert; the patch's reversed pubkey literal equals net.py's key
existing v1 signature
    -> VERIFIES cryptographically today (verify/prove.py check)   — so the v1 binding is stale, not forged
```

## The steps, in order — only the key holder can do these

1. **Sign the staged hash with the genesis key.**
   ```
   python verify/prove.py sign ab2783c708cb6c26d0e5b9b69b07a5ef8f6f9d27f7b0fb3bc778cc06cfc71db2 --key <secret.hex>
   ```
   It prints `r` and `s`. Write `manifests/CHAIN_SOURCE_MANIFEST.json.secp256k1` in the same layout as the
   schema-1 file (header line, `message signed`, `r`, `s`, `public key` across two lines) —
   `verify/prove.py check` parses exactly that layout.

2. **Retire schema 1 under the SUPERSEDED prefix. Delete nothing.** Its OpenTimestamps proofs are
   over its bytes, not its name, and they stay valid:
   ```
   manifests/CHAIN_SOURCE_MANIFEST.json                 -> manifests/SUPERSEDED-2026-08-12_CHAIN_SOURCE_MANIFEST.v1.json
   manifests/CHAIN_SOURCE_MANIFEST.json.secp256k1       -> …v1.json.secp256k1
   manifests/CHAIN_SOURCE_MANIFEST.json.ots             -> …v1.json.ots
   manifests/CHAIN_SOURCE_MANIFEST.json.secp256k1.ots   -> …v1.json.secp256k1.ots
   ```

3. **Put schema 2 in place**: rename `CHAIN_SOURCE_MANIFEST.v2-UNSIGNED.json` → `CHAIN_SOURCE_MANIFEST.json`
   (the `.secp256k1` from step 1 sits beside it).

4. **Check it, cryptographically, before anything else:**
   ```
   python verify/prove.py check manifests/CHAIN_SOURCE_MANIFEST.json     # must say VERIFIES
   python ../../../_verify_self_sufficient.py
   ```
   Section 6b's manifest block should then print exactly four `ok` lines — pinned files match,
   signature VERIFIES, the rule selects exactly the pinned set, chain identity matches — and no
   `note` about a staged successor.

5. **Timestamp both new files** (`_ots_stamp.py` at the workspace root), and upgrade the proofs after
   the calendars anchor them.

6. **Commit** — `parthod0x <parthms.id@gmail.com>`, no co-author trailer — then push and `_rad_sync.py`.
   The commit message should say plainly that schema 1 was true when signed, is superseded not
   withdrawn, and why the scope changed. Delete this file in the same commit, or rewrite its header
   to say it is done.

## What the verifier now does that it did not before

Section 6b of `_verify_self_sufficient.py` used to check two proxies: that the signature *file
existed*, and that every *listed* file still hashed as listed. Presence is not validity, and a
listed-files check cannot see an omission — `net.py` was unpinned for a month while the section
printed `ok`. It now:

- verifies the ECDSA signature against the agent key, over the manifest's *current* bytes;
- for schema 2, regenerates the pinned set from the **rule** and fails on any omission or extra;
- for schema 2, re-reads the chain identity from `net.py` and the patch and fails on any drift;
- reports a staged, unsigned successor on every run, so this state is never silent.

⚠️ Both the generator and the verifier **refuse** if a file appears at the root of
`derivatives/bitcoin/` that matches none of the rule's classes. That is deliberate. Classify it in
the generator's tables with a written reason; do not add its name to a list.

**NOT money.** Experimental.
