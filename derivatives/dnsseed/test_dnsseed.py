"""The DNS seed: the DNS codec round-trips a query + A-record response; the UDP server answers a
real query with the healthy IPs; and the crawler, over the real netnode wire, marks a live node
reachable (right magic), rejects a wrong-magic node, harvests its gossiped address, and reports it
healthy. Evidence: NEW-EXP (not money)."""

import asyncio
import pathlib
import struct
import sys

_HERE = pathlib.Path(__file__).resolve().parent
for _p in (_HERE.parent / "model", _HERE.parent / "p2p", _HERE.parent / "nov08x",
           _HERE.parent / "netnode", _HERE):
    sys.path.insert(0, str(_p))

from dnsmsg import TYPE_A, _question_bytes, build_response, parse_a_records, parse_query  # noqa: E402
from server import serve                                            # noqa: E402
from crawler import Crawler, probe                                  # noqa: E402


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


# ---- DNS codec --------------------------------------------------------------

def test_dns_codec_roundtrips_query_and_a_records():
    query = struct.pack(">HHHHHH", 0xABCD, 0x0100, 1, 0, 0, 0) + _question_bytes("seed.x.test", TYPE_A)
    txid, qname, qtype = parse_query(query)
    assert txid == 0xABCD and qname == "seed.x.test" and qtype == TYPE_A
    resp = build_response(txid, qname, ["10.0.0.1", "10.0.0.2"], ttl=42)
    assert parse_a_records(resp) == ["10.0.0.1", "10.0.0.2"]


# ---- UDP DNS server answers a real query ------------------------------------

async def _server_scenario():
    ips = ["1.2.3.4", "5.6.7.8", "9.9.9.9"]
    transport = await serve("127.0.0.1", 0, "seed.x.test", lambda: ips, max_answers=12)
    port = transport.get_extra_info("sockname")[1]
    loop = asyncio.get_event_loop()
    fut = loop.create_future()

    class _Client(asyncio.DatagramProtocol):
        def datagram_received(self, data, addr):
            if not fut.done():
                fut.set_result(data)

    ct, _ = await loop.create_datagram_endpoint(_Client, remote_addr=("127.0.0.1", port))
    ct.sendto(struct.pack(">HHHHHH", 0x1111, 0x0100, 1, 0, 0, 0) + _question_bytes("seed.x.test", TYPE_A))
    resp = await asyncio.wait_for(fut, 2.0)
    ct.close()
    transport.close()
    return set(parse_a_records(resp)), set(ips)


def test_dns_server_answers_with_healthy_ips(tmp_path):
    got, expected = _run(_server_scenario())
    assert got == expected                                          # every healthy IP served (order shuffled)


# ---- crawler over the real netnode wire -------------------------------------

async def _crawl_scenario(datadir):
    from chains import CHAINS
    from livenode import Node
    cfg = CHAINS["jan09x"]
    node = Node(cfg, datadir, listen=("127.0.0.1", 0), advertise_host="127.0.0.1")
    await node.start()
    port = node.port
    reachable, addrs = await probe("127.0.0.1", port, cfg.magic, timeout=2.0)
    wrong, _ = await probe("127.0.0.1", port, b"ZZZZ", timeout=1.5)   # wrong chain magic
    crawler = Crawler(cfg.magic, cfg.port, [("127.0.0.1", port)])
    healthy = await crawler.crawl_once()
    await node.stop()
    return reachable, addrs, wrong, ("127.0.0.1", port) in healthy


def test_crawler_finds_reachable_nodes_and_rejects_wrong_magic(tmp_path):
    reachable, addrs, wrong, healthy = _run(_crawl_scenario(str(tmp_path / "N")))
    assert reachable is True                                        # right magic → handshake succeeded
    assert any(h == "127.0.0.1" for h, _p in addrs)                # harvested its gossiped address
    assert wrong is False                                          # wrong magic → not counted reachable
    assert healthy is True                                         # crawl marked it healthy
