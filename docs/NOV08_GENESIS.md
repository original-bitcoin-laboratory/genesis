# The November 2008 genesis — what it is, and what it is not

*A field-by-field reading of the genesis block hardcoded into the 15 November 2008 pre-release,
against the one hardcoded into v0.1.0. Hash-anchored, and re-derived from its own constants.*

The lab's earlier work compares the November pre-release with v0.1.0 at the level of consensus rules,
and `V010_TO_V013.md` carries the source lineage forward to 13 January 2009. This looks at the one
object both releases contain and almost nobody examines: **the genesis block itself.**

The finding, in one line: **the November genesis carries no proof of time.** Its coinbase is a bare
integer, its timestamp predates the whitepaper's publication, and the work behind it is roughly one
fourteen-thousandth of January's. It is a developer's test fixture, not a commitment — and the
archive it lives in is, by Satoshi's own description, not a complete program.

---

## Provenance

| | |
|---|---|
| `bitcoin-nov08.rar` | 33,657 bytes · sha256 `f0327ebbea17f7d6e14be5f5534c6ff16c7648f588cbb096fc8fdfcb7e071abf` |
| `bitcoin-nov08.tgz` | 31,830 bytes · sha256 `ababfeb72cf82ede27fd86a0eb330f3738afd7c5c9595e44a43570f32fcba5d7` |

Held in `pre-genesis/artifacts/nov08/`. Everything below is reproducible from `main.cpp` and
`main.h` in those archives, with `sha256sum`, a text editor, and about twenty lines of Python.

### An external anchor for this archive

The bytes above are self-describing, which is worth exactly as much as any other self-description.
There is, however, a third-party record that dates an artifact of this description — and it is not
cited anywhere else in this lab's material.

The `cryptography@metzdowd.com` archive holds a message from Satoshi Nakamoto, timestamped by the
list server at **Mon 17 Nov 2008 12:24:43 EST**, replying to James A. Donald
([`014863`](https://www.metzdowd.com/pipermail/cryptography/2008-November/014863.html)):

> The functional details are not covered in the paper, but the sourcecode is coming soon.
> **I sent you the main files.** (available by request at the moment, full release soon)

Set that beside the readme inside this archive:

> This is a pre-release sourcecode preview.
> **These are just the main files. The rest is coming soon.**

| the email, 17 Nov 2008 | this archive's readme |
|---|---|
| "the sourcecode is coming soon" | "The rest is coming soon" |
| "I sent you **the main files**" | "These are just **the main files**" |
| "available by request at the moment" | "a pre-release sourcecode preview" |

And the archive contains precisely that: `main.cpp`, `main.h`, `node.cpp`, `node.h`, and the readme.
Nothing else.

**What this establishes.** A record kept by a mailing list — not by Satoshi, not by this lab, not by
whoever later published the file — places, on a specific dated day, a statement that a four-file
"main files" pre-release had been sent to a named recipient, described in near-identical words to the
readme in the artifact.

**What it does not establish.** That the bytes here are the bytes he sent. No hash was published, no
copy was attached, and the recipient's own copy has never surfaced. The anchor dates *an artifact of
this description*; it does not authenticate *this file*.

That is still a materially stronger position than the artifact had a moment ago, and it is the
strongest available: it is the only claim about the November code that rests on something outside the
November code. Two independent acquisition paths for the RAR agree byte-for-byte
(`f0327ebb…`), which is corroboration of transmission, not of origin.

## What the archive actually is

Five files. `main.cpp`, `main.h`, `node.cpp`, `node.h`, `readme.txt`. That is all of it, and the
readme says so in Satoshi's own words:

> This is a pre-release sourcecode preview.
>
> These are just the main files. The rest is coming soon.

It is worth being exact about what "just the main files" excludes, because it is most of a program.
`main.cpp` opens with `#include "headers.h"` and `#include "sha.h"`; **neither file is in the
archive.** Counted across `main.cpp` and `main.h`, these are used and never defined:

| symbol | uses | defined in the archive |
|---|---:|---|
| `uint256` | 97 | no |
| `CScript` | 13 | no |
| `CDataStream` | 7 | no |
| `SHA256` | 6 | no |
| `OP_CHECKSIG`, `OP_CODESEPARATOR` | 5 | no |
| `CBigNum` | 3 | no |
| `CDB` | 2 | no |

The script engine, the bignum layer, serialization, the database and the hash primitives are all
absent. **The November pre-release cannot be compiled from what survives**, and it never could be —
it was circulated as a preview of the design, privately, to a handful of correspondents. `NOV08-X`
exists because the lab supplied the missing halves under strict per-line discipline; it is a
reconstruction, and the honest word for the archive itself is *fragment*.

## The genesis, as the code declares it

From `main.cpp`, in `LoadBlockIndex`:

```cpp
txNew.vin[0].scriptSig     = CScript() << 247422313;
txNew.vout[0].nValue       = 10000;
txNew.vout[0].scriptPubKey = CScript() << OP_CODESEPARATOR << CBigNum("0x31D1…D404") << OP_CHECKSIG;
block.hashPrevBlock = 0;
block.nTime  = 1221069728;
block.nBits  = 20;
block.nNonce = 141755;
```

and the constant it must reproduce:

```cpp
const uint256 hashGenesisBlock("0x000006b15d1327d67e971d1de9116bd60a3a01556c91b6ebaa416ebc0cfaa646");
```

### Re-derived

`CBlock::GetHash()` in the November tree is

```cpp
uint256 GetHash() const { return Hash(BEGIN(hashPrevBlock), END(nNonce)); }
```

— a raw memory range from `hashPrevBlock` to `nNonce`, which is **76 bytes**. `nVersion` is written
only when `!(nType & SER_GETHASH)`, so it is in the block on the wire and on disk but **not in the
hash**. January's header is 80 bytes with `nVersion` inside the preimage.

Double-SHA-256 over those 76 bytes reproduces the constant exactly:

```
hashPrevBlock   32 bytes of zero
hashMerkleRoot  769a5e93fac273fd825da42d39ead975b5d712b2d50953f35a4fdebdec8083e3
nTime           1221069728        (uint32 LE)
nBits           20                (uint32 LE)
nNonce          141755            (uint32 LE)
                                  -> 000006b15d1327d67e971d1de9116bd60a3a01556c91b6ebaa416ebc0cfaa646  ✓
```

The same fields under a January-style 80-byte header — `nVersion=1` prepended — give
`a9a05946db04bfc4283e0864…`, which matches nothing. The header shape is a real structural
difference, not a formatting detail, and this is the check that proves it.

### The merkle root, and what re-deriving it recovered

An earlier version of this document said the merkle root **could not** be recomputed from this
archive, and stopped there. That was too cautious, and the caution hid a result.

The reasoning was sound as far as it went. A single-transaction block's merkle root is the
transaction hash, which needs the coinbase serialized, which needs the numeric values of
`OP_CODESEPARATOR` and `OP_CHECKSIG`. **`script.h` is not in this archive** — it is a four-file
fragment — so those values cannot be read. Importing January's values and declaring a match would
have been the error this lab keeps naming: assuming a later artifact's constants hold in an earlier
one.

But there is a difference between *assuming* a constant and *solving* for it. The root is a 256-bit
commitment published by the author. Everything else in the preimage comes from `main.h`, which **is**
in the archive:

```
vin   count 1, prevout null (32 zero bytes + 0xFFFFFFFF), scriptSig = 04 695dbf0e
vout  count 1, nValue 10000, nSequence 0xFFFFFFFF  <- on CTxOut in November, not CTxIn
      scriptPubKey = [OP_CODESEPARATOR] [0x41] [65-byte pubkey] [OP_CHECKSIG]
nLockTime 0        nVersion excluded (SER_GETHASH)     posNext excluded (SER_DISK only)
```

That leaves exactly two unknown bytes. There are 65,536 possibilities. **Exactly one reproduces
`769a5e93…`:**

| | November 2008 | January 2009 (`script.h`) |
|---|---|---|
| `OP_CODESEPARATOR` | **0xa9** | 0xab |
| `OP_CHECKSIG` | **0xaa** | 0xac |

A chance match is on the order of 65,536 / 2²⁵⁶. This is not an inference.

### What the shift means: no OP_HASH160 in November

January's opcode enum is sequential through this range:

```
OP_RIPEMD160 0xa6   OP_SHA1 0xa7   OP_SHA256 0xa8
OP_HASH160   0xa9   OP_HASH256 0xaa
OP_CODESEPARATOR 0xab   OP_CHECKSIG 0xac
```

November's `CODESEPARATOR`/`CHECKSIG` sit **exactly two slots lower** — precisely the two positions
January gives to `OP_HASH160` and `OP_HASH256`. Two opcodes were inserted between the versions, and
they are those two.

**`OP_HASH160` is the opcode that makes a Bitcoin address possible.** Pay-to-public-key-hash is
`OP_DUP OP_HASH160 <20-byte hash> OP_EQUALVERIFY OP_CHECKSIG`; without `OP_HASH160` there is no way
to pay to the *hash* of a key, only to a key itself — which is what both genesis blocks in fact do.

The lab had already concluded from the source diff that P2PKH and the address format are
January-born. This establishes the same thing by a different and stronger route: a cryptographic
commitment made by the author in September 2008, which can only be satisfied by an opcode table that
has no `OP_HASH160` in it.

### It also validates the whole reconstruction at once

The two unknowns were solved against everything else being right. Had `nSequence` been on `CTxIn`
rather than `CTxOut`, or `nVersion` been included under `SER_GETHASH`, or `posNext` been in the hash
preimage, or the `CBigNum` pubkey literal not been byte-reversed — **no** pair of bytes in 65,536
would have matched. One did. Every structural claim in the table below is therefore confirmed by the
same 256-bit check, not asserted alongside it.

An independent corroboration, from Satoshi's own debug line: it prints
`scriptPubKey=51b0`, which is bytes **4 and 5** of the script. Under this reconstruction those bytes
are the third and fourth of the reversed pubkey — `04 d4 51 b0 …`. They match.

## November against January

| | 15 Nov 2008 pre-release | 3 Jan 2009 v0.1.0 |
|---|---|---|
| **coinbase** | `CScript() << 247422313` — an integer | `The Times 03/Jan/2009 Chancellor on brink…` |

> ### ⚠️ On reading `247422313` as a date — don't
>
> The claim circulates that the coinbase integer decodes as a Unix timestamp:
> **`247422313` → 1977-11-03 16:25:13 UTC.** *The arithmetic is correct.* **The inference is not.**
>
> **Every nine-digit integer decodes to some date.** The range `100000000`–`999999999` maps onto
> **1973-03-03 to 2001-09-09** — so any value of that size is *guaranteed* to land on a plausible
> historical date. Finding one is not a discovery; it is arithmetic.
>
> ```
> 247422313  ->  1977-11-03    "significant?"
> 141755     ->  1970-01-02    the nNonce, decoded the same way
> 10000      ->  1970-01-01    the nValue
> 20         ->  1970-01-01    nBits
> ```
>
> **There is no independent reason to read this field as a time.** In the January genesis the coinbase
> carries a newspaper headline — an *external, checkable* commitment. Here it carries a bare integer
> with no unit, no encoding marker, and no corroborating artifact. **The honest reading is the one
> this document already gives: it commits to nothing.**
>
> *Recorded because the numerology is in public circulation (satoshitimeline.com card 8) and will
> otherwise be re-derived by someone who has not checked the base rate.*
| **proof of time** | **none** | the front page of that morning |
| `nTime` | 1221069728 = **2008-09-10** 18:02:08 UTC | 1231006505 = 2009-01-03 18:15:05 UTC |
| `nBits` | `20` — leading-zero **bits**, `MINPROOFOFWORK=20`, "ridiculously easy for testing" | `0x1d00ffff` — compact target |
| `nNonce` | **141,755** (~1.4 × 10⁵ hashes) | 2,083,236,893 (~2.1 × 10⁹ hashes) |
| **work** | 1× | ~**14,700×** |
| `nValue` | 10000, and `COIN = 1000000` → **0.01 coins** | 5000000000, `COIN = 100000000` → 50 coins |
| block hash preimage | **76 bytes**, `nVersion` excluded | 80 bytes, `nVersion` included |
| tx hash preimage | `nVersion` excluded under `SER_GETHASH` | `nVersion` included |
| `nSequence` lives on | **`CTxOut`** (plus a disk-only `posNext`) | `CTxIn` |
| pubkey literal | `CBigNum` **byte-reversed**; reversed begins `0x04` | same convention |
| archive | fragment — 4 source files, uncompilable | complete, builds to a running client |

Two of those rows carry the weight.

**The timestamp is 10 September 2008.** The whitepaper was published to the cryptography mailing
list on 31 October 2008 and this preview circulated around 16 November. The genesis in it was
therefore stamped roughly seven weeks *before* the design was public and two months before the code
was shown to anyone. A genesis coinbase can commit to a moment only if the moment is external and
checkable; this one commits to nothing, and its timestamp is simply when the developer happened to
run it.

**The coinbase is the integer 247422313.** It serializes as `04 695dbf0e` — a four-byte push of
`0x0EBF5D69`. There is no message, no newspaper, nothing that could not have been produced a year
earlier or a year later. The proof-of-time device that everyone knows Bitcoin for **does not exist
in November.** It arrives, fully formed, in January.

## What this establishes

The lab already showed that the *monetary* constitution is January-born: subsidy 100→50, halving
100k→210k, block time 15→10 minutes, `COIN` 1e6→1e8, so the "satoshi" as a unit is genesis-born.
This adds the other half. **The evidentiary constitution is January-born too.** Real difficulty, a
committed external fact, and a genesis whose coinbase says something checkable all appear at the
same moment, in the same release, as the money.

November has the data structures and not the commitment. It is the design of Bitcoin without the
one gesture that makes a chain's first block mean anything, and the archive carrying it is a
fragment its author labelled as such.

That is worth stating plainly because the November pre-release is routinely described as "the first
Bitcoin code," which it is, and then treated as though it were a first Bitcoin, which it is not. It
had no network, no release, no complete source, and a genesis that commits to nothing.

## Verify it yourself

```python
import hashlib, struct
h2 = lambda b: hashlib.sha256(hashlib.sha256(b).digest()).digest()
merkle = bytes.fromhex("769a5e93fac273fd825da42d39ead975b5d712b2d50953f35a4fdebdec8083e3")[::-1]
hdr = b"\x00"*32 + merkle + struct.pack("<III", 1221069728, 20, 141755)
assert len(hdr) == 76
print(h2(hdr)[::-1].hex())
# 000006b15d1327d67e971d1de9116bd60a3a01556c91b6ebaa416ebc0cfaa646
```

The merkle root above is taken from the debug comment in `main.cpp` rather than recomputed, for the
reason given earlier. Everything else is derived.

**NOT money.**
