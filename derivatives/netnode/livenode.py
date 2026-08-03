"""A hardened, joinable node for the experimental X-chains — NEW-EXP (Path B, Stages 1-4 + full node).

Turns the MODEL's localhost demo into something two people on *different machines* can run and
sync. Consensus is the lab's faithful `chainsync.Chain`; the netnode adds the adversarial-
conditions transport around it:

- Stage 1 — hardened `wire` (checksum + size cap + timeouts), crash-safe `store`, real TCP,
  outbound reconnection, per-peer misbehavior scoring, block relay, a miner.
- Stage 2 — a real `difficulty` retarget: the miner mines at the retarget target, and received
  blocks are rejected if their nBits doesn't match the expected retarget for their parent.
- Stage 3 — peer discovery: nodes gossip known addresses (`addr`) and auto-connect, so a
  stranger with one seed address meshes into the network without a manual `--connect` chain.
- Full node — a validated UTXO chainstate (`chainstate.py`) is the **sole authority** for what
  the node serves and mines (difficulty re-checked authoritatively on connect, covering the orphan
  path; an optional `--min-difficulty` floor), and a validating `mempool` carries **real
  transactions**: `tx` messages are validated, pooled, and relayed (`inv`→`getdata`→`tx`) — with an
  orphan buffer and fee-rate eviction — and the miner assembles pooled transactions after the
  coinbase (claiming subsidy + fees), removing them once mined.
- Wallet — with `--wallet` the miner earns its coinbase to a persistent wallet (`nodewallet.py`);
  `wallet_balance` / `wallet_new_address` / `wallet_send` build payments on the faithful v0.1
  SelectCoins path, driven over a loopback control interface (`rpc.py`, `python -m netnode ctl`).

Evidence: MODEL / NEW-EXP. **Not money.** Not production-secure — see
`../../docs/PUBLIC_TESTNET_SCOPE.md` for what still lies ahead (a security review, signed
releases, a faster node, and — above all — other operators).
"""

from __future__ import annotations

import asyncio
import pathlib
import random
import socket
import sys

_HERE = pathlib.Path(__file__).resolve().parent
for _p in ("model", "p2p", "nov08x"):
    sys.path.insert(0, str(_HERE.parent / _p))
sys.path.insert(0, str(_HERE))

from chainsync import block_hash, locator_payload, nbits_of, parse_getblocks  # noqa: E402
from p2p import MSG_BLOCK, MSG_TX, inv_payload, parse_inv, version_payload    # noqa: E402
from chainsync import read_compact                     # noqa: E402
from tx_sighash import compact_size, dsha256, _le      # noqa: E402

from chains import ChainConfig, mine_block             # noqa: E402
from chainstate import COINBASE_MATURITY, ChainState  # noqa: E402
from difficulty import expected_bits                  # noqa: E402
from fullnode import validate_block                   # noqa: E402
from mempool import Mempool, MempoolReject            # noqa: E402
from nodewallet import NodeWallet                      # noqa: E402
from peerdb import PeerDB, group_of                    # noqa: E402
from store import BlockStore                           # noqa: E402
from wire import WireError, frame, read_message        # noqa: E402

BAN_THRESHOLD = 20
RECONNECT_BACKOFF = 5.0
MAX_PEERS = 8
MAX_ADDRS_PER_MSG = 20
MAX_INBOUND = 64                 # cap inbound connections (connection-flood DoS)
MAX_KNOWN_ADDRS = 1024           # cap the gossiped peer table (addr-flood / poisoning)
MAX_OUTBOUND_PER_GROUP = 2       # cap outbound dials per /16 (anti-eclipse: not all peers in one subnet)
PEERS_SAVE_INTERVAL = 60.0       # persist the peer table this often (+ on stop)
RESYNC_INTERVAL = 30.0           # self-healing sync watchdog: `getblocks` is otherwise sent only at
                                 # handshake and on an orphan, so a node that ends up with a gap (orphans
                                 # it can't connect, or a tip that stops advancing while peers are present)
                                 # would sit stuck forever. Re-request the chain this often; a no-op once
                                 # caught up (the peer's blocks_after returns nothing).
MSG_RATE_MAX = 5000              # per-peer messages allowed per window (flood); high enough that a
                                 # legitimate initial-block-download burst isn't throttled
MSG_RATE_WINDOW = 10.0           # seconds


# ---- addr codec (NEW-EXP: [count:2][ len:1 host port:2 ]*) --------------------
def encode_addrs(addrs) -> bytes:
    out = len(addrs).to_bytes(2, "little")
    for host, port in addrs:
        hb = host.encode("ascii", "ignore")[:255]
        out += bytes([len(hb)]) + hb + int(port).to_bytes(2, "little")
    return out


CADDRESS_LEN = 26                        # nServices8 + pchReserved12 + ip4 + port2
_PCH_IPV4 = b"\x00" * 10 + b"\xff\xff"   # what every v0.1 CAddress constructor memcpy's in


def _is_ipv4(host: str) -> bool:
    parts = host.split(".")
    return len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)


def encode_addrs_v01(addrs) -> bytes:
    """v0.1's `addr` body: a compact_size-prefixed vector<CAddress>.

    CAddress (net.h): `uint64 nServices | uchar pchReserved[12] | uint ip | ushort port`.
    Bitcoin writes integers little-endian, but `ip` and `port` already hold NETWORK byte order
    (they come from inet_addr/htons), so writing that value little-endian puts the dotted quad
    back on the wire in order and the port big-endian.

    `ip` is 32 bits, so **v0.1 cannot express an IPv6 peer at all** -- v6 addresses are dropped
    rather than encoded, and the count reflects what is actually emitted."""
    v4 = [(h, p) for h, p in addrs if _is_ipv4(h)]
    out = compact_size(len(v4))
    for host, port in v4:
        out += (_le(1, 8) + _PCH_IPV4 + socket.inet_aton(host)
                + int(port).to_bytes(2, "big"))
    return out


def decode_addrs_v01(payload: bytes):
    n, i = read_compact(payload, 0)
    out = []
    for _ in range(min(n, 1000)):
        if i + CADDRESS_LEN > len(payload):
            break
        host = socket.inet_ntoa(payload[i + 20:i + 24])
        port = int.from_bytes(payload[i + 24:i + 26], "big")
        i += CADDRESS_LEN
        if 0 < port < 65536:
            out.append((host, port))
    return out


def decode_addrs(payload: bytes):
    n = int.from_bytes(payload[:2], "little")
    i, out = 2, []
    for _ in range(min(n, 1000)):
        if i + 1 > len(payload):
            break
        ln = payload[i]; i += 1
        host = payload[i:i + ln].decode("ascii", "replace"); i += ln
        port = int.from_bytes(payload[i:i + 2], "little"); i += 2
        if host and 0 < port < 65536:
            out.append((host, port))
    return out


class Node:
    def __init__(self, cfg: ChainConfig, datadir, *, listen=None, advertise_host=None,
                 mine=False, mine_interval: float = 2.0, max_peers: int = MAX_PEERS,
                 max_inbound: int = MAX_INBOUND, max_known_addrs: int = MAX_KNOWN_ADDRS,
                 maturity: int = COINBASE_MATURITY, min_bits: int | None = None,
                 wallet: bool = False, resync_interval: float = RESYNC_INTERVAL, log=None):
        self.cfg = cfg
        self.datadir = pathlib.Path(datadir)
        self.store = BlockStore(datadir)
        self.chain = cfg.new_chain()
        self.listen = listen                         # (host, port) or None
        self.advertise_host = advertise_host
        self.mine = mine
        self.mine_interval = mine_interval
        self.resync_interval = resync_interval
        self.max_peers = max_peers
        self.max_inbound = max_inbound
        self.max_known_addrs = max_known_addrs
        self.min_bits = min_bits                         # difficulty floor (None -> easy genesis)
        self._log = log or (lambda m: None)
        self._writers: set[asyncio.StreamWriter] = set()
        self._tasks: list[asyncio.Task] = []
        self._server = None
        self._closing = False
        self._inbound_count = 0
        self.port = None
        self.advertise = None                        # our own dialable (host, port), if listening
        self._self_ids: set[tuple[str, int]] = set()  # every (addr, port) form that is us
        self.peers = PeerDB(max_addrs=max_known_addrs)   # persisted, diversity-aware peer table
        self._peers_path = self.datadir / "peers.json"
        self.peers.load(self._peers_path)            # remember peers across restarts
        self._dialing: set[tuple[str, int]] = set()  # outbound addrs in flight (dedup + self)
        self._load_or_init()
        self.state = ChainState(self.chain, cfg.rules, maturity=maturity, min_bits=min_bits)  # validated UTXO chainstate
        self.state.activate_best()                       # validate + build the UTXO from the loaded chain
        self.mempool = Mempool(maturity=maturity)        # not-yet-mined transactions (policy)
        self.wallet = NodeWallet(self.datadir / "wallet.json") if wallet else None

    @property
    def known_addrs(self) -> set:
        """All peers we know (tried + gossiped) — for gossip, discovery, and status."""
        return self.peers.addrs()

    def _learn_addr(self, addr) -> bool:
        """Record a gossiped peer, bounded per-/16 and in total (anti-eclipse). Returns True if new."""
        if addr == self.advertise:
            return False
        return self.peers.add(addr)

    # -- persistence / genesis -------------------------------------------------
    def _load_or_init(self):
        raws = self.store.read_all()
        if raws:
            self.chain.add_genesis(raws[0], nbits_of(raws[0]))
            for raw in raws[1:]:
                self.chain.process_block(raw)
            self._log(f"loaded {len(raws)} block(s); height={self.chain.best_height}")
        else:
            g = self.cfg.mint_genesis()
            self.chain.add_genesis(g, nbits_of(g))
            self.store.append(g)
            self._log(f"minted genesis {block_hash(g)[::-1].hex()[:16]}…")

    @property
    def height(self) -> int:
        return self.state.height                         # the VALIDATED tip, not chainsync's PoW tip

    @property
    def tip(self) -> bytes:
        return self.state.tip

    def recent_blocks(self, count: int = 15) -> list:
        """Summaries of the last `count` validated main-chain blocks (newest first) — for a status
        page / lightweight explorer. Read-only, derived from the validated active chain."""
        from chainsync import read_compact
        out = []
        for h in self.state.active[-count:][::-1]:
            idx = self.chain.by_hash[h]
            raw = idx.raw
            ntime = int.from_bytes(raw[68:72], "little")
            try:
                ntx, _ = read_compact(raw, 80)
            except (IndexError, ValueError):
                ntx = 0
            out.append({"height": idx.height, "hash": h[::-1].hex(),
                        "time": ntime, "ntx": int(ntx), "bytes": len(raw)})
        return out

    def submit_tx(self, raw: bytes):
        """Validate a raw transaction into the local mempool (against the validated UTXO).
        Returns the accepted `mempool.Entry`; raises `MempoolReject` if it fails validation."""
        return self.mempool.accept(raw, self.state.utxo, self.state.height)

    async def accept_and_broadcast(self, raw: bytes):
        """Validate a raw transaction into the mempool and relay it to peers (inv → getdata → tx) —
        the exact submit path a peer's transaction takes. Used by the wallet's payment builder and by
        the `sendrawtransaction` RPC. Returns the accepted `mempool.Entry`; raises on invalid tx."""
        entry = self.submit_tx(raw)
        await self._announce([(MSG_TX, entry.txid)])
        return entry

    # -- wallet (present only when the node is started with a wallet) -----------
    def wallet_new_address(self) -> bytes:
        return self.wallet.new_address()

    def wallet_primary_pubkey(self) -> bytes:
        """The wallet's primary receive pubkey — no new key is minted."""
        return self.wallet.primary_pubkey()

    def wallet_balance(self) -> int:
        return self.wallet.balance(self.state.utxo, self.state.height, self.state.maturity)

    async def wallet_send(self, to_pubkey: bytes, amount: int, fee: int = 0):
        """Build + sign a bare-P2PK payment, submit it to the mempool, and broadcast it."""
        from wallet import p2pk
        return await self.wallet_send_to_script(p2pk(bytes(to_pubkey)), amount, fee)

    async def wallet_send_to_script(self, recipient_spk: list, amount: int, fee: int = 0):
        """Build + sign a payment to an arbitrary recipient scriptPubKey (P2PK or P2PKH) against the
        validated UTXO, submit it to the mempool, and broadcast it. Returns the `mempool.Entry`."""
        raw = self.wallet.create_payment_to_script(self.state.utxo, self.state.height,
                                                   self.state.maturity, recipient_spk, amount, fee)
        return await self.accept_and_broadcast(raw)

    # -- lifecycle -------------------------------------------------------------
    async def start(self, connect=()):
        if self.listen:
            # `::` (from --listen [::]:PORT) binds every interface in both families -- asyncio opens
            # one socket per family, so the node is reachable over IPv4 and IPv6 at once. `0.0.0.0`
            # stays IPv4-only, so existing deployments are unchanged unless they ask for dual-stack.
            bind = self.listen[0]
            dual = bind in ("::", "*")
            self._server = await asyncio.start_server(
                self._inbound, None if dual else bind, self.listen[1])
            self.port = self._server.sockets[0].getsockname()[1]
            host = self.advertise_host or (bind if bind not in ("0.0.0.0", "::", "*", "") else None)
            if host:
                self.advertise = (host, self.port)
                # Peers gossip us by whatever form they dialled -- a hostname as readily as an IP.
                # Comparing only the advertised string lets `seed.example:PORT` past the self-check
                # and the node dials itself, burning an outbound slot. Resolve once and remember
                # every form that is us.
                self._self_ids = {self.advertise}
                try:
                    for info in await asyncio.get_running_loop().getaddrinfo(
                            host, self.port, type=socket.SOCK_STREAM):
                        self._self_ids.add((info[4][0], self.port))
                except OSError:
                    pass
            fams = {s.family.name for s in self._server.sockets}
            self._log(f"listening on {bind}:{self.port}" + (f" ({'+'.join(sorted(fams))})" if dual else ""))
        for host, port in connect:
            self._dial(host, port)
        for host, port in self.peers.sample(self.max_peers, exclude=set(connect),
                                            per_group=MAX_OUTBOUND_PER_GROUP):
            self._dial(host, port)               # re-mesh from remembered peers (persisted DB)
        self._tasks.append(asyncio.create_task(self._peers_save_loop()))
        self._tasks.append(asyncio.create_task(self._resync_loop()))
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
        self._save_peers()                           # persist the peer table for next start

    # -- connections -----------------------------------------------------------
    def _dial(self, host, port):
        addr = (host, int(port))
        if addr == self.advertise or addr in self._dialing or len(self._dialing) >= self.max_peers:
            return
        if not (host == "localhost" or host.startswith("127.") or host == "::1"):
            g = group_of(host)                       # anti-eclipse: cap outbound per /16 (routable only)
            if sum(1 for d in self._dialing if group_of(d[0]) == g) >= MAX_OUTBOUND_PER_GROUP:
                return
        self._dialing.add(addr)
        self._tasks.append(asyncio.create_task(self._outbound(host, int(port))))

    async def _inbound(self, reader, writer):
        if self._inbound_count >= self.max_inbound:      # connection-flood cap
            writer.close()
            return
        self._inbound_count += 1
        try:
            await self._session(reader, writer, initiate=False)
        finally:
            self._inbound_count -= 1

    async def _is_self(self, host, port) -> bool:
        """True if (host, port) resolves to us -- catches the hostname form of our own address."""
        if not self._self_ids:
            return False
        if (host, int(port)) in self._self_ids:
            return True
        try:
            infos = await asyncio.get_running_loop().getaddrinfo(
                host, int(port), type=socket.SOCK_STREAM)
        except OSError:
            return False
        return any((i[4][0], int(port)) in self._self_ids for i in infos)

    async def _outbound(self, host, port):
        try:
            if await self._is_self(host, port):
                self._log(f"not dialling {host}:{port} — that is us")
                return
            while not self._closing:
                try:
                    reader, writer = await asyncio.open_connection(host, port)
                    self._log(f"connected out to {host}:{port}")
                    self.peers.mark_good((host, int(port)))   # promote to 'tried' (preferred later)
                    await self._session(reader, writer, initiate=True)
                except (OSError, WireError) as e:
                    self._log(f"outbound {host}:{port}: {e}")
                if self._closing:
                    return
                await asyncio.sleep(RECONNECT_BACKOFF)
        finally:
            self._dialing.discard((host, int(port)))

    def _enc_addrs(self, addrs):
        """v0.1's vector<CAddress> for the Bitcoin chain, netnode's own form for the X-chains."""
        return (encode_addrs_v01 if self.cfg.addr_v01 else encode_addrs)(addrs)

    def _dec_addrs(self, payload):
        return (decode_addrs_v01 if self.cfg.addr_v01 else decode_addrs)(payload)

    async def _send(self, writer, command, payload):
        writer.write(frame(command, payload, self.cfg.magic, checksum=self.cfg.wire_checksum))
        await writer.drain()

    async def _announce(self, items, exclude=None):
        for w in list(self._writers):
            if w is exclude:
                continue
            try:
                await self._send(w, "inv", inv_payload(items))
            except (WireError, ConnectionError, OSError):
                pass

    def _addr_sample(self):
        addrs = [self.advertise] if self.advertise else []
        addrs += self.peers.sample(MAX_ADDRS_PER_MSG - len(addrs), exclude=addrs,
                                   per_group=max(2, MAX_ADDRS_PER_MSG // 4))
        return addrs[:MAX_ADDRS_PER_MSG]

    def _save_peers(self):
        try:
            self.peers.save(self._peers_path)
        except OSError as e:
            self._log(f"peers save failed: {e}")

    async def _peers_save_loop(self):
        try:
            while not self._closing:
                await asyncio.sleep(PEERS_SAVE_INTERVAL)
                self._save_peers()
        except asyncio.CancelledError:
            pass

    async def _resync_loop(self):
        """Self-healing sync watchdog. If, over one interval, the validated tip has not advanced
        while peers are connected, or the chain is holding orphan blocks it could not connect,
        re-request the chain from every peer so a stuck node recovers on its own instead of sitting
        on a gap forever. Once caught up this is a no-op (the peer's `blocks_after` returns nothing)."""
        try:
            last_height = self.height
            while not self._closing:
                await asyncio.sleep(self.resync_interval)
                if not self._writers:                        # no peer to ask
                    last_height = self.height
                    continue
                stalled = self.height == last_height         # no validated progress this window
                gapped = bool(self.chain.orphans)            # received blocks we could not connect
                if stalled or gapped:
                    loc = locator_payload(self.state.get_locator())
                    for w in list(self._writers):
                        try:
                            await self._send(w, "getblocks", loc)
                        except (WireError, ConnectionError, OSError):
                            pass
                last_height = self.height
        except asyncio.CancelledError:
            pass

    # -- one peer session ------------------------------------------------------
    async def _session(self, reader, writer, initiate):
        self._writers.add(writer)
        misbehavior = 0
        loop = asyncio.get_event_loop()
        window_start, msgs = loop.time(), 0
        try:
            await self._send(writer, "version", version_payload())
            while not self._closing:
                command, payload = await read_message(reader, self.cfg.magic,
                                                      checksum=self.cfg.wire_checksum)
                now = loop.time()                        # per-peer message rate limit (flood)
                if now - window_start >= MSG_RATE_WINDOW:
                    window_start, msgs = now, 0
                msgs += 1
                if msgs > MSG_RATE_MAX:
                    raise WireError("rate limit exceeded")
                if command == "version":
                    if initiate:
                        await self._send(writer, "getblocks",
                                         locator_payload(self.state.get_locator()))
                    sample = self._addr_sample()
                    if sample:
                        await self._send(writer, "addr", self._enc_addrs(sample))
                elif command == "addr":
                    fresh = []
                    for host, port in self._dec_addrs(payload):
                        if self._learn_addr((host, port)):   # bounded peer table
                            fresh.append((host, port))
                        self._dial(host, port)       # auto-connect (capped, dedup, non-self)
                    if fresh:                        # gossip newly-learned peers onward
                        for w in list(self._writers):
                            if w is writer:
                                continue
                            try:
                                await self._send(w, "addr", self._enc_addrs(fresh))
                            except (WireError, ConnectionError, OSError):
                                pass
                elif command == "getblocks":
                    have, hash_stop = parse_getblocks(payload)
                    invs = self.state.blocks_after(have, hash_stop)
                    if invs:
                        await self._send(writer, "inv",
                                         inv_payload([(MSG_BLOCK, h) for h in invs]))
                elif command == "inv":
                    want = []
                    for typ, h in parse_inv(payload):
                        if typ == MSG_BLOCK and not self.chain.have(MSG_BLOCK, h):
                            want.append((typ, h))
                        elif typ == MSG_TX and not self.mempool.has(h):
                            want.append((typ, h))
                    if want:
                        await self._send(writer, "getdata", inv_payload(want))
                elif command == "getdata":
                    for typ, h in parse_inv(payload):
                        if typ == MSG_BLOCK and h in self.chain.by_hash:
                            await self._send(writer, "block", self.chain.by_hash[h].raw)
                        elif typ == MSG_TX:
                            raw = self.mempool.get(h)
                            if raw is not None:
                                await self._send(writer, "tx", raw)
                elif command == "tx":
                    misbehavior += await self._on_tx(payload, writer)
                    if misbehavior >= BAN_THRESHOLD:
                        raise WireError("peer banned (misbehavior)")
                elif command == "block":
                    misbehavior += await self._on_block(payload, writer)
                    if misbehavior >= BAN_THRESHOLD:
                        raise WireError("peer banned (misbehavior)")
                else:
                    misbehavior += 1
        except (WireError, ConnectionError, OSError) as e:
            self._log(f"peer dropped: {e}")
        except Exception as e:      # malformed/adversarial payload (bad parse) — drop the peer, never crash the node
            self._log(f"peer dropped (bad message): {e!r}")
        finally:
            self._writers.discard(writer)
            try:
                writer.close()
            except OSError:
                pass

    async def _on_tx(self, raw: bytes, origin) -> int:
        txid = dsha256(raw)
        if self.mempool.has(txid):
            return 0                                  # already pooled — don't re-relay (loop guard)
        try:
            entry, promoted = self.mempool.accept_or_orphan(raw, self.state.utxo, self.state.height)
        except MempoolReject as e:                    # provably invalid (not merely missing a parent)
            self._log(f"reject tx: {e}")
            return 1
        if entry is None:
            return 0                                  # buffered as an orphan (parent not yet seen)
        items = [(MSG_TX, entry.txid)] + [(MSG_TX, e.txid) for e in promoted]  # relay it + any it unblocked
        await self._announce(items, exclude=origin)
        return 0

    async def _on_block(self, raw: bytes, origin) -> int:
        ok, reason = validate_block(raw, self.chain, self.cfg.rules, self.min_bits)  # context-free (struct/merkle/difficulty)
        if not ok:
            self._log(f"reject block: {reason}")
            return 5
        status, h = self.chain.process_block(raw)
        if status in ("accepted", "orphan"):
            self.store.append(raw)
        if status == "accepted":
            self.state.activate_best()               # full UTXO/tx validation of the active chain
            if h in self.state.invalid:              # indexed by PoW but fails full validity
                self._log(f"block {h[::-1].hex()[:12]} failed full validation")
                return 5
            self.mempool.reconcile(self.state.utxo, self.state.height)   # drop mined/conflicting txs
            await self._announce([(MSG_BLOCK, h)], exclude=origin)
            return 0
        if status == "orphan":
            root = self.chain.get_orphan_root(h)
            await self._send(origin, "getblocks",
                             locator_payload(self.state.get_locator(), root))
            return 0
        return 5 if status == "invalid" else 0

    # -- mining ----------------------------------------------------------------
    async def _mine_loop(self):
        loop = asyncio.get_event_loop()
        while not self._closing:
            prev, height = self.tip, self.height + 1
            nbits = expected_bits(self.chain, prev, self.cfg.rules, self.min_bits)   # retarget, floored
            subsidy = self.cfg.rules.get_block_value(self.height)       # coinbase claims subsidy + fees
            selected = self.mempool.select(self.state.utxo)             # pool txs, parents before children
            fees = sum(e.fee for e in selected)
            extra = [e.tx for e in selected]
            payout = self.wallet.receive_script() if self.wallet else b"\x51"   # earn to the wallet, if any
            raw = await loop.run_in_executor(None, mine_block, prev, height, nbits,
                                             self.chain.check_block, subsidy + fees, extra,
                                             self.cfg.genesis_msg[:0], payout)
            status, h = self.chain.process_block(raw)
            if status == "accepted":
                self.store.append(raw)
                self.state.activate_best()                             # keep the UTXO current
                self.mempool.reconcile(self.state.utxo, self.state.height)   # remove the txs we just mined
                self._log(f"mined {h[::-1].hex()[:12]} height={self.state.height} "
                          f"nBits={nbits} txs={len(extra)}")
                await self._announce([(MSG_BLOCK, h)])
            await asyncio.sleep(self.mine_interval)
