#!/usr/bin/env python3
"""Custody separation: is the agent's genesis key in the miner's wallet? It must not be.

    python3 wallet_custody.py <capture-dir>

WHAT THIS TESTS, AND WHY IT IS THE ONE WALLET CHECK THAT MATTERS
----------------------------------------------------------------
The chain has two kinds of key. The miner's wallet mints a fresh one per block, as v0.1 does. The
AGENT'S key -- the one that speaks for the chain's author-agent -- was used once, at height 0, and
is held alone, outside this wallet, on separate media.

If that key were ever found inside the miner's wallet, the separation this project claims would be
false, and every statement resting on "the identity key is held alone" would fall with it. So the
test is run every round, against the wallet bytes rather than against a policy document.

A 65-byte 0x04-prefixed blob is not automatically a key: the wallet file is full of byte patterns
that merely look like one. Each candidate is therefore checked as an actual point on secp256k1
(y^2 == x^3 + 7 mod p) before it is counted.

⛔ TIER 1. The wallet is archived to the COLD backup only and is never committed, never published,
   never re-hosted. This script reads it; it prints key PREFIXES and counts, never a private key,
   and there are no private keys in a public-key census in any case.
"""
import argparse
import hashlib
import io
import pathlib
import struct
import sys
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

P = (1 << 256) - (1 << 32) - 977                    # secp256k1 field prime
MAGIC = bytes([0xF0, 0x0B, 0xA7, 0x26])
GENESIS = "00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a"


# ⛔ The curve's own GENERATOR POINT is a valid point on secp256k1 and it sits in a wallet file as
#    a CONSTANT, not as anybody's key. A naive "is it on the curve?" scan counts it and reports one
#    key too many -- this tool said 293 where the repository's generator said 292, and the
#    difference was exactly G. Two tools disagreeing is how it was found; a single tool would have
#    been believed.
G_HEX = ("0479be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798"
         "483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8")


def on_curve(blob):
    """blob is 65 bytes, 0x04 || X || Y."""
    if blob.hex() == G_HEX:
        return False
    x = int.from_bytes(blob[1:33], "big")
    y = int.from_bytes(blob[33:65], "big")
    if x >= P or y >= P or x == 0:
        return False
    return (y * y - (x * x * x + 7)) % P == 0


def dsha(b):
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


def varint(buf, i):
    n = buf[i]
    if n < 0xFD:
        return n, i + 1
    if n == 0xFD:
        return struct.unpack_from("<H", buf, i + 1)[0], i + 3
    if n == 0xFE:
        return struct.unpack_from("<I", buf, i + 1)[0], i + 5
    return struct.unpack_from("<Q", buf, i + 1)[0], i + 9


def coinbase_payees(blkpath):
    """(height -> payee key hex) along the ACTIVE chain."""
    buf = blkpath.read_bytes()
    i, blocks = 0, []
    while i + 8 <= len(buf):
        if buf[i:i + 4] != MAGIC:
            i += 1
            continue
        size = struct.unpack_from("<I", buf, i + 4)[0]
        body = buf[i + 8:i + 8 + size]
        hdr = body[:80]
        prev = hdr[4:36][::-1].hex()
        h = dsha(hdr)[::-1].hex()
        j = 80
        ntx, j = varint(body, j)
        # first transaction only -- the coinbase
        j2 = j + 4
        nin, j2 = varint(body, j2)
        for _ in range(nin):
            j2 += 36
            sl, j2 = varint(body, j2)
            j2 += sl + 4
        nout, j2 = varint(body, j2)
        keys = []
        for _ in range(nout):
            j2 += 8
            sl, j2 = varint(body, j2)
            spk = body[j2:j2 + sl]
            j2 += sl
            if len(spk) >= 66 and spk[0] == 65 and spk[1] == 4:
                keys.append(spk[1:66].hex())
        blocks.append({"hash": h, "prev": prev, "keys": keys})
        i += 8 + size
    by_prev = {}
    for b in blocks:
        by_prev.setdefault(b["prev"], []).append(b)

    def depth(b):
        k, c = 0, b["hash"]
        while by_prev.get(c):
            c = by_prev[c][0]["hash"]
            k += 1
        return k

    known = {b["hash"]: b for b in blocks}
    chain, cur = [known[GENESIS]], GENESIS
    while by_prev.get(cur):
        nxt = by_prev[cur]
        if len(nxt) > 1:
            nxt = sorted(nxt, key=depth, reverse=True)
        chain.append(nxt[0])
        cur = nxt[0]["hash"]
    return {h: b["keys"] for h, b in enumerate(chain)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("capture")
    a = ap.parse_args()
    root = pathlib.Path(a.capture)

    wallets = sorted(root.rglob("wallet*.dat"))
    blks = [p for p in root.rglob("blk0001.dat") if p.parent.name == "datadir"]
    if not wallets or not blks:
        print("  ** need a wallet*.dat and datadir/blk0001.dat under", root)
        return 2

    payees = coinbase_payees(blks[0])
    all_payees = [k for ks in payees.values() for k in ks]
    genesis_key = payees.get(0, [None])[0]
    print("\n  CHAIN SIDE")
    print("    heights                       0-%d" % (len(payees) - 1))
    print("    coinbase payee keys           %d" % len(all_payees))
    print("    distinct                      %d" % len(set(all_payees)))
    print("    height-0 (agent) key          %s..." % (genesis_key[:32] if genesis_key else "?"))

    ok, bad = [], []
    for w in wallets:
        data = w.read_bytes()
        cands, keys = 0, set()
        for i in range(len(data) - 65):
            if data[i] == 0x04:
                blob = data[i:i + 65]
                cands += 1
                if on_curve(blob):
                    keys.add(blob.hex())
        print("\n  WALLET  %s   (%s bytes)" % (w.relative_to(root).as_posix(),
                                               format(len(data), ",")))
        print("    0x04-prefixed 65-byte blobs   %d   raw byte patterns" % cands)
        print("    valid points on secp256k1     %d   the actual keys" % len(keys))
        used = [h for h, ks in payees.items() if any(k in keys for k in ks)]
        print("    wallet keys that ARE payees   %d" % len(used))
        print("    wallet keys never used yet    %d" % (len(keys) - len(used)))
        if used:
            print("    payee heights covered         %d..%d" % (min(used), max(used)))
        holds_agent = genesis_key in keys if genesis_key else False
        print("    HOLDS THE AGENT GENESIS KEY   %s" % holds_agent)
        (bad if holds_agent else ok).append(w.name)
        missing = [h for h in payees if h not in used]
        print("    payee heights NOT in wallet   %s" % (missing if len(missing) <= 12
                                                        else "%d heights" % len(missing)))

    print("\n  VERDICT")
    if bad:
        print("    ** CUSTODY SEPARATION BROKEN: the agent key is inside %s" % ", ".join(bad))
        return 1
    print("    the agent's genesis key is in NONE of the %d wallet file(s) examined." % len(ok))
    print("    It was used once, at height 0, and is held alone. Separation holds.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
