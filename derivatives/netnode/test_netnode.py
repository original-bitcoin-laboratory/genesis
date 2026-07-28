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
from difficulty import (NET_RETARGET_INTERVAL, NET_TARGET_SPACING,  # noqa: E402
                        _retarget, check_difficulty, expected_bits, target_to_compact)
from fullnode import is_coinbase, parse_block, parse_tx, validate_block  # noqa: E402
from tx_sighash import Tx, TxIn, TxOut, serialize                   # noqa: E402

TESTMAGIC = b"TEST"
_EXPECTED_WINDOW = NET_RETARGET_INTERVAL * NET_TARGET_SPACING


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
        subsidy = node.cfg.rules.get_block_value(node.height)
        raw = mine_next(node.tip, node.height + 1, gen_nbits, node.chain.check_block, subsidy)
        assert node.chain.process_block(raw)[0] == "accepted"
        node.store.append(raw)
        node.state.activate_best()               # advance the validated chainstate (now authoritative)


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


# ---- Stage 2: difficulty retarget (deterministic) ---------------------------

def test_compact_target_roundtrips():
    rules = CHAINS["jan09x"].rules                        # compact encoding
    for nb in (0x207FFFFF, 0x1D00FFFF, 0x1C0FFFFF):
        t = rules.pow_target(nb)
        assert rules.pow_target(target_to_compact(t)) == t


def test_leading_zero_bits_retarget_nudges_and_floors():
    rn = CHAINS["nov08x"].rules                           # leading-zero-bits, floor = genesis
    assert _retarget(20, 1, _EXPECTED_WINDOW, rn, 20) == 21        # too fast -> +1 bit (harder)
    assert _retarget(21, 10 ** 9, _EXPECTED_WINDOW, rn, 20) == 20  # too slow -> -1 bit (easier)
    assert _retarget(20, 10 ** 9, _EXPECTED_WINDOW, rn, 20) == 20  # slow but already at the floor


def test_proportional_retarget_hardens_when_fast_and_floors_when_slow():
    rj = CHAINS["jan09x"].rules
    gen = 0x207FFFFF
    fast = _retarget(gen, 1, _EXPECTED_WINDOW, rj, gen)           # very fast
    assert rj.pow_target(fast) < rj.pow_target(gen)               # harder (smaller target)
    slow = _retarget(gen, 10 ** 9, _EXPECTED_WINDOW, rj, gen)     # very slow
    assert rj.pow_target(slow) == rj.pow_target(gen)              # floored at genesis (never easier)


def test_node_rejects_a_block_with_wrong_nbits(tmp_path):
    cfg = CHAINS["jan09x"]
    n = Node(cfg, str(tmp_path / "D"))
    good = mine_next(n.tip, 1, expected_bits(n.chain, n.tip, cfg.rules), n.chain.check_block)
    assert check_difficulty(n.chain, good, cfg.rules) is True
    bad = bytearray(good)
    bad[72:76] = (0x1D00FFFF).to_bytes(4, "little")              # forge an easier nBits
    assert check_difficulty(n.chain, bytes(bad), cfg.rules) is False
    n.store.close()


# ---- Stage 3: peer discovery (addr gossip meshes the network) ---------------

async def _discovery_scenario(da, db, dc):
    cfg = CHAINS["jan09x"]
    a = Node(cfg, da, listen=("127.0.0.1", 0), advertise_host="127.0.0.1")
    _seed(a, 3)
    await a.start()
    b = Node(cfg, db, listen=("127.0.0.1", 0), advertise_host="127.0.0.1")
    await b.start(connect=[("127.0.0.1", a.port)])
    # C is told ONLY about B — it must *discover* A through B's gossip.
    c = Node(cfg, dc, listen=("127.0.0.1", 0), advertise_host="127.0.0.1")
    await c.start(connect=[("127.0.0.1", b.port)])
    learned = synced = False
    for _ in range(400):
        learned = ("127.0.0.1", a.port) in c.known_addrs
        synced = c.height == a.height
        if learned and synced:
            break
        await asyncio.sleep(0.02)
    result = (learned, synced, c.height, a.height)
    for n in (a, b, c):
        await n.stop()
    return result


def test_discovery_meshes_three_nodes(tmp_path):
    learned, synced, hc, ha = _run(_discovery_scenario(
        str(tmp_path / "A"), str(tmp_path / "B"), str(tmp_path / "C")))
    assert learned                                          # C discovered A's address via B
    assert synced and hc == ha == 3                         # and synced A's chain through the mesh


# ---- Stage 4 hardening: resource bounds (DoS) -------------------------------

def test_known_addrs_are_bounded(tmp_path):
    n = Node(CHAINS["jan09x"], str(tmp_path / "K"), max_known_addrs=5)
    for i in range(50):
        n._learn_addr((f"10.0.0.{i % 256}", 1000 + i))
    assert len(n.known_addrs) <= 5                          # peer table can't be flooded unbounded
    n.store.close()


async def _inbound_cap_scenario(d):
    from p2p import version_payload
    cfg = CHAINS["jan09x"]
    n = Node(cfg, d, listen=("127.0.0.1", 0), max_inbound=1)
    await n.start()
    r1, w1 = await asyncio.open_connection("127.0.0.1", n.port)
    w1.write(frame("version", version_payload(), cfg.magic)); await w1.drain()
    try:
        first_ok = len(await asyncio.wait_for(r1.readexactly(24), 0.5)) == 24   # served a header
    except (asyncio.TimeoutError, asyncio.IncompleteReadError):
        first_ok = False
    r2, w2 = await asyncio.open_connection("127.0.0.1", n.port)   # over the cap
    try:
        second_eof = (await asyncio.wait_for(r2.read(1), 0.5)) == b""           # closed at once
    except asyncio.TimeoutError:
        second_eof = False
    w1.close(); w2.close()
    await n.stop()
    return first_ok, second_eof


def test_inbound_connection_cap(tmp_path):
    first_ok, second_eof = _run(_inbound_cap_scenario(str(tmp_path / "I")))
    assert first_ok and second_eof


async def _rate_limit_scenario(d):
    from p2p import inv_payload, version_payload
    from livenode import MSG_RATE_MAX
    cfg = CHAINS["jan09x"]
    n = Node(cfg, d, listen=("127.0.0.1", 0))
    await n.start()
    r, w = await asyncio.open_connection("127.0.0.1", n.port)
    w.write(frame("version", version_payload(), cfg.magic))
    w.write(frame("inv", inv_payload([]), cfg.magic) * (MSG_RATE_MAX + 30))   # flood, no misbehavior
    await w.drain()
    dropped = False
    for _ in range(20):
        try:
            if (await asyncio.wait_for(r.read(65536), 0.5)) == b"":
                dropped = True
                break
        except asyncio.TimeoutError:
            break
    w.close()
    await n.stop()
    return dropped


def test_rate_limit_drops_a_flooding_peer(tmp_path):
    assert _run(_rate_limit_scenario(str(tmp_path / "R"))) is True


async def _adversarial_survival_scenario(da, db):
    from p2p import version_payload
    cfg = CHAINS["jan09x"]
    a = Node(cfg, da, listen=("127.0.0.1", 0))
    _seed(a, 4)
    await a.start()
    # a hostile raw peer floods malformed frames — including the "huge claimed count" vectors that
    # once spun an unbounded parse loop and hung the whole event loop (a one-packet DoS).
    r, w = await asyncio.open_connection("127.0.0.1", a.port)
    w.write(frame("version", version_payload(), cfg.magic))
    for atk in (
        frame("inv", b"\xff" + b"\xff" * 8, cfg.magic),                        # inv claims 2**64 items
        frame("getblocks", b"\x00\x00\x00\x00\xff" + b"\xff" * 8, cfg.magic),  # getblocks claims 2**64 hashes
        frame("tx", b"\x01\x00\x00\x00\xff" + b"\x00" * 8, cfg.magic),         # tx claims 2**64 inputs
        frame("getblocks", b"\x05", cfg.magic),                               # truncated locator
        frame("block", b"\x00" * 80 + b"\xfd\xff\xff", cfg.magic),            # header + junk ntx
        frame("addr", b"\xff\x01\x02\x03", cfg.magic),                        # garbage addr
        frame("frobnicate", b"\x00" * 20, cfg.magic),                        # unknown command
    ):
        w.write(atk)
    await w.drain()
    await asyncio.sleep(0.1)
    # liveness proof: a legitimate node must still fully sync from the victim — impossible if the
    # victim's event loop had hung on the barrage.
    b = Node(cfg, db, listen=("127.0.0.1", 0))
    await b.start(connect=[("127.0.0.1", a.port)])
    synced = False
    for _ in range(250):
        if b.height == a.height and b.tip == a.tip:
            synced = True
            break
        await asyncio.sleep(0.02)
    w.close()
    result = (synced, a.height, b.height)
    await a.stop()
    await b.stop()
    return result


def test_node_survives_a_malformed_message_flood_and_still_serves(tmp_path):
    # regression: a huge claimed count in inv/getblocks/tx must not spin an unbounded loop (which hung
    # the event loop). The node shrugs off the barrage and a fresh peer still syncs the whole chain.
    synced, ha, hb = _run(_adversarial_survival_scenario(str(tmp_path / "A"), str(tmp_path / "B")))
    assert synced and hb == ha == 4


# ---- production node (part 1): full block validation ------------------------

def test_block_tx_parser_roundtrips_serialization():
    tx = Tx(1, [TxIn(b"\x11" * 32, 3, b"\xab\xcd\xef", 0xFFFFFFFF)],
            [TxOut(5_000_000_000, b"\x51"), TxOut(1, b"")], 7)
    raw = serialize(tx)
    parsed, off = parse_tx(raw, 0)
    assert off == len(raw)
    assert parsed.version == 1 and parsed.locktime == 7
    assert parsed.vin[0].prevhash == b"\x11" * 32 and parsed.vin[0].n == 3
    assert parsed.vin[0].script == b"\xab\xcd\xef"
    assert [(o.value, o.script) for o in parsed.vout] == [(5_000_000_000, b"\x51"), (1, b"")]


def test_validate_accepts_a_good_block(tmp_path):
    cfg = CHAINS["jan09x"]
    n = Node(cfg, str(tmp_path / "V"))
    subsidy = cfg.rules.get_block_value(n.height)
    nbits = expected_bits(n.chain, n.tip, cfg.rules)
    good = mine_next(n.tip, 1, nbits, n.chain.check_block, subsidy)
    ok, why = validate_block(good, n.chain, cfg.rules)
    assert ok, why
    assert is_coinbase(parse_block(good)[0])
    n.store.close()


def test_chainstate_rejects_overclaimed_coinbase(tmp_path):
    from chainsync import block_hash
    cfg = CHAINS["jan09x"]
    n = Node(cfg, str(tmp_path / "C"))
    subsidy = cfg.rules.get_block_value(n.height)
    nbits = expected_bits(n.chain, n.tip, cfg.rules)
    bad = mine_next(n.tip, n.height + 1, nbits, n.chain.check_block, subsidy * 2)  # 2x the subsidy
    assert validate_block(bad, n.chain, cfg.rules)[0]        # PoW/structure/merkle are all fine…
    assert n.chain.process_block(bad)[0] == "accepted"       # …the index accepts it (value is UTXO-level)
    n.state.activate_best()
    assert block_hash(bad) in n.state.invalid                # …but the validated chainstate rejects it
    assert n.state.tip == n.chain.genesis                    # and the authoritative chain didn't advance
    n.store.close()


def test_validate_rejects_merkle_tampering(tmp_path):
    cfg = CHAINS["jan09x"]
    n = Node(cfg, str(tmp_path / "M"))
    subsidy = cfg.rules.get_block_value(n.height)
    good = mine_next(n.tip, 1, expected_bits(n.chain, n.tip, cfg.rules), n.chain.check_block, subsidy)
    bad = bytearray(good); bad[36] ^= 1                                 # corrupt the header merkle root
    ok, why = validate_block(bytes(bad), n.chain, cfg.rules)
    assert not ok and "merkle" in why
    n.store.close()


def test_node_maintains_a_validated_utxo_chainstate(tmp_path):
    cfg = CHAINS["jan09x"]
    n = Node(cfg, str(tmp_path / "U"))
    _seed(n, 3)
    n.state.activate_best()                                             # validate the seeded chain
    assert n.state.height == n.height == 3
    assert n.state.tip == n.tip
    assert n.state.balance() > 0                                        # genesis + 3 subsidies in the UTXO
    n.store.close()


# ---- production node (part 4): difficulty floor + orphan-path validation ----

def test_min_difficulty_floor_raises_the_required_work_above_the_easy_genesis(tmp_path):
    cfg = CHAINS["jan09x"]
    n = Node(cfg, str(tmp_path / "MB"))
    gen_nbits = n.chain.by_hash[n.chain.genesis].nBits                  # 0x207FFFFF (easy)
    floor = 0x207FFFFE                                                  # a hair harder (smaller target)
    assert expected_bits(n.chain, n.tip, cfg.rules, None) == gen_nbits          # default: easy genesis
    assert expected_bits(n.chain, n.tip, cfg.rules, floor) == floor            # floored: requires real work
    easy = mine_next(n.tip, 1, gen_nbits, n.chain.check_block, cfg.rules.get_block_value(0))
    assert check_difficulty(n.chain, easy, cfg.rules, None) is True             # fine with no floor
    assert check_difficulty(n.chain, easy, cfg.rules, floor) is False           # too easy under the floor
    n.store.close()


def test_min_difficulty_floor_is_enforced_on_connect(tmp_path):
    from chainsync import block_hash
    cfg = CHAINS["jan09x"]
    n = Node(cfg, str(tmp_path / "MBC"), min_bits=0x207FFFFE)           # floor harder than the easy genesis
    gen_nbits = n.chain.by_hash[n.chain.genesis].nBits
    easy = mine_next(n.tip, 1, gen_nbits, n.chain.check_block, cfg.rules.get_block_value(0))
    assert n.chain.process_block(easy)[0] == "accepted"                # the PoW-only index accepts it
    n.state.activate_best()
    assert block_hash(easy) in n.state.invalid                         # the floor rejects it on connect
    assert n.state.height == 0                                         # validated chain stays at genesis
    n.store.close()


def test_orphan_path_difficulty_is_validated_on_connect(tmp_path):
    from chainsync import block_hash
    cfg = CHAINS["jan09x"]
    n = Node(cfg, str(tmp_path / "OD"))
    gen_nbits = n.chain.by_hash[n.chain.genesis].nBits
    b1 = mine_next(n.tip, 1, gen_nbits, n.chain.check_block, cfg.rules.get_block_value(0))
    forged = 0x207FFFFE                                                 # != expected genesis nBits, still mineable
    b2 = mine_next(block_hash(b1), 2, forged, n.chain.check_block, cfg.rules.get_block_value(1))
    # deliver b2 FIRST: its parent b1 is unknown, so the direct difficulty check is deferred…
    assert validate_block(b2, n.chain, cfg.rules, n.min_bits)[0]
    assert n.chain.process_block(b2)[0] == "orphan"
    # …b1 arrives and chainsync reconnects the orphan b2 into the PoW index *unchecked*…
    assert n.chain.process_block(b1)[0] == "accepted"
    assert block_hash(b2) in n.chain.by_hash
    # …but the authoritative connect gate catches b2's forged difficulty.
    n.state.activate_best()
    assert block_hash(b1) in n.state.active                            # correct-difficulty block connected
    assert block_hash(b2) in n.state.invalid                          # forged-difficulty orphan rejected
    assert n.state.tip == block_hash(b1) and n.state.height == 1
    n.store.close()


# ---- performance harness (measures where validation time goes) --------------

def test_bench_runs_and_reports_throughput():
    import bench
    m = bench.run(n_blocks=12, spends_per_block=2, reps=50)
    assert m["blocks"] == 12                                          # the whole chain validated
    assert m["txs"] >= 12 and m["sigs"] > 0                           # it carried real signed spends
    assert m["blocks_per_s"] > 0 and m["sigs_per_s"] > 0
    assert m["interp_us"] > 0 and m["fast_us"] > 0                    # both verify paths were measured
    assert m["speedup"] > 0                                           # accelerated vs faithful interpreter
