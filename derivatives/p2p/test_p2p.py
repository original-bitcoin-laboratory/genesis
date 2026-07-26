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
