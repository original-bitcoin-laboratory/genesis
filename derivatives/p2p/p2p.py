"""MODEL of the Bitcoin v0.1 peer-to-peer wire protocol (derivative).

Faithful to net.h/main.cpp: a message is [magic:4][command:12][size:4 LE][payload]
with **no checksum** (net.h CMessageHeader) — magic = f9 be b4 d9 (net.h:54),
PROTOCOL_VERSION = 101 (serialize.h:22). The handshake is a plain `version`
exchange with **no verack** (main.cpp:1705). Peers relay via `inv` → `getdata`
→ `block`/`tx` (main.cpp:1772-1955).

This runs two headless nodes over localhost TCP — no VM, no GUI. Block/tx bytes
use the same serialization as the rest of the lab (tx_sighash). Evidence level:
MODEL (test infrastructure; wire format anchored to source).
"""

from __future__ import annotations

import asyncio
import hashlib
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "model"))
from tx_sighash import Tx, TxIn, TxOut, compact_size, serialize as ser_tx, _le  # noqa: E402

MAGIC = b"\xf9\xbe\xb4\xd9"
PROTOCOL_VERSION = 101
MSG_TX, MSG_BLOCK = 1, 2


def dsha256(b: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


# ---- message framing (CMessageHeader: magic|command|size, no checksum) --------

def build_message(command: str, payload: bytes, magic: bytes = MAGIC) -> bytes:
    cmd = command.encode().ljust(12, b"\x00")
    return magic + cmd + _le(len(payload), 4) + payload


class MsgReader:
    def __init__(self, reader: asyncio.StreamReader, magic: bytes = MAGIC):
        self.r = reader
        self.magic = magic

    async def read(self):
        hdr = await self.r.readexactly(20)                 # 4 + 12 + 4
        if hdr[:4] != self.magic:
            raise ValueError("bad magic")
        command = hdr[4:16].rstrip(b"\x00").decode("latin-1")
        size = int.from_bytes(hdr[16:20], "little")
        payload = await self.r.readexactly(size) if size else b""
        return command, payload


# ---- payload codecs -----------------------------------------------------------

def enc_addr(services=1, ip=b"\x00" * 4, port=8333) -> bytes:
    reserved = b"\x00" * 10 + b"\xff\xff"                   # IPv4-mapped prefix
    return _le(services, 8) + reserved + ip + port.to_bytes(2, "big")


def version_payload(nTime=0, addrMe=None) -> bytes:
    # int nVersion, uint64 nServices, int64 nTime, CAddress addrMe (net-serialized)
    return _le(PROTOCOL_VERSION, 4) + _le(1, 8) + _le(nTime, 8) + (addrMe or enc_addr())


def inv_payload(items) -> bytes:
    out = compact_size(len(items))
    for typ, h in items:
        out += _le(typ, 4) + h                             # CInv: int type + uint256 hash
    return out


def parse_inv(payload: bytes):
    # CompactSize count + [type(4) hash(32)]* — decode the FULL varint, not just the first byte
    # (counts >= 0xfd use a multi-byte prefix; reading payload[0] alone breaks any inv of >=253 items).
    b0 = payload[0]
    if b0 < 0xFD:
        n, i = b0, 1
    elif b0 == 0xFD:
        n, i = int.from_bytes(payload[1:3], "little"), 3
    elif b0 == 0xFE:
        n, i = int.from_bytes(payload[1:5], "little"), 5
    else:
        n, i = int.from_bytes(payload[1:9], "little"), 9
    items = []
    for _ in range(n):
        typ = int.from_bytes(payload[i:i + 4], "little"); i += 4
        h = payload[i:i + 32]; i += 32
        items.append((typ, h))
    return items


def block_bytes(nVersion, hashPrevBlock, hashMerkleRoot, nTime, nBits, nNonce, vtx) -> bytes:
    header = (_le(nVersion, 4) + hashPrevBlock + hashMerkleRoot
              + _le(nTime, 4) + _le(nBits, 4) + _le(nNonce, 4))
    body = compact_size(len(vtx)) + b"".join(ser_tx(t) for t in vtx)
    return header + body


def block_header(raw_block: bytes) -> bytes:
    return raw_block[:80]


def merkle_root(vtx) -> bytes:
    h = [dsha256(ser_tx(t)) for t in vtx]
    while len(h) > 1:
        if len(h) & 1:
            h.append(h[-1])
        h = [dsha256(h[i] + h[i + 1]) for i in range(0, len(h), 2)]
    return h[0] if h else b"\x00" * 32


def target_from_bits(nBits: int) -> int:
    exp = nBits >> 24
    mant = nBits & 0x007FFFFF
    return mant * (1 << (8 * (exp - 3))) if exp > 3 else mant >> (8 * (3 - exp))


def pow_ok(raw_block: bytes, nBits: int) -> bool:
    h = dsha256(block_header(raw_block))
    return int.from_bytes(h, "little") <= target_from_bits(nBits)


# ---- a headless node ----------------------------------------------------------

class Node:
    def __init__(self, name: str):
        self.name = name
        self.blocks: dict[bytes, bytes] = {}   # block hash -> raw block bytes
        self.txs: dict[bytes, bytes] = {}       # txid -> raw tx bytes
        self.block_bits: dict[bytes, int] = {}  # block hash -> nBits (for PoW check on receive)
        self.log: list[str] = []
        self._peers: list[asyncio.StreamWriter] = []
        self.handshaked = asyncio.Event()

    def have(self, typ, h):
        return (h in self.blocks) if typ == MSG_BLOCK else (h in self.txs)

    def add_block(self, raw, nBits):
        h = dsha256(block_header(raw)); self.blocks[h] = raw; self.block_bits[h] = nBits; return h

    def add_tx(self, raw):
        h = dsha256(raw); self.txs[h] = raw; return h

    async def _send(self, w, command, payload):
        w.write(build_message(command, payload)); await w.drain()

    async def announce(self, items):
        for w in self._peers:
            await self._send(w, "inv", inv_payload(items))

    async def handle(self, reader, writer):
        self._peers.append(writer)
        mr = MsgReader(reader)
        await self._send(writer, "version", version_payload())     # v0.1: send version on connect
        try:
            while True:
                command, payload = await mr.read()
                self.log.append(f"recv {command}")
                if command == "version":
                    self.handshaked.set()
                elif command == "inv":
                    want = [it for it in parse_inv(payload) if not self.have(*it)]
                    if want:
                        await self._send(writer, "getdata", inv_payload(want))
                elif command == "getdata":
                    for typ, h in parse_inv(payload):
                        if typ == MSG_BLOCK and h in self.blocks:
                            await self._send(writer, "block", self.blocks[h])
                        elif typ == MSG_TX and h in self.txs:
                            await self._send(writer, "tx", self.txs[h])
                elif command == "block":
                    h = dsha256(block_header(payload))
                    nBits = int.from_bytes(payload[72:76], "little")   # header: ver4 prev32 merkle32 time4 [bits4] nonce4
                    valid = pow_ok(payload, nBits)
                    if valid:
                        self.blocks[h] = payload; self.block_bits[h] = nBits
                        self.log.append(f"accepted block {h[::-1].hex()[:16]} pow_ok={valid}")
                        await self._send(writer, "inv", inv_payload([(MSG_BLOCK, h)]))  # relay
                elif command == "tx":
                    h = dsha256(payload)
                    self.txs[h] = payload
                    self.log.append(f"accepted tx {h[::-1].hex()[:16]}")
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
