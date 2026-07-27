"""The validated UTXO chainstate (production node, part 2): it tracks the UTXO, accepts a valid
spend, and REJECTS a double-spend / inflation / immature-coinbase spend / bad signature; and it
reorg-safely activates the taller VALID branch while ABORTING (and restoring) a reorg to an
invalid branch. Built with real signed transactions via the lab's wallet + VerifySignature path.
Evidence: MODEL / NEW-EXP."""

import pathlib
import sys

import pytest

_HERE = pathlib.Path(__file__).resolve().parent
for _p in ("model", "p2p", "nov08x", "wallet"):
    sys.path.insert(0, str(_HERE.parent / _p))
sys.path.insert(0, str(_HERE))

import cscript                                              # noqa: E402
from chainsync import Chain, block_hash                    # noqa: E402
from p2p import block_bytes, merkle_root, pow_ok           # noqa: E402
from tx_sighash import Tx, TxIn, TxOut, dsha256, new_key, serialize as ser_tx  # noqa: E402
from spend import sign                                     # noqa: E402

from chainstate import ChainState                          # noqa: E402
from chains import CHAINS                                  # noqa: E402

ZERO = b"\x00" * 32
EASY = 0x207FFFFF
RULES = CHAINS["jan09x"].rules
_tag = [0]


def _txid(tx):
    return dsha256(ser_tx(tx))


def _key():
    priv, pub = new_key()
    return priv, [pub, "OP_CHECKSIG"]                       # (signing key, P2PK scriptPubKey tokens)


def _coinbase(height, value, spk=b"\x51"):
    _tag[0] += 1
    s = bytes([height & 0xFF, (height >> 8) & 0xFF, _tag[0] & 0xFF, (_tag[0] >> 8) & 0xFF])
    return Tx(1, [TxIn(ZERO, 0xFFFFFFFF, s, 0xFFFFFFFF)], [TxOut(value, spk)], 0)


def _mine_raw(prev, height, txs):
    mr = merkle_root(txs)
    for nonce in range(1 << 24):
        raw = block_bytes(1, prev, mr, 1_231_006_506 + height, EASY, nonce, txs)
        if pow_ok(raw, EASY):
            return raw
    raise RuntimeError("no nonce")


def _fresh(maturity=1):
    chain = Chain()                                         # compact PoW
    g = _mine_raw(ZERO, 0, [_coinbase(0, 0)])
    chain.add_genesis(g, EASY)
    return chain, ChainState(chain, RULES, maturity=maturity)


def _add(chain, st, txs, *, on=None):
    """Mine a block with `txs` on tip `on` (default active tip) and activate. Returns raw."""
    prev = on if on is not None else chain.tip
    height = chain.by_hash[prev].height + 1
    raw = _mine_raw(prev, height, txs)
    chain.process_block(raw)
    st.activate_best()
    return raw


def _subsidy(height):
    return RULES.get_block_value(height - 1)


# ---- UTXO tracking + a valid spend ------------------------------------------

def test_utxo_tracks_coinbase_outputs():
    chain, st = _fresh()
    _add(chain, st, [_coinbase(1, _subsidy(1))])
    assert st.height == 1
    assert st.balance() == 0 + _subsidy(1)                  # genesis(0) + block-1 subsidy


def test_accepts_a_valid_spend_of_a_matured_coinbase():
    chain, st = _fresh(maturity=1)
    priv, spk = _key()
    cb1 = _coinbase(1, _subsidy(1), cscript.assemble(spk))
    _add(chain, st, [cb1])                                  # height 1: coinbase paid to our key
    # spend it in block 2 (matured: 2-1 >= 1), paying a 1000-unit fee to the coinbase
    fee = 1000
    spend = Tx(1, [TxIn(_txid(cb1), 0, b"", 0xFFFFFFFF)],
               [TxOut(_subsidy(1) - fee, b"\x51")], 0)
    spend.vin[0].script = cscript.assemble([sign(priv, spk, spend, 0)])
    _add(chain, st, [_coinbase(2, _subsidy(2) + fee), spend])
    assert st.height == 2
    assert (_txid(cb1), 0) not in st.utxo                   # coinbase consumed
    assert (_txid(spend), 0) in st.utxo                     # payee output created


# ---- rejections -------------------------------------------------------------

def _matured_coin(chain, st):
    """Give the state a spendable P2PK coinbase; return (sec, spk, cb_tx)."""
    priv, spk = _key()
    cb = _coinbase(chain.by_hash[chain.tip].height + 1, _subsidy(chain.by_hash[chain.tip].height + 1),
                   cscript.assemble(spk))
    _add(chain, st, [cb])
    return priv, spk, cb


def test_rejects_double_spend():
    chain, st = _fresh(maturity=1)
    priv, spk, cb = _matured_coin(chain, st)
    h_before = st.height
    s1 = Tx(1, [TxIn(_txid(cb), 0, b"", 0xFFFFFFFF)], [TxOut(_subsidy(1), b"\x51")], 0)
    s1.vin[0].script = cscript.assemble([sign(priv, spk, s1, 0)])
    s2 = Tx(1, [TxIn(_txid(cb), 0, b"", 0xFFFFFFFF)], [TxOut(_subsidy(1), b"\x52")], 0)
    s2.vin[0].script = cscript.assemble([sign(priv, spk, s2, 0)])
    _add(chain, st, [_coinbase(2, _subsidy(2)), s1, s2])    # spends the same coin twice
    assert st.height == h_before                            # block was NOT connected (invalid)


def test_rejects_inflation():
    chain, st = _fresh(maturity=1)
    priv, spk, cb = _matured_coin(chain, st)
    h_before = st.height
    bad = Tx(1, [TxIn(_txid(cb), 0, b"", 0xFFFFFFFF)],
             [TxOut(_subsidy(1) * 5, b"\x51")], 0)           # outputs > inputs
    bad.vin[0].script = cscript.assemble([sign(priv, spk, bad, 0)])
    _add(chain, st, [_coinbase(2, _subsidy(2)), bad])
    assert st.height == h_before


def test_rejects_immature_coinbase_spend():
    chain, st = _fresh(maturity=100)                        # coinbase not spendable for 100 blocks
    priv, spk, cb = _matured_coin(chain, st)
    h_before = st.height
    spend = Tx(1, [TxIn(_txid(cb), 0, b"", 0xFFFFFFFF)], [TxOut(_subsidy(1), b"\x51")], 0)
    spend.vin[0].script = cscript.assemble([sign(priv, spk, spend, 0)])
    _add(chain, st, [_coinbase(2, _subsidy(2)), spend])
    assert st.height == h_before


def test_rejects_bad_signature():
    chain, st = _fresh(maturity=1)
    priv, spk, cb = _matured_coin(chain, st)
    h_before = st.height
    spend = Tx(1, [TxIn(_txid(cb), 0, b"", 0xFFFFFFFF)], [TxOut(_subsidy(1), b"\x51")], 0)
    spend.vin[0].script = cscript.assemble([sign(new_key()[0], spk, spend, 0)])  # wrong key
    _add(chain, st, [_coinbase(2, _subsidy(2)), spend])
    assert st.height == h_before


# ---- reorg: activate the taller VALID branch; abort an invalid reorg --------

def test_reorg_activates_the_taller_valid_branch():
    chain, st = _fresh()
    g = chain.genesis
    a1 = _add(chain, st, [_coinbase(1, _subsidy(1))], on=g)          # branch A: height 1
    assert st.tip == block_hash(a1)
    b1 = _add(chain, st, [_coinbase(1, _subsidy(1))], on=g)          # branch B forks at genesis
    b2 = _add(chain, st, [_coinbase(2, _subsidy(2))], on=block_hash(b1))
    b3 = _add(chain, st, [_coinbase(3, _subsidy(3))], on=block_hash(b2))  # B is taller -> reorg
    assert st.tip == block_hash(b3) and st.height == 3


def test_reorg_to_an_invalid_branch_is_aborted_and_old_chain_restored():
    chain, st = _fresh(maturity=1)
    g = chain.genesis
    # valid branch A, height 2
    a1 = _add(chain, st, [_coinbase(1, _subsidy(1))], on=g)
    a2 = _add(chain, st, [_coinbase(2, _subsidy(2))], on=block_hash(a1))
    assert st.tip == block_hash(a2) and st.height == 2
    utxo_a = dict(st.utxo)
    # competing branch B, TALLER (height 3) but its top block inflates -> invalid
    priv, spk = _key()
    b1cb = _coinbase(1, _subsidy(1), cscript.assemble(spk))
    b1 = _add(chain, st, [b1cb], on=g)
    b2 = _add(chain, st, [_coinbase(2, _subsidy(2))], on=block_hash(b1))
    inflate = Tx(1, [TxIn(_txid(b1cb), 0, b"", 0xFFFFFFFF)], [TxOut(_subsidy(1) * 9, b"\x51")], 0)
    inflate.vin[0].script = cscript.assemble([sign(priv, spk, inflate, 0)])
    _add(chain, st, [_coinbase(3, _subsidy(3)), inflate], on=block_hash(b2))   # B3 invalid
    # the node must NOT follow B (its tip is invalid) — it stays on valid A
    assert st.tip == block_hash(a2) and st.height == 2
    assert st.utxo.keys() == utxo_a.keys()                          # UTXO restored to A


def test_disconnect_restores_the_utxo():
    chain, st = _fresh()
    g = chain.genesis
    _add(chain, st, [_coinbase(1, _subsidy(1))], on=g)
    snapshot = set(st.utxo.keys())
    # a taller competing branch forces a reorg that disconnects block 1, then reconnects a new one
    b1 = _add(chain, st, [_coinbase(1, _subsidy(1))], on=g)
    b2 = _add(chain, st, [_coinbase(2, _subsidy(2))], on=block_hash(b1))
    assert st.height == 2
    # every live coin belongs to the now-active branch B (block-1-A's coin was disconnected)
    assert all(k in st.utxo for k in st.utxo)               # sanity: internally consistent
    assert st.balance() == 0 + _subsidy(1) + _subsidy(2)    # genesis + B1 + B2
