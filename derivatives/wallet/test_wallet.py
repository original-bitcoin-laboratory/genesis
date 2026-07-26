"""Headless v0.1 wallet: key store, coin selection, CreateTransaction, signing.

Every created transaction is re-verified by the lab's independent EvalScript (the
v0.1 VerifySignature path) and checked for value conservation. Real ECDSA on
secp256k1. Evidence level: MODEL. No VM."""

import random

import pytest

from wallet import (COIN, Wallet, hash160, p2pk, p2pkh, verify_transaction,
                    _is_p2pk, _is_p2pkh)


def _fund(w, values, kind="p2pk"):
    """Give the wallet one coin per value, paying to its own key."""
    for i, v in enumerate(values):
        sec = w.new_key()
        spk = p2pk(sec) if kind == "p2pk" else p2pkh(sec)
        w.add_coin(bytes([i + 1]) * 32, 0, v, spk)


def test_balance_counts_only_mine_and_unspent():
    w = Wallet()
    _fund(w, [50 * COIN, 10 * COIN])
    # an output to someone else's key is not ours
    other = Wallet(); osec = other.new_key()
    assert not w.add_coin(b"\x09" * 32, 0, 99 * COIN, p2pk(osec))
    assert w.get_balance() == 60 * COIN
    w.mark_spent([w.coins[0]])
    assert w.get_balance() == 10 * COIN


def test_ismine_and_extract_pubkey_both_templates():
    w = Wallet()
    sec = w.new_key()
    for spk in (p2pk(sec), p2pkh(sec)):
        assert w.is_mine(spk)
        assert w.extract_pubkey(spk) == sec
    assert not w.is_mine(p2pk(Wallet().new_key()))


def test_select_coins_exact_match_wins():
    w = Wallet(random.Random(1))
    _fund(w, [50 * COIN, 10 * COIN, 25 * COIN])
    picked = w.select_coins(10 * COIN)
    assert len(picked) == 1 and picked[0].value == 10 * COIN


def test_select_coins_lowest_larger_when_no_subset():
    w = Wallet(random.Random(2))
    _fund(w, [3 * COIN, 40 * COIN])           # can't make 20 from {3}; take the 40
    picked = w.select_coins(20 * COIN)
    assert len(picked) == 1 and picked[0].value == 40 * COIN


def test_select_coins_subset_sum_combination():
    w = Wallet(random.Random(3))
    _fund(w, [5 * COIN, 6 * COIN, 7 * COIN])  # no single coin >= 12; must combine
    picked = w.select_coins(12 * COIN)
    assert sum(c.value for c in picked) >= 12 * COIN
    assert len(picked) >= 2


@pytest.mark.parametrize("kind", ["p2pk", "p2pkh"])
def test_create_transaction_signs_and_verifies(kind):
    w = Wallet(random.Random(4))
    _fund(w, [50 * COIN], kind=kind)
    dest = p2pk(Wallet().new_key())
    tx, coins, (change, change_spk) = w.create_transaction(dest, 30 * COIN)
    assert len(tx.vout) == 2                    # payee + change
    assert tx.vout[0].value == 30 * COIN
    assert change == 20 * COIN
    assert _is_p2pk(change_spk)                 # change is a bare P2PK to self (v0.1)
    # independent verification: each input's signature + no inflation
    assert verify_transaction(w, tx, coins)


def test_no_change_output_when_exact():
    w = Wallet(random.Random(5))
    _fund(w, [30 * COIN])
    dest = p2pk(Wallet().new_key())
    tx, coins, (change, change_spk) = w.create_transaction(dest, 30 * COIN)
    assert len(tx.vout) == 1 and change == 0 and change_spk is None
    assert verify_transaction(w, tx, coins)


def test_insufficient_funds_raises():
    w = Wallet(random.Random(6))
    _fund(w, [5 * COIN])
    with pytest.raises(ValueError):
        w.create_transaction(p2pk(Wallet().new_key()), 10 * COIN)


def test_fee_comes_out_of_change_and_value_is_conserved():
    w = Wallet(random.Random(7))
    _fund(w, [50 * COIN])
    fee = 5_000_000
    tx, coins, (change, _) = w.create_transaction(p2pk(Wallet().new_key()), 30 * COIN, fee=fee)
    assert change == 20 * COIN - fee
    value_in = sum(c.value for c in coins)
    value_out = sum(o.value for o in tx.vout)
    assert value_in - value_out == fee         # the fee is exactly the unspent remainder
    assert verify_transaction(w, tx, coins)


def test_change_output_is_spendable_round_trip():
    """The wallet's own change output must itself be a valid, re-spendable coin."""
    w = Wallet(random.Random(8))
    _fund(w, [50 * COIN])
    dest = p2pk(Wallet().new_key())
    tx1, coins1, (change, change_spk) = w.create_transaction(dest, 30 * COIN)
    assert verify_transaction(w, tx1, coins1)
    w.mark_spent(coins1)
    # the change (vout[1]) comes back to the wallet as a fresh coin
    from wallet import Tx  # noqa: F401  (tx type already imported transitively)
    import hashlib
    txid1 = hashlib.sha256(hashlib.sha256(b"tx1").digest()).digest()  # stand-in txid
    assert w.add_coin(txid1, 1, change, change_spk)
    assert w.get_balance() == change
    # spend the change again
    tx2, coins2, _ = w.create_transaction(p2pk(Wallet().new_key()), 15 * COIN)
    assert coins2[0].value == change
    assert verify_transaction(w, tx2, coins2)


if __name__ == "__main__":
    w = Wallet(random.Random(0))
    _fund(w, [50 * COIN, 10 * COIN, 5 * COIN])
    print("balance:", w.get_balance() / COIN, "coins")
    tx, coins, (change, _) = w.create_transaction(p2pk(Wallet().new_key()), 42 * COIN, fee=50000)
    print("spent", len(coins), "coins; outputs:", [o.value / COIN for o in tx.vout])
    print("verify:", verify_transaction(w, tx, coins))
