"""Executed native v0.1 financial instruments, built only from original primitives
and run through the MODEL interpreter with real secp256k1. Evidence level: MODEL.

Instruments: hash-lock (preimage) claim; hash-lock OR refund branch (OP_IF); and an
assurance/crowdfund contract demonstrating SIGHASH_ANYONECANPAY (pledges can be
collected independently and survive later inputs being added). See INSTRUMENTS.md.
"""

import hashlib

import cscript
from evalscript_model import valid
from spend import scriptcode, sign, verify_spend
from tx_sighash import (SIGHASH_ALL, SIGHASH_ANYONECANPAY, SigChecker, Tx, TxIn,
                        TxOut, demo_tx, new_key, sign_input)


def _hash256(b: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


# --- 1. Hash-lock claim: OP_HASH256 <H> OP_EQUALVERIFY <pubkey> OP_CHECKSIG ------

def test_hashlock_claim():
    tx, _ = demo_tx()
    priv, pub = new_key()
    secret = b"correct horse battery staple"
    H = _hash256(secret)
    spk = ["OP_HASH256", H, "OP_EQUALVERIFY", pub, "OP_CHECKSIG"]
    sig = sign(priv, spk, tx, 0)
    assert verify_spend([sig, secret], spk, tx, 0) is True       # preimage + signature
    assert verify_spend([sig, b"wrong-secret"], spk, tx, 0) is False   # wrong preimage
    wrongpriv, _ = new_key()
    assert verify_spend([sign(wrongpriv, spk, tx, 0), secret], spk, tx, 0) is False  # wrong key


# --- 2. Hash-lock OR refund, selected by OP_IF ---------------------------------

def test_hashlock_or_refund_branch():
    tx, _ = demo_tx()
    rpriv, rpub = new_key()      # recipient: claim with preimage + sig
    spriv, spub = new_key()      # sender: refund with sig
    secret = b"payment-secret"
    H = _hash256(secret)
    spk = ["OP_IF",
           "OP_HASH256", H, "OP_EQUALVERIFY", rpub, "OP_CHECKSIG",
           "OP_ELSE",
           spub, "OP_CHECKSIG",
           "OP_ENDIF"]
    # claim path: <sig_r> <preimage> OP_1
    assert verify_spend([sign(rpriv, spk, tx, 0), secret, "OP_1"], spk, tx, 0) is True
    # refund path: <sig_s> OP_0
    assert verify_spend([sign(spriv, spk, tx, 0), "OP_0"], spk, tx, 0) is True
    # claim with wrong preimage fails
    assert verify_spend([sign(rpriv, spk, tx, 0), b"nope", "OP_1"], spk, tx, 0) is False
    # refund path but with recipient's key (not the refund key) fails
    assert verify_spend([sign(rpriv, spk, tx, 0), "OP_0"], spk, tx, 0) is False


# --- 3. Assurance contract / crowdfund via SIGHASH_ANYONECANPAY ----------------

def test_assurance_anyonecanpay():
    acp = SIGHASH_ALL | SIGHASH_ANYONECANPAY               # 0x81
    goal = TxOut(10_000_000_000, cscript.assemble(["OP_1"]))   # the campaign output
    p1, p2, p3 = new_key(), new_key(), new_key()

    def spk(pub):
        return [pub, "OP_CHECKSIG"]

    def txin(i):
        return TxIn(bytes([i + 1]) * 32, i, b"")

    tx2 = Tx(1, [txin(0), txin(1)], [goal], 0)
    tx3 = Tx(1, [txin(0), txin(1), txin(2)], [goal], 0)      # a third pledge added later

    # each pledger signs ONLY their own input (ANYONECANPAY), committing to the goal
    sig1 = sign_input(p1[0], tx2, 0, scriptcode(spk(p1[1])), acp)
    sig2 = sign_input(p2[0], tx2, 1, scriptcode(spk(p2[1])), acp)
    assert verify_spend([sig1], spk(p1[1]), tx2, 0) is True
    assert verify_spend([sig2], spk(p2[1]), tx2, 1) is True

    # KEY property: a later pledge (input 2) can be ADDED and pledge 1 stays valid
    assert verify_spend([sig1], spk(p1[1]), tx3, 0) is True

    # control: plain SIGHASH_ALL breaks the moment another input is added
    sig1_all = sign_input(p1[0], tx2, 0, scriptcode(spk(p1[1])), SIGHASH_ALL)
    assert verify_spend([sig1_all], spk(p1[1]), tx2, 0) is True
    assert verify_spend([sig1_all], spk(p1[1]), tx3, 0) is False
