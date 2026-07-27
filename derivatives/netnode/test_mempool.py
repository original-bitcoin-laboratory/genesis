"""The mempool + tx relay + block assembly (production node, part 3): the pool validates a spend
against the confirmed UTXO *and* pooled parents (chained unconfirmed spends), rejects a
double-spend / inflation / bad signature / immature-coinbase spend and records the fee; `select`
orders parents before children; `reconcile` drops a tx whose input was spent; the miner assembles
a pooled tx into a block (claiming subsidy + fees) after which it leaves the pool; and a tx
**relays over real TCP** into a second node's mempool. Built with the lab's real signed
transactions + VerifySignature path. Evidence: MODEL / NEW-EXP (not money)."""

import asyncio
import pathlib
import sys

import pytest

_HERE = pathlib.Path(__file__).resolve().parent
# netnode's own dir LAST so it lands at sys.path[0] and wins name clashes (e.g. node.py)
for _p in (_HERE.parent / "model", _HERE.parent / "p2p", _HERE.parent / "nov08x", _HERE):
    sys.path.insert(0, str(_p))

import cscript                                                       # noqa: E402
from p2p import MSG_TX                                              # noqa: E402
from spend import sign                                              # noqa: E402
from tx_sighash import (Tx, TxIn, TxOut, dsha256, new_key,          # noqa: E402
                        serialize as ser_tx)

from chains import CHAINS, mine_block, mine_next                    # noqa: E402
from chainstate import Coin                                         # noqa: E402
from difficulty import expected_bits                               # noqa: E402
from fullnode import parse_block                                    # noqa: E402
from livenode import Node                                           # noqa: E402
from mempool import Mempool, MempoolReject                          # noqa: E402


def _run(coro):
    loop = asyncio.SelectorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        pending = asyncio.all_tasks(loop)
        for t in pending:
            t.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()


def _seed(node, n):
    gen_nbits = node.chain.by_hash[node.chain.genesis].nBits
    for _ in range(n):
        subsidy = node.cfg.rules.get_block_value(node.height)
        raw = mine_next(node.tip, node.height + 1, gen_nbits, node.chain.check_block, subsidy)
        assert node.chain.process_block(raw)[0] == "accepted"
        node.store.append(raw)
        node.state.activate_best()


def _p2pk_coin(value, *, coinbase=False, height=0, txid=b"\xaa" * 32, n=0):
    """A confirmed UTXO holding one P2PK coin we can sign for. Returns (utxo, outpoint, priv, spk)."""
    priv, pub = new_key()
    spk = [pub, "OP_CHECKSIG"]
    return {(txid, n): Coin(value, spk, height, coinbase)}, (txid, n), priv, spk


def _signed_spend(op, priv, spk, out_value, out_spk=b"\x51"):
    tx = Tx(1, [TxIn(op[0], op[1], b"", 0xFFFFFFFF)], [TxOut(out_value, out_spk)], 0)
    tx.vin[0].script = cscript.assemble([sign(priv, spk, tx, 0)])
    return tx


# ---- mempool acceptance -----------------------------------------------------

def test_accepts_a_valid_spend_and_records_the_fee():
    utxo, op, priv, spk = _p2pk_coin(10_000)
    spend = _signed_spend(op, priv, spk, 9_000)
    mp = Mempool()
    e = mp.accept(ser_tx(spend), utxo, 1)
    assert e.fee == 1_000                                           # 10_000 in − 9_000 out
    assert len(mp) == 1 and mp.has(e.txid)


def test_rejects_a_double_spend_within_the_pool():
    utxo, op, priv, spk = _p2pk_coin(10_000)
    mp = Mempool()
    mp.accept(ser_tx(_signed_spend(op, priv, spk, 9_000)), utxo, 1)
    with pytest.raises(MempoolReject):
        mp.accept(ser_tx(_signed_spend(op, priv, spk, 8_000, out_spk=b"\x52")), utxo, 1)


def test_rejects_inflation():
    utxo, op, priv, spk = _p2pk_coin(10_000)
    mp = Mempool()
    with pytest.raises(MempoolReject):
        mp.accept(ser_tx(_signed_spend(op, priv, spk, 20_000)), utxo, 1)   # out > in


def test_rejects_a_bad_signature():
    utxo, op, _priv, spk = _p2pk_coin(10_000)
    wrong = new_key()[0]                                            # not the key the coin pays to
    mp = Mempool()
    with pytest.raises(MempoolReject):
        mp.accept(ser_tx(_signed_spend(op, wrong, spk, 9_000)), utxo, 1)


def test_rejects_then_accepts_a_coinbase_spend_across_maturity():
    utxo, op, priv, spk = _p2pk_coin(10_000, coinbase=True, height=5)
    spend = ser_tx(_signed_spend(op, priv, spk, 9_000))
    mp = Mempool()
    with pytest.raises(MempoolReject):
        mp.accept(spend, utxo, 10)                                  # 10 − 5 = 5 < 100 → immature
    e = mp.accept(spend, utxo, 200)                                 # 200 − 5 = 195 ≥ 100 → mature
    assert e.fee == 1_000


def test_allows_and_orders_a_chained_unconfirmed_spend():
    utxo, op, priv, spk = _p2pk_coin(10_000)
    mp = Mempool()
    parent = _signed_spend(op, priv, spk, 9_000)                   # pays OP_1 (anyone can spend)
    pe = mp.accept(ser_tx(parent), utxo, 1)
    child = Tx(1, [TxIn(pe.txid, 0, b"", 0xFFFFFFFF)], [TxOut(8_000, b"\x51")], 0)  # spends the pooled output
    ce = mp.accept(ser_tx(child), utxo, 1)
    assert ce.fee == 1_000 and len(mp) == 2
    chosen = mp.select(utxo)
    assert [x.txid for x in chosen] == [pe.txid, ce.txid]          # parent before child


def test_reconcile_drops_a_tx_whose_input_was_spent():
    utxo, op, priv, spk = _p2pk_coin(10_000)
    mp = Mempool()
    mp.accept(ser_tx(_signed_spend(op, priv, spk, 9_000)), utxo, 1)
    assert len(mp) == 1
    mp.reconcile({}, 2)                                            # the coin is gone (mined/reorged away)
    assert len(mp) == 0


# ---- block assembly: a pooled tx is mined and leaves the pool ---------------

def test_miner_assembles_a_pool_tx_and_it_leaves_the_pool(tmp_path):
    cfg = CHAINS["jan09x"]
    n = Node(cfg, str(tmp_path / "MP"), maturity=1)                # block-1 coinbase matures at height 2
    _seed(n, 2)
    cb1 = parse_block(n.chain.by_hash[n.state.active[1]].raw)[0]   # block-1 coinbase (pays OP_1)
    cb1_txid = dsha256(ser_tx(cb1))
    value, fee = cb1.vout[0].value, 1_000
    raw = ser_tx(Tx(1, [TxIn(cb1_txid, 0, b"", 0xFFFFFFFF)], [TxOut(value - fee, b"\x51")], 0))
    e = n.submit_tx(raw)
    assert e.fee == fee and len(n.mempool) == 1
    selected = n.mempool.select(n.state.utxo)
    fees = sum(x.fee for x in selected)
    subsidy = cfg.rules.get_block_value(n.height)
    nbits = expected_bits(n.chain, n.tip, cfg.rules)
    block = mine_block(n.tip, n.height + 1, nbits, n.chain.check_block,
                       subsidy + fees, [x.tx for x in selected])
    assert n.chain.process_block(block)[0] == "accepted"
    n.state.activate_best()
    n.mempool.reconcile(n.state.utxo, n.state.height)
    assert n.state.height == 3
    assert len(n.mempool) == 0                                     # mined → out of the pool
    assert (dsha256(raw), 0) in n.state.utxo                       # payee output confirmed
    assert (cb1_txid, 0) not in n.state.utxo                       # coinbase consumed
    n.store.close()


# ---- part 4: orphan-tx buffering + fee-rate eviction ------------------------

def test_orphan_tx_is_held_then_promoted_when_its_parent_arrives():
    utxo, op, priv, spk = _p2pk_coin(10_000)
    mp = Mempool()
    parent = _signed_spend(op, priv, spk, 9_000)                  # pays OP_1
    ptxid = dsha256(ser_tx(parent))
    child = Tx(1, [TxIn(ptxid, 0, b"", 0xFFFFFFFF)], [TxOut(8_000, b"\x51")], 0)
    ctxid = dsha256(ser_tx(child))
    # child arrives first — its parent is unseen → buffered as an orphan, neither accepted nor rejected
    entry, promoted = mp.accept_or_orphan(ser_tx(child), utxo, 1)
    assert entry is None and promoted == []
    assert len(mp) == 0 and ctxid in mp.orphans
    # parent arrives → accepted, and it unblocks (promotes) the waiting child
    entry, promoted = mp.accept_or_orphan(ser_tx(parent), utxo, 1)
    assert entry is not None and [e.txid for e in promoted] == [ctxid]
    assert len(mp) == 2 and mp.has(ctxid) and not mp.orphans      # orphan buffer drained


def test_a_provably_invalid_tx_is_rejected_not_buffered():
    utxo, op, priv, spk = _p2pk_coin(10_000)
    mp = Mempool()
    bad = _signed_spend(op, priv, spk, 20_000)                    # inflation (input present, out > in)
    with pytest.raises(MempoolReject):
        mp.accept_or_orphan(ser_tx(bad), utxo, 1)
    assert not mp.orphans                                         # inputs exist → not an orphan


def test_fee_rate_eviction_prefers_higher_paying_transactions():
    priv, pub = new_key()
    spk = [pub, "OP_CHECKSIG"]
    ca, cb, cc = (b"\xaa" * 32, 0), (b"\xbb" * 32, 0), (b"\xcc" * 32, 0)
    utxo = {c: Coin(10_000, spk, 0, False) for c in (ca, cb, cc)}
    mp = Mempool(max_txs=1)
    lo = mp.accept(ser_tx(_signed_spend(ca, priv, spk, 9_900)), utxo, 1)   # fee 100
    assert len(mp) == 1
    hi = mp.accept(ser_tx(_signed_spend(cb, priv, spk, 5_000)), utxo, 1)   # fee 5_000 → higher rate
    assert len(mp) == 1 and mp.has(hi.txid) and not mp.has(lo.txid)        # evicted the cheap one
    with pytest.raises(MempoolReject):                                     # a cheaper newcomer can't evict it
        mp.accept(ser_tx(_signed_spend(cc, priv, spk, 9_950)), utxo, 1)    # fee 50 → lower rate
    assert mp.has(hi.txid)


# ---- tx relay over REAL TCP -------------------------------------------------

async def _tx_relay_scenario(da, db):
    cfg = CHAINS["jan09x"]
    a = Node(cfg, da, listen=("127.0.0.1", 0), maturity=1)
    _seed(a, 2)
    await a.start()
    b = Node(cfg, db, listen=("127.0.0.1", 0), maturity=1)
    await b.start(connect=[("127.0.0.1", a.port)])
    for _ in range(250):                                          # B syncs A's chain first
        if b.height == a.height:
            break
        await asyncio.sleep(0.02)
    cb1 = parse_block(a.chain.by_hash[a.state.active[1]].raw)[0]
    cb1_txid = dsha256(ser_tx(cb1))
    raw = ser_tx(Tx(1, [TxIn(cb1_txid, 0, b"", 0xFFFFFFFF)],
                    [TxOut(cb1.vout[0].value - 500, b"\x51")], 0))
    txid = dsha256(raw)
    a.submit_tx(raw)
    await a._announce([(MSG_TX, txid)])                           # broadcast: inv → getdata → tx
    relayed = False
    for _ in range(250):
        if b.mempool.has(txid):
            relayed = True
            break
        await asyncio.sleep(0.02)
    synced = b.height == a.height
    await a.stop()
    await b.stop()
    return synced, relayed


def test_tx_relays_over_tcp_into_a_second_mempool(tmp_path):
    synced, relayed = _run(_tx_relay_scenario(str(tmp_path / "A"), str(tmp_path / "B")))
    assert synced                                                 # B validated A's chain
    assert relayed                                                # …then accepted A's tx via inv/getdata/tx
