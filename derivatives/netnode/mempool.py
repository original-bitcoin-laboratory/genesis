"""A validating transaction mempool + block assembly — Path B toward a production node (part 3).

With a validated UTXO chainstate in hand (`chainstate.ChainState`), a node can carry **real
transactions**, not just coinbases. This module is the pool of not‑yet‑mined transactions and the
selector that assembles them into a block:

- `accept(raw, utxo, height)` validates a candidate transaction against the confirmed UTXO **and
  the transactions already in the pool** (so a chain of unconfirmed spends is allowed), enforcing
  the same value rules the chainstate does on connect — every input exists and is unspent, no
  in‑pool double‑spend, coinbase maturity, the input script satisfies the referenced output (the
  v0.1 `VerifySignature` path, full vocabulary), and no inflation — and records the **fee**.
- `select(utxo, ...)` returns a **topologically‑ordered** batch (parents before children) whose
  inputs are all available, for the miner to place after the coinbase.
- `reconcile(utxo, height)` re‑validates the pool against a freshly‑advanced (or reorged)
  chainstate, dropping transactions that were mined or are no longer valid.

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


class MempoolReject(Exception):
    pass


class Entry:
    __slots__ = ("tx", "raw", "txid", "fee", "size")

    def __init__(self, tx, raw, txid, fee):
        self.tx, self.raw, self.txid, self.fee, self.size = tx, raw, txid, fee, len(raw)


class Mempool:
    def __init__(self, max_txs: int = MAX_POOL_TXS, maturity: int = COINBASE_MATURITY):
        self.max_txs = max_txs
        self.maturity = maturity                            # must match the chainstate's (consensus)
        self.txs: dict[bytes, Entry] = {}                   # txid -> Entry (insertion = topo order)
        self.spent: dict[tuple[bytes, int], bytes] = {}     # outpoint -> spending txid (in pool)

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

    # -- accept a candidate transaction ---------------------------------------------------------
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
        if len(self.txs) >= self.max_txs:
            raise MempoolReject("mempool full")
        value_in = 0
        seen = set()
        for i, vin in enumerate(tx.vin):
            key = (vin.prevhash, vin.n)
            if key in seen:
                raise MempoolReject("duplicate input within the transaction")
            seen.add(key)
            if key in self.spent:
                raise MempoolReject("conflicts with a pooled transaction (double-spend)")
            coin = self._coin_for(key, utxo)
            if coin is None:
                raise MempoolReject("input missing or already spent")
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
        self.txs[txid] = entry
        for vin in tx.vin:
            self.spent[(vin.prevhash, vin.n)] = txid
        return entry

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
