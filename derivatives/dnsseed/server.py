"""An authoritative UDP DNS server that answers A queries for the seed zone. NOT money.

Answers only for one configured zone and only `A` (IPv4) — with a fresh batch of healthy node IPs
supplied by a provider callback (the `Crawler`). Everything else gets an empty/error response. This
is the classic Bitcoin bootstrap: a new node resolves `seed.<zone>` and dials the returned peers.
Bound wherever the operator points it (port 53 needs privileges; a high port + a delegating NS
record also works). Evidence: NEW-EXP.
"""

from __future__ import annotations

import asyncio
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from dnsmsg import TYPE_A, build_error, build_response, parse_query   # noqa: E402


class DnsSeedProtocol(asyncio.DatagramProtocol):
    def __init__(self, zone: str, ips_provider, *, ttl: int = 60, max_answers: int = 12, log=None):
        self.zone = zone.lower().rstrip(".")
        self.ips_provider = ips_provider                    # () -> list[str] of healthy IPv4s
        self.ttl = ttl
        self.max_answers = max_answers
        self._log = log or (lambda m: None)
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        try:
            txid, qname, qtype = parse_query(data)
        except ValueError:
            return                                          # malformed — ignore (don't amplify)
        name = qname.lower().rstrip(".")
        if name != self.zone:
            self.transport.sendto(build_error(txid, qname, qtype), addr)   # not our zone
            return
        if qtype != TYPE_A:
            self.transport.sendto(build_error(txid, qname, qtype, 0x8404), addr)   # A only
            return
        ips = list(self.ips_provider())
        random.shuffle(ips)                                 # spread load across the healthy set
        self.transport.sendto(build_response(txid, qname, ips[:self.max_answers], self.ttl), addr)


async def serve(host: str, port: int, zone: str, ips_provider, *, ttl: int = 60,
                max_answers: int = 12, log=None):
    """Start the UDP DNS responder; returns the transport (close it to stop). `port` may be 0 to
    let the OS pick (the chosen port is on `transport.get_extra_info('sockname')`)."""
    loop = asyncio.get_event_loop()
    transport, _protocol = await loop.create_datagram_endpoint(
        lambda: DnsSeedProtocol(zone, ips_provider, ttl=ttl, max_answers=max_answers, log=log),
        local_addr=(host, port))
    return transport
