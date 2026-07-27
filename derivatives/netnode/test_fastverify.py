"""The optional libsecp256k1 fast verifier stays byte-faithful to v0.1 (production node, part 7):
`faithful_verify` returns exactly what OpenSSL would on low-S / high-S / invalid signatures, and
`verify_spend_fast` equals the faithful interpreter on bare-P2PK spends (valid, wrong-key,
high-S-malleated) while **delegating** every non-standard script. It also documents the fidelity
catch — raw libsecp256k1 rejects high-S where OpenSSL accepts (the BIP66 axis) — which is *why* the
fast path normalizes + falls back rather than swapping. Evidence: MODEL / NEW-EXP (not money)."""

import hashlib
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
for _p in (_HERE.parent / "model", _HERE.parent / "p2p", _HERE.parent / "nov08x", _HERE):
    sys.path.insert(0, str(_p))

from cryptography.hazmat.primitives import hashes                   # noqa: E402
from cryptography.hazmat.primitives.asymmetric import ec, utils     # noqa: E402

import cscript                                                      # noqa: E402
from spend import sign, verify_spend                               # noqa: E402
from tx_sighash import Tx, TxIn, TxOut, new_key                    # noqa: E402

import fastverify                                                   # noqa: E402
from fastverify import N, faithful_verify, openssl_verify, verify_spend_fast

ZERO = b"\x00" * 32


def _der_variants(priv, digest):
    der = priv.sign(digest, ec.ECDSA(utils.Prehashed(hashes.SHA256())))
    r, s = utils.decode_dss_signature(der)
    low = utils.encode_dss_signature(r, s if s <= N // 2 else N - s)
    high = utils.encode_dss_signature(r, N - s if s <= N // 2 else s)
    return der, low, high


# ---- the ECDSA primitive is byte-faithful to OpenSSL ------------------------

def test_faithful_verify_equals_openssl_on_low_high_and_invalid():
    priv, pub = new_key()
    digest = hashlib.sha256(b"a message").digest()
    der, low, high = _der_variants(priv, digest)
    wrong = _der_variants(new_key()[0], digest)[0]                  # signed by a different key
    for sig in (der, low, high, wrong):
        assert faithful_verify(pub, sig, digest) == openssl_verify(pub, sig, digest)
    assert openssl_verify(pub, high, digest)                       # OpenSSL (and so we) accept high-S
    assert not openssl_verify(pub, wrong, digest)


def test_documents_the_libsecp_high_s_divergence():
    if not fastverify.HAVE_LIBSECP:
        import pytest
        pytest.skip("libsecp256k1 backend not installed")
    priv, pub = new_key()
    digest = hashlib.sha256(b"another message").digest()
    _der, low, high = _der_variants(priv, digest)
    assert fastverify.libsecp_verify(pub, low, digest)             # native accepts the canonical form
    assert not fastverify.libsecp_verify(pub, high, digest)        # native REJECTS high-S (BIP66) …
    assert openssl_verify(pub, high, digest)                       # … while OpenSSL accepts it —
    assert faithful_verify(pub, high, digest)                      # so the faithful path must accept it too


# ---- the script fast path equals the interpreter ----------------------------

def _p2pk_spend(priv, spk):
    tx = Tx(1, [TxIn(b"\xaa" * 32, 0, b"", 0xFFFFFFFF)], [TxOut(1000, b"\x51")], 0)
    return tx, sign(priv, spk, tx, 0)


def test_verify_spend_fast_matches_the_interpreter_on_p2pk():
    priv, pub = new_key()
    spk = [pub, "OP_CHECKSIG"]
    tx, sig = _p2pk_spend(priv, spk)
    assert verify_spend_fast([sig], spk, tx, 0) is True
    assert verify_spend_fast([sig], spk, tx, 0) == verify_spend([sig], spk, tx, 0)
    wrong = sign(new_key()[0], spk, tx, 0)                         # wrong key -> both reject
    assert verify_spend_fast([wrong], spk, tx, 0) == verify_spend([wrong], spk, tx, 0) is False
    hashtype, der = sig[-1], sig[:-1]                              # high-S malleation -> both agree (lenient)
    r, s = utils.decode_dss_signature(der)
    high = utils.encode_dss_signature(r, N - s if s <= N // 2 else s) + bytes([hashtype])
    assert verify_spend_fast([high], spk, tx, 0) == verify_spend([high], spk, tx, 0)


def test_verify_spend_fast_delegates_for_nonstandard_scripts():
    priv, pub = new_key()
    tx = Tx(1, [TxIn(b"\xbb" * 32, 0, b"", 0xFFFFFFFF)], [TxOut(1000, b"\x51")], 0)
    # anyone-can-spend OP_1 (empty scriptSig) — not P2PK -> delegates to the interpreter
    assert verify_spend_fast([], ["OP_1"], tx, 0) == verify_spend([], ["OP_1"], tx, 0)
    # P2PKH — a different standard template; the fast path must delegate, not misread it
    h160 = hashlib.new("ripemd160", hashlib.sha256(pub).digest()).digest()
    p2pkh = ["OP_DUP", "OP_HASH160", h160, "OP_EQUALVERIFY", "OP_CHECKSIG"]
    sig = sign(priv, p2pkh, tx, 0)
    assert verify_spend_fast([sig, pub], p2pkh, tx, 0) == verify_spend([sig, pub], p2pkh, tx, 0) is True
