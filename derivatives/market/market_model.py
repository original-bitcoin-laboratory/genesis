"""Executable MODEL of v0.1's commerce subsystem (R6 — the marketplace runs).

The static audit (`inventory/MARKET_AUDIT.md`) showed v0.1 shipped a working,
off-chain decentralized marketplace. This runs its two core mechanisms:

1. **Signed listings / reviews** — `CProduct`/`CReview` are signed over their hash
   *excluding the signature* (`GetSigHash = SerializeHash(*this, SER_GETHASH|
   SER_SKIPSIG)`, market.h:107,165) and verified with `CKey::Verify`
   (market.cpp:203,239). Modeled with real secp256k1 (a *model* field serialization,
   not byte-exact to v0.1's CDataStream — the sign→verify mechanism is faithful).

2. **The "atoms" web-of-trust reputation** — `CUser::AddAtom` flow-through
   (`nFlowthroughRate=2`, random atom to `vAtomsOut`; market.cpp:109) and
   `AddAtomsAndPropagate`'s two-frontier flood over `vLinksOut` (market.cpp:143).
   This is pure algorithm and is reproduced exactly.

Off-chain by design (audit finding): this is the commerce layer a node carries, not
blockchain state. Evidence level: MODEL.
"""

from __future__ import annotations

import bisect
import hashlib
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "model"))
from tx_sighash import new_key                          # noqa: E402  (secp256k1 keygen)

FLOWTHROUGH = 2                                          # nFlowthroughRate (market.h:9)


def dsha256(b: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


# ---- signed listings / reviews (CProduct / CReview) ---------------------------

def _sign_hash(priv, h: bytes) -> bytes:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec, utils
    return priv.sign(h, ec.ECDSA(utils.Prehashed(hashes.SHA256())))


def _verify_hash(pub_sec: bytes, h: bytes, sig: bytes) -> bool:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec, utils
    try:
        pub = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), bytes(pub_sec))
        pub.verify(bytes(sig), h, ec.ECDSA(utils.Prehashed(hashes.SHA256())))
        return True
    except (InvalidSignature, ValueError):
        return False


class SignedMarketObject:
    """A CProduct/CReview-style signed object: fields + pubkey + sig, signed over the
    fields (the signature excluded from the hash, as GetSigHash does)."""

    def __init__(self, kind: str, fields: dict):
        self.kind = kind                                # "product" | "review"
        self.fields = dict(fields)
        self.pubkey = b""
        self.sig = b""

    def sig_hash(self) -> bytes:
        # deterministic serialization of the signed content (fields + pubkey), no sig
        parts = [self.kind.encode()]
        for k in sorted(self.fields):
            v = self.fields[k]
            parts.append(k.encode())
            parts.append(v if isinstance(v, bytes) else str(v).encode())
        parts.append(self.pubkey)
        return dsha256(b"\x00".join(parts))

    def sign(self, priv, pub_sec: bytes):
        self.pubkey = pub_sec
        self.sig = _sign_hash(priv, self.sig_hash())

    def verify(self) -> bool:                            # CReview::AcceptReview / CProduct::CheckSignature
        return bool(self.sig) and _verify_hash(self.pubkey, self.sig_hash(), self.sig)

    def user_hash(self) -> bytes:                        # GetUserHash = Hash(vchPubKeyFrom)
        return dsha256(self.pubkey)


def make_product(priv, pub, name, price):
    p = SignedMarketObject("product", {"name": name, "price": price})
    p.sign(priv, pub)
    return p


def make_review(priv, pub, hash_to: bytes, text: str):
    r = SignedMarketObject("review", {"hashTo": hash_to, "text": text})
    r.sign(priv, pub)
    return r


# ---- atoms web-of-trust reputation (CUser / AddAtom / AddAtomsAndPropagate) ----

def _in_sorted(v: list, x: int) -> bool:
    i = bisect.bisect_left(v, x)
    return i < len(v) and v[i] == x


def _union_sorted(v1: list, v2: list) -> None:
    """v1 = sorted(set(v1) | set(v2)), in place (market.cpp Union)."""
    merged = sorted(set(v1) | set(v2))
    v1[:] = merged


class CUser:
    def __init__(self):
        self.vAtomsIn: list[int] = []
        self.vAtomsNew: list[int] = []
        self.vAtomsOut: list[int] = []
        self.vLinksOut: list[bytes] = []

    def atom_count(self) -> int:                         # GetAtomCount (market.h:58)
        return len(self.vAtomsIn) + len(self.vAtomsNew)

    def add_atom(self, nAtom: int, fOrigin: bool, rng):  # CUser::AddAtom (market.cpp:109)
        if _in_sorted(self.vAtomsIn, nAtom) or nAtom in self.vAtomsNew:
            return                                       # ignore duplicates
        if nAtom == 0 or fOrigin:                        # zero atom / origin: straight to vAtomsIn
            _union_sorted(self.vAtomsIn, [nAtom])
            if fOrigin:
                self.vAtomsOut.append(nAtom)             # origin atoms always propagate
            return
        self.vAtomsNew.append(nAtom)
        if len(self.vAtomsNew) >= FLOWTHROUGH or not self.vAtomsOut:
            self.vAtomsOut.append(self.vAtomsNew[rng.randrange(len(self.vAtomsNew))])  # random flow-through
            self.vAtomsNew.sort()
            _union_sorted(self.vAtomsIn, self.vAtomsNew)
            self.vAtomsNew = []


class ReviewGraph:
    """The user/atoms store (stands in for CReviewDB's users)."""

    def __init__(self, rng=None):
        import random
        self.users: dict[bytes, CUser] = {}
        self.rng = rng or random.Random(0)

    def user(self, h: bytes) -> CUser:
        return self.users.setdefault(h, CUser())

    def link(self, hash_from: bytes, hash_to: bytes):    # AcceptReview adds vLinksOut (market.cpp:219)
        self.user(hash_from).vLinksOut.append(hash_to)

    def add_atoms_and_propagate(self, hash_start: bytes, atoms: list[int], fOrigin: bool) -> None:
        # two-frontier flood over vLinksOut (market.cpp:143-189)
        frontier = {hash_start: list(atoms)}
        while frontier:
            nxt: dict[bytes, list[int]] = {}
            for hash_user, received in frontier.items():
                u = self.user(hash_user)
                n_out = len(u.vAtomsOut)
                for a in received:
                    u.add_atom(a, fOrigin, self.rng)
                fOrigin = False                          # only the start is origin
                if len(u.vAtomsOut) > n_out:             # propagate newly-out atoms downstream
                    new_out = u.vAtomsOut[n_out:]
                    for link in u.vLinksOut:
                        nxt.setdefault(link, []).extend(new_out)
            frontier = nxt


if __name__ == "__main__":
    priv, pub = new_key()
    p = make_product(priv, pub, "widget", 100)
    print("product signature verifies:", p.verify())
    g = ReviewGraph()
    seller, buyer = p.user_hash(), dsha256(b"buyer")
    g.link(buyer, seller)                                # a review from buyer about seller
    g.add_atoms_and_propagate(seller, [1, 2, 3], fOrigin=True)
    print("seller atom count after origin seeding:", g.user(seller).atom_count())
