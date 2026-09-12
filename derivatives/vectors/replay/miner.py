"""Find a nonce for an 80-byte header: native Rust miner when available, multiprocessing hashlib otherwise.

    python miner.py <prefix76_hex> <nbits_hex> [--exe PATH] [--threads N]

The difficulty-1 target needs about 2^32 hashes per block. Pure Python manages a few MH/s per core, so
101 blocks (one funding block + 100 to mature it) is hours on a laptop; the Rust miner in ./miner-rs does
the same in minutes. Either path returns the same thing: the first nonce (from `start`) whose double
SHA-256 header hash, read as a little-endian 256-bit integer, is at or below the target. NOT money.
"""
from __future__ import annotations

import hashlib
import multiprocessing
import os
import pathlib
import subprocess
import sys

CHUNK = 1 << 20


def target_of(nbits: int) -> int:
    size = nbits >> 24
    word = nbits & 0x007FFFFF
    return word >> (8 * (3 - size)) if size <= 3 else word << (8 * (size - 3))


def _scan(args):
    prefix, target, start, count = args
    for nonce in range(start, start + count):
        h = hashlib.sha256(hashlib.sha256(prefix + nonce.to_bytes(4, "little")).digest()).digest()
        if int.from_bytes(h, "little") <= target:
            return nonce
    return None


def mine_python(prefix76: bytes, nbits: int, start: int = 0, procs: int | None = None, log=None) -> int | None:
    target = target_of(nbits)
    procs = procs or max(1, (os.cpu_count() or 2) - 1)
    with multiprocessing.Pool(procs) as pool:
        nonce = start
        while nonce < (1 << 32):
            jobs = [(prefix76, target, nonce + i * CHUNK, min(CHUNK, (1 << 32) - (nonce + i * CHUNK)))
                    for i in range(procs) if nonce + i * CHUNK < (1 << 32)]
            for r in pool.imap(_scan, jobs):
                if r is not None:
                    return r
            nonce += CHUNK * procs
            if log:
                log(f"  scanned {nonce:,} nonces")
    return None


def mine_native(exe: str, prefix76: bytes, nbits: int, start: int = 0, threads: int | None = None) -> int | None:
    cmd = [exe, prefix76.hex(), f"{nbits:08x}", str(start), str(threads or 0)]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.strip()
    return None if out == "none" else int(out)


def default_exe() -> str | None:
    here = pathlib.Path(__file__).resolve().parent
    for cand in (here / "miner-rs" / "target" / "release" / "miner.exe", here / "miner-rs" / "target" / "release" / "miner",
                 here / "miner.exe", here / "miner"):
        if cand.exists():
            return str(cand)
    return None


def make_miner(exe: str | None = None, threads: int | None = None, log=None):
    """Return mine(prefix76, nbits) -> nonce, choosing the native binary when one exists."""
    exe = exe or default_exe()
    if exe and not pathlib.Path(exe).exists():
        if log:
            log(f"miner: {exe} not found, falling back to Python")
        exe = None

    def mine(prefix76: bytes, nbits: int) -> int | None:
        if exe:
            return mine_native(exe, prefix76, nbits, 0, threads)
        return mine_python(prefix76, nbits, 0, threads, log)
    mine.backend = f"native {exe}" if exe else "python multiprocessing"   # type: ignore[attr-defined]
    return mine


def check(prefix76: bytes, nbits: int, nonce: int) -> bool:
    h = hashlib.sha256(hashlib.sha256(prefix76 + nonce.to_bytes(4, "little")).digest()).digest()
    return int.from_bytes(h, "little") <= target_of(nbits)


if __name__ == "__main__":
    a = sys.argv[1:]
    exe = None
    threads = None
    if "--exe" in a:
        exe = a[a.index("--exe") + 1]
    if "--threads" in a:
        threads = int(a[a.index("--threads") + 1])
    prefix, nbits = bytes.fromhex(a[0]), int(a[1], 16)
    m = make_miner(exe, threads, print)
    print("backend:", m.backend, file=sys.stderr)
    n = m(prefix, nbits)
    print("none" if n is None else n)
