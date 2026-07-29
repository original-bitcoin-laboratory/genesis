"""A validated UTXO chainstate — Path B toward a production node (part 2).

Layered over the chainsync block index (PoW tree), this maintains the **active, fully‑validated
chain** and its **UTXO set**, with reorg‑safe **connect / disconnect** (undo data per block) and
`activate_best`, which moves the validated chain toward the index's best chain — **gating every
step on full validity** and rolling back (restoring the prior chain) if a branch fails to validate.

Per block it enforces, on top of the structural/PoW checks (`fullnode.validate_block`):
- **difficulty** — `nBits` equals the expected retarget for the parent (floored at `min_bits`).
  Because this authoritative gate runs on *connect*, it also covers the **orphan reconnection
  path**, where the direct‑receipt difficulty check is deferred (parent not yet known),
- every input exists in the UTXO (no missing / double‑spent coins),
- coinbase maturity (`COINBASE_MATURITY`),
- the input script satisfies the referenced output's script (the v0.1 `VerifySignature` path,
  full vocabulary — via `model/spend.verify_spend`),
- no inflation (Σ inputs ≥ Σ outputs), and
- the chain's coinbase‑value rule with fees (`Rules.coinbase_ok`).

Same‑block spends (a later tx spending an earlier tx's output) are handled, and the undo nets
them out. Evidence: MODEL / NEW‑EXP.
"""

from __future__ import annotations

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
for _p in ("model", "p2p", "nov08x"):
    sys.path.insert(0, str(_HERE.parent / _p))
sys.path.insert(0, str(_HERE))

import cscript                                              # noqa: E402

from difficulty import expected_bits                       # noqa: E402
from fastverify import verify_spend_fast                    # noqa: E402  (== faithful verify_spend, accelerated)
from fullnode import is_coinbase, parse_block_with_txids   # noqa: E402

COINBASE_MATURITY = 100


class InvalidBlock(Exception):
    pass


class Coin:
    __slots__ = ("value", "spk", "height", "coinbase")

    def __init__(self, value, spk, height, coinbase):
        self.value, self.spk, self.height, self.coinbase = value, spk, height, coinbase


class ChainState:
    def __init__(self, chain, rules, maturity: int = COINBASE_MATURITY, min_bits: int | None = None,
                 reopen=frozenset()):
        self.chain = chain
        self.rules = rules
        self.maturity = maturity
        self.min_bits = min_bits                            # difficulty floor (None -> genesis nBits)
        self.reopen = frozenset(reopen)                     # script posture: {} faithful | {'OP_NOTEQUAL'} nothing-disabled
        self.utxo: dict[tuple[bytes, int], Coin] = {}
        self.active: list[bytes] = []                       # genesis .. validated tip
        self.undo: dict[bytes, tuple[list, list]] = {}      # block -> (spent_prior, created_keys)
        self.invalid: set[bytes] = set()
        if chain.genesis is not None:
            self._connect(chain.genesis)                    # genesis coinbase seeds the UTXO

    # -- queries ---------------------------------------------------------------
    @property
    def tip(self) -> bytes | None:
        return self.active[-1] if self.active else None

    @property
    def height(self) -> int:
        return self.chain.by_hash[self.active[-1]].height if self.active else -1

    def balance(self) -> int:
        return sum(c.value for c in self.utxo.values())

    # -- locator / serving over the VALIDATED chain (authoritative) -------------
    def get_locator(self) -> list[bytes]:
        have, i, step = [], len(self.active) - 1, 1
        while i >= 0:
            have.append(self.active[i])
            i -= step
            if len(have) > 10:
                step *= 2
        if self.active and have[-1] != self.active[0]:
            have.append(self.active[0])
        return have

    def blocks_after(self, have, hash_stop) -> list[bytes]:
        pos = {h: k for k, h in enumerate(self.active)}
        start = max((pos[h] for h in have if h in pos), default=0)
        out = []
        for h in self.active[start + 1:]:
            if h == hash_stop:
                break
            out.append(h)
        return out

    # -- connect / disconnect --------------------------------------------------
    def _connect(self, h: bytes):
        idx = self.chain.by_hash[h]
        height = idx.height
        txs = parse_block_with_txids(idx.raw)                # [(tx, txid)] — txid from parsed bytes
        is_genesis = h == self.chain.genesis
        if not is_genesis and idx.nBits != expected_bits(self.chain, idx.prev, self.rules, self.min_bits):
            raise InvalidBlock("wrong difficulty")           # authoritative — also covers orphan reconnection
        created: dict[tuple[bytes, int], Coin] = {}          # block-created outputs still live
        spent_prior: list = []                               # (outpoint, coin) pre-block coins consumed
        fees = 0
        try:
            for tx, tid in txs:
                coinbase = is_coinbase(tx)
                if not coinbase:
                    value_in = 0
                    for i, vin in enumerate(tx.vin):
                        key = (vin.prevhash, vin.n)
                        coin = self.utxo.get(key)
                        if coin is None:
                            raise InvalidBlock("input missing or already spent")
                        if coin.coinbase and height - coin.height < self.maturity:
                            raise InvalidBlock("immature coinbase spend")
                        if not verify_spend_fast(cscript.parse(vin.script), coin.spk, tx, i, reopen=self.reopen):
                            raise InvalidBlock("input script does not satisfy output")
                        value_in += coin.value
                        del self.utxo[key]
                        if key in created:
                            del created[key]                 # same-block output consumed -> nets out
                        else:
                            spent_prior.append((key, coin))
                    value_out = sum(o.value for o in tx.vout)
                    if value_in < value_out:
                        raise InvalidBlock("inflation (inputs < outputs)")
                    fees += value_in - value_out
                for n, o in enumerate(tx.vout):
                    k = (tid, n)
                    c = Coin(o.value, cscript.parse(o.script), height, coinbase)
                    self.utxo[k] = c
                    created[k] = c
            if not is_genesis:
                subsidy = self.rules.get_block_value(height - 1)
                claimed = sum(o.value for o in txs[0][0].vout)
                if not self.rules.coinbase_ok(claimed, subsidy + fees):
                    raise InvalidBlock("coinbase value violates the chain rule")
        except InvalidBlock:                                 # atomic: revert partial mutations
            for k in created:
                self.utxo.pop(k, None)
            for key, coin in reversed(spent_prior):
                self.utxo[key] = coin
            raise
        self.undo[h] = (spent_prior, list(created.keys()))
        self.active.append(h)

    def _disconnect(self):
        h = self.active.pop()
        spent_prior, created_keys = self.undo.pop(h)
        for k in created_keys:
            self.utxo.pop(k, None)
        for key, coin in spent_prior:
            self.utxo[key] = coin

    # -- activate the best VALID chain (reorg-safe, gated on validity) ---------
    def activate_best(self):
        target = self.chain.main_chain()                    # the index's best-by-work chain
        if self.active and self.active[-1] == target[-1]:
            return
        old_active = list(self.active)
        old_height = self.height
        fork = 0
        while (fork < len(old_active) and fork < len(target)
               and old_active[fork] == target[fork]):
            fork += 1
        while len(self.active) > fork:                       # disconnect down to the fork
            self._disconnect()
        for h in target[fork:]:                              # connect the new branch, validating
            if h in self.invalid:
                break
            try:
                self._connect(h)
            except InvalidBlock:
                self.invalid.add(h)
                break
        if self.height <= old_height and self.active != old_active:
            while len(self.active) > fork:                   # reorg didn't improve -> restore old chain
                self._disconnect()
            for h in old_active[fork:]:
                self._connect(h)                             # previously valid -> reconnects
