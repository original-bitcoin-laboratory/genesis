"""v0.1's ECDSA cross-checked against the real libsecp256k1 (via bitcoinx /
electrumsv-secp256k1). Executes Thread A of THE_OPENSSL_THREAD.md: the curve math is
identical; the only divergence is the high-S malleability libsecp256k1 rejects and
OpenSSL (v0.1's stack) accepts. Evidence: MODEL."""

import pathlib
import sys

import pytest

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "model"))
sys.path.insert(0, str(_HERE))

from crypto_conformance import (LIBSECP, is_low_s, libsecp_sign, libsecp_verify,
                                model_sign, model_verify, raw_priv, to_high_s,
                                to_low_s, v01_sighash)
from tx_sighash import new_key

pytestmark = pytest.mark.skipif(LIBSECP is None,
                                reason="libsecp256k1 (bitcoinx/electrumsv-secp256k1) not installed")


def test_libsecp256k1_is_really_the_c_library():
    import electrumsv_secp256k1 as es
    assert getattr(es, "lib", None) is not None          # the real libsecp256k1 C lib


@pytest.mark.parametrize("seed", range(5))
def test_canonical_v01_signature_verifies_under_libsecp256k1(seed):
    # a genuine v0.1 SignatureHash, signed the v0.1 way (OpenSSL EC), canonicalized to
    # low-S, verifies under libsecp256k1 — the ECDSA math is identical.
    priv, sec = new_key()
    h = v01_sighash(n_in=seed % 2)
    der = to_low_s(model_sign(priv, h))
    assert model_verify(sec, h, der)                     # v0.1 stack accepts
    assert libsecp_verify(sec, h, der)                   # libsecp256k1 accepts the same sig


@pytest.mark.parametrize("seed", range(5))
def test_libsecp256k1_signature_verifies_under_our_model(seed):
    priv, sec = new_key()
    h = v01_sighash(n_in=seed % 2)
    der = libsecp_sign(raw_priv(priv), h)                # libsecp256k1 signs (low-S)
    assert is_low_s(der)                                 # libsecp256k1 always produces low-S
    assert model_verify(sec, h, der)                     # our v0.1-style verify accepts it


@pytest.mark.parametrize("seed", range(8))
def test_high_s_is_the_only_divergence_thread_A(seed):
    # THE finding: a high-S signature is valid ECDSA (OpenSSL/v0.1 accepts it) but
    # libsecp256k1 REJECTS it — the malleability that BIP66 / libsecp256k1 fixed.
    priv, sec = new_key()
    h = v01_sighash(n_in=seed % 2)
    high = to_high_s(model_sign(priv, h))
    assert not is_low_s(high)
    assert model_verify(sec, h, high)                    # OpenSSL (v0.1) accepts high-S
    assert not libsecp_verify(sec, h, high)              # libsecp256k1 rejects high-S


def test_same_secp256k1_key_both_stacks():
    priv, sec = new_key()
    bx_pub = LIBSECP.PrivateKey(raw_priv(priv)).public_key
    assert bx_pub.to_bytes(compressed=False) == bytes(sec)   # identical curve + key


def test_canonicalization_is_idempotent_and_correct():
    priv, _ = new_key()
    h = v01_sighash()
    der = model_sign(priv, h)
    low = to_low_s(der)
    assert is_low_s(low) and to_low_s(low) == low        # already low-S -> unchanged
    assert not is_low_s(to_high_s(low))                  # flips to high-S
