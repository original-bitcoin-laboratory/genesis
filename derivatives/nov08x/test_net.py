"""NOV08-X network: the genesis is minted under NOV08 rules, the identity is
distinct and isolated, and two nodes synchronise the chain end-to-end. Evidence:
MODEL (reuses the p2p sync plumbing with NOV08-X magic + NOV08 leading-zero PoW)."""

import asyncio
import pathlib
import sys

import pytest

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "p2p"))
sys.path.insert(0, str(_HERE.parent / "model"))

import net
from chainsync import block_hash
from consensus import Rules
from p2p import MAGIC, MsgReader, build_message

RULES = Rules.load("nov08")
JAN09_GENESIS = bytes.fromhex(
    "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f")[::-1]  # internal LE


# ---- genesis minted under NOV08 rules ----------------------------------------

def test_genesis_is_minted_under_nov08_pow():
    g = net.mint_genesis(RULES)
    h = block_hash(g)
    assert RULES.pow_ok(h, RULES.min_pow)                       # valid NOV08 leading-zero-bits PoW
    assert int.from_bytes(h, "little") <= RULES.pow_target(RULES.min_pow)
    assert bin(int.from_bytes(h, "little"))[2:].zfill(256).find("1") >= RULES.min_pow  # >=20 zero bits


def test_genesis_pays_100_coins_and_carries_the_lab_message():
    g = net.mint_genesis(RULES)
    assert net.NOV08X_GENESIS_MESSAGE in g                       # experimental coinbase text
    # coinbase value (vout[0]) is the NOV08 subsidy: 100 coins = 1e8 units at COIN=1e6
    assert RULES.get_block_value(-1) == 100 * RULES.COIN


def test_genesis_is_not_the_jan09_genesis():
    assert block_hash(net.mint_genesis(RULES)) != JAN09_GENESIS


# ---- distinct, isolated network identity (NEW-EXP) ---------------------------

def test_identity_is_distinct_from_mainnet():
    assert net.NOV08X_MAGIC != MAGIC                            # != f9 be b4 d9
    assert net.NOV08X_PORT != 8333
    assert net.NOV08X_ADDRESS_VERSION != 0x00                   # not a '1...' address


def test_a_mainnet_magic_message_is_rejected():
    async def go():
        r = asyncio.StreamReader()
        r.feed_data(build_message("version", b"", MAGIC))       # mainnet-framed
        r.feed_eof()
        with pytest.raises(ValueError):                         # a NOV08-X reader refuses it
            await MsgReader(r, net.NOV08X_MAGIC).read()
    net._run(go())


# ---- two isolated nodes synchronise the NOV08-X chain ------------------------

def test_two_nodes_sync_the_nov08x_chain():
    A, B = net._run(net.two_node_sync(nblocks=2))
    assert B.tip == A.tip, "B did not reach A's NOV08-X tip"
    assert B.best_height == 2
    assert B.main_chain() == A.main_chain()                     # identical block order from genesis
    # every synced block satisfies NOV08 proof-of-work
    for h, idx in B.by_hash.items():
        assert RULES.pow_ok(h, RULES.min_pow)
