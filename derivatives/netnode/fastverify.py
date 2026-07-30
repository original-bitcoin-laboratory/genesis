"""An optional libsecp256k1-accelerated verifier that stays byte-faithful to v0.1 — Path B. NOT money.

`bench.py` shows ~95% of validation time is ECDSA signature verification, so the one real lever for
a faster node is a **native verifier**. libsecp256k1 (via `bitcoinx` / `electrumsv-secp256k1`) is
that verifier — but it **cannot be dropped in naively**, and this module is about *why*, and the
consensus-safe way to use it anyway.

**The fidelity catch (the high-S / malleability axis).** libsecp256k1 rejects **high-S** (malleated)
signatures and enforces strict DER; the v0.1 origin verifies with **OpenSSL**, which *accepts* high-S.
The X-chains are faithful **pre-strictness** reconstructions, so their consensus is the *lenient*
OpenSSL behaviour. Swapping in raw libsecp256k1 would make the node reject signatures the origin
accepts — a **consensus drift** from the origin (see `crypto_conformance/`). (This high-S axis is
*distinct from BIP66*, which enforces strict DER *encoding*, not the S value.)

**The consensus-safe fast path.** For any DER signature, OpenSSL accepts `(r, s)` iff it accepts
`(r, n−s)` (both are valid signatures for the same message — that *is* the malleability). So
`libsecp(to_low_s(der))` accepts exactly the canonical form, and:

    faithful_verify(der)  ==  libsecp(to_low_s(der))  OR  openssl(der)

is identical to this module's own `openssl_verify` backend on every input — it just lets the fast
native verifier short-circuit the common (valid) case and only falls back to OpenSSL for the rare
divergent one. This is **differential-tested against `openssl_verify` on the canonical-DER / high-S
corpus**; it does **not** claim exhaustive emulation of the 2009 OpenSSL parser's acceptance of
non-strict DER encodings. On top of that, `verify_spend_fast` bypasses the pure-Python script
interpreter for the bare-P2PK template (the overwhelmingly common script), delegating everything
non-standard to the faithful interpreter. Evidence: MODEL / NEW-EXP.
"""

from __future__ import annotations

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
for _p in ("model", "p2p", "nov08x"):
    sys.path.insert(0, str(_HERE.parent / _p))
sys.path.insert(0, str(_HERE))

from cryptography.exceptions import InvalidSignature                # noqa: E402
from cryptography.hazmat.primitives import hashes                   # noqa: E402
from cryptography.hazmat.primitives.asymmetric import ec, utils     # noqa: E402

from cscript import assemble                                        # noqa: E402
from spend import verify_spend                                      # noqa: E402
from tx_sighash import signature_hash                               # noqa: E402

N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141   # secp256k1 group order

# ---- the native backend (bitcoinx -> electrumsv-secp256k1), optional --------------
_LIBSECP = None
try:
    import bitcoinx as _bx
    import electrumsv_secp256k1 as _es          # noqa: F401 — the C lib bitcoinx binds
    _LIBSECP = _bx
except Exception:                                # noqa: BLE001
    _LIBSECP = None

HAVE_LIBSECP = _LIBSECP is not None
BACKEND = "libsecp256k1 (bitcoinx) + OpenSSL fallback" if HAVE_LIBSECP else "OpenSSL (cryptography)"
_ID = lambda x: x                                # identity "hasher": operate on the 32-byte digest


def openssl_verify(pubkey_sec: bytes, der: bytes, digest: bytes) -> bool:
    """The reference backend the fast path must match: a modern OpenSSL EC verify (via `cryptography`),
    **lenient** — accepts high-S. It matches v0.1's OpenSSL acceptance on the tested canonical-DER /
    high-S paths; it is not a bit-exact emulation of the 2009 OpenSSL DER parser on non-strict
    encodings."""
    try:
        pub = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), bytes(pubkey_sec))
        pub.verify(bytes(der), bytes(digest), ec.ECDSA(utils.Prehashed(hashes.SHA256())))
        return True
    except (InvalidSignature, ValueError):
        return False


def libsecp_verify(pubkey_sec: bytes, der: bytes, digest: bytes) -> bool:
    """Native libsecp256k1 verify — **strict** (rejects high-S / non-canonical DER). Faster, but
    NOT the origin's semantics; used only on the low-S-normalized form inside `faithful_verify`."""
    try:
        return _LIBSECP.PublicKey.from_bytes(bytes(pubkey_sec)).verify_der_signature(
            bytes(der), bytes(digest), hasher=_ID)
    except Exception:                            # noqa: BLE001 — any parse/verify failure is "no"
        return False


def to_low_s(der: bytes) -> bytes:
    """The canonical (low-S) form of a DER signature (same validity as the input, per malleability)."""
    r, s = utils.decode_dss_signature(bytes(der))
    if s > N // 2:
        s = N - s
    return utils.encode_dss_signature(r, s)


def faithful_verify(pubkey_sec: bytes, der: bytes, digest: bytes) -> bool:
    """Verify with the native lib when possible, but return **exactly what OpenSSL would** — the
    origin's lenient semantics — for every input. Provably `== openssl_verify` (differential-tested):
    the native path short-circuits the common canonical case; OpenSSL is the fallback for the rest."""
    if HAVE_LIBSECP:
        try:
            if libsecp_verify(pubkey_sec, to_low_s(der), digest):
                return True                      # native accepted the canonical form -> OpenSSL would too
        except Exception:                        # noqa: BLE001 — malformed DER, etc. -> defer to OpenSSL
            pass
    return openssl_verify(pubkey_sec, der, digest)


# ---- a script-level fast path for the bare-P2PK template -------------------------
def _is_p2pk(spk) -> bool:
    return len(spk) == 2 and isinstance(spk[0], (bytes, bytearray)) and spk[1] == "OP_CHECKSIG"


def verify_spend_fast(script_sig_tokens, spk_tokens, tx, n_in: int, reopen=frozenset()) -> bool:
    """A drop-in for `spend.verify_spend` that fast-paths the bare-P2PK case (native ECDSA, no
    Python script interpreter) and **delegates every other script to the faithful interpreter**.
    Differential-tested to equal `verify_spend` on every input. `reopen` forwards the script posture
    (empty = faithful; `{'OP_NOTEQUAL'}` = experimental, a token-level `OP_EQUAL OP_NOT` macro rather than a
    reopened wire opcode) — the P2PK fast path is unaffected by it."""
    if (_is_p2pk(spk_tokens) and len(script_sig_tokens) == 1
            and isinstance(script_sig_tokens[0], (bytes, bytearray)) and script_sig_tokens[0]):
        sig = bytes(script_sig_tokens[0])
        hashtype, der = sig[-1], sig[:-1]
        digest = signature_hash(assemble(list(spk_tokens)), tx, n_in, hashtype)   # scriptCode = the P2PK spk
        return faithful_verify(bytes(spk_tokens[0]), der, digest)
    return verify_spend(script_sig_tokens, spk_tokens, tx, n_in, reopen=reopen)
