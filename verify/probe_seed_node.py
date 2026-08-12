"""Ask the public seed node, over the wire, how much of this chain it actually has.

WHY
---
The DigitalOcean seed at bitcoin.bitcoin-lab.org:18026 is the one piece of this project that is
OPERATED rather than merely published. After each mining round the honest question is not "is the
droplet up" but "is it serving the blocks we just captured".

A TCP connect cannot answer that, and neither can a version handshake: v0.1's `version` message
carries nVersion, nServices, nTime and addrMe -- and NO block height. nBestHeight was added to the
protocol later. So the height is obtained the way a 2009 client obtains it: ask for an inventory.

  1. version handshake (v0.1 header is 20 B, magic || 12-byte command || length -- NO checksum,
     which arrived with protocol 209)
  2. getblocks with a locator containing only the genesis hash
  3. count the block hashes in the `inv` that comes back

WHAT A FAILURE MEANS, stated up front so it cannot be misread
-------------------------------------------------------------
If the handshake succeeds and the inv does not, that is evidence about THIS SCRIPT'S wire format,
not about the seed. Report it that way. A silent or malformed answer is never proof a service is
broken -- the same discipline as an HTTP 200 from a bot wall, or a crashing tool read as a negative
result.
"""
import hashlib
import socket
import struct
import sys
import time

HOST = "bitcoin.bitcoin-lab.org"
PORT = 18026
MAGIC = bytes.fromhex("f00ba726")
GENESIS = bytes.fromhex(
    "00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a")[::-1]  # internal order


def msg(command, payload):
    return MAGIC + command.encode().ljust(12, b"\x00") + struct.pack("<I", len(payload)) + payload


def caddress(services=1, ip="0.0.0.0", port=PORT):
    return (struct.pack("<Q", services) + b"\x00" * 10 + b"\xff\xff"
            + socket.inet_aton(ip) + struct.pack(">H", port))


def version_payload():
    return (struct.pack("<i", 209)          # nVersion
            + struct.pack("<Q", 1)          # nServices = NODE_NETWORK
            + struct.pack("<q", int(time.time()))
            + caddress())                   # addrMe


def varint(n):
    if n < 0xfd:
        return struct.pack("<B", n)
    if n <= 0xffff:
        return b"\xfd" + struct.pack("<H", n)
    return b"\xfe" + struct.pack("<I", n)


def read_message(sock):
    hdr = b""
    while len(hdr) < 20:
        chunk = sock.recv(20 - len(hdr))
        if not chunk:
            return None, None
        hdr += chunk
    if hdr[:4] != MAGIC:
        return "BAD-MAGIC", hdr[:4]
    cmd = hdr[4:16].rstrip(b"\x00").decode(errors="replace")
    size = struct.unpack("<I", hdr[16:20])[0]
    body = b""
    while len(body) < size:
        chunk = sock.recv(min(65536, size - len(body)))
        if not chunk:
            break
        body += chunk
    return cmd, body


def local_chain():
    """Every block hash in the newest chain capture we hold, heights 0..n."""
    import glob
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    ws = os.path.normpath(os.path.join(here, "..", "..", "..", ".."))
    cands = glob.glob(os.path.join(ws, "OBL-BACKUP", "04-evidence",
                                   "bitcoin-chain-evidence", "**", "blk0001.dat"), recursive=True)
    if not cands:
        return None, None
    path = max(cands, key=os.path.getsize)
    data = open(path, "rb").read()
    magic, off, hs = data[:4], 0, []
    while off + 8 <= len(data):
        if data[off:off + 4] != magic:
            break
        ln = struct.unpack("<I", data[off + 4:off + 8])[0]
        hs.append(hashlib.sha256(hashlib.sha256(data[off + 8:off + 8 + 80]).digest())
                  .digest()[::-1].hex())
        off += 8 + ln
    return os.path.relpath(path, ws), hs


def compare(advertised):
    """Is the seed on OUR chain, and how far ahead or behind?"""
    rel, ours = local_chain()
    if not ours:
        print("  (no local capture found to compare against)")
        return
    print()
    print("  COMPARED AGAINST OUR NEWEST CAPTURE")
    print("    %s — %d blocks, heights 0-%d" % (rel, len(ours), len(ours) - 1))
    shared = ours[1:]                       # the seed advertises from height 1
    common = min(len(shared), len(advertised))
    mismatch = [i + 1 for i in range(common) if shared[i] != advertised[i]]
    if mismatch:
        print("    !! FORK: heights %s differ. The seed is NOT on our chain." % mismatch[:5])
        return
    print("    heights 1-%d identical      SAME CHAIN, no fork" % common)
    if len(advertised) > len(shared):
        extra = len(advertised) - len(shared)
        print("    seed is AHEAD by %d block(s) — heights %d-%d we have not captured yet"
              % (extra, len(shared) + 1, len(advertised)))
        for i in range(len(shared), len(advertised)):
            print("      height %-3d %s" % (i + 1, advertised[i]))
        print("    => the VM kept mining after the snapshot. Expected; capture again to catch up.")
    elif len(advertised) < len(shared):
        print("    seed is BEHIND by %d block(s) — it has not received our newest blocks"
              % (len(shared) - len(advertised)))
    else:
        print("    seed is EXACTLY level with our capture")


def main():
    print("seed          %s:%d" % (HOST, PORT))
    try:
        ip = socket.gethostbyname(HOST)
        print("resolves to   %s" % ip)
    except Exception as exc:
        print("DNS FAILED    %s" % exc)
        return 1

    s = socket.create_connection((HOST, PORT), timeout=25)
    print("tcp           connected")
    s.sendall(msg("version", version_payload()))

    got_version = False
    deadline = time.time() + 30
    while time.time() < deadline:
        cmd, body = read_message(s)
        if cmd is None:
            break
        if cmd == "BAD-MAGIC":
            print("WRONG NETWORK  peer magic %s, expected %s" % (body.hex(), MAGIC.hex()))
            return 1
        print("  <- %-10s %d B" % (cmd, len(body)))
        if cmd == "version":
            v, svc, t = struct.unpack("<iQq", body[:20])
            print("     peer protocol version %d, services %d, clock %s UTC"
                  % (v, svc, time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(t))))
            got_version = True
            s.sendall(msg("verack", b""))
            # ask for the inventory from genesis forward
            loc = struct.pack("<i", 209) + varint(1) + GENESIS + b"\x00" * 32
            s.sendall(msg("getblocks", loc))
        if cmd == "inv":
            n = body[0] if body[0] < 0xfd else struct.unpack("<H", body[1:3])[0]
            off = 1 if body[0] < 0xfd else 3
            blocks = [body[off + i * 36 + 4: off + i * 36 + 36][::-1].hex()
                      for i in range(n) if struct.unpack("<I", body[off + i * 36: off + i * 36 + 4])[0] == 2]
            print()
            print("  INVENTORY: %d block hashes advertised (heights 1-%d)"
                  % (len(blocks), len(blocks)))
            s.close()
            compare(blocks)
            return 0
    s.close()
    if got_version:
        print()
        print("  handshake OK, no inv returned.")
        print("  ⚠ That is evidence about THIS SCRIPT'S getblocks encoding, NOT about the seed:")
        print("    the seed answered on the correct magic with a valid version message, so it is")
        print("    live and on this network. Height simply was not obtained.")
        return 0
    print("  no version reply within 30 s")
    return 1


if __name__ == "__main__":
    sys.exit(main())
