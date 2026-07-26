"""NOV08-X — a headless node that actually runs November's constitution.

Reuses the lab's existing block plumbing (`derivatives/p2p/chainsync`: block
serialization, merkle root, double-SHA256) and drives it with the NOV08 `Rules`
(`consensus.py`) — NOV08 subsidy, NOV08 leading-zero-bits proof-of-work, and the
NOV08 exact-equality coinbase rule. Evidence level: MODEL.

This is NOV08-Minimal: the smallest thing that mines and validates a chain under the
surviving November rules, so the counterfactual can be observed, not just diffed.
"""

from __future__ import annotations

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "p2p"))
sys.path.insert(0, str(_HERE.parent / "model"))
from chainsync import ZERO, dsha256, merkle_root                       # noqa: E402
from tx_sighash import Tx, TxIn, TxOut, compact_size, serialize as ser_tx, _le  # noqa: E402
from consensus import Rules                                            # noqa: E402


def coinbase(height: int, value: int, tag: int = 0) -> Tx:
    t = Tx(1, [], [], 0)
    t.vin.append(TxIn(ZERO, 0xFFFFFFFF, bytes([2, height & 0xFF, tag & 0xFF]), 0xFFFFFFFF))
    t.vout.append(TxOut(value, b"\x51"))               # OP_1 placeholder scriptPubKey
    return t


class Nov08xNode:
    """A minimal NOV08-X chain: mine blocks whose coinbase pays exactly the NOV08
    block value, under NOV08 leading-zero-bits PoW, connecting only if the exact-
    equality coinbase rule holds."""

    def __init__(self, rules: Rules | None = None):
        self.rules = rules or Rules.load("nov08")
        self.blocks: list[dict] = []
        self.best_height = -1
        self.tip = ZERO

    def mine_and_add(self, nBits: int | None = None, fees: int = 0, tag: int = 0,
                     ntime: int = 1231006505, claim: int | None = None):
        """Mine + connect the next block. `claim` overrides the coinbase value to
        test the acceptance rule (default: pay exactly the block value)."""
        r = self.rules
        nBits = r.min_pow if nBits is None else nBits
        height = self.best_height + 1
        block_value = r.get_block_value(self.best_height, fees)   # global-best-height quirk (both editions)
        value = block_value if claim is None else claim
        vtx = [coinbase(height, value, tag)]
        mr = merkle_root(vtx)
        body = compact_size(len(vtx)) + b"".join(ser_tx(t) for t in vtx)
        prefix = _le(1, 4) + self.tip + mr + _le(ntime, 4) + _le(nBits, 4)   # 76B; nonce appended
        for nonce in range(1 << 28):
            header = prefix + _le(nonce, 4)
            h = dsha256(header)
            if r.pow_ok(h, nBits):
                raw = header + body
                if not r.coinbase_ok(value, block_value):        # ConnectBlock coinbase check
                    raise ValueError(
                        f"coinbase {r.fmt(value)} rejected: rule={r.coinbase_rule}, "
                        f"block_value={r.fmt(block_value)}")
                self.blocks.append({"hash": h, "height": height, "raw": raw,
                                    "nBits": nBits, "value": value, "nonce": nonce})
                self.tip = h
                self.best_height = height
                return self.blocks[-1]
        raise RuntimeError("no nonce found in range")

    def summary(self) -> str:
        r = self.rules
        lines = [f"NOV08-X chain — {len(self.blocks)} block(s), tip height {self.best_height}"]
        for b in self.blocks:
            lines.append(f"  h={b['height']:>3}  nBits={b['nBits']} (leading-zero bits)  "
                         f"reward={r.fmt(b['value'])}  nonce={b['nonce']}  "
                         f"hash={b['hash'][::-1].hex()[:16]}…")
        return "\n".join(lines)


if __name__ == "__main__":
    node = Nov08xNode()
    print(f"mining NOV08-X at difficulty nBits={node.rules.min_pow} "
          f"(MINPROOFOFWORK, 'ridiculously easy for testing')…")
    for _ in range(3):
        node.mine_and_add(tag=_)
    print(node.summary())
