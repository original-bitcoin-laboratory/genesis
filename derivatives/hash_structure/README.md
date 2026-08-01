# Bitcoin's hash layer, executed — NUMS constants, merkle ambiguity, the RIPEMD floor

**Evidence level: `MODEL` / pure computation.** Companion to [`../curve_structure/`](../curve_structure/):
that maps the elliptic curve (the signature layer); this maps the **hash layer** — proof-of-work, txids,
the merkle tree, and addresses — from the published constants and the hash functions themselves.

## What it shows

```
(1) SHA-256 constants vs roots of the first primes:
    K[0..63] == frac(cuberoot(prime_i))*2^32 : 64/64    H[0..7] == frac(sqrt)*2^32 : 8/8
(2) 64-byte-transaction merkle ambiguity:
    dsha256(L||R) as an interior node == txid of the 64-byte tx L||R : True
(3) hash security margins:
    RIPEMD-160 ~2^80  <- FLOOR ;  SHA-256 ~2^128 ;  secp256k1 ~2^127
```

## The three facts

1. **SHA-256's constants are nothing-up-my-sleeve.** The 64 round constants `K` and 8 initial values
   `H` are the first 32 fractional bits of the **cube roots / square roots of the first primes** —
   reproduced here from the primes by exact integer arithmetic (`frac(p^(1/3))·2³² = icbrt(p<<96) & 2³²−1`).
   So Bitcoin's hash layer is **fully derivable**, leaving no room for a hidden relation. Contrast the
   curve: secp256k1's generator `G` has **no** such derivation (`curve_structure/`). The hashes are
   *more* transparent than the curve; `G` is the single irreducible trust-atom in the whole system.

2. **The 64-byte-transaction merkle ambiguity.** Leaves and interior nodes are hashed with the same
   double-SHA-256, so a transaction whose raw serialization is exactly **64 bytes** has a `txid` equal
   to the interior-node hash of its two 32-byte halves. A verifier handed a merkle branch cannot tell a
   64-byte leaf from an interior node — enabling **forged SPV inclusion proofs**. A collision with no
   broken hash (cf. the odd-level duplication in `common/conformance/CONSENSUS_BEHAVIORS.md`). The
   defensive rule is to reject 64-byte transactions.

3. **RIPEMD-160 is the weakest margin.** Addresses commit to `HASH160 = RIPEMD-160(SHA-256(x))`,
   160-bit, so collision resistance is only **~2⁸⁰** — below SHA-256's 2¹²⁸ and secp256k1's ~2¹²⁷. Real,
   astronomically far off, but the floor of the system; the module demonstrates a small birthday
   collision so the 2⁸⁰ scaling is concrete.

## Why it's a MODEL

Pure computation over the published constants and the standard hash functions; the SHA-256 whose
constants are verified is confirmed to be the standard function (`sha256("") = e3b0c442…`). No key, no
secret, no chain privileged. Honest boundary: this documents the hash layer's *structure/margins*, not
v0.1's runtime — but every fact holds for every version that keeps these primitives.

## Tests (`test_hash_structure.py`, 5)

SHA-256 K/H are the prime roots (64/64, 8/8); `icbrt` exact; SHA-256 is the standard function; the
64-byte merkle ambiguity; RIPEMD-160 is 160-bit and the birthday collision scales as ~2^(bits/2).

```bash
python hash_structure.py   # the demo above
python -m pytest           # 5 passed
```

## Boundary

MODEL / pure computation; no chain privileged; not a break claim (SHA-256 is clean NUMS, the merkle
ambiguity is defended by rejecting 64-byte txs, the 2⁸⁰ margin is far off). A tool, never authority
(`common/AUTHORITY.md`). Neutral write-up in
[`common/conformance/HASH_STRUCTURE.md`](https://github.com/original-bitcoin-laboratory/common/blob/main/conformance/HASH_STRUCTURE.md).
