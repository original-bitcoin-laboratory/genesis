"""A hardened, joinable node for the experimental X-chains — NEW-EXP (Path B, Stage 1).

Turns the MODEL's localhost demo into something two people on *different machines* can run
and sync: real TCP, the hardened `wire` framing (checksum + size cap + timeouts), crash-safe
persistence (`store`), outbound reconnection, per-peer misbehavior scoring, block relay, and
an optional miner. Consensus (validation / reorg / orphans / locator) is the lab's faithful
`chainsync.Chain`; the netnode only supplies the adversarial-conditions transport around it.

Evidence: MODEL / NEW-EXP. **Not money.** Not production-secure — this is Stage 1 of the plan
in `../../docs/PUBLIC_TESTNET_SCOPE.md` (a real difficulty retarget, discovery/seeds, a security
review, and — above all — other operators — are still ahead).
"""

from __future__ import annotations

import asyncio
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
for _p in ("model", "p2p", "nov08x"):
    sys.path.insert(0, str(_HERE.parent / _p))
sys.path.insert(0, str(_HERE))

from chainsync import ZERO, block_hash, locator_payload, nbits_of, parse_getblocks  # noqa: E402
from p2p import MSG_BLOCK, inv_payload, parse_inv, version_payload                  # noqa: E402

from chains import ChainConfig, mine_next          # noqa: E402
from store import BlockStore                        # noqa: E402
from wire import WireError, frame, read_message     # noqa: E402

BAN_THRESHOLD = 20            # cumulative misbehavior points before a peer is dropped
RECONNECT_BACKOFF = 5.0


class Node:
    def __init__(self, cfg: ChainConfig, datadir, *, listen=None, mine=False,
                 mine_interval: float = 2.0, log=None):
        self.cfg = cfg
        self.store = BlockStore(datadir)
        self.chain = cfg.new_chain()
        self.listen = listen                         # (host, port) or None
        self.mine = mine
        self.mine_interval = mine_interval
        self._log = log or (lambda m: None)
        self._writers: set[asyncio.StreamWriter] = set()
        self._tasks: list[asyncio.Task] = []
        self._server = None
        self._closing = False
        self._load_or_init()

    # -- persistence / genesis -------------------------------------------------
    def _load_or_init(self):
        raws = self.store.read_all()
        if raws:
            self.chain.add_genesis(raws[0], nbits_of(raws[0]))
            for raw in raws[1:]:
                self.chain.process_block(raw)
            self._log(f"loaded {len(raws)} block(s) from disk; height={self.chain.best_height}")
        else:
            g = self.cfg.mint_genesis()
            self.chain.add_genesis(g, nbits_of(g))
            self.store.append(g)
            self._log(f"minted genesis {block_hash(g)[::-1].hex()[:16]}…")

    @property
    def height(self) -> int:
        return self.chain.best_height

    @property
    def tip(self) -> bytes:
        return self.chain.tip

    # -- lifecycle -------------------------------------------------------------
    async def start(self, connect=()):
        if self.listen:
            self._server = await asyncio.start_server(self._inbound, self.listen[0], self.listen[1])
            self._log(f"listening on {self.listen[0]}:{self.listen[1]}")
        for host, port in connect:
            self._tasks.append(asyncio.create_task(self._outbound(host, port)))
        if self.mine:
            self._tasks.append(asyncio.create_task(self._mine_loop()))

    async def stop(self):
        self._closing = True
        for t in self._tasks:
            t.cancel()
        if self._server:
            self._server.close()
        for w in list(self._writers):
            w.close()
        self.store.close()

    # -- connections -----------------------------------------------------------
    async def _inbound(self, reader, writer):
        await self._session(reader, writer, initiate=False)

    async def _outbound(self, host, port):
        while not self._closing:
            try:
                reader, writer = await asyncio.open_connection(host, port)
                self._log(f"connected out to {host}:{port}")
                await self._session(reader, writer, initiate=True)
            except (OSError, WireError) as e:
                self._log(f"outbound {host}:{port} failed: {e}")
            if self._closing:
                return
            await asyncio.sleep(RECONNECT_BACKOFF)   # reconnection

    async def _send(self, writer, command, payload):
        writer.write(frame(command, payload, self.cfg.magic))
        await writer.drain()

    async def _announce(self, items, exclude=None):
        for w in list(self._writers):
            if w is exclude:
                continue
            try:
                await self._send(w, "inv", inv_payload(items))
            except (WireError, ConnectionError, OSError):
                pass

    # -- one peer session ------------------------------------------------------
    async def _session(self, reader, writer, initiate):
        self._writers.add(writer)
        misbehavior = 0
        try:
            await self._send(writer, "version", version_payload())
            while not self._closing:
                command, payload = await read_message(reader, self.cfg.magic)
                if command == "version":
                    if initiate:                     # a fresh/behind node asks its peer for blocks
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
                    misbehavior += await self._on_block(payload, writer)
                    if misbehavior >= BAN_THRESHOLD:
                        raise WireError("peer banned (misbehavior)")
                else:
                    misbehavior += 1                 # unknown command
        except (WireError, ConnectionError, OSError) as e:
            self._log(f"peer dropped: {e}")
        finally:
            self._writers.discard(writer)
            try:
                writer.close()
            except OSError:
                pass

    async def _on_block(self, raw: bytes, origin) -> int:
        """Validate + persist + relay a received block. Returns misbehavior points to add."""
        status, h = self.chain.process_block(raw)
        if status in ("accepted", "orphan"):
            self.store.append(raw)                   # persist every valid new block (orphans included)
        if status == "accepted":
            self._log(f"block {h[::-1].hex()[:12]} height={self.chain.best_height}")
            await self._announce([(MSG_BLOCK, h)], exclude=origin)
            return 0
        if status == "orphan":
            root = self.chain.get_orphan_root(h)
            await self._send(origin, "getblocks",
                             locator_payload(self.chain.get_locator(), root))
            return 0
        if status == "invalid":
            return 5                                 # bad PoW etc. — penalise
        return 0                                      # dup

    # -- mining ----------------------------------------------------------------
    async def _mine_loop(self):
        loop = asyncio.get_event_loop()
        gen_nbits = self.chain.by_hash[self.chain.genesis].nBits
        while not self._closing:
            prev, height, check = self.tip, self.height + 1, self.chain.check_block
            raw = await loop.run_in_executor(None, mine_next, prev, height, gen_nbits,
                                             check, self.cfg.genesis_msg[:0])
            status, h = self.chain.process_block(raw)
            if status == "accepted":
                self.store.append(raw)
                self._log(f"mined {h[::-1].hex()[:12]} height={self.chain.best_height}")
                await self._announce([(MSG_BLOCK, h)])
            await asyncio.sleep(self.mine_interval)
