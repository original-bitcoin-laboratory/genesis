"""Transacting on the full-capability chains. A Rules-parameterised UTXO ledger
validates real spends on NOV08-X and JAN09-X — wallet payments, the safety rules
(no double-spend / inflation / immature coinbase), each chain's coinbase value rule,
and a coin locked by a script BTC cannot express (an OP_CAT hash-lock). Evidence:
MODEL."""

import hashlib
import pathlib
import sys

import pytest

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "model"))
sys.path.insert(0, str(_HERE.parent / "wallet"))
sys.path.insert(0, str(_HERE.parent / "nov08x"))
sys.path.insert(0, str(_HERE))

from ledger import Ledger, LedgerError
from consensus import Rules
from wallet import Wallet, p2pk
from cscript import assemble
from tx_sighash import Tx, TxIn, TxOut

JAN = Rules.load("jan09")
NOV = Rules.load("nov08")


# ---- a wallet payment settles on JAN09-X -------------------------------------

def test_wallet_payment_settles_and_updates_utxo():
    led = Ledger(JAN, maturity=2)
    w = Wallet()
    sec = w.new_key()
    spk = p2pk(sec)
    cb, tid = led.connect_coinbase(spk)                 # 50-coin coinbase to the wallet
    reward = cb.vout[0].value
    w.add_coin(tid, 0, reward, spk)
    led.advance(2)                                      # mature the coinbase

    dest = p2pk(Wallet().new_key())
    tx, _, (change, _) = w.create_transaction(dest, reward // 2)
    coin = led.utxos[(tid, 0)]
    new_tid, fee = led.connect_tx(tx, [coin])           # ConnectInputs validates + applies
    assert fee == 0
    assert (tid, 0) not in led.utxos                    # coinbase spent
    assert (new_tid, 0) in led.utxos and (new_tid, 1) in led.utxos   # payee + change
    assert led.balance() == reward                      # value conserved


# ---- the ledger safety rules --------------------------------------------------

def _funded_wallet(led):
    w = Wallet(); sec = w.new_key(); spk = p2pk(sec)
    cb, tid = led.connect_coinbase(spk)
    w.add_coin(tid, 0, cb.vout[0].value, spk)
    return w, tid, cb.vout[0].value


def test_immature_coinbase_is_rejected():
    led = Ledger(JAN, maturity=100)
    w, tid, reward = _funded_wallet(led)                # height 0
    led.advance(10)                                     # still < 100
    tx, _, _ = w.create_transaction(p2pk(Wallet().new_key()), reward // 2)
    with pytest.raises(LedgerError, match="immature"):
        led.connect_tx(tx, [led.utxos[(tid, 0)]])


def test_double_spend_is_rejected():
    led = Ledger(JAN, maturity=1)
    w, tid, reward = _funded_wallet(led)
    led.advance(1)
    tx, _, _ = w.create_transaction(p2pk(Wallet().new_key()), reward // 2)
    coin = led.utxos[(tid, 0)]
    led.connect_tx(tx, [coin])                          # first spend ok
    with pytest.raises(LedgerError, match="double-spend"):
        led.connect_tx(tx, [coin])                      # same input again


def test_inflation_is_rejected():
    # use an anyone-can-spend (OP_1) coin so the scriptSig doesn't commit to the
    # outputs — otherwise tampering vout would trip the signature check first.
    led = Ledger(JAN, maturity=1)
    _, tid = led.connect_coinbase(["OP_1"])
    led.advance(1)
    coin = led.utxos[(tid, 0)]
    tx = Tx(1, [TxIn(tid, 0, b"", 0xFFFFFFFF)], [TxOut(coin.value * 2, b"\x51")], 0)
    with pytest.raises(LedgerError, match="inflation"):
        led.connect_tx(tx, [coin])


# ---- each chain's coinbase value rule ----------------------------------------

def test_jan09x_coinbase_upper_bound():
    led = Ledger(JAN, maturity=1)
    bv = JAN.get_block_value(-1)
    led.connect_coinbase(p2pk(Wallet().new_key()), claim=bv - 1)   # <= ok
    with pytest.raises(LedgerError):
        led.connect_coinbase(p2pk(Wallet().new_key()), claim=bv + 1)   # > rejected


def test_nov08x_coinbase_exact_equality():
    led = Ledger(NOV, maturity=1)
    bv = NOV.get_block_value(-1)
    with pytest.raises(LedgerError):
        led.connect_coinbase(p2pk(Wallet().new_key()), claim=bv - 1)   # != rejected
    led.connect_coinbase(p2pk(Wallet().new_key()), claim=bv)           # == ok


# ---- full capability: a coin BTC could not lock, spent on both X-chains -------

@pytest.mark.parametrize("rules", [JAN, NOV], ids=["JAN09-X", "NOV08-X"])
def test_op_cat_hashlock_coin_is_spendable(rules):
    led = Ledger(rules, maturity=2)
    h1, h2 = b"the-preimage-", b"two-halves"
    lock = hashlib.sha256(h1 + h2).digest()
    spk = ["OP_CAT", "OP_SHA256", lock, "OP_EQUAL"]     # BTC disables OP_CAT -> unspendable there
    cb, tid = led.connect_coinbase(spk)
    led.advance(2)
    coin = led.utxos[(tid, 0)]

    # spend it by revealing the two halves
    spend = Tx(1, [TxIn(tid, 0, assemble([h1, h2]), 0xFFFFFFFF)],
               [TxOut(coin.value, assemble(p2pk(Wallet().new_key())))], 0)
    new_tid, _ = led.connect_tx(spend, [coin])
    assert (new_tid, 0) in led.utxos                    # settled on a full-vocabulary chain

    # a wrong preimage does not satisfy the lock
    led2 = Ledger(rules, maturity=2)
    _, tid2 = led2.connect_coinbase(spk)
    led2.advance(2)
    bad = Tx(1, [TxIn(tid2, 0, assemble([h1, b"WRONG"]), 0xFFFFFFFF)],
             [TxOut(led2.utxos[(tid2, 0)].value, b"\x51")], 0)
    with pytest.raises(LedgerError, match="does not satisfy"):
        led2.connect_tx(bad, [led2.utxos[(tid2, 0)]])
