#!/usr/bin/env python3
"""R3 verifier: from one or two nodes' blk0001.dat, parse the v0.1 block file, verify the historical
genesis (block 0), each block's difficulty-1 proof-of-work, and that block 1 builds on the genesis. If two
files are given it also confirms they are byte-identical (both nodes agree on the mined+relayed chain).

Reads the files named on the command line (it does NOT embed any block bytes):
    python verify_r3.py nodeA/blk0001.dat [nodeB/blk0001.dat]

NOT money.
"""
import hashlib, struct, sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")           # render '…' on Windows cp1252 consoles too

GENESIS = "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f"
TARGET1 = 0x00000000FFFF0000000000000000000000000000000000000000000000000000


def dsha(b): return hashlib.sha256(hashlib.sha256(b).digest()).digest()
def rh(b):   return b[::-1].hex()                       # display (big-endian) hash


def parse(raw: bytes):
    """v0.1 block file: repeated [magic f9beb4d9][size u32][block]."""
    blocks, off = [], 0
    while off + 8 <= len(raw):
        magic, size = struct.unpack_from("<I I", raw, off); off += 8
        blk = raw[off:off+size]; off += size
        if len(blk) >= 80:
            blocks.append((magic, blk))
    return blocks


def report(label, raw):
    blocks = parse(raw)
    print(f"\n== {label} ({len(raw)} bytes, {len(blocks)} block(s)) ==")
    all_pow = True
    for i, (magic, blk) in enumerate(blocks):
        hdr = blk[:80]
        ver, = struct.unpack_from("<I", hdr, 0)
        t, bits, nonce = struct.unpack_from("<I I I", hdr, 68)
        h = dsha(hdr)
        pow_ok = int.from_bytes(h, "little") < TARGET1
        all_pow = all_pow and pow_ok
        if i <= 1 or i >= len(blocks) - 1 or not pow_ok:
            print(f"  block {i}: {rh(h)[:24]}…  prev={rh(hdr[4:36])[:16]}…  "
                  f"bits={bits:08x} nonce={nonce}  magic_ok={magic == 0xd9b4bef9}  PoW_ok={pow_ok}")
        if b"Chancellor" in blk:
            s = blk.find(b"The Times")
            print(f"           coinbase: {blk[s:s+64].decode('latin-1')}")
    g = rh(dsha(blocks[0][1][:80])) if blocks else None
    print(f"  block 0 IS the historical genesis {GENESIS[:20]}… : {g == GENESIS}")
    print(f"  every block has valid difficulty-1 PoW : {all_pow}")
    if len(blocks) > 1:
        print(f"  block 1 builds on the genesis : {rh(blocks[1][1][4:36]) == g}")
    return raw, g


def main(argv):
    files = [a for a in argv if not a.startswith("--")]
    if not files:
        print(__doc__); return 1
    results = []
    for f in files:
        raw = open(f, "rb").read()
        results.append((f, *report(f, raw)))
    if len(results) == 2:
        (fa, ra, ga), (fb, rb, gb) = results
        print("\n== two-node agreement ==")
        print(f"  node A blk == node B blk (byte-identical): {ra == rb}")
        print(f"  both re-derive the historical genesis: {ga == GENESIS == gb}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
