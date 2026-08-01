#!/usr/bin/env python3
"""R4 verifier: from one or two nodes' blk0001.dat, rebuild the block index, follow the
height-based best chain (v0.1 selects by height, not chainwork), verify every block's
proof-of-work and prev-linkage, and report sustained-mining depth + any reorg (orphans).

This is the R4b copy: it additionally NAMES each off-best (orphaned) block — the block that
was mined but replaced by a longer competing chain — and the height it forked off the best
chain, so a witnessed reorganisation is legible directly from the raw bytes.

Usage:
    python verify_r4.py nodeA/blk0001.dat [nodeB/blk0001.dat]
    python verify_r4.py --b64 nodeA.b64 nodeB.b64        # base64-encoded blk files

If two files are given, it confirms both nodes converged on the SAME best tip (relay/reorg
agreement). NOT money.
"""
import base64, hashlib, struct, sys

MAGIC = bytes.fromhex("f9beb4d9")
GENESIS = "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f"


def dsha(b): return hashlib.sha256(hashlib.sha256(b).digest()).digest()


def bits_to_target(bits: int) -> int:
    exp = bits >> 24
    mant = bits & 0x007fffff
    return mant * (1 << (8 * (exp - 3)))


def parse_blocks(raw: bytes):
    """Yield (hash_hex, prev_hex, header) for every [magic][len][block] record."""
    i, n = 0, len(raw)
    while i + 8 <= n:
        if raw[i:i+4] != MAGIC:
            i += 1
            continue
        size = struct.unpack_from("<I", raw, i + 4)[0]
        blk = raw[i+8:i+8+size]
        i += 8 + size
        if len(blk) < 80:
            continue
        hdr = blk[:80]
        h = dsha(hdr)[::-1].hex()                          # display (big-endian) hash
        prev = hdr[4:36][::-1].hex()
        bits = struct.unpack_from("<I", hdr, 72)[0]
        pow_ok = int.from_bytes(dsha(hdr), "little") < bits_to_target(bits)
        yield h, prev, {"bits": bits, "pow_ok": pow_ok,
                        "time": struct.unpack_from("<I", hdr, 68)[0],
                        "nonce": struct.unpack_from("<I", hdr, 76)[0]}


def best_chain(raw: bytes):
    """Build index, then walk the tallest chain from genesis (height-based selection)."""
    idx = {h: (prev, meta) for h, prev, meta in parse_blocks(raw)}
    children = {}
    for h, (prev, _) in idx.items():
        children.setdefault(prev, []).append(h)

    def height(h, seen=None):                              # longest descent from h
        seen = seen or set()
        kids = [c for c in children.get(h, []) if c not in seen]
        return 1 + max((height(c, seen | {h}) for c in kids), default=0)

    # genesis is the block whose prev is all-zero
    roots = [h for h, (prev, _) in idx.items() if prev == "0"*64]
    if not roots:
        return [], idx
    tip_root = max(roots, key=height)
    chain, cur = [], tip_root
    while cur:
        chain.append(cur)
        kids = children.get(cur, [])
        cur = max(kids, key=height) if kids else None
    return chain, idx


def report(label, raw):
    chain, idx = best_chain(raw)
    on_best = set(chain)
    total, orphans = len(idx), len(idx) - len(chain)
    print(f"\n== {label} ==")
    print(f"  blocks in file: {total}   best-chain height: {len(chain)-1}   orphans (off-best): {orphans}")
    all_pow = True
    for ht, h in enumerate(chain):
        m = idx[h][1]
        ok = m["pow_ok"]; all_pow = all_pow and ok
        mark = "OK " if ok else "BAD"
        genesis_tag = "  <- genesis (real)" if h == GENESIS else ""
        if ht <= 2 or ht >= len(chain)-2 or not ok:
            print(f"  [{mark}] h{ht:<3} {h[:24]}...  nonce={m['nonce']}{genesis_tag}")
    # Name every off-best (orphaned) block: the mined block a longer chain replaced.
    for h in idx:
        if h in on_best:
            continue
        prev, m = idx[h]
        fork_h = chain.index(prev) if prev in on_best else "?"
        print(f"  [ORPHAN] {h[:24]}...  nonce={m['nonce']}  pow_ok={m['pow_ok']}  "
              f"prev={prev[:16]}... (forked off best chain at height {fork_h})")
    print(f"  genesis is the real historical genesis: {chain and chain[0] == GENESIS}")
    print(f"  every best-chain block has valid PoW: {all_pow}")
    print(f"  reorg witnessed (>=1 orphan off the best chain): {orphans >= 1}")
    return chain[-1] if chain else None, len(chain)-1, all_pow


def load(path, b64):
    data = open(path, "rb").read()
    return base64.b64decode(data) if b64 else data


def main(argv):
    b64 = "--b64" in argv
    files = [a for a in argv if not a.startswith("--")]
    if not files:
        print(__doc__); return 1
    tips = []
    for f in files:
        tip, ht, ok = report(f, load(f, b64))
        tips.append((f, tip, ht))
    if len(tips) == 2:
        (fa, ta, ha), (fb, tb, hb) = tips
        print("\n== two-node agreement ==")
        print(f"  {fa}: height {ha}, tip {ta[:24] if ta else None}...")
        print(f"  {fb}: height {hb}, tip {tb[:24] if tb else None}...")
        print(f"  BOTH NODES converged on the same best tip: {ta == tb and ta is not None}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
