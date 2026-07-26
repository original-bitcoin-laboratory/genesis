"""Transacting on the full-capability chains. A Rules-parameterised UTXO ledger
validates real spends on NOV08-X and JAN09-X — wallet payments, the safety rules
(no double-spend / inflation / immature coinbase), each chain's coinbase value rule,
block-level ConnectBlock, two independent nodes agreeing on a tx-carrying chain, and
a coin locked by a script BTC cannot express (an OP_CAT hash-lock). Evidence: MODEL."""

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


def _funded_wallet(led, spk=None):
    w = Wallet(); sec = w.new_key(); spk = spk or p2pk(sec)
    cb, tid = led.connect_coinbase(spk)
    w.add_coin(tid, 0, cb.vout[0].value, spk)
    return w, tid, cb.vout[0].value


# ---- a wallet payment settles on JAN09-X -------------------------------------

def test_wallet_payment_settles_and_updates_utxo():
    led = Ledger(JAN, maturity=2)
    w, tid, reward = _funded_wallet(led)
    led.advance(2)                                      # mature the coinbase
    tx, _, (change, _) = w.create_transaction(p2pk(Wallet().new_key()), reward // 2)
    new_tid, fee = led.connect_tx(tx)                   # ConnectInputs validates + applies
    assert fee == 0
    assert (tid, 0) not in led.utxos                    # coinbase spent
    assert (new_tid, 0) in led.utxos and (new_tid, 1) in led.utxos   # payee + change
    assert led.balance() == reward                      # value conserved


# ---- the ledger safety rules --------------------------------------------------

def test_immature_coinbase_is_rejected():
    led = Ledger(JAN, maturity=100)
    w, tid, reward = _funded_wallet(led)
    led.advance(10)                                     # still < 100
    tx, _, _ = w.create_transaction(p2pk(Wallet().new_key()), reward // 2)
    with pytest.raises(LedgerError, match="immature"):
        led.connect_tx(tx)


def test_double_spend_is_rejected():
    led = Ledger(JAN, maturity=1)
    w, tid, reward = _funded_wallet(led)
    led.advance(1)
    tx, _, _ = w.create_transaction(p2pk(Wallet().new_key()), reward // 2)
    led.connect_tx(tx)                                  # first spend ok
    with pytest.raises(LedgerError, match="double-spend"):
        led.connect_tx(tx)                              # same input again


def test_inflation_is_rejected():
    # anyone-can-spend (OP_1) coin: scriptSig doesn't commit to outputs, so tampering
    # vout trips the value check rather than the signature check.
    led = Ledger(JAN, maturity=1)
    _, tid = led.connect_coinbase(["OP_1"])
    led.advance(1)
    coin = led.utxos[(tid, 0)]
    tx = Tx(1, [TxIn(tid, 0, b"", 0xFFFFFFFF)], [TxOut(coin.value * 2, b"\x51")], 0)
    with pytest.raises(LedgerError, match="inflation"):
        led.connect_tx(tx)


# ---- each chain's coinbase value rule ----------------------------------------

def test_jan09x_coinbase_upper_bound():
    led = Ledger(JAN, maturity=1)
    bv = JAN.get_block_value(-1)
    led.connect_coinbase(p2pk(Wallet().new_key()), claim=bv - 1)         # <= ok
    with pytest.raises(LedgerError):
        led.connect_coinbase(p2pk(Wallet().new_key()), claim=bv + 1)     # > rejected


def test_nov08x_coinbase_exact_equality():
    led = Ledger(NOV, maturity=1)
    bv = NOV.get_block_value(-1)
    with pytest.raises(LedgerError):
        led.connect_coinbase(p2pk(Wallet().new_key()), claim=bv - 1)     # != rejected
    led.connect_coinbase(p2pk(Wallet().new_key()), claim=bv)             # == ok


# ---- ConnectBlock: coinbase may collect the fees of the block's txs -----------

def test_connect_block_coinbase_claims_subsidy_plus_fees():
    led = Ledger(JAN, maturity=1)
    w, tid, reward = _funded_wallet(led)
    led.advance(1)
    # a tx that pays a fee (outputs < inputs)
    fee = 1_000_000
    tx, _, _ = w.create_transaction(p2pk(Wallet().new_key()), reward // 2, fee=fee)
    subsidy = JAN.get_block_value(led.height)
    # coinbase claiming subsidy + fee is accepted; claiming more is rejected
    with pytest.raises(LedgerError):
        led2 = Ledger(JAN, maturity=1)
        w2, _, r2 = _funded_wallet(led2); led2.advance(1)
        tx2, _, _ = w2.create_transaction(p2pk(Wallet().new_key()), r2 // 2, fee=fee)
        led2.connect_block(p2pk(Wallet().new_key()), [tx2],
                           cb_claim=JAN.get_block_value(led2.height) + fee + 1)
    cb = led.connect_block(p2pk(Wallet().new_key()), [tx], cb_claim=subsidy + fee)
    assert cb.vout[0].value == subsidy + fee


def test_connect_block_is_atomic_on_failure():
    led = Ledger(JAN, maturity=1)
    w, tid, reward = _funded_wallet(led)
    led.advance(1)
    before = dict(led.utxos)
    tx, _, _ = w.create_transaction(p2pk(Wallet().new_key()), reward // 2)
    with pytest.raises(LedgerError):
        led.connect_block(p2pk(Wallet().new_key()), [tx], cb_claim=JAN.get_block_value(led.height) + 10**9)
    assert led.utxos == before                          # rolled back: the tx did not apply


# ---- two independent nodes agree on a tx-carrying chain ----------------------

def test_two_ledgers_agree_on_a_tx_carrying_chain():
    # Build ONE fixed sequence of blocks (fixed keys + one signed payment tx), then
    # have two independent ledgers each validate the identical blocks -> identical
    # UTXO state. That is the essence of two nodes agreeing on the chain.
    import random
    rng = random.Random(7)
    w = Wallet(rng); spk0 = p2pk(w.new_key())
    spk1, spk2, dest = (p2pk(Wallet(rng).new_key()) for _ in range(3))
    reward = JAN.get_block_value(-1)

    # deterministic block-0 coinbase txid, to fund the wallet and sign the payment once
    scratch = Ledger(JAN, maturity=1)
    scratch.connect_block(spk0)
    cb_tid = next(k[0] for k, c in scratch.utxos.items() if c.coinbase)
    w.add_coin(cb_tid, 0, reward, spk0)
    tx, _, _ = w.create_transaction(dest, reward // 3)

    plan = [(spk0, []), (spk1, []), (spk2, [tx])]       # coinbase, empty(matures), payment

    def apply_plan(led):
        for cbspk, txs in plan:
            led.connect_block(cbspk, txs)
        return led

    A = apply_plan(Ledger(JAN, maturity=1))
    B = apply_plan(Ledger(JAN, maturity=1))
    assert set(A.utxos.keys()) == set(B.utxos.keys())   # independent nodes, identical UTXO set
    assert A.balance() == B.balance() == 3 * reward     # three coinbases' worth, conserved


# ---- full capability: a coin BTC could not lock, spent on both X-chains -------

@pytest.mark.parametrize("rules", [JAN, NOV], ids=["JAN09-X", "NOV08-X"])
def test_op_cat_hashlock_coin_is_spendable(rules):
    led = Ledger(rules, maturity=2)
    h1, h2 = b"the-preimage-", b"two-halves"
    lock = hashlib.sha256(h1 + h2).digest()
    spk = ["OP_CAT", "OP_SHA256", lock, "OP_EQUAL"]     # BTC disables OP_CAT -> unspendable there
    cb, tid = led.connect_coinbase(spk)
    led.advance(2)
    spend = Tx(1, [TxIn(tid, 0, assemble([h1, h2]), 0xFFFFFFFF)],
               [TxOut(cb.vout[0].value, assemble(p2pk(Wallet().new_key())))], 0)
    new_tid, _ = led.connect_tx(spend)
    assert (new_tid, 0) in led.utxos                    # settled on a full-vocabulary chain

    led2 = Ledger(rules, maturity=2)
    _, tid2 = led2.connect_coinbase(spk)
    led2.advance(2)
    bad = Tx(1, [TxIn(tid2, 0, assemble([h1, b"WRONG"]), 0xFFFFFFFF)],
             [TxOut(led2.utxos[(tid2, 0)].value, b"\x51")], 0)
    with pytest.raises(LedgerError, match="does not satisfy"):
        led2.connect_tx(bad)
