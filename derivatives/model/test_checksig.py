"""End-to-end OP_CHECKSIG / OP_CHECKMULTISIG through the MODEL interpreter with
real secp256k1 — now with scriptCode derived from the real subscript (byte-level),
the way v0.1 VerifySignature runs scriptSig + OP_CODESEPARATOR + scriptPubKey.
Evidence level: MODEL.
"""

import cscript
from spend import scriptcode, sign, verify_spend
from tx_sighash import demo_tx, new_key


def test_p2pk_scriptcode_is_scriptpubkey():
    tx, _ = demo_tx()
    priv, pub = new_key()
    spk = [pub, "OP_CHECKSIG"]                       # scriptPubKey
    # scriptCode a signature commits to == the scriptPubKey bytes
    assert scriptcode(spk) == cscript.assemble([pub, "OP_CHECKSIG"])
    sig = sign(priv, spk, tx, 0)
    assert verify_spend([sig], spk, tx, 0) is True
    bad = bytearray(sig); bad[10] ^= 1
    assert verify_spend([bytes(bad)], spk, tx, 0) is False
    _, other = new_key()
    assert verify_spend([sig], [other, "OP_CHECKSIG"], tx, 0) is False


def test_checksigverify_then_true():
    tx, _ = demo_tx()
    priv, pub = new_key()
    spk = [pub, "OP_CHECKSIGVERIFY", "OP_1"]
    sig = sign(priv, spk, tx, 0)
    assert verify_spend([sig], spk, tx, 0) is True


def test_escrow_2of3():
    tx, _ = demo_tx()
    ks = [new_key() for _ in range(3)]
    pubs = [p for _, p in ks]
    spk = ["OP_2"] + pubs + ["OP_3", "OP_CHECKMULTISIG"]   # bare 2-of-3

    def sig(i):
        return sign(ks[i][0], spk, tx, 0)

    def spend(sigs):
        return verify_spend(["OP_0"] + sigs, spk, tx, 0)   # OP_0 = the off-by-one dummy

    assert spend([sig(0), sig(1)]) is True     # buyer + seller
    assert spend([sig(0), sig(2)]) is True     # buyer + arbiter
    assert spend([sig(1), sig(2)]) is True     # seller + arbiter
    xpriv, _ = new_key()
    xsig = sign(xpriv, spk, tx, 0)
    assert spend([sig(0), xsig]) is False      # outsider signature
    assert spend([sig(2), sig(0)]) is False    # wrong (descending) order
    assert spend([sig(0)]) is False            # only one of two required
