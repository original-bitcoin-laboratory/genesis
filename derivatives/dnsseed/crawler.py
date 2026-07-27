"""Crawl the X-chain network to find reachable nodes for the DNS seed. NOT money.

A DNS seed is only useful if it hands out addresses that actually **work**. This connects to
candidate nodes over the real netnode wire (magic + checksum framing), does the `version`
handshake — which proves the node is reachable *and* on the right chain — and harvests the peers
it gossips (`addr`), expanding the known set. Nodes that answer are marked **healthy**; the DNS
server serves only those.

Decoupled from a specific chain: it takes the chain's `magic` and default port, so it is unit-
testable against any node. Evidence: NEW-EXP.
"""

from __future__ import annotations

import asyncio
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "netnode"))
sys.path.insert(0, str(_HERE.parent / "p2p"))

from p2p import version_payload                              # noqa: E402
from wire import WireError, frame, read_message              # noqa: E402


def _decode_addrs(payload: bytes):
    """The netnode `addr` format: [count:2][ len:1 host port:2 ]* (little-endian)."""
    n = int.from_bytes(payload[:2], "little")
    i, out = 2, []
    for _ in range(min(n, 1000)):
        if i + 1 > len(payload):
            break
        ln = payload[i]; i += 1
        host = payload[i:i + ln].decode("ascii", "replace"); i += ln
        port = int.from_bytes(payload[i:i + 2], "little"); i += 2
        if host and 0 < port < 65536:
            out.append((host, port))
    return out


async def probe(host: str, port: int, magic: bytes, timeout: float = 5.0):
    """Connect + handshake. Returns (reachable, gossiped_addrs). `reachable` is True only if the
    node answers with a valid framed `version` on the expected magic (wrong chain → not reachable)."""
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout)
    except (OSError, asyncio.TimeoutError):
        return False, []
    reachable, addrs = False, []
    try:
        writer.write(frame("version", version_payload(), magic))
        await writer.drain()
        for _ in range(4):                                   # read a few messages: version, then addr
            command, payload = await asyncio.wait_for(read_message(reader, magic), timeout)
            if command == "version":
                reachable = True
            elif command == "addr":
                addrs += _decode_addrs(payload)
            if reachable and addrs:
                break
    except (WireError, OSError, asyncio.TimeoutError, ConnectionError):
        pass
    finally:
        try:
            writer.close()
        except OSError:
            pass
    return reachable, addrs


class Crawler:
    def __init__(self, magic: bytes, default_port: int, seeds, *, max_known: int = 5000,
                 timeout: float = 5.0):
        self.magic = magic
        self.default_port = default_port
        self.timeout = timeout
        self.max_known = max_known
        self.known: set[tuple[str, int]] = {(h, int(p)) for h, p in seeds}
        self.healthy: set[tuple[str, int]] = set()

    async def crawl_once(self, max_probe: int = 256):
        """Probe a batch of known nodes; refresh the healthy set; expand `known` via gossip."""
        batch = list(self.known)[:max_probe]
        results = await asyncio.gather(*(probe(h, p, self.magic, self.timeout) for h, p in batch))
        healthy = set()
        for (addr, (reachable, addrs)) in zip(batch, results):
            if reachable:
                healthy.add(addr)
            for h, p in addrs:
                if len(self.known) < self.max_known:
                    self.known.add((h, int(p) or self.default_port))
        self.healthy = healthy
        return healthy

    def healthy_ips(self):
        """Distinct IPv4 hosts of healthy nodes (what an A-record seed hands out)."""
        seen, ips = set(), []
        for host, _port in sorted(self.healthy):
            if host not in seen and _looks_ipv4(host):
                seen.add(host)
                ips.append(host)
        return ips


def _looks_ipv4(host: str) -> bool:
    parts = host.split(".")
    return len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)
