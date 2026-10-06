"""Fidelity of netnode to the January 2009 client at the points where a stranger could split the
network along our own implementation boundary (standing review, 5 Oct 2026).

Each test states what v0.1 does, with the source line, and asserts netnode does the same:

  value sums      int64, two's-complement (main.h:492 GetValueOut; main.cpp:845-854 ConnectInputs;
                  main.cpp:953 coinbase vs GetBlockValue). The Aug 2010 overflow tx is ACCEPTED.
  CheckTransaction (main.h, called from CheckBlock): vin/vout non-empty; no negative output;
                  coinbase scriptSig 2..100 bytes (JAN09) / <=100 (NOV08 main.h); no null prevout
                  on a non-coinbase input.
  block size      MAX_SIZE = 0x02000000 (serialize.h) -- a block up to 32 MiB is valid and must be
                  receivable on the wire.

A shared flaw is documented, not "fixed": the 2012 duplicate-transaction Merkle ambiguity (two block
bodies, one header hash) exists in v0.1 and is reproduced here as a faithful property. What v0.1 does
NEXT is matched too: a block that fails ConnectBlock is erased, not banned, so the honest body under
the same hash is accepted afterwards (OBL-F-0049).
Evidence: MODEL / NEW-EXP. Executed against netnode only; the 2009 binary column is replay/'s job.
"""

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
for _p in ("model", "p2p", "nov08x", "wallet", "profiles"):
    sys.path.insert(0, str(_HERE.parent / _p))
sys.path.insert(0, str(_HERE))

import cscript                                              # noqa: E402
import profiles                                             # noqa: E402
from chainstate import ChainState                          # noqa: E402
from chainsync import Chain, block_hash                     # noqa: E402
from p2p import block_bytes, merkle_root, pow_ok           # noqa: E402
from spend import sign                                      # noqa: E402
from tx_sighash import Tx, TxIn, TxOut, dsha256, new_key, serialize as ser_tx   # noqa: E402
import wire                                                 # noqa: E402

ZERO = b"\x00" * 32
NULL_N = 0xFFFFFFFF
EASY = 0x207FFFFF
RULES = profiles.load("jan09-faithful").rules()
OVERFLOW_OUT = 9223372036854277039          # block 74638 (15 Aug 2010), each of two outputs
_tag = [0]


def _txid(tx):
    return dsha256(ser_tx(tx))


def _coinbase(height, value, spk=b"\x51", script=None):
    _tag[0] += 1
    s = script if script is not None else bytes(
        [height & 0xFF, (height >> 8) & 0xFF, _tag[0] & 0xFF, (_tag[0] >> 8) & 0xFF])
    return Tx(1, [TxIn(ZERO, NULL_N, s, 0xFFFFFFFF)], [TxOut(value, spk)], 0)


def _mine_raw(prev, height, txs, merkle_txs=None):
    mr = merkle_root(merkle_txs if merkle_txs is not None else txs)
    for nonce in range(1 << 24):
        raw = block_bytes(1, prev, mr, 1_231_006_506 + height, EASY, nonce, txs)
        if pow_ok(raw, EASY):
            return raw
    raise RuntimeError("no nonce")


def _fresh(rules=RULES):
    chain = Chain()
    chain.add_genesis(_mine_raw(ZERO, 0, [_coinbase(0, 0)]), EASY)
    return chain, ChainState(chain, rules, maturity=1)


def _add(chain, st, txs):
    prev = chain.tip
    raw = _mine_raw(prev, chain.by_hash[prev].height + 1, txs)
    chain.process_block(raw)
    st.activate_best()
    return raw


def _subsidy(h):
    return RULES.get_block_value(h - 1)


def _matured(chain, st):
    priv, pub = new_key()
    spk = [pub, "OP_CHECKSIG"]
    h = chain.by_hash[chain.tip].height + 1
    cb = _coinbase(h, _subsidy(h), cscript.assemble(spk))
    _add(chain, st, [cb])
    return priv, spk, cb


def _spend(priv, spk, cb, outs):
    tx = Tx(1, [TxIn(_txid(cb), 0, b"", 0xFFFFFFFF)], outs, 0)
    tx.vin[0].script = cscript.assemble([sign(priv, spk, tx, 0)])
    return tx


# ---- 1. the August 2010 overflow: v0.1 ACCEPTS --------------------------------------------------

def test_overflow_transaction_is_accepted_as_v01_does():
    chain, st = _fresh()
    priv, spk, cb = _matured(chain, st)
    h0 = st.height
    bad = _spend(priv, spk, cb, [TxOut(OVERFLOW_OUT, b"\x51"), TxOut(OVERFLOW_OUT, b"\x51")])
    _add(chain, st, [_coinbase(h0 + 1, _subsidy(h0 + 1)), bad])
    assert st.height == h0 + 1, "v0.1 accepts the block: int64 output sum wraps to -997538"
    assert st.utxo[(_txid(bad), 0)].value == OVERFLOW_OUT


def test_plain_inflation_is_still_rejected():
    chain, st = _fresh()
    priv, spk, cb = _matured(chain, st)
    h0 = st.height
    bad = _spend(priv, spk, cb, [TxOut(_subsidy(1) + 1, b"\x51")])
    _add(chain, st, [_coinbase(h0 + 1, _subsidy(h0 + 1)), bad])
    assert st.height == h0, "nTxFee < 0 (main.cpp:850) rejects without any wrap"


# ---- 2. CheckTransaction rules v0.1 enforces inside CheckBlock -----------------------------------

def test_negative_output_rejected():
    chain, st = _fresh()
    priv, spk, cb = _matured(chain, st)
    h0 = st.height
    bad = _spend(priv, spk, cb, [TxOut(-1, b"\x51"), TxOut(1000, b"\x51")])
    _add(chain, st, [_coinbase(h0 + 1, _subsidy(h0 + 1)), bad])
    assert st.height == h0, "CheckTransaction: txout.nValue negative"


def test_empty_vout_rejected():
    chain, st = _fresh()
    priv, spk, cb = _matured(chain, st)
    h0 = st.height
    bad = _spend(priv, spk, cb, [])
    _add(chain, st, [_coinbase(h0 + 1, _subsidy(h0 + 1)), bad])
    assert st.height == h0, "CheckTransaction: vin or vout empty"


def test_coinbase_script_one_byte_rejected_under_jan09():
    chain, st = _fresh()
    h0 = st.height
    _add(chain, st, [_coinbase(h0 + 1, _subsidy(h0 + 1), script=b"\x01")])
    assert st.height == h0, "JAN09 CheckTransaction: coinbase script size < 2"


def test_coinbase_script_101_bytes_rejected():
    chain, st = _fresh()
    h0 = st.height
    _add(chain, st, [_coinbase(h0 + 1, _subsidy(h0 + 1), script=b"\x00" * 101)])
    assert st.height == h0, "CheckTransaction: coinbase script size > 100"


def test_coinbase_script_one_byte_accepted_under_nov08():
    """NOV08 main.h checks only `scriptSig.size() > 100`; the 2-byte minimum is a JAN09 addition."""
    from fullnode import check_transaction_2009       # the bound follows the chain's own profile
    nov = profiles.load("nov08-source-bounded").rules()
    assert nov.profile == "NOV08"
    assert check_transaction_2009(_coinbase(1, 0, script=b"\x01"), nov) is None
    assert check_transaction_2009(_coinbase(1, 0, script=b"\x01"), RULES) is not None


# ---- 3. block size: up to MAX_SIZE must be receivable --------------------------------------------

MAGIC = b"\xf9\xbe\xb4\xd9"


def _read(framed):
    import asyncio

    async def go():
        r = asyncio.StreamReader()
        r.feed_data(framed)
        r.feed_eof()
        return await wire.read_message(r, MAGIC)
    return asyncio.run(go())


def test_wire_accepts_a_block_message_above_4_mib():
    payload = b"\x00" * (5 * 1024 * 1024)
    cmd, got = _read(wire.frame("block", payload, MAGIC))
    assert cmd == "block" and len(got) == len(payload)


def test_wire_still_caps_non_block_messages_at_4_mib():
    import pytest
    big = b"\x00" * (4 * 1024 * 1024 + 1)
    with pytest.raises(wire.WireError):
        wire.frame("inv", big, MAGIC)                    # refused at framing
    hdr = MAGIC + b"inv".ljust(12, b"\x00") + len(big).to_bytes(4, "little") + wire.dsha256(big)[:4]
    with pytest.raises(wire.WireError):
        _read(hdr + big)                                 # refused on read


def test_wire_caps_block_messages_at_max_size():
    import pytest
    big = 0x02000000 + 1                                 # MAX_SIZE + 1
    hdr = MAGIC + b"block".ljust(12, b"\x00") + big.to_bytes(4, "little") + b"\x00" * 4
    with pytest.raises(wire.WireError):
        _read(hdr)                                       # declared size refused before any read


# ---- 4. a shared flaw, reproduced faithfully: duplicate-tx Merkle ambiguity ----------------------

def test_duplicate_tx_merkle_ambiguity_is_a_shared_property():
    """[cb, A, B] and [cb, A, B, B] have the same Merkle root (odd levels duplicate the last hash in
    v0.1 BuildMerkleTree) and therefore the same header hash. Recorded, not changed."""
    a = Tx(1, [TxIn(b"\x11" * 32, 0, b"\x51", 0xFFFFFFFF)], [TxOut(1, b"\x51")], 0)
    b = Tx(1, [TxIn(b"\x22" * 32, 0, b"\x51", 0xFFFFFFFF)], [TxOut(1, b"\x51")], 0)
    cb = _coinbase(1, 0)
    assert merkle_root([cb, a, b]) == merkle_root([cb, a, b, b])


# ---- 5. a block that fails ConnectBlock is ERASED, so an honest copy of it is accepted ---------
#
# v0.1 main.cpp:1104-1112 (AddToBlockIndex, extending the best chain) and :1024-1036 (Reorganize):
# when ConnectBlock fails, the block is erased from disk, from the tx index AND from mapBlockIndex.
# AcceptBlock's duplicate check (main.cpp:1196) is on mapBlockIndex, so a later block with the SAME
# hash is accepted afresh. With the Merkle ambiguity above, a peer can send a mutated body under an
# honest block's header hash first; a node that remembers the hash as invalid then refuses the honest
# block for good, while every 2009 client recovers.

def _two_spends(chain, st):
    p1, s1, c1 = _matured(chain, st)
    p2, s2, c2 = _matured(chain, st)
    return _spend(p1, s1, c1, [TxOut(1, b"\x51")]), _spend(p2, s2, c2, [TxOut(1, b"\x51")])


def _honest_and_mutated(chain, txs, mutated_txs):
    prev = chain.tip
    height = chain.by_hash[prev].height + 1
    honest = _mine_raw(prev, height, txs)
    nonce = int.from_bytes(honest[76:80], "little")
    mutated = block_bytes(1, prev, merkle_root(txs), 1_231_006_506 + height, EASY, nonce, mutated_txs)
    assert block_hash(mutated) == block_hash(honest) and mutated != honest
    return honest, mutated


def test_mutated_copy_does_not_lock_out_the_honest_block():
    chain, st = _fresh()
    a, b = _two_spends(chain, st)
    h0 = st.height
    cb = _coinbase(h0 + 1, _subsidy(h0 + 1))
    honest, mutated = _honest_and_mutated(chain, [cb, a, b], [cb, a, b, b])

    chain.process_block(mutated)                              # B twice: its input is spent twice
    st.activate_best()
    assert st.height == h0, "the mutated body fails ConnectBlock"
    assert chain.tip == st.tip, "the index forgets it, as mapBlockIndex.erase does"

    status, h = chain.process_block(honest)
    assert status == "accepted", "v0.1 AcceptBlock: the hash is no longer in mapBlockIndex"
    st.activate_best()
    assert st.height == h0 + 1 and st.tip == h
    assert h not in st.invalid


def test_a_failed_block_takes_the_rest_of_its_branch_with_it():
    """Reorganize() erases vConnect[i:] -- the failing block and every block above it."""
    chain, st = _fresh()
    a, b = _two_spends(chain, st)
    h0 = st.height
    cb = _coinbase(h0 + 1, _subsidy(h0 + 1))
    honest, mutated = _honest_and_mutated(chain, [cb, a, b], [cb, a, b, b])
    chain.process_block(mutated)
    child = _mine_raw(block_hash(mutated), h0 + 2, [_coinbase(h0 + 2, _subsidy(h0 + 2))])
    chain.process_block(child)                                # arrives before anything is validated
    st.activate_best()
    assert st.height == h0
    assert block_hash(mutated) not in chain.by_hash and block_hash(child) not in chain.by_hash
    assert chain.tip == st.tip
