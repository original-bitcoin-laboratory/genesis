"""End-to-end OP_CHECKSIG / OP_CHECKMULTISIG through the MODEL interpreter with
real secp256k1 (via `cryptography`). Evidence level: MODEL.

Signs the demo transaction and asserts the interpreter validates a P2PK spend and
a 2-of-3 escrow (arbitration) — and rejects tampered / wrong-key / wrong-order
signatures. The v0.1 CHECKMULTISIG off-by-one dummy (leading OP_0) is included.
"""

from evalscript_model import valid
from tx_sighash import demo_tx, new_key, sign_input, SigChecker


def test_checksig_p2pk():
    tx, spk0 = demo_tx()
    priv, pub = new_key()
    sig = sign_input(priv, tx, 0, spk0)
    ck = SigChecker(tx, 0, spk0)
    assert valid([sig, pub, "OP_CHECKSIG"], ck) is True
    bad = bytearray(sig); bad[10] ^= 1
    assert valid([bytes(bad), pub, "OP_CHECKSIG"], ck) is False
    _, other = new_key()
    assert valid([sig, other, "OP_CHECKSIG"], ck) is False


def test_checksigverify_then_continue():
    tx, spk0 = demo_tx()
    priv, pub = new_key()
    sig = sign_input(priv, tx, 0, spk0)
    ck = SigChecker(tx, 0, spk0)
    # CHECKSIGVERIFY consumes the true result, then OP_1 leaves true
    assert valid([sig, pub, "OP_CHECKSIGVERIFY", "OP_1"], ck) is True


def test_escrow_2of3():
    tx, spk0 = demo_tx()
    ks = [new_key() for _ in range(3)]
    pubs = [p for _, p in ks]
    ck = SigChecker(tx, 0, spk0)

    def sig(i):
        return sign_input(ks[i][0], tx, 0, spk0)

    def escrow(sigs):
        return valid(["OP_0"] + sigs + ["OP_2"] + pubs + ["OP_3", "OP_CHECKMULTISIG"], ck)

    assert escrow([sig(0), sig(1)]) is True     # A,B
    assert escrow([sig(0), sig(2)]) is True     # A,C  (buyer + arbiter)
    assert escrow([sig(1), sig(2)]) is True     # B,C
    xpriv, _ = new_key()
    xsig = sign_input(xpriv, tx, 0, spk0)
    assert escrow([sig(0), xsig]) is False      # outsider signature
    assert escrow([sig(2), sig(0)]) is False    # wrong (descending) order
