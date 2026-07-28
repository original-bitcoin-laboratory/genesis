"""MODEL of Bitcoin v0.1 chain synchronisation (derivative) — the getblocks /
block-locator / orphan / reorg path that lets a behind node catch up to a peer.

Anchored to main.cpp / main.h of the v0.1.0 release:

- `version` -> the fresh node asks its peer for blocks with
  `getblocks(CBlockLocator(pindexBest), 0)`                    (main.cpp:1734)
- `CBlockLocator::Set` records the tip then steps back exponentially (step 1 for
  the first 10, then doubling) and always appends the genesis hash (main.h:1241).
- `getblocks` handler: `pindex = locator.GetBlockIndex()`, advance `pindex->pnext`
  and walk the main chain forward, sending an `inv(MSG_BLOCK)` for each block until
  `hashStop` or the tip                                        (main.cpp:1832-1864).
- `ProcessBlock`: dup-check, CheckBlock; if `hashPrevBlock` is unknown, hold the
  block in `mapOrphanBlocks` and ask `getblocks(pindexBest, GetOrphanRoot(pblock))`
  to fill the gap; otherwise AcceptBlock and recursively reconnect any orphans whose
  prev is now present                                          (main.cpp:1236-1293).
- Best chain is **height-based** in this earliest release: `pindexNew->nHeight >
  nBestHeight`; a block that extends `hashBestChain` is appended, otherwise a longer
  branch triggers `Reorganize`                                 (main.cpp:1097-1130).

Two headless nodes over localhost TCP synchronise a multi-block chain end-to-end —
no VM, no GUI. Wire framing / codecs are reused from `p2p.py`. Evidence: MODEL.
"""

from __future__ import annotations

import asyncio

from p2p import (MAGIC, MSG_BLOCK, MsgReader, PROTOCOL_VERSION, block_bytes,
                 build_message, dsha256, inv_payload, merkle_root, parse_inv,
                 pow_ok, version_payload)
from tx_sighash import Tx, TxIn, TxOut, compact_size, _le

ZERO = b"\x00" * 32
EASY = 0x207FFFFF                                   # regtest-style easy target


# ---- header field accessors (ver4 prev32 merkle32 time4 bits4 nonce4) ---------

def block_hash(raw: bytes) -> bytes:
    return dsha256(raw[:80])


def prev_hash(raw: bytes) -> bytes:
    return raw[4:36]


def nbits_of(raw: bytes) -> int:
    return int.from_bytes(raw[72:76], "little")


# ---- CompactSize reader + getblocks/locator codecs ----------------------------

def read_compact(buf: bytes, i: int):
    n = buf[i]; i += 1
    if n < 0xFD:
        return n, i
    if n == 0xFD:
        return int.from_bytes(buf[i:i + 2], "little"), i + 2
    if n == 0xFE:
        return int.from_bytes(buf[i:i + 4], "little"), i + 4
    return int.from_bytes(buf[i:i + 8], "little"), i + 8


def locator_payload(hashes, hash_stop: bytes = ZERO) -> bytes:
    # getblocks = CBlockLocator + hashStop; CBlockLocator = [nVersion:4][vHave]
    out = _le(PROTOCOL_VERSION, 4) + compact_size(len(hashes)) + b"".join(hashes)
    return out + hash_stop


def parse_getblocks(payload: bytes):
    i = 4                                          # skip locator nVersion
    n, i = read_compact(payload, i)
    hashes = []
    for _ in range(n):
        if i + 32 > len(payload):                  # bound to the real bytes: a huge count must not spin
            break
        hashes.append(payload[i:i + 32]); i += 32
    return hashes, payload[i:i + 32]               # (vHave, hashStop)


# ---- block-index + chain (faithful ProcessBlock / AddToBlockIndex) ------------

class BlockIndex:
    __slots__ = ("hash", "prev", "height", "raw", "nBits", "pnext", "in_main")

    def __init__(self, h, prev, height, raw, nBits):
        self.hash = h; self.prev = prev; self.height = height
        self.raw = raw; self.nBits = nBits
        self.pnext = None; self.in_main = False


class Chain:
    """In-memory block index with a single best (main) chain, orphan holding area,
    a CBlockLocator generator, and height-based reorganisation."""

    def __init__(self, pow_check=None):
        self.by_hash: dict[bytes, BlockIndex] = {}
        self.orphans: dict[bytes, tuple[bytes, int]] = {}     # hash -> (raw, nBits)
        self.orphans_by_prev: dict[bytes, list[bytes]] = {}
        self.genesis: bytes | None = None
        self.tip: bytes | None = None
        # pluggable proof-of-work check (raw, nBits) -> bool; default JAN09 compact.
        # NOV08-X passes its leading-zero-bits check here.
        self._pow_check = pow_check or (lambda raw, nBits: pow_ok(raw, nBits))

    # -- construction ----------------------------------------------------------
    def add_genesis(self, raw: bytes, nBits: int) -> bytes:
        h = block_hash(raw)
        idx = BlockIndex(h, prev_hash(raw), 0, raw, nBits)
        idx.in_main = True
        self.by_hash[h] = idx
        self.genesis = self.tip = h
        return h

    @property
    def best_height(self) -> int:
        return self.by_hash[self.tip].height

    def have(self, typ: int, h: bytes) -> bool:
        return typ == MSG_BLOCK and (h in self.by_hash or h in self.orphans)

    # -- CheckBlock (preliminary) ---------------------------------------------
    def check_block(self, raw: bytes) -> bool:
        return self._pow_check(raw, nbits_of(raw))  # PoW is the check we can enforce headlessly

    # -- ProcessBlock ----------------------------------------------------------
    def process_block(self, raw: bytes):
        """Returns (status, hash): 'dup' | 'invalid' | 'orphan' | 'accepted'.
        Faithful to main.cpp ProcessBlock incl. recursive orphan reconnection."""
        h = block_hash(raw)
        if h in self.by_hash or h in self.orphans:
            return "dup", h
        if not self.check_block(raw):
            return "invalid", h
        prev = prev_hash(raw)
        if prev not in self.by_hash:               # orphan: shunt to holding area
            self.orphans[h] = (raw, nbits_of(raw))
            self.orphans_by_prev.setdefault(prev, []).append(h)
            return "orphan", h
        self._add_index(raw)
        # recursively reconnect orphans that were waiting on this block
        queue = [h]
        for cur in queue:
            for oh in self.orphans_by_prev.pop(cur, []):
                oraw, _ = self.orphans.pop(oh)
                self._add_index(oraw)
                queue.append(oh)
        return "accepted", h

    def get_orphan_root(self, h: bytes) -> bytes:
        raw, _ = self.orphans[h]
        prev = prev_hash(raw)
        while prev in self.orphans:
            raw, _ = self.orphans[prev]
            prev = prev_hash(raw)
        return block_hash(raw)

    # -- AddToBlockIndex (height-based best chain) -----------------------------
    def _add_index(self, raw: bytes) -> BlockIndex:
        h = block_hash(raw); prev = prev_hash(raw)
        pprev = self.by_hash[prev]
        idx = BlockIndex(h, prev, pprev.height + 1, raw, nbits_of(raw))
        self.by_hash[h] = idx
        if idx.height > self.best_height:
            if prev == self.tip:                   # extend the current best branch
                pprev.pnext = h; idx.in_main = True; self.tip = h
            else:                                  # longer competing branch -> reorganize
                self._reorganize(idx)
        # else: stored as a shorter side branch (in_main stays False)
        return idx

    def _reorganize(self, new_tip: BlockIndex):
        # collect the new branch back to the first ancestor already on the main chain
        branch, idx = [], new_tip
        while idx is not None and not idx.in_main:
            branch.append(idx)
            idx = self.by_hash.get(idx.prev)
        fork = idx                                 # first in-main ancestor (genesis at worst)
        # disconnect the old main chain above the fork
        cur = fork.pnext
        while cur is not None:
            ci = self.by_hash[cur]; nxt = ci.pnext
            ci.in_main = False; ci.pnext = None
            cur = nxt
        # connect the new branch from the fork up to the new tip
        fork.pnext = branch[-1].hash
        for i in range(len(branch) - 1, -1, -1):
            branch[i].in_main = True
            branch[i].pnext = branch[i - 1].hash if i > 0 else None
        self.tip = new_tip.hash

    # -- CBlockLocator + getblocks support -------------------------------------
    def get_locator(self) -> list[bytes]:
        have, idx, step = [], self.by_hash[self.tip], 1
        while idx is not None:
            have.append(idx.hash)
            for _ in range(step):
                idx = self.by_hash.get(idx.prev)
                if idx is None:
                    break
            if len(have) > 10:
                step *= 2
        have.append(self.genesis)                  # always end with genesis (main.h:1255)
        return have

    def locate(self, have) -> BlockIndex:
        for h in have:                             # first locator hash on our main chain
            idx = self.by_hash.get(h)
            if idx is not None and idx.in_main:
                return idx
        return self.by_hash[self.genesis]

    def blocks_after_locator(self, have, hash_stop: bytes) -> list[bytes]:
        cur = self.locate(have).pnext              # send the rest of the chain (pindex->pnext)
        out = []
        while cur is not None:
            if cur == hash_stop:
                break
            out.append(cur)
            cur = self.by_hash[cur].pnext
        return out

    def main_chain(self) -> list[bytes]:
        out, cur = [], self.genesis
        while cur is not None:
            out.append(cur); cur = self.by_hash[cur].pnext
        return out


# ---- a headless syncing node --------------------------------------------------

class SyncNode:
    def __init__(self, name: str, chain: Chain, magic: bytes = MAGIC):
        self.name = name
        self.chain = chain
        self.magic = magic                             # network identity (NOV08-X uses its own)
        self.log: list[str] = []
        self._peers: list[asyncio.StreamWriter] = []
        self.handshaked = asyncio.Event()

    async def _send(self, w, command, payload):
        w.write(build_message(command, payload, self.magic)); await w.drain()

    async def announce(self, items):
        for w in self._peers:
            await self._send(w, "inv", inv_payload(items))

    async def handle(self, reader, writer, initiate: bool = False):
        self._peers.append(writer)
        mr = MsgReader(reader, self.magic)
        await self._send(writer, "version", version_payload())
        try:
            while True:
                command, payload = await mr.read()
                self.log.append(f"recv {command}")
                if command == "version":
                    self.handshaked.set()
                    if initiate:                   # behind node asks its peer for blocks
                        await self._send(writer, "getblocks",
                                         locator_payload(self.chain.get_locator()))
                elif command == "getblocks":
                    have, hash_stop = parse_getblocks(payload)
                    invs = self.chain.blocks_after_locator(have, hash_stop)
                    if invs:
                        await self._send(writer, "inv",
                                         inv_payload([(MSG_BLOCK, h) for h in invs]))
                elif command == "inv":
                    want = [it for it in parse_inv(payload) if not self.chain.have(*it)]
                    if want:
                        await self._send(writer, "getdata", inv_payload(want))
                elif command == "getdata":
                    for typ, h in parse_inv(payload):
                        if typ == MSG_BLOCK and h in self.chain.by_hash:
                            await self._send(writer, "block", self.chain.by_hash[h].raw)
                elif command == "block":
                    status, h = self.chain.process_block(payload)
                    self.log.append(f"{status} {h[::-1].hex()[:12]} h={self.chain.best_height}")
                    if status == "orphan":         # fill the gap up to the orphan's root
                        root = self.chain.get_orphan_root(h)
                        await self._send(writer, "getblocks",
                                         locator_payload(self.chain.get_locator(), root))
        except (asyncio.IncompleteReadError, ConnectionError):
            pass


# ---- mining helper (unique coinbase per block so hashes differ) ---------------

def _coinbase(height: int, tag: int = 0) -> Tx:
    t = Tx(1, [], [], 0)
    t.vin.append(TxIn(ZERO, 0xFFFFFFFF, bytes([2, height & 0xFF, tag & 0xFF]), 0xFFFFFFFF))
    t.vout.append(TxOut(50 * 100000000, b"\x51"))
    return t


def mine(prev: bytes, height: int, nBits: int = EASY, tag: int = 0) -> bytes:
    vtx = [_coinbase(height, tag)]
    mr = merkle_root(vtx)
    for nonce in range(1 << 24):
        raw = block_bytes(1, prev, mr, 1231006506, nBits, nonce, vtx)
        if pow_ok(raw, nBits):
            return raw
    raise RuntimeError("no nonce found")


def build_chain(n: int, tag: int = 0):
    """Genesis + n blocks; returns (Chain, [genesis_raw, b1_raw, ... bn_raw])."""
    c = Chain()
    g = mine(ZERO, 0, tag=200 + tag)               # distinct genesis per tag
    c.add_genesis(g, EASY)
    raws = [g]; prev = block_hash(g)
    for h in range(1, n + 1):
        raw = mine(prev, h, tag=tag)
        c.process_block(raw)
        raws.append(raw); prev = block_hash(raw)
    return c, raws
