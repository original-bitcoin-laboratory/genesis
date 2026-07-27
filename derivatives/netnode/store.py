"""Crash-safe on-disk block store for the X-chain nodes (Path B, Stage 1).

Every valid block a node accepts is appended, length-prefixed, to `<datadir>/blocks.dat`,
flushed + fsync'd. On startup the records are replayed into a `chainsync.Chain` (genesis
first, then `process_block` for the rest — whose orphan handling tolerates out-of-order
records). A truncated trailing record (from a crash mid-write) is ignored. This gives a node
**restart recovery**: it reloads its chain from disk instead of re-syncing from scratch.
Evidence: MODEL.
"""

from __future__ import annotations

import os
import pathlib
import struct


class BlockStore:
    def __init__(self, datadir: str | pathlib.Path):
        self.dir = pathlib.Path(datadir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "blocks.dat"
        self._f = open(self.path, "ab", buffering=0)     # append, unbuffered

    def append(self, raw: bytes) -> None:
        self._f.write(struct.pack("<I", len(raw)) + raw)
        self._f.flush()
        os.fsync(self._f.fileno())

    def read_all(self) -> list[bytes]:
        if not self.path.exists():
            return []
        data = self.path.read_bytes()
        out, i = [], 0
        while i + 4 <= len(data):
            (n,) = struct.unpack_from("<I", data, i)
            i += 4
            if i + n > len(data):                        # truncated tail from a crash -> stop
                break
            out.append(data[i:i + n])
            i += n
        return out

    def count(self) -> int:
        return len(self.read_all())

    def close(self) -> None:
        try:
            self._f.close()
        except OSError:
            pass
