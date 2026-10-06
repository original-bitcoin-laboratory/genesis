#!/usr/bin/env python3
"""Content gate: flag arbitrary data embedded in blocks BEFORE anything derived from them is
published -- a sealed chain file, a findings write-up that quotes block bytes, or a seed that serves
them.

Why: the January 2009 rules this chain runs let anyone put arbitrary bytes into a coinbase scriptSig
(up to 100 bytes) or into output and input scripts, at no cost, and mining is open. The laboratory
does not control what a third party embeds; it does control what it republishes. This gate makes
that a reviewed decision rather than an accident. (Standing review, 5 Oct 2026.)

What it flags, per pushed data element:
  TEXT        a run of >= --min-text printable ASCII characters
  FILE        a known file signature at the start of a push (PDF, PNG, JPEG, GIF, ZIP, GZIP, ...)
  LARGE       a push > --max-push bytes that is not a standard key or signature shape
Coinbase scriptSigs are scanned like any script. Reviewed findings go into an allow-list (JSON):
  [{"block": "<hash>", "tx": "<txid>", "kind": "TEXT", "reason": "..."}]
Exit 0 = nothing unreviewed; 1 = unreviewed findings (listed); 2 = usage / parse error.

Input: a v0.1 `blk0001.dat` (records: magic | size | block) or a file of raw hex blocks, one per line.

    python scripts/content_gate.py path/to/blk0001.dat [--allow reviewed.json]
    python scripts/content_gate.py --self-test       # the positive controls
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

FILE_MAGIC = {
    b"%PDF": "PDF", b"\x89PNG": "PNG", b"\xff\xd8\xff": "JPEG", b"GIF8": "GIF",
    b"PK\x03\x04": "ZIP", b"\x1f\x8b": "GZIP", b"7z\xbc\xaf": "7Z", b"Rar!": "RAR",
    b"BM": None,  # too short to trust alone; listed so it is a deliberate omission
}
STANDARD_PUSH = {33, 65, 20, 32} | set(range(70, 74))   # keys, hash160, hash, DER sigs (+hashtype)


def dsha(b: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


def compact(b: bytes, i: int):
    n = b[i]
    if n < 0xFD:
        return n, i + 1
    w = {0xFD: 2, 0xFE: 4, 0xFF: 8}[n]
    return int.from_bytes(b[i + 1:i + 1 + w], "little"), i + 1 + w


def parse_tx(b: bytes, i: int):
    s = i
    i += 4
    nin, i = compact(b, i)
    scripts = []
    for _ in range(nin):
        i += 36
        n, i = compact(b, i)
        scripts.append(("in", b[i:i + n]))
        i += n + 4
    nout, i = compact(b, i)
    for _ in range(nout):
        i += 8
        n, i = compact(b, i)
        scripts.append(("out", b[i:i + n]))
        i += n
    i += 4
    return dsha(b[s:i])[::-1].hex(), scripts, i


def parse_block(raw: bytes):
    h = dsha(raw[:80])[::-1].hex()
    ntx, i = compact(raw, 80)
    txs = []
    for _ in range(ntx):
        tid, scripts, i = parse_tx(raw, i)
        txs.append((tid, scripts))
    return h, txs


def pushes(script: bytes):
    """Yield data pushes; a malformed tail is yielded whole (it is still bytes someone embedded)."""
    i = 0
    while i < len(script):
        op = script[i]
        i += 1
        if 1 <= op <= 75:
            n = op
        elif op == 76 and i < len(script):
            n, i = script[i], i + 1
        elif op == 77 and i + 1 < len(script):
            n, i = int.from_bytes(script[i:i + 2], "little"), i + 2
        elif op == 78 and i + 3 < len(script):
            n, i = int.from_bytes(script[i:i + 4], "little"), i + 4
        else:
            continue
        yield script[i:i + n]
        i += n


def text_runs(b: bytes, min_len: int):
    run = bytearray()
    for c in b + b"\x00":
        if 32 <= c < 127:
            run.append(c)
        else:
            if len(run) >= min_len:
                yield run.decode("ascii")
            run = bytearray()


def scan_block(raw: bytes, min_text: int, max_push: int):
    h, txs = parse_block(raw)
    out = []
    for tid, scripts in txs:
        for side, script in scripts:
            for d in pushes(script):
                for magic, kind in FILE_MAGIC.items():
                    if kind and d.startswith(magic):
                        out.append((h, tid, "FILE", f"{kind} signature in {side} push ({len(d)} B)"))
                for t in text_runs(d, min_text):
                    out.append((h, tid, "TEXT", f"{side}: {t[:120]!r}"))
                if len(d) > max_push and len(d) not in STANDARD_PUSH:
                    out.append((h, tid, "LARGE", f"{side} push of {len(d)} B"))
    return out


def read_blocks(path: pathlib.Path):
    data = path.read_bytes()
    if data[:1].isalnum() and all(c in b"0123456789abcdefABCDEF\r\n" for c in data[:2000]):
        return [bytes.fromhex(l) for l in data.decode().split() if l.strip()]
    blocks, i = [], 0
    while i + 8 <= len(data):
        size = int.from_bytes(data[i + 4:i + 8], "little")
        if size == 0 or i + 8 + size > len(data):
            break
        blocks.append(data[i + 8:i + 8 + size])
        i += 8 + size
    return blocks


def gate(blocks, allow, min_text=16, max_push=80):
    allowed = {(a["block"], a["tx"], a["kind"]) for a in allow}
    found = [f for raw in blocks for f in scan_block(raw, min_text, max_push)]
    return [f for f in found if (f[0], f[1], f[2]) not in allowed], found


def _self_test() -> int:
    """Positive controls: a planted text, a planted PDF signature and a planted 90-byte push must
    each be caught; a block of standard shapes must pass clean."""
    def blk(script_sig: bytes, out_script: bytes) -> bytes:
        tx = (b"\x01\x00\x00\x00" + b"\x01" + b"\x00" * 32 + b"\xff" * 4
              + bytes([len(script_sig)]) + script_sig + b"\xff" * 4
              + b"\x01" + (50).to_bytes(8, "little") + bytes([len(out_script)]) + out_script
              + b"\x00" * 4)
        return b"\x01\x00\x00\x00" + b"\x00" * 76 + b"\x01" + tx
    p2pk = b"\x41" + b"\x04" + b"\x11" * 64 + b"\xac"
    clean = blk(b"\x04\xff\xff\x00\x1d\x01\x04", p2pk)
    text = blk(b"\x04\xff\xff\x00\x1d" + bytes([30]) + b"this is an embedded message!!!", p2pk)
    pdf = blk(b"\x04\xff\xff\x00\x1d\x01\x04", bytes([20]) + b"%PDF-1.4" + b"\x00" * 12 + b"\xac")
    large = blk(b"\x04\xff\xff\x00\x1d\x01\x04", b"\x4c" + bytes([90]) + b"\x00" * 90 + b"\xac")
    checks = [
        ("clean block passes", not gate([clean], [])[0]),
        ("planted TEXT caught", any(f[2] == "TEXT" for f in gate([text], [])[0])),
        ("planted PDF caught", any(f[2] == "FILE" for f in gate([pdf], [])[0])),
        ("planted LARGE caught", any(f[2] == "LARGE" for f in gate([large], [])[0])),
    ]
    h, _ = parse_block(text)
    tid = parse_block(text)[1][0][0]
    checks.append(("allow-list suppresses a reviewed finding",
                   not gate([text], [{"block": h, "tx": tid, "kind": "TEXT"}])[0]))
    for name, ok in checks:
        print(("PASS " if ok else "FAIL ") + name)
    return 0 if all(ok for _, ok in checks) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("chain", nargs="?", type=pathlib.Path)
    ap.add_argument("--allow", type=pathlib.Path)
    ap.add_argument("--min-text", type=int, default=16)
    ap.add_argument("--max-push", type=int, default=80)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    if not a.chain:
        ap.print_usage()
        return 2
    try:
        blocks = read_blocks(a.chain)
        allow = json.loads(a.allow.read_text(encoding="utf-8")) if a.allow else []
        unreviewed, found = gate(blocks, allow, a.min_text, a.max_push)
    except Exception as e:                       # noqa: BLE001 -- a gate fails closed
        print(f"content_gate: cannot scan {a.chain}: {e}", file=sys.stderr)
        return 2
    print(f"content_gate: {len(blocks)} blocks, {len(found)} findings, {len(unreviewed)} unreviewed")
    for h, tid, kind, what in unreviewed:
        print(f"  {kind:5s} block {h[:16]}... tx {tid[:16]}... {what}")
    return 1 if unreviewed else 0


if __name__ == "__main__":
    sys.exit(main())
