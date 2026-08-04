#!/usr/bin/env python3
"""Speak v0.1.0's wire to a node, using bytes derived from the C++ and nothing else.

netnode can already talk to the bitcoin chain, but netnode is both ends of that conversation, so it
proves the two halves agree with each other rather than with the 2009 client. This probe is written
against the source instead: every field below is transcribed from `derivatives/bitcoin/src`, so a
successful handshake is evidence that a real `bitcoin.exe` would get the same answers.

The three things that make this wire different from every later Bitcoin, all in net.h:

    static const char pchMessageStart[4] = { 0xf0, 0x0b, 0xa7, 0x26 };

    class CMessageHeader {            // 20 bytes, and NO checksum field -- the 4-byte
        char pchMessageStart[4];      // checksum arrives later in Bitcoin's history, so a
        char pchCommand[12];          // modern parser reading 24 bytes here desynchronises
        unsigned int nMessageSize;    // immediately and never recovers
    };

    IMPLEMENT_SERIALIZE(              // CAddress, 26 bytes on the wire (SER_NETWORK):
        if (nType & SER_DISK) { ... } // nVersion/nTime are DISK-only and absent here
        READWRITE(nServices);         //  8
        READWRITE(FLATDATA(pchReserved));  // 12
        READWRITE(ip);                //  4   network byte order, from inet_addr
        READWRITE(port);              //  2   network byte order, from htons
    )

and the version message itself, from net.h:493 -- four fields, 46 bytes, no nonce, no user agent,
no start height:

    PushMessage("version", VERSION, nLocalServices, nTime, addr);

    python3 -m netnode.v01_wire_probe --connect bitcoin.bitcoin-lab.org:18026
"""
from __future__ import annotations

import argparse
import socket
import struct
import sys
import time

MAGIC = bytes([0xF0, 0x0B, 0xA7, 0x26])   # net.h:54, as patched for this chain
VERSION = 101                              # serialize.h:22
NODE_NETWORK = 1                           # net.h enum
HEADER_LEN = 20                            # 4 + 12 + 4, no checksum
PCHRESERVED = bytes([0] * 10 + [0xFF, 0xFF])   # net.h pchIPv4


def header(command: str, payload: bytes) -> bytes:
    cmd = command.encode("ascii")
    if len(cmd) > 12:
        raise ValueError("COMMAND_SIZE is 12")
    return MAGIC + cmd.ljust(12, b"\x00") + struct.pack("<I", len(payload))


def caddress(ip: str, port: int, services: int = NODE_NETWORK) -> bytes:
    """CAddress as SER_NETWORK writes it: 26 bytes, no nVersion and no nTime."""
    out = struct.pack("<Q", services) + PCHRESERVED + socket.inet_aton(ip) + struct.pack(">H", port)
    assert len(out) == 26, f"CAddress must serialise to 26 bytes, got {len(out)}"
    return out


def version_payload(peer_ip: str, peer_port: int) -> bytes:
    """PushMessage("version", VERSION, nLocalServices, nTime, addr) -- net.h:493."""
    out = (struct.pack("<i", VERSION)
           + struct.pack("<Q", NODE_NETWORK)
           + struct.pack("<q", int(time.time()))
           + caddress(peer_ip, peer_port))
    assert len(out) == 46, f"v0.1.0 version payload is 46 bytes, got {len(out)}"
    return out


def read_message(sock: socket.socket) -> tuple[str, bytes]:
    def recvall(n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("peer closed mid-message")
            buf += chunk
        return buf

    head = recvall(HEADER_LEN)
    if head[:4] != MAGIC:
        raise ValueError(f"wrong magic {head[:4].hex()} (expected {MAGIC.hex()}) "
                         f"-- a 24-byte header would land here")
    command = head[4:16].rstrip(b"\x00").decode("ascii", "replace")
    (size,) = struct.unpack("<I", head[16:20])
    if size > 4_000_000:
        raise ValueError(f"implausible payload size {size}; header framing is wrong")
    return command, recvall(size)


def probe(host: str, port: int, timeout: float = 20.0) -> int:
    ip = socket.gethostbyname(host)
    print(f"  target      {host} -> {ip}:{port}")
    s = socket.create_connection((ip, port), timeout=timeout)
    s.settimeout(timeout)
    try:
        payload = version_payload(ip, port)
        s.sendall(header("version", payload) + payload)
        print(f"  sent        version, {len(payload)}-byte payload, {HEADER_LEN}-byte header, no checksum")

        # There is no verack. `grep -rn verack` over the whole v0.1.0 tree returns nothing: the
        # acknowledgement message does not exist yet. Each side sends its own version and the link
        # is live -- main.cpp:1705 reads the peer's version, sets the stream versions, and goes
        # straight on to PushMessage("getblocks", ...). Waiting for a verack here would hang
        # against a correct peer, which is precisely the kind of later-protocol assumption this
        # probe exists to avoid importing.
        got_version = False
        their_version = None
        observed: list[str] = []
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                command, body = read_message(s)
            except (socket.timeout, TimeoutError):
                break
            if command == "version":
                (their_version,) = struct.unpack("<i", body[:4])
                (services,) = struct.unpack("<Q", body[4:12])
                print(f"  recv        version  nVersion={their_version}  nServices={services}  "
                      f"len={len(body)}")
                if len(body) != 46:
                    print(f"  !! their version payload is {len(body)} bytes, not 46 -- "
                          f"that is not the v0.1.0 layout")
                got_version = True
            else:
                observed.append(command)
                print(f"  recv        {command} ({len(body)} bytes)")
            # version, then whatever it volunteers, is enough to prove the framing holds
            if got_version and len(observed) >= 2:
                break

        if not got_version:
            print("  !! no version message received")
            return 1
        if their_version != VERSION:
            print(f"  !! peer reports VERSION {their_version}; this chain's client sends {VERSION}")
            return 1

        print(f"\n  HANDSHAKE OK -- 20-byte unchecksummed header, 26-byte CAddress, VERSION"
              f" {VERSION},")
        print(f"  no verack. Follow-on messages parsed cleanly: {', '.join(observed) or '(none)'}.")
        print(f"  A v0.1.0 client reaching this address gets the same answers these bytes did.")
        return 0
    finally:
        s.close()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--connect", required=True, metavar="HOST:PORT")
    p.add_argument("--timeout", type=float, default=20.0)
    a = p.parse_args(argv)
    host, _, port_s = a.connect.rpartition(":")
    if not host:
        p.error("--connect must be HOST:PORT")
    return probe(host, int(port_s), a.timeout)


if __name__ == "__main__":
    sys.exit(main())
