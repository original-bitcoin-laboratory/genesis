"""The hardened node, Stage 1: the wire rejects tampering/oversize, the store survives a
crash-truncated tail, two nodes sync a chain over REAL TCP, and a node reloads its chain from
disk on restart. Evidence: MODEL / NEW-EXP (not money, not production-secure)."""

import asyncio
import pathlib
import sys

import pytest

_HERE = pathlib.Path(__file__).resolve().parent
# insert netnode's own dir LAST so it lands at sys.path[0] and wins name clashes
# (e.g. netnode/node.py vs nov08x/node.py)
for _p in (_HERE.parent / "model", _HERE.parent / "p2p", _HERE.parent / "nov08x", _HERE):
    sys.path.insert(0, str(_p))

from wire import MAX_MESSAGE_SIZE, WireError, frame, read_message   # noqa: E402
from store import BlockStore                                        # noqa: E402
from livenode import Node                                           # noqa: E402
from chains import CHAINS, mine_next                                # noqa: E402

TESTMAGIC = b"TEST"


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


async def _fed(data: bytes) -> asyncio.StreamReader:
    r = asyncio.StreamReader()
    r.feed_data(data)
    r.feed_eof()
    return r


# ---- hardened wire ----------------------------------------------------------

def test_wire_roundtrip():
    async def go():
        return await read_message(await _fed(frame("ping", b"hello", TESTMAGIC)), TESTMAGIC)
    assert _run(go()) == ("ping", b"hello")


def test_wire_rejects_bad_checksum():
    async def go():
        m = bytearray(frame("ping", b"hello", TESTMAGIC)); m[-1] ^= 0xFF
        await read_message(await _fed(bytes(m)), TESTMAGIC)
    with pytest.raises(WireError):
        _run(go())


def test_wire_rejects_bad_magic():
    async def go():
        await read_message(await _fed(frame("ping", b"x", b"OTHR")), TESTMAGIC)
    with pytest.raises(WireError):
        _run(go())


def test_wire_rejects_oversize():
    async def go():
        hdr = TESTMAGIC + b"ping".ljust(12, b"\x00") + \
            (MAX_MESSAGE_SIZE + 1).to_bytes(4, "little") + b"\x00" * 4
        await read_message(await _fed(hdr), TESTMAGIC)
    with pytest.raises(WireError):
        _run(go())


# ---- crash-safe store -------------------------------------------------------

def test_store_roundtrip(tmp_path):
    s = BlockStore(tmp_path); s.append(b"aaa"); s.append(b"bbbb"); s.close()
    s2 = BlockStore(tmp_path)
    assert s2.read_all() == [b"aaa", b"bbbb"]
    s2.close()


def test_store_ignores_crash_truncated_tail(tmp_path):
    s = BlockStore(tmp_path); s.append(b"aaa"); s.close()
    with open(tmp_path / "blocks.dat", "ab") as f:
        f.write((10).to_bytes(4, "little") + b"xyz")     # header claims 10 bytes, only 3 written
    s2 = BlockStore(tmp_path)
    assert s2.read_all() == [b"aaa"]                      # truncated record ignored
    s2.close()


# ---- two nodes sync over REAL TCP -------------------------------------------

def _seed(node, n):
    gen_nbits = node.chain.by_hash[node.chain.genesis].nBits
    for _ in range(n):
        raw = mine_next(node.tip, node.height + 1, gen_nbits, node.chain.check_block)
        assert node.chain.process_block(raw)[0] == "accepted"
        node.store.append(raw)


async def _sync_scenario(dir_a, dir_b):
    cfg = CHAINS["jan09x"]                                # instant (regtest-easy) mining
    a = Node(cfg, dir_a, listen=("127.0.0.1", 0))
    _seed(a, 5)
    await a.start()
    port_a = a._server.sockets[0].getsockname()[1]
    b = Node(cfg, dir_b, listen=("127.0.0.1", 0))
    await b.start(connect=[("127.0.0.1", port_a)])
    for _ in range(250):                                 # up to ~5s
        if b.height == a.height and b.tip == a.tip:
            break
        await asyncio.sleep(0.02)
    result = (a.height, b.height, a.tip, b.tip)
    await a.stop()
    await b.stop()
    return result


def test_two_nodes_sync_over_tcp(tmp_path):
    ha, hb, ta, tb = _run(_sync_scenario(str(tmp_path / "A"), str(tmp_path / "B")))
    assert ha == 5 and hb == 5                            # B caught up to A over real sockets
    assert ta == tb                                       # same tip


# ---- restart recovery -------------------------------------------------------

def test_node_reloads_chain_from_disk(tmp_path):
    cfg = CHAINS["jan09x"]
    d = str(tmp_path / "P")
    n1 = Node(cfg, d)
    _seed(n1, 4)
    tip1, h1 = n1.tip, n1.height
    n1.store.close()
    n2 = Node(cfg, d)                                     # fresh node, same datadir
    assert n2.height == h1 == 4
    assert n2.tip == tip1
    n2.store.close()
