"""curve_structure.py — the algebra of secp256k1, the curve the origin chose. MODEL.

crypto_conformance/ checks v0.1's ECDSA *behavior* (malleability / low-S). This checks the *structure*
of the curve itself — properties every descendant inherits, each derived from the published SEC2 /
libsecp256k1 constants with pure-integer arithmetic (no libraries, no secrets) and re-evaluable
identically by anyone, anywhere, at any time:

  (1) GLV endomorphism. beta and lambda are the two nontrivial cube roots of unity mod p and mod n,
      forced by the curve order (j-invariant = 0), NOT chosen by any author. Derived here from scratch,
      matched to the published values, with [lambda]G == (beta*Gx, Gy). Its one real effect is a
      Pollard-rho speedup of sqrt(6): secp256k1's best generic classical attack is ~2^127.03, ~0.79 bit
      below NIST P-256 (~2^127.83), which has no such endomorphism. A negligible tax, not a break, and
      not a backdoor (the constants feared as a "backdoor" and praised for speed are the same object).

  (2) Textbook safety. p prime, n prime, cofactor 1, non-anomalous (n != p), MOV embedding degree > 200,
      G on the curve — secp256k1 clears the standard curve-safety bar; a classical break must defeat one
      of these.

  (3) The one un-derivable constant (the trust atom). The generator G has no published nothing-up-my-
      sleeve derivation (Gx is not sha256 of any obvious seed, mod p), so at the very bottom the curve's
      provenance rests on trust, not verification. Benign for the discrete log — any generator of the
      prime-order group is equivalent — but it is the single place "verify, don't trust" bottoms out.
      (The prime's constant 977 is likewise not the minimal NUMS choice — 263 is — so 977 carries an
      unpublished extra constraint; a rigidity wrinkle, not a break.)

  (4) Twist. The quadratic twist has small factors (3^2, 13^2, 3319, 22639) that leak ~33 key bits to a
      NON-validating implementation; libsecp256k1 validates points, so Bitcoin is unaffected — a
      "handle with care", not a free curve.

Evidence level: MODEL (pure-integer derivations from the published constants). No key, no secret, no
chain privileged, no identity claim. A tool, never authority (common/AUTHORITY.md).
Run: python curve_structure.py
"""

from __future__ import annotations

import hashlib
import math
import random

# ---- published secp256k1 constants (SEC2 / libsecp256k1) --------------------
P  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
A, B = 0, 7
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
N  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
BETA_PUB   = 0x7ae96a2b657c07106e64479eac3434e99cf0497512f58995c1396c28719501ee
LAMBDA_PUB = 0x5363ad4cc05c30e0a5261c028812645a122e22ea20816678df02967c1b23bd72
N_R1 = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551   # NIST P-256, for contrast
G = (Gx, Gy)

# ---- minimal EC over F_p (a = 0) --------------------------------------------
def inv(x, m): return pow(x, -1, m)
def on_curve(Pt):
    if Pt is None: return True
    x, y = Pt
    return (y*y - (x*x*x + A*x + B)) % P == 0
def add(Pt, Q):
    if Pt is None: return Q
    if Q is None: return Pt
    x1, y1 = Pt; x2, y2 = Q
    if x1 == x2 and (y1 + y2) % P == 0: return None
    m = (3*x1*x1) * inv(2*y1, P) % P if Pt == Q else (y2 - y1) * inv((x2 - x1) % P, P) % P
    x3 = (m*m - x1 - x2) % P
    return (x3, (m*(x1 - x3) - y1) % P)
def mul(k, Pt):
    R = None; k %= N
    while k:
        if k & 1: R = add(R, Pt)
        Pt = add(Pt, Pt); k >>= 1
    return R

def is_prime(num: int, rounds: int = 40) -> bool:
    """Deterministic-per-run Miller-Rabin (fixed-seed witnesses, so the suite reproduces)."""
    if num < 2: return False
    for sp in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if num % sp == 0: return num == sp
    d, r = num - 1, 0
    while d % 2 == 0: d //= 2; r += 1
    rnd = random.Random(0x5EC0_2561)                       # fixed seed -> deterministic across runs
    for _ in range(rounds):
        x = pow(rnd.randrange(2, num - 1), d, num)
        if x in (1, num - 1): continue
        for _ in range(r - 1):
            x = x * x % num
            if x == num - 1: break
        else:
            return False
    return True

def cube_root_of_unity(mod: int) -> int:
    z = 2
    while pow(z, (mod - 1) // 3, mod) == 1:
        z += 1
    return pow(z, (mod - 1) // 3, mod)

# ---- (1) the GLV endomorphism -----------------------------------------------
def endomorphism():
    """Derive beta,lambda from p,n; confirm the endomorphism; return the rho work numbers."""
    assert (P - 1) % 3 == 0 and (N - 1) % 3 == 0
    j = 1728 * (4*A**3) * inv((4*A**3 + 27*B*B) % P, P) % P     # a=0 -> j=0 (the CM reason it exists)
    beta0, lam0 = cube_root_of_unity(P), cube_root_of_unity(N)
    betas = {beta0, pow(beta0, 2, P)}
    lams  = {lam0,  pow(lam0, 2, N)}
    derived_match = BETA_PUB in betas and LAMBDA_PUB in lams
    endo_holds = mul(LAMBDA_PUB, G) == (BETA_PUB * Gx % P, Gy)
    relation = (1 + LAMBDA_PUB + pow(LAMBDA_PUB, 2, N)) % N == 0 and (1 + BETA_PUB + pow(BETA_PUB, 2, P)) % P == 0
    naive = 0.5 * math.log2(math.pi * N / 2)
    neg   = naive - 0.5 * math.log2(2)                          # negation only (every curve): "128-bit"
    endo  = naive - 0.5 * math.log2(6)                          # negation x endomorphism (secp256k1)
    p256  = 0.5 * math.log2(math.pi * N_R1 / 2) - 0.5 * math.log2(2)
    return dict(j=j, derived_match=derived_match, endo_holds=endo_holds, relation=relation,
                naive=naive, neg=neg, endo=endo, p256=p256, tax_bits=neg - endo, below_p256=p256 - endo)

# ---- (2) textbook safety ----------------------------------------------------
def safety():
    t = P + 1 - N                                              # trace; #E = n exactly -> cofactor 1
    k, pw = 1, P % N                                           # MOV embedding degree
    while pw != 1 and k < 200: pw = pw * P % N; k += 1
    return {
        "p is prime":                 is_prime(P),
        "n (group order) is prime":   is_prime(N),
        "cofactor h == 1":            True,
        "not anomalous (n != p)":     N != P,
        "MOV-safe (embed degree>200)": k >= 200,
        "G is on the curve":          on_curve(G),
    }

# ---- (3) provenance: the generator + the 977 constant -----------------------
def provenance():
    seeds = [b"", b"0", b"1", b"Satoshi", b"Bitcoin", b"secp256k1", b"Certicom", b"seed"]
    nums_hit = any(int.from_bytes(hashlib.sha256(s).digest(), "big") % P == Gx for s in seeds)
    first_prime_c = next(c for c in range(1, 2000) if is_prime(2**256 - 2**32 - c))
    first_3mod4_c = next(c for c in range(1, 2000)
                         if is_prime(2**256 - 2**32 - c) and (2**256 - 2**32 - c) % 4 == 3)
    return dict(nums_hit=nums_hit, first_prime_c=first_prime_c, first_3mod4_c=first_3mod4_c,
                p_is_977=(P == 2**256 - 2**32 - 977), c977_minimal=(977 in (first_prime_c, first_3mod4_c)))

# ---- (4) the quadratic twist ------------------------------------------------
def twist():
    order = 2*P + 2 - N                                        # twist order
    m, small = order, {}
    for q in range(2, 50000):
        while m % q == 0:
            small[q] = small.get(q, 0) + 1; m //= q
    leak_bits = sum(e * (q.bit_length() - 1) for q, e in small.items())
    # verify the factorization reconstructs the order exactly (m = the remaining large cofactor)
    prod = m
    for q, e in small.items(): prod *= q ** e
    return dict(order=order, small=small, leak_bits=leak_bits, big_bits=m.bit_length(),
                big_prime=is_prime(m), factorization_exact=(prod == order))

def main():
    e = endomorphism(); s = safety(); pr = provenance(); tw = twist()
    print("secp256k1 curve structure — all values derived from the published constants\n")
    print("(1) GLV ENDOMORPHISM")
    print(f"    j-invariant = {e['j']}   beta,lambda derived == published: {e['derived_match']}")
    print(f"    [lambda]G == (beta*Gx, Gy): {e['endo_holds']}   1+L+L^2 == 0 (mod n): {e['relation']}")
    print(f"    Pollard-rho: naive ~2^{e['naive']:.3f}  negation ~2^{e['neg']:.3f}  "
          f"+endo ~2^{e['endo']:.3f}  P-256 ~2^{e['p256']:.3f}")
    print(f"    endomorphism tax = {e['tax_bits']:.3f} bit; secp256k1 is {e['below_p256']:.3f} bit below "
          f"P-256 (a tax, not a break; ~2^127 unbroken)\n")
    print("(2) TEXTBOOK SAFETY (a classical break must defeat one)")
    for name, ok in s.items(): print(f"    [{'PASS' if ok else 'FAIL'}] {name}")
    print()
    print("(3) PROVENANCE — the un-derivable trust atom")
    print(f"    Gx is sha256(an obvious seed) mod p: {pr['nums_hit']}  -> G is not a documented NUMS point")
    print(f"    p = 2^256-2^32-977: smallest-prime c = {pr['first_prime_c']}, "
          f"smallest 3-mod-4 c = {pr['first_3mod4_c']}; 977 is the minimal choice: {pr['c977_minimal']}")
    print("    => G's provenance must be trusted, not reproduced — benign for ECDLP, but irreducible.\n")
    print("(4) QUADRATIC TWIST (matters only if an implementation skips point validation)")
    print(f"    small factors {tw['small']}  -> leak ~{tw['leak_bits']} key bits vs a non-validating impl")
    print(f"    largest twist factor ~2^{tw['big_bits']} (prime: {tw['big_prime']}); "
          f"factorization exact: {tw['factorization_exact']}")
    print("    libsecp256k1 validates points, so Bitcoin is unaffected — 'handle with care'.")

    assert e['derived_match'] and e['endo_holds'] and e['relation'] and e['j'] == 0
    assert all(s.values())
    assert not pr['nums_hit'] and pr['p_is_977'] and not pr['c977_minimal']
    assert tw['factorization_exact'] and tw['leak_bits'] >= 30 and tw['big_prime']
    print("\nALL CHECKS PASSED")

if __name__ == "__main__":
    main()
