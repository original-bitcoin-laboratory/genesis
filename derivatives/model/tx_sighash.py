"""MODEL of v0.1.0 CTransaction serialization + SignatureHash (script.cpp:818).

Evidence level: MODEL. Reproduces the pre-BIP143 signature-hash algorithm and the
standard transaction serialization it hashes. Cross-checked byte-for-byte against
the C++/OpenSSL port (derivatives/port/sighash.cpp) via run_sighash.sh, and used
by evalscript_model's OP_CHECKSIG/OP_CHECKMULTISIG through SigChecker.
"""

from __future__ import annotations

import copy
import hashlib

SIGHASH_ALL = 1
SIGHASH_NONE = 2
SIGHASH_SINGLE = 3
SIGHASH_ANYONECANPAY = 0x80
OP_CODESEPARATOR = 0xAB


def dsha256(b: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


def _le(n: int, length: int) -> bytes:
    return int(n).to_bytes(length, "little")


def _le_signed(n: int, length: int) -> bytes:
    return int(n).to_bytes(length, "little", signed=True)


def compact_size(n: int) -> bytes:
    if n < 0xFD:
        return bytes([n])
    if n <= 0xFFFF:
        return b"\xfd" + _le(n, 2)
    if n <= 0xFFFFFFFF:
        return b"\xfe" + _le(n, 4)
    return b"\xff" + _le(n, 8)


def _push(b: bytes) -> bytes:
    return compact_size(len(b)) + b


class TxIn:
    def __init__(self, prevhash: bytes, n: int, script: bytes, seq: int = 0xFFFFFFFF):
        self.prevhash, self.n, self.script, self.seq = prevhash, n, script, seq


class TxOut:
    def __init__(self, value: int, script: bytes):
        self.value, self.script = value, script

    def set_null(self):
        self.value, self.script = -1, b""


class Tx:
    def __init__(self, version: int, vin: list, vout: list, locktime: int):
        self.version, self.vin, self.vout, self.locktime = version, vin, vout, locktime


def serialize(tx: Tx) -> bytes:
    s = _le(tx.version, 4) + compact_size(len(tx.vin))
    for i in tx.vin:
        s += i.prevhash + _le(i.n, 4) + _push(i.script) + _le(i.seq, 4)
    s += compact_size(len(tx.vout))
    for o in tx.vout:
        s += _le_signed(o.value, 8) + _push(o.script)
    s += _le(tx.locktime, 4)
    return s


def _find_and_delete_codeseparator(script: bytes) -> bytes:
    # Simplified: strip standalone OP_CODESEPARATOR bytes (matches v0.1 for the
    # scripts used here, which contain no 0xab data pushes).
    return bytes(b for b in script if b != OP_CODESEPARATOR)


def signature_hash(script_code: bytes, tx: Tx, n_in: int, hash_type: int) -> bytes:
    if n_in >= len(tx.vin):
        return (1).to_bytes(32, "little")
    t = copy.deepcopy(tx)
    script_code = _find_and_delete_codeseparator(script_code)
    for i in t.vin:
        i.script = b""
    t.vin[n_in].script = script_code

    ht = hash_type & 0x1F
    if ht == SIGHASH_NONE:
        t.vout = []
        for k, i in enumerate(t.vin):
            if k != n_in:
                i.seq = 0
    elif ht == SIGHASH_SINGLE:
        n_out = n_in
        if n_out >= len(t.vout):
            return (1).to_bytes(32, "little")
        t.vout = t.vout[: n_out + 1]
        for k in range(n_out):
            t.vout[k].set_null()
        for k, i in enumerate(t.vin):
            if k != n_in:
                i.seq = 0

    if hash_type & SIGHASH_ANYONECANPAY:
        t.vin = [t.vin[n_in]]

    return dsha256(serialize(t) + _le(hash_type, 4))


def demo_tx():
    """A fixed transaction, built identically here and in sighash.cpp."""
    in0 = TxIn(b"\x11" * 32, 0, bytes([0xDE, 0xAD]))
    in1 = TxIn(b"\x22" * 32, 7, bytes([0xBE, 0xEF]))
    spk0 = bytes.fromhex("76a914" + "33" * 20 + "88ac")   # P2PKH-shaped, 25 bytes
    spk1 = bytes([0x51])                                    # OP_1
    out0 = TxOut(5_000_000_000, spk0)                       # 50 coins
    out1 = TxOut(1_000_000_000, spk1)                       # 10 coins
    return Tx(1, [in0, in1], [out0, out1], 0), spk0


class SigChecker:
    """Signature checker for evalscript_model's OP_CHECKSIG/OP_CHECKMULTISIG.

    Holds the transaction context and the scriptCode (the scriptPubKey being
    spent). check_sig recomputes SignatureHash and verifies the DER signature on
    secp256k1 via `cryptography`. Simplification: it uses the configured
    scriptCode rather than a byte-derived subscript (a standard single-scriptCode
    spend), consistent with the C++ port's CheckSig.
    """

    def __init__(self, tx: Tx, n_in: int, script_code: bytes):
        self.tx, self.n_in, self.script_code = tx, n_in, script_code

    def check_sig(self, sig, pubkey, subscript=None) -> bool:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec, utils
        sig = bytes(sig)
        if not sig:
            return False
        hash_type, der = sig[-1], sig[:-1]
        h = signature_hash(self.script_code, self.tx, self.n_in, hash_type)
        try:
            pub = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), bytes(pubkey))
            pub.verify(der, h, ec.ECDSA(utils.Prehashed(hashes.SHA256())))
            return True
        except (InvalidSignature, ValueError):
            return False


def new_key():
    """Return (private_key, SEC-uncompressed pubkey bytes) on secp256k1."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    priv = ec.generate_private_key(ec.SECP256K1())
    sec = priv.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return priv, sec


def sign_input(priv, tx: Tx, n_in: int, script_code: bytes, hash_type: int = SIGHASH_ALL) -> bytes:
    """Sign the sighash and append the 1-byte hash type (as CKey::Sign does)."""
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec, utils
    h = signature_hash(script_code, tx, n_in, hash_type)
    der = priv.sign(h, ec.ECDSA(utils.Prehashed(hashes.SHA256())))
    return der + bytes([hash_type])


def report() -> None:
    tx, script_code = demo_tx()
    types = [("0x01", 0x01), ("0x02", 0x02), ("0x03", 0x03),
             ("0x81", 0x81), ("0x82", 0x82), ("0x83", 0x83)]
    for n_in in (0, 1):
        for label, ht in types:
            print(f"SH nIn={n_in} type={label} => {signature_hash(script_code, tx, n_in, ht).hex()}")


if __name__ == "__main__":
    report()
