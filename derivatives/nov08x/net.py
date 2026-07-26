"""NOV08-X network — mint the genesis + identity, run two isolated nodes.

Completes R8 for the NOV08 branch: a *live* counterfactual network. It reuses the
lab's sync plumbing (`../p2p/chainsync` SyncNode: version/getblocks/inv/getdata/
block, orphan + height-based reorg) but with NOV08-X's own **network identity**
(NEW-EXP: magic / port / address version / genesis) and NOV08's **leading-zero-bits
proof-of-work** (`consensus.Rules`). Nothing here can be confused with, or connect
to, any historical or live chain. Evidence level: MODEL.
"""

from __future__ import annotations

import asyncio
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "p2p"))
sys.path.insert(0, str(_HERE.parent / "model"))
from chainsync import (Chain, SyncNode, ZERO, block_hash, dsha256,       # noqa: E402
                       merkle_root, nbits_of)
from tx_sighash import Tx, TxIn, TxOut, compact_size, serialize as ser_tx, _le  # noqa: E402
from consensus import Rules                                             # noqa: E402

# ---- NOV08-X network identity (all NEW-EXP — new decisions, never NOV08 semantics) ----
NOV08X_MAGIC = b"\xf0\x0b\xa7\x08"          # distinct from mainnet f9 be b4 d9
NOV08X_PORT = 18008                          # distinct from 8333
NOV08X_ADDRESS_VERSION = 0x35                # distinct base58 prefix
NOV08X_GENESIS_TIME = 1226793600             # 2008-11-16, a NOV08-era marker (experimental)
NOV08X_GENESIS_MESSAGE = b"NOV08-X lab chain: 15 Nov 2008 pre-release, not money"


def pow_check(rules: Rules):
    """A (raw, nBits) -> bool PoW check for chainsync.Chain, using NOV08 rules
    (leading-zero-bits + MINPROOFOFWORK)."""
    return lambda raw, nBits: rules.pow_ok(block_hash(raw), nBits)


def _coinbase(height: int, value: int, msg: bytes = b"", tag: int = 0) -> Tx:
    t = Tx(1, [], [], 0)
    script = (bytes([len(msg)]) + msg if msg else b"") + bytes([2, height & 0xFF, tag & 0xFF])
    t.vin.append(TxIn(ZERO, 0xFFFFFFFF, script, 0xFFFFFFFF))
    t.vout.append(TxOut(value, b"\x51"))       # OP_1 placeholder
    return t


def _mine(prev: bytes, height: int, best_height: int, rules: Rules,
          ntime: int, msg: bytes = b"", tag: int = 0) -> bytes:
    value = rules.get_block_value(best_height)             # NOV08 subsidy (100 coins at start)
    vtx = [_coinbase(height, value, msg, tag)]
    mr = merkle_root(vtx)
    body = compact_size(1) + ser_tx(vtx[0])
    prefix = _le(1, 4) + prev + mr + _le(ntime, 4) + _le(rules.min_pow, 4)   # nBits = MINPROOFOFWORK
    for nonce in range(1 << 28):
        header = prefix + _le(nonce, 4)
        if rules.pow_ok(dsha256(header), rules.min_pow):
            return header + body
    raise RuntimeError("no nonce found")


def mint_genesis(rules: Rules | None = None, ntime: int = NOV08X_GENESIS_TIME) -> bytes:
    """Mine the NOV08-X genesis under NOV08 leading-zero-bits PoW, with an
    experimental coinbase message (NEW-EXP; not the Times headline)."""
    rules = rules or Rules.load("nov08")
    return _mine(ZERO, 0, -1, rules, ntime, msg=NOV08X_GENESIS_MESSAGE)


def new_chain(rules: Rules | None = None) -> Chain:
    """A chainsync.Chain wired for NOV08-X PoW."""
    rules = rules or Rules.load("nov08")
    return Chain(pow_check=pow_check(rules))


def seed_chain(rules: Rules | None = None, nblocks: int = 3):
    """Genesis + nblocks mined NOV08-X blocks; returns (Chain, [raw...])."""
    rules = rules or Rules.load("nov08")
    c = new_chain(rules)
    g = mint_genesis(rules)
    c.add_genesis(g, rules.min_pow)
    raws = [g]
    prev = block_hash(g)
    for h in range(1, nblocks + 1):
        raw = _mine(prev, h, c.best_height, rules, NOV08X_GENESIS_TIME + h, tag=h)
        c.process_block(raw)
        raws.append(raw)
        prev = block_hash(raw)
    return c, raws


# ---- two isolated NOV08-X nodes synchronise the chain -------------------------

async def two_node_sync(nblocks: int = 2):
    rules = Rules.load("nov08")
    A_chain, _ = seed_chain(rules, nblocks)
    B_chain = new_chain(rules)
    B_chain.add_genesis(mint_genesis(rules), rules.min_pow)     # B starts at the same genesis
    assert B_chain.genesis == A_chain.genesis
    A = SyncNode("A", A_chain, magic=NOV08X_MAGIC)
    B = SyncNode("B", B_chain, magic=NOV08X_MAGIC)

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
    r = Rules.load("nov08")
    g = mint_genesis(r)
    print(f"NOV08-X identity: magic={NOV08X_MAGIC.hex()}  port={NOV08X_PORT}  "
          f"addr_version=0x{NOV08X_ADDRESS_VERSION:02x}")
    print(f"genesis hash = {block_hash(g)[::-1].hex()}")
    print(f"genesis coinbase reward = {r.fmt(r.get_block_value(-1))}")
    print(f"genesis message = {NOV08X_GENESIS_MESSAGE.decode()}")
    A, B = _run(two_node_sync(3))
    print(f"two isolated NOV08-X nodes synced: B reached tip height {B.best_height} "
          f"== A ({B.tip == A.tip}); PoW = leading-zero-bits, magic = {NOV08X_MAGIC.hex()}")
