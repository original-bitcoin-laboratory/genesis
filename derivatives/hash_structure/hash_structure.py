"""hash_structure.py — the algebra of Bitcoin's hash layer. MODEL / pure computation.

Companion to curve_structure.py: that maps the elliptic curve (the signature layer); this maps the
hash layer (proof-of-work, txids, the merkle tree, addresses), from the published constants and the
hash functions themselves. All re-evaluable by anyone.

  (1) SHA-256's constants are nothing-up-my-sleeve. The 64 round constants K and 8 initial values H are
      the first 32 fractional bits of the cube roots / square roots of the first primes — reproduced
      here from the primes by integer arithmetic. The hash layer is thus FULLY derivable, MORE
      transparent than the curve, whose generator G is the single un-derivable constant
      (curve_structure.py). Derivability is the backdoor test: SHA-256 leaves no room for a hidden
      relation; G stays the lone (benign) trust-atom in the whole system.

  (2) The 64-byte-transaction merkle ambiguity. Leaves and internal nodes are hashed with the same
      double-SHA-256, so a transaction whose raw serialization is exactly 64 bytes has a txid equal to
      the internal-node hash of its two 32-byte halves — a leaf/node ambiguity enabling forged SPV
      inclusion proofs. A collision with no broken hash (cf. the odd-level duplication in the
      consensus-behaviors map). The defensive rule: reject 64-byte transactions.

  (3) RIPEMD-160 is the weakest margin. Addresses commit to HASH160 = RIPEMD-160(SHA-256(x)), 160-bit,
      so collision resistance is ~2^80 — below SHA-256's 2^128 and secp256k1's ~2^127. Real, far off,
      the floor of the system. A small birthday collision is demonstrated to make the scaling concrete.

Evidence level: MODEL / pure computation. No key, no secret, no chain privileged. A tool, never
authority (common/AUTHORITY.md). Run: python hash_structure.py
"""
from __future__ import annotations

import hashlib
from math import isqrt, log2

# ---- (1) SHA-256 constants are cube/square roots of the first primes ----------
def icbrt(n):
    if n < 2: return n
    x = 1 << (-(-n.bit_length() // 3) + 1)
    while True:
        y = (2*x + n//(x*x)) // 3
        if y >= x: break
        x = y
    while x*x*x > n: x -= 1
    while (x+1)**3 <= n: x += 1
    return x
def first_primes(k):
    out, n = [], 2
    while len(out) < k:
        if all(n % d for d in out if d*d <= n): out.append(n)
        n += 1
    return out
_MASK = (1 << 32) - 1
SHA256_K = [0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
 0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
 0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
 0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
 0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
 0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
 0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
 0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2]
SHA256_H = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19]

def sha256_nums():
    p = first_primes(64)
    okK = sum(1 for i, pr in enumerate(p)     if (icbrt(pr << 96) & _MASK) == SHA256_K[i])
    okH = sum(1 for i, pr in enumerate(p[:8]) if (isqrt(pr << 64) & _MASK) == SHA256_H[i])
    return okK, okH

# ---- (2) the 64-byte-transaction merkle ambiguity ----------------------------
def _dsha(b): return hashlib.sha256(hashlib.sha256(b).digest()).digest()
def merkle_64byte_ambiguity():
    L = _dsha(b"left"); R = _dsha(b"right")            # two 32-byte child hashes
    internal = _dsha(L + R)                            # interior merkle node
    txid_of_64b_tx = _dsha(L + R)                      # leaf txid of the 64-byte tx L||R
    return internal == txid_of_64b_tx and len(L + R) == 64

# ---- (3) RIPEMD-160 margin + a birthday demonstration ------------------------
def hash160(b):
    try: return hashlib.new("ripemd160", hashlib.sha256(b).digest()).digest()
    except Exception: return None
def birthday_collision(bits=32):
    hfn = hash160 if hash160(b"x") is not None else (lambda b: hashlib.sha256(b).digest())
    seen, i = {}, 0
    while True:
        d = hfn(i.to_bytes(6, "big"))[:bits // 8]
        if d in seen: return (seen[d], i), i + 1
        seen[d] = i; i += 1

def main():
    okK, okH = sha256_nums()
    print("(1) SHA-256 constants vs roots of the first primes:")
    print(f"    K[0..63] == frac(cuberoot(prime_i))*2^32 : {okK}/64    H[0..7] == frac(sqrt)*2^32 : {okH}/8")
    print("    => the hash layer is FULLY nothing-up-my-sleeve; secp256k1's generator G is the one")
    print("       un-derivable constant (curve_structure.py). Bitcoin's hashes are more transparent than its curve.")
    amb = merkle_64byte_ambiguity()
    print("\n(2) 64-byte-transaction merkle ambiguity:")
    print(f"    dsha256(L||R) as an interior node == txid of the 64-byte tx L||R : {amb}")
    print("    => a 64-byte tx is indistinguishable from an interior node -> forged SPV proofs; reject 64-byte txs.")
    have = hash160(b"x") is not None
    (a, b), tries = birthday_collision(32)
    print("\n(3) hash security margins:")
    print("    RIPEMD-160 (HASH160/addresses) collision ~2^80  <- the FLOOR;  SHA-256 ~2^128;  secp256k1 ~2^127")
    print(f"    birthday demo, first 32 bits of {'HASH160' if have else 'SHA-256'}: collision after "
          f"{tries:,} tries (~2^{log2(tries):.1f}; predicts 2^16); scales to 2^80 at 160 bits")

    assert okK == 64 and okH == 8
    assert amb
    print("\nALL CHECKS PASSED")

if __name__ == "__main__":
    main()
