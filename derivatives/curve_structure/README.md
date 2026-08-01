# secp256k1 curve structure, executed — the algebra of the curve the origin chose

**Evidence level: `MODEL`.** [`../crypto_conformance/`](../crypto_conformance/) checks v0.1's ECDSA
*behavior* (malleability / low-S vs libsecp256k1). This checks the *structure* of the curve itself —
properties every Bitcoin descendant inherits — derived from the published SEC2 / libsecp256k1 constants
with pure-integer arithmetic (no libraries, no secrets), each re-evaluable identically by anyone.

## What it shows

```
(1) GLV ENDOMORPHISM
    j-invariant = 0   beta,lambda derived == published: True
    [lambda]G == (beta*Gx, Gy): True   1+L+L^2 == 0 (mod n): True
    Pollard-rho: naive ~2^128.326  negation ~2^127.826  +endo ~2^127.033  P-256 ~2^127.826
    endomorphism tax = 0.792 bit; secp256k1 is 0.792 bit below P-256 (a tax, not a break)
(2) TEXTBOOK SAFETY: p prime, n prime, cofactor 1, non-anomalous, MOV-safe, G on curve — all PASS
(3) PROVENANCE: Gx is not sha256(obvious seed) mod p; 977 is not the minimal prime c (263 is)
(4) TWIST: small factors {3^2,13^2,3319,22639} -> ~33-bit leak vs a non-validating impl
```

## The four facts

1. **The GLV endomorphism is derivable, not planted.** `a = 0 ⇒ j-invariant = 0`, which forces an
   order-3 endomorphism `[λ](x,y) = (β·x, y)`. `β` and `λ` are the two nontrivial cube roots of unity
   mod `p` and mod `n` — **derived here from `p` and `n` alone** and matched to the published
   libsecp256k1 values, with `[λ]G == (β·Gx, Gy)` and `1+λ+λ² ≡ 0 (mod n)`. They carry no author
   entropy. Its one real effect is a Pollard-rho speedup of `√6`, so secp256k1's best generic classical
   attack is **~2¹²⁷·⁰³** — ~0.79 bit below NIST P-256 (~2¹²⁷·⁸³), which has no such endomorphism. The
   constants feared as a "backdoor" and praised for GLV speed are the **same object**; the effect is a
   negligible tax, not a break (~2¹²⁷ is unbroken).

2. **The curve clears the textbook safety bar.** `p` and `n` prime, cofactor 1, non-anomalous
   (`n ≠ p`, so Smart's attack is N/A), MOV embedding degree > 200 (no pairing attack), `G` on the
   curve. A classical break would have to defeat one of these.

3. **The one un-derivable constant — where "verify, don't trust" bottoms out.** The generator `G` has
   no published nothing-up-my-sleeve derivation (`Gx` is not `sha256` of any obvious seed, mod `p`), so
   its provenance must be **trusted, not reproduced**. This is benign for the discrete log — any
   generator of the prime-order group is equivalent — but it is the single irreducible trust atom.
   The field prime's constant `977` is likewise **not** the minimal choice (`263` already yields a
   prime; `361` with the 3-mod-4 constraint), so `977` carries an unpublished extra constraint (prime
   curve order + fast reduction). A rigidity wrinkle, not a break. *(This is the neutral, machine-form
   of the "derivable vs un-derivable" test for a backdoor: derivable constants — β, λ — cannot hide a
   master key; only un-derivable ones can, and here the only un-derivable one is a benign generator.)*

4. **The quadratic twist wants point validation.** The twist order has small factors
   `{3², 13², 3319, 22639}` leaking ~33 key bits to an implementation that **skips** point validation;
   the factorization is verified to reconstruct the twist order exactly, and the large cofactor
   (~2²²⁰) is prime. libsecp256k1 validates points, so Bitcoin is unaffected — a "handle with care",
   not a free curve.

## Why it's a MODEL

Everything is pure-integer arithmetic over the published constants (`p`, `n`, `G`, `a=0`, `b=7`), so
there is nothing to trust in the code beyond the constants themselves — which are the public curve.
Primality uses fixed-seed Miller-Rabin (deterministic across runs). Honest boundary: this documents the
curve's *structure*, not v0.1's runtime crypto (that is `crypto_conformance/`); together they cover the
signature layer's behavior and the curve it runs on. No key, no secret, no chain privileged, no identity
claim.

## Tests (`test_curve_structure.py`, 6)

The endomorphism (derived == published, `[λ]G`, `1+λ+λ²≡0`, `j=0`); the tax (2¹²⁷·⁰³, 0.79 bit, below
P-256); textbook safety (all six pass); the generator (not a NUMS point); the 977 constant (263/361
smaller ⇒ not minimal); the twist (`{3²,13²,3319,22639}`, ~33-bit leak, exact factorization, prime
cofactor).

```bash
python curve_structure.py   # the demo above
python -m pytest            # 6 passed
```

## Boundary

MODEL; pure-integer derivations from the published SEC2 / libsecp256k1 constants; no chain privileged;
not a break or backdoor claim (the endomorphism is a ~0.79-bit tax, the trust atom is benign after
15+ years). It is a *tool*, never authority (`common/AUTHORITY.md`). See the neutral write-up in
[`common/conformance/CURVE_STRUCTURE.md`](https://github.com/original-bitcoin-laboratory/common/blob/main/conformance/CURVE_STRUCTURE.md).
