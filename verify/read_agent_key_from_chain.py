"""Read the agent's public key out of the chain itself, over the network, trusting no file of ours.

WHY THIS EXISTS
---------------
This project's strongest single claim is that the agent's public key is not ASSERTED anywhere --
it is INSIDE block 0's coinbase output. Anyone can read it off the chain and compare.

That was true and it was not one command. Our chain is not on a public block explorer, so
"read it off the chain yourself" quietly meant "run a full node sync first". This closes that:
it connects to the public seed, asks for block 0, parses the coinbase, and prints the key.

    python read_agent_key_from_chain.py

WHAT IT TRUSTS
--------------
The seed's ADDRESS, and nothing else. Every byte after that is verified locally:

  * the block it returns is hashed, and the hash must equal the hardcoded genesis
  * the merkle root is recomputed from the coinbase transaction and must match the header
  * the proof-of-work is checked against the difficulty-1 target

If a malicious seed returned a different block, all three checks fail. A seed cannot lie about
block 0 without breaking SHA-256.

THE POINT
---------
The key it prints should equal 04c0414cfdcc0098... -- the value published in IDENTITY-MANIFEST.txt.
If it does not, the manifest is wrong and the chain is right. THE CHAIN IS ALWAYS RIGHT.
"""
import hashlib
import socket
import struct
import sys
import time

HOST = "bitcoin.bitcoin-lab.org"
PORT = 18026
MAGIC = bytes.fromhex("f00ba726")
GENESIS = "00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a"
PUBLISHED = ("04c0414cfdcc009830708543b06e43a03570dc1ffa45ddf98657045e594a815eba7"
             "94ca0602e8527d7ba3197e53c0c2f226892212aa99b827e8e2fd95fcea2f834")


def dsha(b):
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


def msg(cmd, payload):
    return MAGIC + cmd.encode().ljust(12, b"\x00") + struct.pack("<I", len(payload)) + payload


def caddr():
    return (struct.pack("<Q", 1) + b"\x00" * 10 + b"\xff\xff"
            + socket.inet_aton("0.0.0.0") + struct.pack(">H", PORT))


def read(sock):
    hdr = b""
    while len(hdr) < 20:
        c = sock.recv(20 - len(hdr))
        if not c:
            return None, None
        hdr += c
    if hdr[:4] != MAGIC:
        return "BAD-MAGIC", hdr[:4]
    cmd = hdr[4:16].rstrip(b"\x00").decode(errors="replace")
    n = struct.unpack("<I", hdr[16:20])[0]
    body = b""
    while len(body) < n:
        c = sock.recv(min(65536, n - len(body)))
        if not c:
            break
        body += c
    return cmd, body


def main():
    print("connecting to %s:%d -- the ONLY thing trusted is this address" % (HOST, PORT))
    s = socket.create_connection((HOST, PORT), timeout=30)
    s.sendall(msg("version", struct.pack("<i", 209) + struct.pack("<Q", 1)
                  + struct.pack("<q", int(time.time())) + caddr()))

    block = None
    deadline = time.time() + 40
    asked = False
    while time.time() < deadline and block is None:
        cmd, body = read(s)
        if cmd is None:
            break
        if cmd == "version" and not asked:
            asked = True
            s.sendall(msg("verack", b""))
            inv = struct.pack("<B", 1) + struct.pack("<I", 2) + bytes.fromhex(GENESIS)[::-1]
            s.sendall(msg("getdata", inv))
        elif cmd == "block":
            block = body
    s.close()

    if not block:
        print("no block returned -- the seed may be down, or this script's wire format is wrong.")
        print("A silent answer is not proof the seed is broken. Check it another way before saying so.")
        return 1

    h = dsha(block[:80])[::-1].hex()
    print()
    print("block returned      %d B" % len(block))
    print("its hash            %s" % h)
    print("expected genesis    %s" % GENESIS)
    if h != GENESIS:
        print("MISMATCH -- this is not our genesis block. Stop here.")
        return 1
    print("                    MATCH")

    # parse the single coinbase transaction
    o = 80
    ntx = block[o]; o += 1
    tx_start = o
    o += 4                                   # version
    o += 1                                   # vin count
    o += 36                                  # prevout
    sl = block[o]; o += 1
    scriptsig = block[o:o + sl]; o += sl
    o += 4                                   # sequence
    o += 1                                   # vout count
    value = struct.unpack("<Q", block[o:o + 8])[0]; o += 8
    pl = block[o]; o += 1
    spk = block[o:o + pl]; o += pl
    o += 4
    txid = dsha(block[tx_start:o])

    merkle = block[36:68][::-1].hex()
    print("transactions        %d" % ntx)
    print("merkle root, header %s" % merkle)
    print("recomputed from tx  %s" % txid[::-1].hex())
    print("                    %s" % ("MATCH" if merkle == txid[::-1].hex() else "MISMATCH"))

    tgt = 0x00ffff * 256 ** (0x1d - 3)
    print("proof-of-work       %s"
          % ("valid, below the difficulty-1 target"
             if int.from_bytes(dsha(block[:80]), "little") < tgt else "INVALID"))

    print()
    print("coinbase headline   %r" % scriptsig[8:].decode("latin-1"))
    print("output value        %d sat = %d BTC" % (value, value // 100000000))
    key = spk[1:-1].hex() if spk and spk[-1] == 0xac else None
    print()
    print("THE AGENT'S PUBLIC KEY, READ OUT OF THE CHAIN:")
    print("  %s" % key)
    print()
    print("published in IDENTITY-MANIFEST.txt as:")
    print("  %s" % PUBLISHED)
    print()
    print("  %s" % ("IDENTICAL -- the manifest agrees with the chain"
                    if key == PUBLISHED else
                    "DIFFERENT -- the chain is right and the manifest is wrong"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
