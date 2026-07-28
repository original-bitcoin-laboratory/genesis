"""The persisted, diversity-aware peer database (a compact addrman): a per-/16 cap stops one subnet
from filling the table, 'tried' peers are preferred, sampling spreads across subnets, and the table
survives a restart. Evidence: NEW-EXP (discovery hygiene, not money). NOT money."""

import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from peerdb import PeerDB, group_of                                  # noqa: E402


def test_group_of_is_the_ipv4_16():
    assert group_of("143.110.255.205") == "143.110"
    assert group_of("178.62.236.102") == "178.62"
    assert group_of("localhost") == "localhost"                     # non-dotted -> the host itself


def test_one_subnet_cannot_fill_the_table():
    db = PeerDB(max_addrs=1000, max_per_group=8)
    added = sum(db.add((f"10.0.{i // 256}.{i % 256}", 18009)) for i in range(200))
    assert added == 8 and len(db) == 8                              # every 10.0.x.x is one /16 -> capped
    assert db.add(("11.0.0.1", 18009)) is True                     # a different /16 is independent


def test_total_cap_bounds_the_table():
    db = PeerDB(max_addrs=5, max_per_group=100)
    for i in range(50):
        db.add((f"{i + 1}.0.0.1", 18009))                          # distinct groups
    assert len(db) <= 5


def test_tried_is_preferred_in_sampling():
    db = PeerDB(rng=random.Random(1))
    for i in range(10):
        db.add((f"{i + 1}.0.0.1", 18009))
    db.mark_good(("5.0.0.1", 18009))
    assert db.sample(1) == [("5.0.0.1", 18009)]                     # the tried peer wins a size-1 sample


def test_sample_per_group_cap_spreads_across_subnets():
    db = PeerDB(max_per_group=100, rng=random.Random(2))
    for i in range(10):
        db.add((f"20.0.0.{i}", 18009))                             # all one /16
    db.add(("21.0.0.1", 18009))                                    # a second /16
    picked = db.sample(10, per_group=1)
    assert len(picked) == 2 and {group_of(h) for h, _ in picked} == {"20.0", "21.0"}


def test_save_and_load_roundtrip(tmp_path):
    db = PeerDB()
    db.add(("143.110.255.205", 18009))
    db.mark_good(("178.62.236.102", 18009))
    db.save(tmp_path / "peers.json")
    db2 = PeerDB()
    db2.load(tmp_path / "peers.json")
    assert ("178.62.236.102", 18009) in db2.tried                  # tier preserved
    assert ("143.110.255.205", 18009) in db2.new
    assert db2.addrs() == db.addrs()


def test_a_corrupt_peer_file_is_non_fatal(tmp_path):
    p = tmp_path / "peers.json"
    p.write_text("{ this is not json", encoding="utf-8")
    db = PeerDB()
    db.load(p)                                                     # must not raise
    assert len(db) == 0
