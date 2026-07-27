"""A validating transaction mempool + block assembly — Path B toward a production node (parts 3–4).

With a validated UTXO chainstate in hand (`chainstate.ChainState`), a node can carry **real
transactions**, not just coinbases. This module is the pool of not‑yet‑mined transactions and the
selector that assembles them into a block:

- `accept(raw, utxo, height)` validates a candidate transaction against the confirmed UTXO **and
  the transactions already in the pool** (so a chain of unconfirmed spends is allowed), enforcing
  the same value rules the chainstate does on connect — every input exists and is unspent, no
  in‑pool double‑spend, coinbase maturity, the input script satisfies the referenced output (the
  v0.1 `VerifySignature` path, full vocabulary), and no inflation — and records the **fee**.
- `accept_or_orphan(...)` is the relay entry point: a transaction that arrives **before the parent
  it spends** (missing inputs) is held in a bounded **orphan buffer** and retried when a parent is
  later accepted, rather than dropped (Stage 4).
- `select(utxo, ...)` returns a **topologically‑ordered** batch (parents before children) whose
  inputs are all available, for the miner to place after the coinbase.
- `reconcile(utxo, height)` re‑validates the pool against a freshly‑advanced (or reorged)
  chainstate, dropping transactions that were mined or are no longer valid, and retrying orphans
  whose parents may now be confirmed.

When the pool is full, a new transaction can **evict the lowest fee‑rate childless entry** if it
pays a higher fee rate (Stage 4) — otherwise the pool would simply refuse newcomers forever.

The pool is **policy, not consensus** (NEW‑EXP): what a node chooses to relay/assemble. Consensus
still lives in `ChainState._connect`, which re‑checks every rule when the block actually connects —
the mempool never lets an invalid transaction into the validated chain, it only avoids relaying or
mining ones it can already tell are invalid. **Not money.** Evidence: MODEL / NEW‑EXP.
"""

from __future__ import annotations

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
for _p in ("model", "p2p", "nov08x"):
    sys.path.insert(0, str(_HERE.parent / _p))
sys.path.insert(0, str(_HERE))

import cscript                                              # noqa: E402
from spend import verify_spend                             # noqa: E402
from tx_sighash import dsha256                             # noqa: E402

from chainstate import Coin, COINBASE_MATURITY             # noqa: E402
from fullnode import is_coinbase, parse_tx                 # noqa: E402

MAX_POOL_TXS = 50_000            # bound the pool (memory DoS) — policy, not consensus
MAX_BLOCK_TXS = 4_000            # how many pool txs the miner will place after the coinbase (policy)
MAX_ORPHAN_TXS = 1_000           # bound the orphan (missing-parent) buffer (memory DoS)


class MempoolReject(Exception):
    pass


class MissingInputs(MempoolReject):
    """Inputs reference outpoints not (yet) in the UTXO or the pool — may be an orphan."""

    def __init__(self, parents):
        super().__init__("input missing or already spent")
        self.parents = parents                              # candidate parent txids to wait on


class Entry:
    __slots__ = ("tx", "raw", "txid", "fee", "size")

    def __init__(self, tx, raw, txid, fee):
        self.tx, self.raw, self.txid, self.fee, self.size = tx, raw, txid, fee, len(raw)

    def fee_rate(self) -> float:
        return self.fee / self.size


class Mempool:
    def __init__(self, max_txs: int = MAX_POOL_TXS, maturity: int = COINBASE_MATURITY):
        self.max_txs = max_txs
        self.maturity = maturity                            # must match the chainstate's (consensus)
        self.txs: dict[bytes, Entry] = {}                   # txid -> Entry (insertion = topo order)
        self.spent: dict[tuple[bytes, int], bytes] = {}     # outpoint -> spending txid (in pool)
        self.orphans: dict[bytes, bytes] = {}               # txid -> raw (inputs not yet available)
        self.waiting: dict[bytes, set[bytes]] = {}          # parent txid -> orphan txids waiting on it

    def has(self, txid: bytes) -> bool:
        return txid in self.txs

    def get(self, txid: bytes):
        e = self.txs.get(txid)
        return e.raw if e is not None else None

    def __len__(self) -> int:
        return len(self.txs)

    # -- outpoint lookup: confirmed UTXO, else an output created by an in-pool parent ----------
    def _coin_for(self, key, utxo):
        coin = utxo.get(key)
        if coin is not None:
            return coin
        ptxid, n = key
        parent = self.txs.get(ptxid)
        if parent is not None and 0 <= n < len(parent.tx.vout):
            o = parent.tx.vout[n]
            return Coin(o.value, cscript.parse(o.script), -1, False)   # unconfirmed, non-coinbase
        return None

    # -- accept a candidate transaction (strict: missing inputs -> MissingInputs) ---------------
    def accept(self, raw: bytes, utxo, height: int) -> Entry:
        try:
            tx, off = parse_tx(raw, 0)
        except Exception as e:                              # noqa: BLE001
            raise MempoolReject("unparseable") from e
        if off != len(raw):
            raise MempoolReject("trailing bytes")
        txid = dsha256(raw)
        if txid in self.txs:
            return self.txs[txid]                           # idempotent (already pooled)
        if is_coinbase(tx):
            raise MempoolReject("coinbase is not a standalone transaction")
        if not tx.vin or not tx.vout:
            raise MempoolReject("no inputs or no outputs")
        seen = set()
        coins, missing = [], []
        for i, vin in enumerate(tx.vin):
            key = (vin.prevhash, vin.n)
            if key in seen:
                raise MempoolReject("duplicate input within the transaction")
            seen.add(key)
            if key in self.spent:
                raise MempoolReject("conflicts with a pooled transaction (double-spend)")
            coin = self._coin_for(key, utxo)
            if coin is None:
                missing.append(vin.prevhash)
            else:
                coins.append((i, vin, coin))
        if missing:
            raise MissingInputs(missing)                    # maybe an orphan — caller decides
        value_in = 0
        for i, vin, coin in coins:
            if coin.coinbase and coin.height >= 0 and height - coin.height < self.maturity:
                raise MempoolReject("immature coinbase spend")
            if not verify_spend(cscript.parse(vin.script), coin.spk, tx, i):
                raise MempoolReject("input script does not satisfy the output")
            value_in += coin.value
        if any(o.value < 0 for o in tx.vout):
            raise MempoolReject("negative output value")
        value_out = sum(o.value for o in tx.vout)
        if value_in < value_out:
            raise MempoolReject("inflation (inputs < outputs)")
        entry = Entry(tx, raw, txid, value_in - value_out)
        if len(self.txs) >= self.max_txs and not self._make_room(entry):
            raise MempoolReject("mempool full (fee rate too low to evict)")
        self.txs[txid] = entry
        for vin in tx.vin:
            self.spent[(vin.prevhash, vin.n)] = txid
        return entry

    # -- relay entry point: hold missing-parent txs as orphans, retry on parent arrival ---------
    def accept_or_orphan(self, raw: bytes, utxo, height: int):
        """Returns (entry_or_None, promoted): the accepted entry (None if buffered as an orphan)
        and the list of previously‑orphaned entries this arrival unblocked. Raises `MempoolReject`
        only for a *provably* invalid transaction (not for merely‑missing parents)."""
        txid = dsha256(raw)
        if txid in self.txs:
            return self.txs[txid], []
        try:
            entry = self.accept(raw, utxo, height)
        except MissingInputs as e:
            self._add_orphan(raw, txid, e.parents)
            return None, []
        return entry, self._promote_orphans(entry.txid, utxo, height)

    # -- assemble a topologically-ordered, self-consistent batch for a block --------------------
    def select(self, utxo, max_txs: int = MAX_BLOCK_TXS) -> list[Entry]:
        chosen: list[Entry] = []
        created: set[tuple[bytes, int]] = set()             # outpoints made available by chosen txs
        for e in self.txs.values():                         # insertion order = parents before children
            if len(chosen) >= max_txs:
                break
            if all((vin.prevhash, vin.n) in utxo or (vin.prevhash, vin.n) in created
                   for vin in e.tx.vin):
                chosen.append(e)
                created.update((e.txid, n) for n in range(len(e.tx.vout)))
        return chosen

    # -- drop specific txids (and free their spent-outpoint reservations) -----------------------
    def remove(self, txids) -> None:
        for txid in txids:
            e = self.txs.pop(txid, None)
            if e is not None:
                for vin in e.tx.vin:
                    self.spent.pop((vin.prevhash, vin.n), None)

    # -- re-validate the whole pool against a freshly advanced/reorged chainstate ---------------
    def reconcile(self, utxo, height: int) -> None:
        old = list(self.txs.values())                       # insertion (topological) order
        self.txs.clear()
        self.spent.clear()
        for e in old:
            try:
                self.accept(e.raw, utxo, height)            # mined / now-invalid txs quietly drop out
            except MempoolReject:
                pass
        for oid, oraw in list(self.orphans.items()):        # a parent may now be confirmed
            if oid in self.txs:
                self._drop_orphan(oid)
                continue
            try:
                self.accept(oraw, utxo, height)
            except MissingInputs:
                continue                                    # still waiting
            except MempoolReject:
                self._drop_orphan(oid)                      # now provably invalid
                continue
            self._drop_orphan(oid)

    # -- fee-rate eviction (only childless "leaf" entries, so no pooled child is orphaned) ------
    def _is_leaf(self, e: Entry) -> bool:
        return not any((e.txid, n) in self.spent for n in range(len(e.tx.vout)))

    def _make_room(self, newcomer: Entry) -> bool:
        while len(self.txs) >= self.max_txs:
            leaves = [e for e in self.txs.values() if self._is_leaf(e)]
            victim = min(leaves, key=Entry.fee_rate) if leaves else None
            if victim is None or victim.fee_rate() >= newcomer.fee_rate():
                return False                                # newcomer isn't worth more — refuse it
            self.remove([victim.txid])
        return True

    # -- orphan buffer ---------------------------------------------------------------------------
    def _add_orphan(self, raw: bytes, txid: bytes, parents) -> None:
        if txid in self.orphans:
            return
        if len(self.orphans) >= MAX_ORPHAN_TXS:
            self._drop_orphan(next(iter(self.orphans)))     # evict the oldest (bounded)
        self.orphans[txid] = raw
        for p in parents:
            self.waiting.setdefault(p, set()).add(txid)

    def _drop_orphan(self, txid: bytes) -> None:
        self.orphans.pop(txid, None)
        empty = []
        for p, waiters in self.waiting.items():
            waiters.discard(txid)
            if not waiters:
                empty.append(p)
        for p in empty:
            del self.waiting[p]

    def _promote_orphans(self, new_txid: bytes, utxo, height: int) -> list[Entry]:
        promoted: list[Entry] = []
        queue = [new_txid]
        for parent in queue:
            for oid in list(self.waiting.get(parent, ())):
                oraw = self.orphans.get(oid)
                if oraw is None:
                    continue
                try:
                    e = self.accept(oraw, utxo, height)
                except MissingInputs:
                    continue                                # still waiting on another parent
                except MempoolReject:
                    self._drop_orphan(oid)                  # now provably invalid
                    continue
                self._drop_orphan(oid)
                promoted.append(e)
                queue.append(e.txid)                        # its outputs may unblock further orphans
        return promoted
