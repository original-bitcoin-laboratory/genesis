"""A node that loads its chain from blocks.dat must hold the same chain whether block bytes stay in
memory or are read back from the file (BlockIndex.spill, 18 Nov 2026).

The property that matters: for every indexed block, `idx.raw` returns exactly the bytes that were
stored -- the bytes whose hash is the block's hash -- and validation, serving and difficulty all see
the same chain as before. Includes the awkward store layouts: a child recorded before its parent
(orphan reconnected by a later record), a duplicate record, and a crash-truncated tail.
"""
import os
import pathlib
import struct
import sys

import pytest

_HERE = pathlib.Path(__file__).resolve().parent
for _p in (_HERE.parent / "model", _HERE.parent / "p2p", _HERE.parent / "nov08x", _HERE):
    sys.path.insert(0, str(_p))

from chainsync import BlockIndex, block_hash                        # noqa: E402
from chains import CHAINS, mine_next                                # noqa: E402
from livenode import Node                                           # noqa: E402
from store import BlockStore                                        # noqa: E402

CFG = CHAINS["jan09x"]


def _grow(node, count):
    """Mine `count` blocks onto `node` through its own accept path; return their raw bytes."""
    out = []
    for _ in range(count):
        nb = node.chain.by_hash[node.tip].nBits
        raw = mine_next(node.tip, node.height + 1, nb, node.chain.check_block,
                        CFG.rules.get_block_value(node.height))
        assert node.chain.process_block(raw)[0] == "accepted"
        node.store.append(raw)
        node.state.activate_best()
        out.append(raw)
    return out


def _records(path):
    data, i, out = pathlib.Path(path).read_bytes(), 0, []
    while i + 4 <= len(data):
        (n,) = struct.unpack_from("<I", data, i)
        out.append((i, data[i + 4:i + 4 + n]))
        i += 4 + n
    return out


def test_iter_records_and_read_at_match_the_file(tmp_path):
    s = BlockStore(tmp_path)
    blobs = [b"a" * 10, b"", b"b" * 300, b"c"]
    for b in blobs:
        s.append(b)
    got = list(s.iter_records())
    assert [r for _, r in got] == blobs == s.read_all()
    assert [o for o, _ in got] == [o for o, _ in _records(s.path)]
    for off, raw in got:
        assert s.read_at(off) == raw
    with pytest.raises(ValueError):
        s.read_at(pathlib.Path(s.path).stat().st_size)          # no record starts at the end
    s.close()


def test_read_at_sees_records_appended_after_its_first_read(tmp_path):
    s = BlockStore(tmp_path)
    s.append(b"first")
    assert s.read_at(0) == b"first"                             # caches the size: one record
    s.append(b"second-record")
    assert s.read_at(9) == b"second-record"                     # past the cached size -> re-stat
    with pytest.raises(ValueError):
        s.read_at(9 + 4 + 13)
    s.close()


def test_truncated_tail_is_ignored_as_before(tmp_path):
    s = BlockStore(tmp_path)
    s.append(b"x" * 50)
    s.close()
    with open(tmp_path / "blocks.dat", "ab") as f:
        f.write(struct.pack("<I", 100) + b"y" * 10)              # a crash mid-write
    s = BlockStore(tmp_path)
    assert s.read_all() == [b"x" * 50] and s.count() == 1
    s.close()


def test_reloaded_node_spills_every_block_and_reads_identical_bytes(tmp_path):
    n = Node(CFG, str(tmp_path / "A"))
    raws = _grow(n, 12)
    tip, height = n.tip, n.height
    n.store.close()
    m = Node(CFG, str(tmp_path / "A"))
    assert (m.tip, m.height) == (tip, height)
    assert all(idx.spilled for idx in m.chain.by_hash.values())
    for raw in raws:
        idx = m.chain.by_hash[block_hash(raw)]
        assert idx.raw == raw and block_hash(idx.raw) == idx.hash
    assert [b["hash"] for b in m.recent_blocks(5)] == [b["hash"] for b in n.recent_blocks(5)]
    m.store.close()


def test_child_recorded_before_parent_and_duplicates_are_spilled_correctly(tmp_path):
    src = Node(CFG, str(tmp_path / "SRC"))
    raws = _grow(src, 6)
    src.store.close()
    genesis = src.store.read_all()[0]
    d = tmp_path / "OUT"
    s = BlockStore(d)
    for r in [genesis, raws[0], raws[2], raws[1], raws[1], raws[3], raws[5], raws[4]]:
        s.append(r)                                             # 2 before 1, a duplicate, 5 before 4
    s.close()
    m = Node(CFG, str(d))
    assert m.height == 6 and m.tip == block_hash(raws[5])
    assert all(idx.spilled for idx in m.chain.by_hash.values())
    for raw in raws:
        assert m.chain.by_hash[block_hash(raw)].raw == raw
    m.store.close()


def test_an_index_that_never_spills_behaves_as_before():
    idx = BlockIndex(b"h" * 32, b"p" * 32, 7, b"bytes", 0x1D00FFFF)
    assert idx.raw == b"bytes" and not idx.spilled
    idx.spill(lambda off, h: b"from-file-%d-" % off + h[:1], 42)
    assert idx.spilled and idx.raw == b"from-file-42-h"           # the reader is given the hash
    idx.raw = b"again"                                          # assigning bytes un-spills
    assert idx.raw == b"again" and not idx.spilled


def test_the_load_log_counts_every_record(tmp_path):
    n = Node(CFG, str(tmp_path / "L"))
    _grow(n, 5)
    n.store.close()
    lines = []
    m = Node(CFG, str(tmp_path / "L"), log=lines.append)
    assert any(l.startswith("loaded 6 block(s); height=5") for l in lines)
    m.store.close()


def test_blocks_appended_after_load_and_spilled_blocks_read_side_by_side(tmp_path):
    n = Node(CFG, str(tmp_path / "R"))
    old = _grow(n, 4)
    n.store.close()
    m = Node(CFG, str(tmp_path / "R"))
    new = _grow(m, 3)                                           # appended while spilled reads are live
    for raw in old + new:
        idx = m.chain.by_hash[block_hash(raw)]
        assert idx.raw == raw
    assert all(m.chain.by_hash[block_hash(r)].spilled for r in old)
    assert not any(m.chain.by_hash[block_hash(r)].spilled for r in new)   # runtime blocks stay in memory
    m.store.close()
    k = Node(CFG, str(tmp_path / "R"))                          # and the next restart spills them too
    assert k.height == 7 and all(idx.spilled for idx in k.chain.by_hash.values())
    k.store.close()


class Stopped(Exception):
    pass


def _spilled_node_with_damage(tmp_path, monkeypatch, damage):
    """A reloaded node whose block file is then changed by `damage(path, offset_of_block_2)`;
    returns block 2's index. os._exit is replaced so a fail-stop raises Stopped(code)."""
    n = Node(CFG, str(tmp_path / "C"))
    raws = _grow(n, 3)
    n.store.close()
    m = Node(CFG, str(tmp_path / "C"))
    idx = m.chain.by_hash[block_hash(raws[1])]
    assert idx.raw == raws[1]                                   # reads fine before the damage
    damage(tmp_path / "C" / "blocks.dat", m._spill_off[idx._off], len(raws[1]))
    m.store.close()                                             # drop the open reader: re-read the file

    def fake_exit(code):
        raise Stopped(code)
    monkeypatch.setattr("livenode.os._exit", fake_exit)
    return idx


def _flip(path, at):
    data = bytearray(path.read_bytes())
    data[at] ^= 0xFF
    path.write_bytes(bytes(data))


@pytest.mark.parametrize("damage", [
    pytest.param(lambda p, off, n: _flip(p, off + 4 + 10), id="header-byte"),
    pytest.param(lambda p, off, n: _flip(p, off + 4 + n - 1), id="body-byte"),     # hash still matches
    pytest.param(lambda p, off, n: os.truncate(p, off + 2), id="file-truncated"),  # short length prefix
    pytest.param(lambda p, off, n: os.truncate(p, off + 4 + n - 1), id="record-cut"),
])
def test_a_block_file_changed_under_a_running_node_stops_it(tmp_path, monkeypatch, damage):
    idx = _spilled_node_with_damage(tmp_path, monkeypatch, damage)
    with pytest.raises(Stopped) as e:
        idx.raw
    assert e.value.args == (70,)


def test_a_reorg_across_spilled_blocks(tmp_path):
    n = Node(CFG, str(tmp_path / "O"))
    main = _grow(n, 4)                                          # heights 1..4
    n.store.close()
    m = Node(CFG, str(tmp_path / "O"))
    assert all(idx.spilled for idx in m.chain.by_hash.values())
    fork_base = m.chain.by_hash[block_hash(main[1])]            # height 2
    prev, fork = fork_base.hash, []
    for h in range(3, 7):                                       # a longer branch from height 2
        nb = m.chain.by_hash[prev].nBits
        raw = mine_next(prev, h, nb, m.chain.check_block, CFG.rules.get_block_value(h - 1))
        assert m.chain.process_block(raw)[0] in ("accepted", "side")
        m.store.append(raw)
        prev = block_hash(raw)
        fork.append(raw)
    m.state.activate_best()
    assert m.height == 6 and m.tip == block_hash(fork[-1])     # disconnected 4,3 (spilled), connected 3..6
    m.store.close()
    k = Node(CFG, str(tmp_path / "O"))
    assert k.height == 6 and k.tip == block_hash(fork[-1])
    k.store.close()


def test_a_torn_tail_is_set_aside_and_never_appended_after(tmp_path):
    n = Node(CFG, str(tmp_path / "T"))
    raws = _grow(n, 2)
    n.store.close()
    good = (tmp_path / "T" / "blocks.dat").stat().st_size
    with open(tmp_path / "T" / "blocks.dat", "ab") as f:
        f.write(struct.pack("<I", 0xFFFFFFF0) + b"z" * 12)        # a crash mid-write, absurd length
    m = Node(CFG, str(tmp_path / "T"))
    assert (tmp_path / "T" / "blocks.dat").stat().st_size == good
    side = list((tmp_path / "T").glob("blocks.dat.torn-*"))
    assert len(side) == 1 and side[0].stat().st_size == 16       # kept, not deleted
    more = _grow(m, 2)                                          # appended after the cut, not the junk
    assert m.store.torn_tail == side[0]
    m.store.close()
    k = Node(CFG, str(tmp_path / "T"))
    assert k.height == 4 and k.tip == block_hash(more[-1])
    k.store.close()


def test_an_absurd_length_is_rejected_without_allocating_it(tmp_path):
    p = tmp_path / "blocks.dat"
    p.write_bytes(struct.pack("<I", 3) + b"abc" + struct.pack("<I", 0xFFFFFFF0) + b"j" * 12)
    import tracemalloc
    s = BlockStore.__new__(BlockStore)                          # skip __init__: it would cut the tail
    s.path = p
    tracemalloc.start()
    recs = list(s.iter_records())
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert recs == [(0, b"abc")] and peak < 10 * 1024 * 1024
