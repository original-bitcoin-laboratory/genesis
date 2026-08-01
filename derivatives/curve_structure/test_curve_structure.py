"""secp256k1 curve structure, executed: the GLV endomorphism (beta,lambda derivable, ~0.79-bit rho
tax, 2^127.03 best generic attack), textbook safety, the un-derivable generator trust-atom + non-minimal
977, and the twist's ~33-bit leak. All from the published constants with pure-integer math. MODEL."""

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from curve_structure import (                                            # noqa: E402
    P, N, curve_order, endomorphism, field_constant_minimality, is_prime, provenance, safety, twist,
)


# ---- (1) the GLV endomorphism is derivable and real --------------------------

def test_endomorphism_derived_matches_published_and_holds():
    e = endomorphism()
    assert e["j"] == 0                          # a=0 -> j=0 -> the order-3 endomorphism exists
    assert e["derived_match"]                   # beta,lambda derived from p,n == published values
    assert e["endo_holds"]                      # [lambda]G == (beta*Gx, Gy)
    assert e["relation"]                        # 1 + L + L^2 == 0 (mod n), and for beta (mod p)


def test_endomorphism_tax_is_about_0_79_bit_and_2_127():
    e = endomorphism()
    assert round(e["endo"], 2) == 127.03        # secp256k1's actual best generic classical attack
    assert round(e["neg"], 2) == 127.83         # the usual "128-bit" (negation only)
    assert abs(e["tax_bits"] - 0.792) < 1e-3    # sqrt(3) factor
    assert abs(e["below_p256"] - 0.792) < 1e-3  # ~0.79 bit below P-256 (which has no endomorphism)
    assert e["endo"] < e["neg"] < e["naive"]    # ordering: endomorphism is the cheapest attack


# ---- (2) textbook safety -----------------------------------------------------

def test_curve_clears_textbook_safety():
    s = safety()
    assert all(s.values())
    for key in ("p is prime", "n (group order) is prime", "cofactor h == 1",
                "not anomalous (n != p)", "MOV-safe (embed degree>200)", "G is on the curve"):
        assert s[key] is True
    assert is_prime(P) and is_prime(N)


# ---- (3) the trust atom: generator provenance + the 977 constant -------------

def test_generator_is_not_a_documented_nums_point():
    assert provenance()["nums_hit"] is False    # Gx is not sha256 of any obvious seed mod p


def test_977_is_not_the_minimal_prime_constant():
    pr = provenance()
    assert pr["p_is_977"]                        # p == 2^256 - 2^32 - 977
    assert pr["first_prime_c"] == 263            # a smaller c already gives a prime
    assert pr["first_3mod4_c"] == 361            # smaller still even with the 3-mod-4 constraint
    assert pr["c977_minimal"] is False           # so 977 carries an unpublished extra constraint


# ---- (4) the quadratic twist -------------------------------------------------

def test_twist_small_factors_leak_and_factorization_is_exact():
    tw = twist()
    assert tw["small"] == {3: 2, 13: 2, 3319: 1, 22639: 1}
    assert tw["leak_bits"] == 33                 # ~33 key bits vs a non-validating implementation
    assert tw["big_prime"]                       # the large cofactor is prime
    assert tw["big_bits"] >= 200                 # ~2^220
    assert tw["factorization_exact"]             # small factors * big cofactor == twist order exactly


# ---- (5) the field constant 977 is forced, not chosen ------------------------

def test_cm_point_count_reproduces_secp256k1_order():
    # the CM (j=0) point-count is validated against the published order before it's trusted elsewhere
    assert curve_order(P) == N and is_prime(N)


def test_977_is_the_minimal_design_satisfying_constant():
    minimal, rows = field_constant_minimality(1000)
    assert minimal == 977                        # smallest c meeting all four constraints
    by_c = {c: (m4, m3, op, allfour) for (c, m4, m3, op, allfour) in rows}   # by_c[c] = (p%4, p%3, order_prime, all4)
    assert by_c[263][1] == 1 and by_c[263][2] is False   # 263: p%3==1 but composite curve order
    assert by_c[361][0] == 3 and by_c[361][1] == 2       # 361: p%4==3 but p%3==2 (no endomorphism)
    assert by_c[977][2] is True and by_c[977][:2] == (3, 1)  # 977: prime order, p%4==3, p%3==1
