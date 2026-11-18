"""Crash-safe on-disk block store for the X-chain nodes (Path B, Stage 1).

Every valid block a node accepts is appended, length-prefixed, to `<datadir>/blocks.dat`,
flushed + fsync'd. On startup the records are replayed into a `chainsync.Chain` (genesis
first, then `process_block` for the rest — whose orphan handling tolerates out-of-order
records). A truncated trailing record (from a crash mid-write) is set aside before the store is
opened for appending, so new records are never written after it. This gives a node **restart
recovery**: it reloads its chain from disk instead of re-syncing from scratch.

The file is also where a node keeps the bytes of blocks it has loaded: `read_at(offset)` returns a
record by its offset, so the in-memory index can drop them (`BlockIndex.spill`) and read them back on
demand. Evidence: MODEL.
"""

from __future__ import annotations

import os
import pathlib
import struct
import threading
import time


def _complete_end(path: pathlib.Path) -> int:
    """Offset just past the last complete record (0 for a missing or empty file)."""
    if not path.exists():
        return 0
    size = path.stat().st_size
    end = 0
    with open(path, "rb") as f:
        while end + 4 <= size:
            f.seek(end)
            (n,) = struct.unpack("<I", f.read(4))
            if end + 4 + n > size:
                break
            end += 4 + n
    return end


class BlockStore:
    def __init__(self, datadir: str | pathlib.Path):
        self.dir = pathlib.Path(datadir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "blocks.dat"
        # ⛔ 18 Nov 2026. A crash mid-write leaves a partial record at the end. The store ignored it
        #    on reading but then APPENDED after it, so on the next restart the partial record's
        #    length prefix swallowed every block written since. The partial bytes are now moved
        #    aside (kept, not deleted) and the file is cut back to its last complete record before
        #    anything is appended.
        self.torn_tail = None
        end = _complete_end(self.path)
        #    The side file is fsync'd before the cut, and never overwrites an earlier one. (A corrupt
        #    length prefix mid-file sends every later record aside too: kept there, and re-fetched
        #    from peers by the node.)
        if self.path.exists() and self.path.stat().st_size > end:
            stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
            for k in range(1000):
                side = self.dir / f"blocks.dat.torn-{stamp}" if k == 0 else \
                       self.dir / f"blocks.dat.torn-{stamp}.{k}"
                try:
                    g = open(side, "xb")
                    break
                except FileExistsError:
                    continue
            else:
                raise RuntimeError(f"cannot name a side file for the torn tail of {self.path}")
            with open(self.path, "rb") as f, g:
                f.seek(end)
                while chunk := f.read(1 << 20):
                    g.write(chunk)
                g.flush()
                os.fsync(g.fileno())
            os.truncate(self.path, end)
            self.torn_tail = side
        self._f = open(self.path, "ab", buffering=0)     # append, unbuffered
        self._r = None                                   # random-access reader, opened on first use
        self._lock = threading.Lock()                    # one seek+read at a time, from any thread

    def append(self, raw: bytes) -> None:
        self._f.write(struct.pack("<I", len(raw)) + raw)
        self._f.flush()
        os.fsync(self._f.fileno())

    def iter_records(self):
        """Yield (offset, raw) for each complete record, in file order, reading as it goes -- so a
        large store is never held in memory at once. A record whose length runs past the end of the
        file ends it; that length is checked BEFORE anything is read, so a corrupt prefix cannot make
        the reader allocate it."""
        if not self.path.exists():
            return
        with open(self.path, "rb") as f:
            size = os.fstat(f.fileno()).st_size
            while True:
                off = f.tell()
                if off + 4 > size:
                    return
                (n,) = struct.unpack("<I", f.read(4))
                if off + 4 + n > size:                   # truncated tail -> stop
                    return
                yield off, f.read(n)

    def read_all(self) -> list[bytes]:
        return [raw for _, raw in self.iter_records()]

    def read_at(self, off: int) -> bytes:
        """The record that starts at `off`. Raises ValueError if no complete record starts there."""
        with self._lock:
            if self._r is None:
                self._r = open(self.path, "rb")
                self._size = os.fstat(self._r.fileno()).st_size
            # The file only grows while open, so the size is re-read only when a record seems to
            # run past the last one seen (a stat per read cost ~40 us on Windows, 9 s per load).
            if off + 4 > self._size:
                self._size = os.fstat(self._r.fileno()).st_size
            if off < 0 or off + 4 > self._size:
                raise ValueError(f"no block record at offset {off}")
            self._r.seek(off)
            head = self._r.read(4)
            if len(head) != 4:                           # the file shrank under us
                raise ValueError(f"short read at offset {off}")
            (n,) = struct.unpack("<I", head)
            if off + 4 + n > self._size:
                self._size = os.fstat(self._r.fileno()).st_size
                if off + 4 + n > self._size:             # checked BEFORE reading n bytes
                    raise ValueError(f"truncated block record at offset {off}")
            data = self._r.read(n)
            if len(data) != n:
                raise ValueError(f"short read at offset {off}")
            return data

    def count(self) -> int:
        return sum(1 for _ in self.iter_records())

    def close(self) -> None:
        for name in ("_f", "_r"):
            f = getattr(self, name)
            try:
                if f is not None:
                    f.close()
            except OSError:
                pass
        self._r = None                                   # a later read_at reopens it
