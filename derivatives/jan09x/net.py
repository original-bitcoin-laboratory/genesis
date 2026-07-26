"""JAN09-X network — the released v0.1.0 chain, full vocabulary, as an isolated net.

The symmetric twin of NOV08-X. JAN09-X runs January's *released* constitution
(`COIN=1e8`, 50-coin subsidy, 210k halving, 10-min spacing, **compact** proof-of-work,
`<=` coinbase rule — exactly what the lab's `p2p/chainsync` + `node` already execute)
with the **full opcode vocabulary re-opened** (`../jan09x/script_full.py` re-enables
`OP_NOTEQUAL`, the one thing v0.1 disabled). Its own network identity (NEW-EXP) keeps
it isolated from mainnet. Two nodes synchronise the chain. Evidence level: MODEL.
"""

from __future__ import annotations

import asyncio
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "p2p"))
sys.path.insert(0, str(_HERE.parent / "model"))
sys.path.insert(0, str(_HERE.parent / "nov08x"))
from chainsync import (EASY, Chain, SyncNode, ZERO, block_hash, dsha256,   # noqa: E402
                       merkle_root, pow_ok)
from tx_sighash import Tx, TxIn, TxOut, compact_size, serialize as ser_tx, _le  # noqa: E402
from consensus import Rules                                               # noqa: E402

# ---- JAN09-X network identity (NEW-EXP) --------------------------------------
JAN09X_MAGIC = b"\xf0\x0b\xa7\x09"          # distinct from mainnet f9 be b4 d9 (and NOV08-X f0 0b a7 08)
JAN09X_PORT = 18009
JAN09X_ADDRESS_VERSION = 0x36
JAN09X_GENESIS_TIME = 1231469665            # 2009-01-09, the v0.1.0 era (experimental marker)
JAN09X_GENESIS_MESSAGE = b"JAN09-X lab chain: v0.1.0 released rules, full vocabulary, not money"

_RULES = Rules.load("jan09")


def _coinbase(height: int, value: int, msg: bytes = b"", tag: int = 0) -> Tx:
    t = Tx(1, [], [], 0)
    script = (bytes([len(msg)]) + msg if msg else b"") + bytes([2, height & 0xFF, tag & 0xFF])
    t.vin.append(TxIn(ZERO, 0xFFFFFFFF, script, 0xFFFFFFFF))
    t.vout.append(TxOut(value, b"\x51"))
    return t


def _mine(prev: bytes, height: int, ntime: int, msg: bytes = b"", tag: int = 0) -> bytes:
    value = _RULES.get_block_value(-1)                  # 50 coins at COIN=1e8 (released subsidy)
    vtx = [_coinbase(height, value, msg, tag)]
    mr = merkle_root(vtx)
    body = compact_size(1) + ser_tx(vtx[0])
    prefix = _le(1, 4) + prev + mr + _le(ntime, 4) + _le(EASY, 4)   # compact nBits (regtest-easy)
    for nonce in range(1 << 28):
        header = prefix + _le(nonce, 4)
        if pow_ok(header, EASY):                         # pow_ok reads raw[:80] = the header
            return header + body
    raise RuntimeError("no nonce found")


def mint_genesis(ntime: int = JAN09X_GENESIS_TIME) -> bytes:
    return _mine(ZERO, 0, ntime, msg=JAN09X_GENESIS_MESSAGE)


def new_chain() -> Chain:
    return Chain()                                       # default = JAN09 compact PoW


def seed_chain(nblocks: int = 3):
    c = new_chain()
    g = mint_genesis()
    c.add_genesis(g, EASY)
    raws = [g]
    prev = block_hash(g)
    for h in range(1, nblocks + 1):
        raw = _mine(prev, h, JAN09X_GENESIS_TIME + h, tag=h)
        c.process_block(raw)
        raws.append(raw)
        prev = block_hash(raw)
    return c, raws


async def two_node_sync(nblocks: int = 3):
    A_chain, _ = seed_chain(nblocks)
    B_chain = new_chain()
    B_chain.add_genesis(mint_genesis(), EASY)
    assert B_chain.genesis == A_chain.genesis
    A = SyncNode("A", A_chain, magic=JAN09X_MAGIC)
    B = SyncNode("B", B_chain, magic=JAN09X_MAGIC)
    server = await asyncio.start_server(lambda r, w: A.handle(r, w), "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        task = asyncio.ensure_future(B.handle(reader, writer, initiate=True))
        await asyncio.wait_for(asyncio.gather(A.handshaked.wait(), B.handshaked.wait()), 3)
        for _ in range(200):
            await asyncio.sleep(0.02)
            if B_chain.tip == A_chain.tip:
                break
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        return A_chain, B_chain
    finally:
        server.close()


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


if __name__ == "__main__":
    g = mint_genesis()
    print(f"JAN09-X identity: magic={JAN09X_MAGIC.hex()}  port={JAN09X_PORT}  "
          f"addr_version=0x{JAN09X_ADDRESS_VERSION:02x}")
    print(f"genesis hash = {block_hash(g)[::-1].hex()}")
    print(f"genesis coinbase reward = {_RULES.fmt(_RULES.get_block_value(-1))}")
    print(f"genesis message = {JAN09X_GENESIS_MESSAGE.decode()}")
    A, B = _run(two_node_sync(3))
    print(f"two isolated JAN09-X nodes synced: B tip height {B.best_height} == A "
          f"({B.tip == A.tip}); PoW = compact, magic = {JAN09X_MAGIC.hex()}")
