"""Two headless v0.1 nodes over localhost TCP exchange a block and a transaction
via the real wire protocol (version handshake -> inv -> getdata -> block/tx).
No VM, no GUI. Evidence level: MODEL (wire format anchored to net.h/main.cpp)."""

import asyncio
import sys

from p2p import (MSG_BLOCK, MSG_TX, MAGIC, Node, block_bytes, build_message,
                 dsha256, merkle_root, pow_ok, ser_tx)
from tx_sighash import Tx, TxIn, TxOut

def _run(coro):
    """Run on an explicit Selector loop (the Windows Proactor loop hangs on
    teardown here) and cancel any lingering server-handler tasks before closing."""
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

EASY = 0x207FFFFF


def _coinbase(height: int) -> Tx:
    t = Tx(1, [], [], 0)
    t.vin.append(TxIn(b"\x00" * 32, 0xFFFFFFFF, bytes([1, height & 0xFF]), 0xFFFFFFFF))
    t.vout.append(TxOut(50 * 100000000, b"\x51"))   # OP_1 scriptPubKey (dummy)
    return t


def _mine_block(prevhash: bytes):
    vtx = [_coinbase(1)]
    mr = merkle_root(vtx)
    for nonce in range(1 << 24):
        raw = block_bytes(1, prevhash, mr, 1231006506, EASY, nonce, vtx)
        if pow_ok(raw, EASY):
            return raw, dsha256(raw[:80])
    raise RuntimeError("no nonce")


def test_wire_framing_roundtrip():
    payload = b"\xde\xad\xbe\xef"
    msg = build_message("inv", payload)
    assert msg[:4] == MAGIC
    assert msg[4:16] == b"inv".ljust(12, b"\x00")
    assert int.from_bytes(msg[16:20], "little") == len(payload)
    assert msg[20:] == payload


def test_inv_roundtrips_across_compactsize_boundary():
    """inv_payload/parse_inv must round-trip counts >= 0xfd (the CompactSize prefix boundary).
    Regression: parse_inv read only payload[0] as the count, so any inv of >= 253 items misparsed
    (0xfd/0xfe/0xff were taken as a literal count) and initial-block-download silently stalled for a
    chain past ~252 blocks."""
    from p2p import inv_payload, parse_inv, MSG_BLOCK
    for n in (1, 200, 252, 253, 512, 1357):
        items = [(MSG_BLOCK, bytes([i & 0xFF, (i >> 8) & 0xFF]) + b"\x00" * 30) for i in range(n)]
        parsed = parse_inv(inv_payload(items))
        assert len(parsed) == n, f"count {n}: parsed {len(parsed)} items"
        assert parsed == items, f"count {n}: item mismatch"


def test_inv_and_getblocks_bound_a_huge_claimed_count():
    """A malformed inv/getblocks claiming a huge item count must NOT spin an unbounded loop over
    empty slices (a one-packet DoS that hangs the event loop). The parse is bounded to the real
    bytes — if this test returns at all, the bound holds (an unbounded loop would hang it)."""
    from p2p import parse_inv
    from chainsync import parse_getblocks
    # inv claims 2**64-1 CInv items but carries only 2 real (36 B) ones
    huge_inv = b"\xff" + b"\xff" * 8 + (b"\x01\x00\x00\x00" + b"\xab" * 32) * 2
    assert len(parse_inv(huge_inv)) == 2
    assert parse_inv(b"") == []                       # empty payload is benign, not a crash
    # getblocks claims a huge locator but carries only ~1 hash + hashStop
    huge_gb = b"\x00\x00\x00\x00" + b"\xff" + b"\xff" * 8 + b"\xcd" * 32 + b"\x00" * 32
    hashes, _stop = parse_getblocks(huge_gb)
    assert len(hashes) <= 2


async def _scenario():
    B = Node("B")
    server = await asyncio.start_server(B.handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        # A has a mined block and a transaction; it will announce them to B
        raw_block, block_h = _mine_block(b"\x00" * 32)
        tx = _coinbase(2); raw_tx = ser_tx(tx); tx_h = dsha256(raw_tx)
        A = Node("A"); A.add_block(raw_block, EASY); A.add_tx(raw_tx)

        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        task = asyncio.ensure_future(A.handle(reader, writer))
        await asyncio.wait_for(asyncio.gather(A.handshaked.wait(), B.handshaked.wait()), 3)

        await A.announce([(MSG_BLOCK, block_h), (MSG_TX, tx_h)])
        for _ in range(50):                       # let inv->getdata->block/tx settle
            await asyncio.sleep(0.02)
            if block_h in B.blocks and tx_h in B.txs:
                break
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        result = (B, block_h, tx_h, EASY)
    finally:
        server.close()   # do NOT await wait_closed(): it blocks on the active handler
    return result


def test_two_nodes_relay_block_and_tx():
    B, block_h, tx_h, bits = _run(_scenario())
    assert block_h in B.blocks, "B did not receive the block"
    assert tx_h in B.txs, "B did not receive the tx"
    # B independently re-checked the block's proof-of-work before accepting
    assert pow_ok(B.blocks[block_h], bits)
    assert any("accepted block" in l for l in B.log)
    assert any("accepted tx" in l for l in B.log)


if __name__ == "__main__":
    B, bh, th, _ = _run(_scenario())
    print("B inventory:", len(B.blocks), "blocks,", len(B.txs), "txs")
    print("B log:", B.log)
