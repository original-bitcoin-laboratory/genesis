"""Crypto conformance — v0.1's ECDSA vs the real libsecp256k1.

The Script matrix cross-checks the *interpreter* against independent implementations.
This does the same for the *crypto*: it takes a genuine v0.1 `SignatureHash` and an
ECDSA signature made the way v0.1 makes them (OpenSSL EC, via the lab's MODEL) and
cross-checks it against **libsecp256k1** — the library every modern Bitcoin-lineage
chain runs — through `bitcoinx`, which is backed by `electrumsv-secp256k1` (a real
libsecp256k1 binding).

The result *is* Thread A of `inventory/THE_OPENSSL_THREAD.md`, executed:

- the underlying **ECDSA math is identical** — a canonical (low-S) v0.1 signature
  verifies under libsecp256k1, and a libsecp256k1 signature verifies under our MODEL;
- the one real difference is **malleability**: OpenSSL accepts high-S signatures,
  libsecp256k1 **rejects** them — the exact issue BIP66 / libsecp256k1 fixed.

Neutral: libsecp256k1 is the crypto every descendant inherited (Thread A converged);
using it here is a cross-check tool, never authority. Evidence level: MODEL.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "model"))
from cryptography.hazmat.primitives import hashes                        # noqa: E402
from cryptography.hazmat.primitives.asymmetric import ec, utils          # noqa: E402
from tx_sighash import SIGHASH_ALL, demo_tx, new_key, signature_hash     # noqa: E402

# secp256k1 group order
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

# ---- the independent libsecp256k1 reference (bitcoinx -> electrumsv-secp256k1) ----
LIBSECP = None
try:
    import bitcoinx as _bx
    import electrumsv_secp256k1 as _es  # noqa: F401  (the C lib bitcoinx binds)
    LIBSECP = _bx
except Exception:
    LIBSECP = None

_ID = lambda x: x        # identity "hasher": verify/sign the 32-byte digest directly


def libsecp_verify(sec_pubkey: bytes, digest: bytes, der: bytes) -> bool:
    """Verify a DER signature over a 32-byte digest with libsecp256k1 (rejects high-S)."""
    try:
        return LIBSECP.PublicKey.from_bytes(bytes(sec_pubkey)).verify_der_signature(
            der, digest, hasher=_ID)
    except Exception:
        return False


def libsecp_sign(raw_priv: bytes, digest: bytes) -> bytes:
    """Sign a 32-byte digest with libsecp256k1 (produces canonical low-S DER)."""
    return LIBSECP.PrivateKey(bytes(raw_priv)).sign(digest, hasher=_ID)


# ---- v0.1-style crypto (the lab MODEL: OpenSSL EC via `cryptography`) --------------

def raw_priv(priv) -> bytes:
    return priv.private_numbers().private_value.to_bytes(32, "big")


def model_sign(priv, digest: bytes) -> bytes:
    """Sign the sighash the way v0.1 does — ECDSA over the digest (not re-hashed)."""
    return priv.sign(digest, ec.ECDSA(utils.Prehashed(hashes.SHA256())))


def model_verify(sec_pubkey: bytes, digest: bytes, der: bytes) -> bool:
    """OpenSSL-style verify (lenient: accepts high-S)."""
    from cryptography.exceptions import InvalidSignature
    try:
        pub = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), bytes(sec_pubkey))
        pub.verify(der, digest, ec.ECDSA(utils.Prehashed(hashes.SHA256())))
        return True
    except (InvalidSignature, ValueError):
        return False


# ---- low-S / high-S handling (the malleability axis) ------------------------------

def is_low_s(der: bytes) -> bool:
    _r, s = utils.decode_dss_signature(der)
    return s <= N // 2


def to_low_s(der: bytes) -> bytes:
    r, s = utils.decode_dss_signature(der)
    if s > N // 2:
        s = N - s
    return utils.encode_dss_signature(r, s)


def to_high_s(der: bytes) -> bytes:
    """The other valid signature for the same message — malleated to high-S."""
    r, s = utils.decode_dss_signature(der)
    if s <= N // 2:
        s = N - s
    return utils.encode_dss_signature(r, s)


def v01_sighash(n_in: int = 0) -> bytes:
    """A genuine v0.1 SignatureHash over the model's demo transaction."""
    tx, script_code = demo_tx()
    return signature_hash(script_code, tx, n_in, SIGHASH_ALL)


if __name__ == "__main__":
    if LIBSECP is None:
        print("libsecp256k1 (bitcoinx/electrumsv-secp256k1) not available"); sys.exit(0)
    priv, sec = new_key()
    h = v01_sighash()
    der = model_sign(priv, h)
    print("v0.1 SignatureHash:", h.hex())
    print("model (OpenSSL) verifies own sig     :", model_verify(sec, h, der))
    print("libsecp256k1 verifies canonical (low-S):", libsecp_verify(sec, h, to_low_s(der)))
    print("libsecp256k1 rejects high-S (malleable):", not libsecp_verify(sec, h, to_high_s(der)))
    print("  ...but OpenSSL accepts that high-S   :", model_verify(sec, h, to_high_s(der)))
    d2 = libsecp_sign(raw_priv(priv), h)
    print("model verifies a libsecp256k1 signature:", model_verify(sec, h, d2))
