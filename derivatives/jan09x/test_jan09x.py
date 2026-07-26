"""JAN09-X — the released v0.1.0 constitution with the full vocabulary re-opened,
as an isolated network. Symmetric twin of NOV08-X. Evidence: MODEL."""

import asyncio
import pathlib
import sys

import pytest

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "model"))
sys.path.insert(0, str(_HERE.parent / "p2p"))
sys.path.insert(0, str(_HERE))                 # jan09x at path[0] -> our net.py wins

import net                                      # jan09x/net.py
from script_full import DISABLED_IN_V01, op_notequal, run_full, valid_full
from evalscript_model import num
from chainsync import block_hash
from p2p import MAGIC, MsgReader, build_message

NOV08X_MAGIC = b"\xf0\x0b\xa7\x08"
JAN09_GENESIS = bytes.fromhex(
    "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f")[::-1]


# ---- nothing disabled: OP_NOTEQUAL re-opened ---------------------------------

def test_op_notequal_is_the_only_thing_v01_disabled():
    assert DISABLED_IN_V01 == {"OP_NOTEQUAL"}


def test_op_notequal_is_byte_level_inequality():
    assert valid_full([b"\xaa", b"\xbb", "OP_NOTEQUAL"])          # unequal -> true
    assert not valid_full([b"\xaa", b"\xaa", "OP_NOTEQUAL"])      # equal   -> false


def test_op_notequal_reproduces_satoshis_malleability_caveat():
    # 0x01 and 0x0001 are numerically equal (1 == 1) but byte-UNequal — exactly the
    # footgun Satoshi cited when disabling it (script.cpp:494).
    assert valid_full([b"\x01", b"\x00\x01", "OP_NOTEQUAL"])
    assert op_notequal(b"\x01", b"\x00\x01")


@pytest.mark.parametrize("tokens", [
    [b"\x11", b"\x22", "OP_CAT"],
    [num(6), num(7), "OP_MUL"],
    [b"\xf0", b"\x3c", "OP_XOR"],
    [num(21), "OP_2MUL"],
    [b"\xaa", b"\xbb", "OP_NOTEQUAL"],          # the re-opened one
])
def test_full_vocabulary_executes_nothing_disabled(tokens):
    ok, _ = run_full(tokens)
    assert ok


# ---- JAN09-X network identity + genesis --------------------------------------

def test_genesis_and_reward_are_the_released_constitution():
    g = net.mint_genesis()
    assert net.JAN09X_GENESIS_MESSAGE in g
    assert net._RULES.get_block_value(-1) == 50 * net._RULES.COIN     # 50 coins
    assert net._RULES.COIN == 100_000_000                            # the satoshi


def test_identity_distinct_from_mainnet_and_nov08x():
    assert net.JAN09X_MAGIC != MAGIC                                 # != mainnet f9beb4d9
    assert net.JAN09X_MAGIC != NOV08X_MAGIC                          # != NOV08-X f00ba708
    assert net.JAN09X_PORT not in (8333, 18008)


def test_genesis_is_not_the_real_jan09_genesis():
    assert block_hash(net.mint_genesis()) != JAN09_GENESIS


def test_a_mainnet_magic_message_is_rejected():
    async def go():
        r = asyncio.StreamReader()
        r.feed_data(build_message("version", b"", MAGIC))
        r.feed_eof()
        with pytest.raises(ValueError):
            await MsgReader(r, net.JAN09X_MAGIC).read()
    net._run(go())


# ---- two isolated nodes synchronise the JAN09-X chain ------------------------

def test_two_nodes_sync_the_jan09x_chain():
    A, B = net._run(net.two_node_sync(nblocks=3))
    assert B.tip == A.tip and B.best_height == 3
    assert B.main_chain() == A.main_chain()
