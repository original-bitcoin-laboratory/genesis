"""Chain synchronisation between two headless v0.1 nodes (no VM).

Unit checks (Chain: locator / orphan reconnection / height-based reorg) plus two
end-to-end wire scenarios over localhost TCP:
  * linear sync   — a fresh node catches up to a peer's multi-block chain via
                    version -> getblocks -> inv -> getdata -> block;
  * orphan-driven — the peer announces only its tip; the fresh node orphans it,
                    fires getblocks(GetOrphanRoot), fills the gap and reconnects.
Evidence level: MODEL (protocol anchored to main.cpp / main.h)."""

import asyncio
import sys

from chainsync import (Chain, EASY, SyncNode, ZERO, block_hash, build_chain,
                       mine, prev_hash)


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


# ---- unit: block-locator shape ------------------------------------------------

def test_locator_starts_at_tip_ends_at_genesis():
    c, raws = build_chain(15)
    loc = c.get_locator()
    assert loc[0] == c.tip                          # newest first
    assert loc[-1] == c.genesis                     # always ends with genesis
    assert c.locate(loc).hash == c.tip              # a peer at the same tip locates the tip


# ---- unit: orphan reconnection (out-of-order delivery) ------------------------

def test_orphans_reconnect_when_parent_arrives():
    _, raws = build_chain(4)                         # genesis + b1..b4
    gen, b1, b2, b3, b4 = raws
    c = Chain(); c.add_genesis(gen, EASY)
    # deliver the children before their parents
    assert c.process_block(b4)[0] == "orphan"
    assert c.process_block(b3)[0] == "orphan"
    assert c.process_block(b2)[0] == "orphan"
    assert c.best_height == 0                        # nothing connected yet
    # the missing parent unlocks the whole queue
    assert c.process_block(b1)[0] == "accepted"
    assert c.best_height == 4
    assert c.tip == block_hash(b4)
    assert not c.orphans and not c.orphans_by_prev


# ---- unit: height-based reorg to a longer competing branch --------------------

def test_reorg_switches_to_the_longer_branch():
    c, raws = build_chain(3)                         # main: g,b1,b2,b3  (height 3)
    gen, b1, b2, b3 = raws
    assert c.best_height == 3 and c.tip == block_hash(b3)
    # competing branch off b1: c2,c3,c4  (tag=9 makes the coinbases distinct)
    h1 = block_hash(b1)
    c2 = mine(h1, 2, tag=9)
    c3 = mine(block_hash(c2), 3, tag=9)
    c4 = mine(block_hash(c3), 4, tag=9)
    assert c.process_block(c2)[0] == "accepted"     # shorter side branch, no reorg
    assert c.tip == block_hash(b3)
    assert c.process_block(c3)[0] == "accepted"     # equal height, still no reorg
    assert c.tip == block_hash(b3)
    assert c.process_block(c4)[0] == "accepted"     # longer -> reorg
    assert c.tip == block_hash(c4) and c.best_height == 4
    # new branch is main; the old tip blocks are off-chain
    for r in (b1, c2, c3, c4):
        assert c.by_hash[block_hash(r)].in_main
    for r in (b2, b3):
        assert not c.by_hash[block_hash(r)].in_main
    # the main-chain walk follows the new branch
    assert c.main_chain() == [c.genesis, h1, block_hash(c2), block_hash(c3), block_hash(c4)]


# ---- wire: linear multi-block sync -------------------------------------------

async def _linear(nblocks):
    A_chain, raws = build_chain(nblocks)
    B_chain = Chain(); B_chain.add_genesis(raws[0], EASY)
    A = SyncNode("A", A_chain); B = SyncNode("B", B_chain)

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
        task.cancel(); await asyncio.gather(task, return_exceptions=True)
        return A_chain, B_chain
    finally:
        server.close()


def test_wire_linear_sync():
    A, B = _run(_linear(6))
    assert B.tip == A.tip, "B did not reach A's tip"
    assert B.best_height == 6
    assert B.main_chain() == A.main_chain()         # identical block order, from genesis up
    assert not B.orphans


# ---- wire: orphan-driven catch-up (peer announces only its tip) ---------------

async def _orphan_driven(nblocks):
    A_chain, raws = build_chain(nblocks)
    B_chain = Chain(); B_chain.add_genesis(raws[0], EASY)
    A = SyncNode("A", A_chain); B = SyncNode("B", B_chain)

    server = await asyncio.start_server(lambda r, w: A.handle(r, w), "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        task = asyncio.ensure_future(B.handle(reader, writer, initiate=False))
        await asyncio.wait_for(asyncio.gather(A.handshaked.wait(), B.handshaked.wait()), 3)
        await A.announce([(2, A_chain.tip)])         # 2 == MSG_BLOCK: broadcast only the tip
        for _ in range(200):
            await asyncio.sleep(0.02)
            if B_chain.tip == A_chain.tip:
                break
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        task.cancel(); await asyncio.gather(task, return_exceptions=True)
        return A_chain, B_chain, B
    finally:
        server.close()


def test_wire_orphan_driven_sync():
    A, B, Bnode = _run(_orphan_driven(5))
    assert B.tip == A.tip, "B did not catch up from a tip-only announcement"
    assert B.best_height == 5
    assert not B.orphans, "orphans should have been reconnected"
    assert any(l.startswith("orphan") for l in Bnode.log), "expected an orphan then catch-up"


if __name__ == "__main__":
    A, B = _run(_linear(6))
    print("linear:", B.best_height, "blocks, tip==A:", B.tip == A.tip)
    A, B, Bnode = _run(_orphan_driven(5))
    print("orphan-driven:", B.best_height, "blocks, tip==A:", B.tip == A.tip)
    print("B log:", Bnode.log)
