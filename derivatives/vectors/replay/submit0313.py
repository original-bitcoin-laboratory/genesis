#!/usr/bin/env python3
"""Submit one block or transaction to a v0.3.x node over the 209 wire.

wire01.py speaks the January 2009 protocol: a 20-byte header, no checksum.
v0.3.13 sets its receive stream to version 209 before the handshake
(net.h:550) and verifies a checksum on every message (main.cpp:2030), so the
two are not interoperable. Hence a sibling rather than a flag on wire01.

This does the least that answers the question: handshake, send, wait. The
verdict is the node's own debug.log line, not anything read back here.
ONLY ever point this at an ISOLATED node. NOT money.
"""
import argparse, hashlib, socket, struct, sys, time


def dsha(b):
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


def frame(magic, cmd, payload):
    return (magic + cmd.encode().ljust(12, b"\x00")
            + struct.pack("<I", len(payload)) + dsha(payload)[:4] + payload)


def netaddr():
    return struct.pack("<Q", 1) + b"\x00" * 10 + b"\xff\xff" + b"\x00\x00\x00\x00" + struct.pack(">H", 0)


def version_payload(version):
    p = struct.pack("<i", version)
    p += struct.pack("<Q", 1)
    p += struct.pack("<q", int(time.time()))
    p += netaddr() + netaddr()
    p += struct.pack("<Q", 0)
    p += b"\x00"
    p += struct.pack("<i", 0)
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--node", required=True, help="HOST:PORT")
    ap.add_argument("--magic", default="f9beb4d9")
    ap.add_argument("--send", required=True, help="file of raw hex")
    ap.add_argument("--kind", choices=["block", "tx"], default="block")
    ap.add_argument("--version", type=int, default=31700)
    ap.add_argument("--wait", type=float, default=5.0)
    a = ap.parse_args()

    host, port = a.node.split(":")
    magic = bytes.fromhex(a.magic)
    raw = bytes.fromhex(open(a.send).read().strip())
    h = dsha(raw[:80]) if a.kind == "block" else dsha(raw)
    print(f"sending {a.kind} {len(raw):,} B  hash {h[::-1].hex()}")

    s = socket.create_connection((host, int(port)), timeout=20)
    s.sendall(frame(magic, "version", version_payload(a.version)))

    buf = b""
    deadline = time.time() + 15
    seen = set()
    while time.time() < deadline and not {"version", "verack"} <= seen:
        try:
            d = s.recv(65536)
        except socket.timeout:
            break
        if not d:
            break
        buf += d
        while len(buf) >= 24:
            if buf[:4] != magic:
                buf = buf[1:]
                continue
            n = struct.unpack("<I", buf[16:20])[0]
            if len(buf) < 24 + n:
                break
            cmd = buf[4:16].rstrip(b"\x00").decode("latin-1")
            seen.add(cmd)
            print("  <-", cmd, n, "bytes")
            if cmd == "version":
                s.sendall(frame(magic, "verack", b""))
            buf = buf[24 + n:]

    if "version" not in seen:
        print("!! no version from peer - handshake failed")
        return 2

    s.sendall(frame(magic, a.kind, raw))
    print(f"  -> {a.kind} sent; read the node's debug.log for its verdict")
    time.sleep(a.wait)
    s.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())