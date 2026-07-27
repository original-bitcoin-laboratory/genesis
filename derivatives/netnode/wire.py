"""Hardened wire framing for the experimental X-chain nodes — NEW-EXP (Path B, Stage 1).

This is **not** a reproduction of v0.1's fragile framing (which had *no checksum* — see
`../p2p/p2p.py`); it is the hardened transport a public node needs. Every message is:

    [magic:4][command:12][length:4 LE][checksum:4][payload]

with `checksum = dsha256(payload)[:4]` and a hard `MAX_MESSAGE_SIZE` cap. Any framing fault
— bad magic, oversize, bad checksum, short read, or a stalled peer (timeout) — raises
`WireError`, and the caller drops the peer. No resync, no trust. Evidence: MODEL / NEW-EXP.
"""

from __future__ import annotations

import asyncio
import hashlib

MAX_MESSAGE_SIZE = 4 * 1024 * 1024          # 4 MiB hard cap (DoS resistance)
HEADER = 24                                  # magic4 + command12 + length4 + checksum4
READ_TIMEOUT = 120.0                         # drop a peer that stalls mid-message


class WireError(Exception):
    pass


def dsha256(b: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


def frame(command: str, payload: bytes, magic: bytes) -> bytes:
    if len(payload) > MAX_MESSAGE_SIZE:
        raise WireError(f"outgoing payload too large: {len(payload)}")
    cmd = command.encode("ascii").ljust(12, b"\x00")
    return magic + cmd + len(payload).to_bytes(4, "little") + dsha256(payload)[:4] + payload


async def read_message(reader: asyncio.StreamReader, magic: bytes,
                       *, timeout: float = READ_TIMEOUT):
    """Read one framed message or raise WireError. Verifies magic, size cap, and checksum."""
    try:
        hdr = await asyncio.wait_for(reader.readexactly(HEADER), timeout)
    except asyncio.IncompleteReadError as e:
        raise WireError("connection closed") from e
    except (asyncio.TimeoutError, TimeoutError) as e:
        raise WireError("header read timeout") from e
    if hdr[:4] != magic:
        raise WireError("bad magic")
    command = hdr[4:16].rstrip(b"\x00").decode("ascii", "replace")
    length = int.from_bytes(hdr[16:20], "little")
    checksum = hdr[20:24]
    if length > MAX_MESSAGE_SIZE:
        raise WireError(f"declared size too large: {length}")
    try:
        payload = await asyncio.wait_for(reader.readexactly(length), timeout) if length else b""
    except asyncio.IncompleteReadError as e:
        raise WireError("payload truncated") from e
    except (asyncio.TimeoutError, TimeoutError) as e:
        raise WireError("payload read timeout") from e
    if dsha256(payload)[:4] != checksum:
        raise WireError("bad checksum")
    return command, payload
