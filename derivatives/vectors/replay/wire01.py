"""A client for the v0.1 wire protocol, as the January 2009 bitcoin.exe speaks it.

Framing (net.h CMessageHeader): [magic 4][command 12, NUL-padded][size 4 LE][payload] — no checksum.
Handshake (main.cpp:1705): each side sends `version` on connect; there is no verack. A node ignores
everything until it has our version. Payload layouts follow serialize.h / net.h / main.h exactly.

Two verdict channels the replay uses, both read from the node itself:
  * a loose transaction the node ACCEPTED is served back from its relay pool by `getdata` (main.cpp:1795,
    mapRelay), and announced to other peers by `inv`; a rejected one is not;
  * a block the node placed in its index is served back by `getdata`; whether it became the BEST chain is
    read with `getblocks` from a locator at the previous tip (main.cpp:1832 walks pnext, main chain only).
"""
from __future__ import annotations

import collections
import socket
import struct
import time

MAGIC_2009 = b"\xf9\xbe\xb4\xd9"
VERSION = 101
NODE_NETWORK = 1
MSG_TX, MSG_BLOCK = 1, 2


def le(n: int, length: int) -> bytes:
    return n.to_bytes(length, "little")


def varint(n: int) -> bytes:
    if n < 0xFD:
        return bytes([n])
    if n <= 0xFFFF:
        return b"\xfd" + le(n, 2)
    return b"\xfe" + le(n, 4)


def read_varint(b: bytes, i: int) -> tuple[int, int]:
    b0 = b[i]
    if b0 < 0xFD:
        return b0, i + 1
    if b0 == 0xFD:
        return int.from_bytes(b[i + 1:i + 3], "little"), i + 3
    if b0 == 0xFE:
        return int.from_bytes(b[i + 1:i + 5], "little"), i + 5
    return int.from_bytes(b[i + 1:i + 9], "little"), i + 9


def enc_addr(services: int = NODE_NETWORK, ip: bytes = b"\x7f\x00\x00\x01", port: int = 8333) -> bytes:
    return le(services, 8) + b"\x00" * 10 + b"\xff\xff" + ip + port.to_bytes(2, "big")


def version_payload(now: int) -> bytes:
    return le(VERSION, 4) + le(NODE_NETWORK, 8) + le(now, 8) + enc_addr()


def inv_payload(items: list[tuple[int, bytes]]) -> bytes:
    return varint(len(items)) + b"".join(le(t, 4) + h for t, h in items)


def parse_inv(payload: bytes) -> list[tuple[int, bytes]]:
    n, i = read_varint(payload, 0)
    out = []
    for _ in range(n):
        if i + 36 > len(payload):
            break
        out.append((int.from_bytes(payload[i:i + 4], "little"), payload[i + 4:i + 36]))
        i += 36
    return out


def getblocks_payload(locator: list[bytes], stop: bytes = b"\x00" * 32) -> bytes:
    """CBlockLocator: nVersion (int32) + vector<uint256>; then hashStop."""
    return le(VERSION, 4) + varint(len(locator)) + b"".join(locator) + stop


def frame(command: str, payload: bytes, magic: bytes = MAGIC_2009) -> bytes:
    return magic + command.encode().ljust(12, b"\x00") + le(len(payload), 4) + payload


class Peer:
    """One connection to a 2009 node. Reads are buffered; `expect` pulls the first message matching a
    predicate and queues the rest, so unsolicited traffic (addr, inv, getblocks) never desynchronises us."""

    def __init__(self, host: str, port: int = 8333, magic: bytes = MAGIC_2009, timeout: float = 15.0):
        self.host, self.port, self.magic = host, port, magic
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.settimeout(timeout)
        self.buf = b""
        self.queue: collections.deque = collections.deque()
        self.their_version: dict | None = None
        self.seen_inv: list[tuple[int, bytes]] = []
        self.send("version", version_payload(int(time.time())))
        v = self.expect(lambda c, p: c == "version", timeout=timeout)
        if v is None:
            raise ConnectionError("no version from peer")
        self.their_version = {"version": int.from_bytes(v[0:4], "little"),
                              "services": int.from_bytes(v[4:12], "little"),
                              "time": int.from_bytes(v[12:20], "little")}
        self._time_offset = self.their_version["time"] - int(time.time())

    def node_now(self) -> int:
        """The node's clock, as it reported it in `version`, advanced by our elapsed time."""
        return int(time.time()) + self._time_offset

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass

    # ---- raw i/o -----------------------------------------------------------------------------
    def send(self, command: str, payload: bytes) -> None:
        self.sock.sendall(frame(command, payload, self.magic))

    def _read_one(self, timeout: float):
        deadline = time.time() + timeout
        while True:
            if len(self.buf) >= 20:
                if self.buf[:4] != self.magic:
                    raise ValueError("bad magic from peer")
                size = int.from_bytes(self.buf[16:20], "little")
                if len(self.buf) >= 20 + size:
                    cmd = self.buf[4:16].rstrip(b"\x00").decode("latin-1")
                    payload = self.buf[20:20 + size]
                    self.buf = self.buf[20 + size:]
                    if cmd == "inv":
                        self.seen_inv.extend(parse_inv(payload))
                    return cmd, payload
            remaining = deadline - time.time()
            if remaining <= 0:
                return None
            self.sock.settimeout(remaining)
            try:
                chunk = self.sock.recv(1 << 16)
            except socket.timeout:
                return None
            if not chunk:
                raise ConnectionError("peer closed")
            self.buf += chunk

    def expect(self, pred, timeout: float = 5.0):
        """Return the payload of the first queued-or-incoming message satisfying pred(cmd, payload)."""
        for i, (c, p) in enumerate(self.queue):
            if pred(c, p):
                del self.queue[i]
                return p
        deadline = time.time() + timeout
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                return None
            m = self._read_one(remaining)
            if m is None:
                return None
            if pred(*m):
                return m[1]
            self.queue.append(m)

    def drain(self, quiet: float = 0.5) -> None:
        """Read whatever arrives until the line is quiet for `quiet` seconds; everything is queued."""
        while True:
            m = self._read_one(quiet)
            if m is None:
                return
            self.queue.append(m)

    # ---- the three questions the replay asks -------------------------------------------------
    def getdata(self, typ: int, h: bytes, timeout: float = 4.0):
        """Ask for one object by hash. Returns its payload if the node serves it, else None."""
        self.send("getdata", inv_payload([(typ, h)]))
        want = "block" if typ == MSG_BLOCK else "tx"
        return self.expect(lambda c, p: c == want and _matches(want, p, h), timeout=timeout)

    def probe(self, typ: int, h: bytes, sentinel_block: bytes, timeout: float = 10.0) -> bool:
        """Is object (typ, h) served? One round trip: a single getdata asking for it AND for a block the
        node certainly has (the sentinel). main.cpp:1795 answers the items in order, so if the sentinel
        block arrives and the object did not precede it, the node does not serve it."""
        self.send("getdata", inv_payload([(typ, h), (MSG_BLOCK, sentinel_block)]))
        want = "block" if typ == MSG_BLOCK else "tx"
        deadline = time.time() + timeout
        got = False
        while time.time() < deadline:
            m = self._read_one(max(0.05, deadline - time.time()))
            if m is None:
                break
            c, p = m
            if c == want and _matches(want, p, h):
                got = True
            elif c == "block" and _matches("block", p, sentinel_block):
                return got
            else:
                self.queue.append(m)
        raise TimeoutError("sentinel block was not served")

    def main_chain_after(self, locator_hash: bytes, timeout: float = 3.0, stop: bytes = b"\x00" * 32) -> list[bytes]:
        """getblocks from a locator holding one main-chain hash: the node answers with `inv`s of the
        main-chain blocks after it (sent on its next SendMessages tick). Returns them in order."""
        self.send("getblocks", getblocks_payload([locator_hash], stop))
        hashes: list[bytes] = []
        deadline = time.time() + timeout
        while time.time() < deadline:
            p = self.expect(lambda c, _p: c == "inv", timeout=max(0.05, deadline - time.time()))
            if p is None:
                break
            for t, h in parse_inv(p):
                if t == MSG_BLOCK and h not in hashes:
                    hashes.append(h)
            deadline = min(deadline, time.time() + 0.8)     # once it starts, it finishes quickly
        return hashes

    def sync_chain(self, genesis_hash: bytes, on_block=None, batch: int = 50) -> list[bytes]:
        """Fetch the node's whole main chain after genesis, in order, as raw blocks."""
        raws: list[bytes] = []
        cursor = genesis_hash
        while True:
            hashes = self.main_chain_after(cursor, timeout=5.0)
            if not hashes:
                return raws
            for i in range(0, len(hashes), batch):
                chunk = hashes[i:i + batch]
                self.send("getdata", inv_payload([(MSG_BLOCK, h) for h in chunk]))
                for h in chunk:
                    p = self.expect(lambda c, q, hh=h: c == "block" and _matches("block", q, hh), timeout=20.0)
                    if p is None:
                        raise ConnectionError(f"block {h[::-1].hex()[:16]} not served during sync")
                    raws.append(p)
                    if on_block:
                        on_block(p)
            cursor = hashes[-1]


def dsha256(b: bytes) -> bytes:
    import hashlib
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


def _matches(kind: str, payload: bytes, h: bytes) -> bool:
    if kind == "block":
        return dsha256(payload[:80]) == h
    return dsha256(payload) == h


__all__ = ["Peer", "MSG_TX", "MSG_BLOCK", "MAGIC_2009", "frame", "inv_payload", "parse_inv", "getblocks_payload",
           "version_payload", "read_varint", "varint", "le", "dsha256"]
_ = struct  # keep the import for tools that grep it
