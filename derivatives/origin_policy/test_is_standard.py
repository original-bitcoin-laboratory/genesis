"""IsStandard as a policy, executed: the January 2009 node relays a non-template transaction that the
7 December 2010 node (a206a2398) refuses, and CheckTransaction accepts it in both eras. Evidence: MODEL."""

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent / "model"))

from is_standard import (                                                 # noqa: E402
    OP_CHECKMULTISIG, OP_CHECKSIG, PUBKEY, PREV, SCRIPT_SIG, accept_to_memory_pool_20101207,
    accept_to_memory_pool_v01, block_validity_unaffected, hashlock_tx, is_standard_output,
    p2pk_tx, sigop_count,
)
from tx_sighash import Tx, TxIn, TxOut, serialize                         # noqa: E402


def test_january_relays_the_hashlock_and_december_2010_refuses_it():
    tx = hashlock_tx()
    assert len(serialize(tx)) >= 100                       # not refused for size: the clause under test is standardness
    assert accept_to_memory_pool_v01(tx) == (True, "ok")
    assert accept_to_memory_pool_20101207(tx) == (False, "nonstandard")


def test_a_block_carrying_it_is_valid_under_both_eras():
    assert block_validity_unaffected(hashlock_tx()) == (True, True)
    assert block_validity_unaffected(p2pk_tx()) == (True, True)


def test_both_eras_relay_the_template_transaction():
    tx = p2pk_tx()
    assert accept_to_memory_pool_v01(tx) == (True, "ok")
    assert accept_to_memory_pool_20101207(tx) == (True, "ok")


def test_the_two_templates_and_their_edges():
    assert is_standard_output(b"\x41" + PUBKEY + bytes([OP_CHECKSIG]))                     # 65-byte push, CHECKSIG
    assert is_standard_output(b"\x21" + b"\x02" + b"\x11" * 32 + bytes([OP_CHECKSIG]))       # 33 > 32: Solver accepts
    assert not is_standard_output(b"\x20" + b"\x11" * 32 + bytes([OP_CHECKSIG]))             # 32 bytes: `<= sizeof(uint256)` fails
    assert is_standard_output(b"\x76\xa9\x14" + b"\x44" * 20 + b"\x88\xac")                  # P2PKH
    assert not is_standard_output(b"\x76\xa9\x13" + b"\x44" * 19 + b"\x88\xac")              # 19-byte hash: not uint160
    assert not is_standard_output(b"\x51")                                                    # OP_1 alone
    assert not is_standard_output(b"\x41" + PUBKEY)                                           # no CHECKSIG


def test_the_other_two_clauses_of_a206a2398():
    # sigops: three CHECKSIG outputs exceed `GetSigOpCount() > 2`
    three = Tx(1, [TxIn(PREV, 0, SCRIPT_SIG)], [TxOut(1, b"\x41" + PUBKEY + bytes([OP_CHECKSIG]))] * 3, 0)
    assert sigop_count(three) == 3
    assert accept_to_memory_pool_20101207(three) == (False, "nonstandard")
    assert accept_to_memory_pool_v01(three) == (True, "ok")
    # a bare CHECKMULTISIG output counts twenty
    multi = Tx(1, [TxIn(PREV, 0, SCRIPT_SIG)], [TxOut(1, bytes([OP_CHECKMULTISIG]))], 0)
    assert sigop_count(multi) == 20
    # size: a template transaction under 100 bytes is refused for size alone
    tiny = Tx(1, [TxIn(PREV, 0, b"\x51")], [TxOut(1, b"\x76\xa9\x14" + b"\x44" * 20 + b"\x88\xac")], 0)
    assert len(serialize(tiny)) < 100
    assert accept_to_memory_pool_20101207(tiny) == (False, "nonstandard")
    assert accept_to_memory_pool_v01(tiny) == (True, "ok")
