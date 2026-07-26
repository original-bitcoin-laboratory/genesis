"""The commerce subsystem runs (R6 executable model): signed listings/reviews
verify (and reject tampering), and the atoms web-of-trust reputation propagates
exactly as market.cpp specifies. Evidence: MODEL."""

import pathlib
import random
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "model"))
sys.path.insert(0, str(_HERE))

from market_model import (CUser, FLOWTHROUGH, ReviewGraph, dsha256, make_product,
                          make_review)
from tx_sighash import new_key


# ---- signed listings / reviews -----------------------------------------------

def test_product_signature_verifies():
    priv, pub = new_key()
    p = make_product(priv, pub, "widget", 100)
    assert p.verify()


def test_tampering_a_signed_field_breaks_verification():
    priv, pub = new_key()
    p = make_product(priv, pub, "widget", 100)
    p.fields["price"] = 1                                 # change the price after signing
    assert not p.verify()


def test_a_review_is_signed_by_its_author():
    priv, pub = new_key()
    seller = dsha256(b"seller-pubkey")
    r = make_review(priv, pub, seller, "great, fast shipping")
    assert r.verify()
    assert r.user_hash() == dsha256(pub)                 # GetUserHash = Hash(pubkey)
    # a different key cannot have produced this signature
    _, other = new_key()
    r.pubkey = other
    assert not r.verify()


# ---- atoms flow-through (CUser::AddAtom) --------------------------------------

def test_origin_atoms_go_straight_out():
    u = CUser(); rng = random.Random(1)
    u.add_atom(1, fOrigin=True, rng=rng)
    assert u.vAtomsIn == [1] and u.vAtomsOut == [1]      # origin propagates immediately


def test_flow_through_needs_rate_2_once_out_is_seeded():
    u = CUser(); rng = random.Random(1)
    u.add_atom(1, fOrigin=True, rng=rng)                 # seeds vAtomsOut
    u.add_atom(5, fOrigin=False, rng=rng)
    assert u.vAtomsOut == [1] and u.vAtomsNew == [5]     # 1 < rate -> held, not out
    u.add_atom(6, fOrigin=False, rng=rng)
    assert len(u.vAtomsOut) == 2                          # rate reached -> one flows through
    assert u.vAtomsNew == [] and set(u.vAtomsIn) >= {1, 5, 6}


def test_zero_atom_never_propagates():
    u = CUser(); rng = random.Random(1)
    u.add_atom(0, fOrigin=False, rng=rng)
    assert 0 in u.vAtomsIn and u.vAtomsOut == []         # the zero atom never goes out


def test_duplicate_atoms_are_ignored():
    u = CUser(); rng = random.Random(1)
    u.add_atom(7, fOrigin=True, rng=rng)
    before = (list(u.vAtomsIn), list(u.vAtomsOut))
    u.add_atom(7, fOrigin=True, rng=rng)                 # dup
    assert (u.vAtomsIn, u.vAtomsOut) == before


# ---- propagation across the trust graph --------------------------------------

def test_atoms_propagate_along_review_links():
    g = ReviewGraph(random.Random(3))
    seller = dsha256(b"seller")
    downstream = dsha256(b"downstream")
    g.user(seller).vLinksOut.append(downstream)          # seller links to downstream
    g.add_atoms_and_propagate(seller, [1, 2, 3], fOrigin=True)
    assert g.user(seller).atom_count() == 3
    assert g.user(downstream).atom_count() > 0           # trust flowed one hop out


def test_review_then_reputation_end_to_end():
    g = ReviewGraph(random.Random(5))
    priv, pub = new_key()
    reviewer = dsha256(pub)
    seller = dsha256(b"seller-pubkey")
    r = make_review(priv, pub, seller, "vouch")
    assert r.verify()                                    # accept only if signed
    g.link(reviewer, seller)                             # AcceptReview: reviewer -> seller
    g.add_atoms_and_propagate(seller, [1], fOrigin=True)
    assert seller in g.users and g.user(seller).atom_count() >= 1
