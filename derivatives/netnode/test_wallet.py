"""The node wallet + localhost control interface (usability layer): a wallet persists its keys,
**earns its coinbase from mining** (respecting coinbase maturity), and **builds + signs a real
payment** whose output is owned by the recipient; and the RPC control socket answers
`getinfo` / `getnewaddress` / `getbalance` and **builds + submits a payment via `send`**. Built on
the lab's faithful v0.1 wallet MODEL (SelectCoins / CreateTransaction / VerifySignature).
Evidence: MODEL / NEW-EXP (not money)."""

import asyncio
import json
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
for _p in (_HERE.parent / "model", _HERE.parent / "p2p", _HERE.parent / "nov08x",
           _HERE.parent / "wallet", _HERE):
    sys.path.insert(0, str(_p))

from chains import CHAINS, mine_block                                # noqa: E402
from livenode import Node                                            # noqa: E402
from nodewallet import InsufficientFunds, NodeWallet                 # noqa: E402
from rpc import RpcServer                                            # noqa: E402
import pytest                                                        # noqa: E402


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


def _mine_to_wallet(node, n):
    """Mine `n` blocks whose coinbase pays the node's wallet (mirrors the miner's payout)."""
    gen_nbits = node.chain.by_hash[node.chain.genesis].nBits
    payout = node.wallet.receive_script()
    for _ in range(n):
        subsidy = node.cfg.rules.get_block_value(node.height)
        raw = mine_block(node.tip, node.height + 1, gen_nbits, node.chain.check_block,
                         subsidy, (), b"", payout)
        assert node.chain.process_block(raw)[0] == "accepted"
        node.store.append(raw)
        node.state.activate_best()


# ---- wallet ------------------------------------------------------------------

def test_wallet_persists_its_keys_across_restart(tmp_path):
    w = NodeWallet(tmp_path / "wallet.json")
    a0 = w.addresses()[0]
    a1 = w.new_address()
    reloaded = NodeWallet(tmp_path / "wallet.json")
    assert reloaded.addresses() == [a0, a1]                         # same keys after reload
    assert len(a0) == 65 and a0[0] == 0x04                          # SEC-uncompressed pubkey


def test_wallet_earns_its_coinbase_and_respects_maturity(tmp_path):
    cfg = CHAINS["jan09x"]
    n = Node(cfg, str(tmp_path / "E"), wallet=True, maturity=2)
    _mine_to_wallet(n, 3)                                           # blocks 1..3 pay our wallet
    subsidy = cfg.rules.get_block_value(0)
    # at height 3, maturity 2: blocks 1 (3-1=2✓) and 2 (3-2=1✗) — only block 1 is spendable yet
    assert n.wallet_balance() == subsidy
    _mine_to_wallet(n, 1)                                           # height 4 -> block 2 matures too
    assert n.wallet_balance() == 2 * subsidy
    n.store.close()


def test_wallet_builds_a_payment_owned_by_the_recipient(tmp_path):
    cfg = CHAINS["jan09x"]
    a = Node(cfg, str(tmp_path / "A"), wallet=True, maturity=1)
    _mine_to_wallet(a, 2)                                           # block-1 coinbase matured
    recipient = NodeWallet(tmp_path / "B.json")                    # a separate wallet (the payee)
    to = recipient.addresses()[0]
    amount = a.wallet_balance() // 2
    raw = a.wallet.create_payment(a.state.utxo, a.state.height, a.state.maturity, to, amount, 0)
    e = a.submit_tx(raw)
    assert len(a.mempool) == 1
    # mine the payment (paying subsidy + its fee, again to A's wallet)
    selected = a.mempool.select(a.state.utxo)
    from difficulty import expected_bits
    nbits = expected_bits(a.chain, a.tip, cfg.rules)
    subsidy = cfg.rules.get_block_value(a.height)
    blk = mine_block(a.tip, a.height + 1, nbits, a.chain.check_block,
                     subsidy + sum(x.fee for x in selected), [x.tx for x in selected],
                     b"", a.wallet.receive_script())
    assert a.chain.process_block(blk)[0] == "accepted"
    a.state.activate_best()
    a.mempool.reconcile(a.state.utxo, a.state.height)
    # the recipient wallet, viewing A's UTXO, now owns the paid amount
    assert recipient.balance(a.state.utxo, a.state.height, a.state.maturity) == amount
    a.store.close()


def test_wallet_send_rejects_an_overspend(tmp_path):
    cfg = CHAINS["jan09x"]
    n = Node(cfg, str(tmp_path / "OS"), wallet=True, maturity=1)
    _mine_to_wallet(n, 2)
    with pytest.raises(InsufficientFunds):
        n.wallet.create_payment(n.state.utxo, n.state.height, n.state.maturity,
                                n.wallet.addresses()[0], n.wallet_balance() * 10, 0)
    n.store.close()


# ---- localhost control interface (RPC) --------------------------------------

async def _rpc_session(node, calls):
    rpc = RpcServer(node, port=0)
    await rpc.start()
    r, w = await asyncio.open_connection("127.0.0.1", rpc.port)
    out = []
    for method, params in calls:
        w.write((json.dumps({"method": method, "params": list(params)}) + "\n").encode())
        await w.drain()
        out.append(json.loads(await r.readline()))
    w.close()
    await rpc.stop()
    return out


def test_rpc_getinfo_getbalance_getnewaddress(tmp_path):
    cfg = CHAINS["jan09x"]
    n = Node(cfg, str(tmp_path / "R"), wallet=True, maturity=1)
    _mine_to_wallet(n, 2)
    info, bal, addr = _run(_rpc_session(
        n, [("getinfo", ()), ("getbalance", ()), ("getnewaddress", ())]))
    assert info["result"]["chain"] == "jan09x" and info["result"]["money"] is False
    assert info["result"]["height"] == 2 and info["result"]["wallet"] is True
    assert bal["result"] == cfg.rules.get_block_value(0)            # one matured coinbase
    assert len(bytes.fromhex(addr["result"])) == 65                # a fresh SEC pubkey
    n.store.close()


def test_rpc_send_builds_and_submits_a_payment(tmp_path):
    cfg = CHAINS["jan09x"]
    n = Node(cfg, str(tmp_path / "RS"), wallet=True, maturity=1)
    _mine_to_wallet(n, 2)
    to = n.wallet.addresses()[0].hex()                             # send to self (simplest round-trip)
    amount = n.wallet_balance() // 2
    (resp,) = _run(_rpc_session(n, [("send", (to, amount, 0))]))
    assert "result" in resp and len(bytes.fromhex(resp["result"])) == 32   # returns a txid
    assert len(n.mempool) == 1                                     # the built payment is now pooled
    n.store.close()


def test_rpc_getrecentblocks_summarizes_the_chain(tmp_path):
    cfg = CHAINS["jan09x"]
    n = Node(cfg, str(tmp_path / "RB"), wallet=True, maturity=1)
    _mine_to_wallet(n, 3)
    (resp,) = _run(_rpc_session(n, [("getrecentblocks", (2,))]))
    blocks = resp["result"]
    assert len(blocks) == 2                                # last 2 blocks, newest first
    assert blocks[0]["height"] == 3 and blocks[1]["height"] == 2
    assert all(len(b["hash"]) == 64 and b["ntx"] >= 1 for b in blocks)
    n.store.close()


def test_rpc_send_without_a_wallet_errors(tmp_path):
    cfg = CHAINS["jan09x"]
    n = Node(cfg, str(tmp_path / "NW"))                            # no --wallet
    (resp,) = _run(_rpc_session(n, [("getbalance", ())]))
    assert "error" in resp and "wallet" in resp["error"]
    n.store.close()


# ---- P2PKH / Base58 addresses (v0.1 'Bitcoin address' format) ----------------

def test_base58check_roundtrips_and_detects_addresses():
    from base58 import (address_to_hash160, b58decode, b58encode, hash160,
                        is_p2pkh_address, pubkey_to_address)
    from tx_sighash import new_key
    for raw in (b"\x00\x00\x01\x02", b"hello world", bytes(range(20))):
        assert b58decode(b58encode(raw)) == raw               # roundtrip incl. leading-zero '1's
    _, sec = new_key()
    addr = pubkey_to_address(sec)
    assert addr[0] == "1"                                      # v0.1 mainnet version byte -> '1...'
    assert address_to_hash160(addr) == hash160(sec)           # the address commits to hash160(pubkey)
    assert is_p2pkh_address(addr)
    assert not is_p2pkh_address(sec.hex())                    # a raw pubkey hex is not an address
    bad = addr[:-1] + ("2" if addr[-1] != "2" else "3")       # corrupt the checksum
    assert not is_p2pkh_address(bad)


def test_rpc_getprimaryaddress_shows_the_existing_key_without_minting(tmp_path):
    cfg = CHAINS["jan09x"]
    n = Node(cfg, str(tmp_path / "PP"), wallet=True, maturity=1)
    _mine_to_wallet(n, 1)
    keys_before = len(n.wallet.keys)
    a1, a2 = _run(_rpc_session(n, [("getprimaryaddress", ()), ("getprimaryaddress", ())]))
    r1, r2 = a1["result"], a2["result"]
    assert r1 == r2                                            # stable across calls
    assert len(n.wallet.keys) == keys_before                  # minted nothing
    from base58 import address_to_hash160, hash160
    assert address_to_hash160(r1["address"]) == hash160(bytes.fromhex(r1["pubkey"]))
    assert r1["address"][0] == "1" and r1["not_money"] is True
    n.store.close()


def test_send_to_a_p2pkh_address_is_owned_by_the_recipient(tmp_path):
    cfg = CHAINS["jan09x"]
    a = Node(cfg, str(tmp_path / "PA"), wallet=True, maturity=1)
    _mine_to_wallet(a, 2)                                      # block-1 coinbase matured
    recipient = NodeWallet(tmp_path / "PB.json")
    from base58 import pubkey_to_address
    addr = pubkey_to_address(recipient.addresses()[0])        # a '1...' P2PKH address
    assert addr[0] == "1"
    amount = a.wallet_balance() // 2
    (resp,) = _run(_rpc_session(a, [("send", (addr, amount, 0))]))   # exercises the address resolver
    assert "result" in resp, resp
    assert len(a.mempool) == 1
    selected = a.mempool.select(a.state.utxo)
    from difficulty import expected_bits
    nbits = expected_bits(a.chain, a.tip, cfg.rules)
    subsidy = cfg.rules.get_block_value(a.height)
    blk = mine_block(a.tip, a.height + 1, nbits, a.chain.check_block,
                     subsidy + sum(x.fee for x in selected), [x.tx for x in selected],
                     b"", a.wallet.receive_script())
    assert a.chain.process_block(blk)[0] == "accepted"
    a.state.activate_best()
    # the recipient owns the P2PKH output — IsMine resolves it via the hash160 -> pubkey map
    assert recipient.balance(a.state.utxo, a.state.height, a.state.maturity) == amount
    a.store.close()
