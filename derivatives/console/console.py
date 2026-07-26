"""Full-stack console — drive a full-capability X-chain end to end (R7 capstone).

Ties the whole lab together on one object: a chain's `Rules` + the UTXO `Ledger`
(ConnectBlock) + the `Wallet` (CreateTransaction, real secp256k1) + the `studio`
tracer + the `market` commerce model. Mine, pay, lock a coin under a full-vocabulary
contract BTC cannot express, run a signed marketplace listing with reputation, and
export a deterministic evidence bundle — all under NOV08-X's *or* JAN09-X's
constitution (same driver, two profiles).

This is the assembled financial machine: NOV08-X run here is **NOV08-Full's**
executable form (see `common/nov08x/NOV08_FULL.md`), a counterfactual completion,
never recovered code. Evidence level: MODEL.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import random
import sys

_HERE = pathlib.Path(__file__).resolve().parent
for sub in ("model", "wallet", "nov08x", "ledger", "market", "studio"):
    sys.path.insert(0, str(_HERE.parent / sub))
from consensus import Rules                                              # noqa: E402
from ledger import Ledger, txid                                         # noqa: E402
from wallet import Wallet, p2pk                                         # noqa: E402
from cscript import assemble                                            # noqa: E402
from tx_sighash import Tx, TxIn, TxOut                                  # noqa: E402
from market_model import ReviewGraph, dsha256, make_product, make_review  # noqa: E402
from studio import render as trace_render                              # noqa: E402


def _sha256(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


def describe_spk(spk: list) -> str:
    if spk == ["OP_1"]:
        return "anyone-can-spend"
    if len(spk) == 2 and isinstance(spk[0], (bytes, bytearray)) and spk[1] == "OP_CHECKSIG":
        return "P2PK"
    if spk[:1] == ["OP_CAT"]:
        return "OP_CAT hash-lock (BTC-disabled)"
    return "script"


class XConsole:
    """A running full-capability node you can drive."""

    def __init__(self, rules: Rules, name: str, maturity: int = 2, seed: int = 0):
        self.rules = rules
        self.name = name
        self.led = Ledger(rules, maturity=maturity)
        self.w = Wallet(random.Random(seed))
        self.key = self.w.new_key()
        self.mine_spk = p2pk(self.key)
        self.priv = self.w.map_keys[self.key]
        self.events: list[str] = []
        self.market = ReviewGraph(random.Random(seed + 1))
        self.products: list = []

    # -- mining ----------------------------------------------------------------
    def mine(self, txs=None):
        """Mine a block (coinbase to self) optionally containing `txs`."""
        cb = self.led.connect_block(self.mine_spk, txs or [])   # coinbase auto-claims subsidy+fees
        self.w.add_coin(txid(cb), 0, cb.vout[0].value, self.mine_spk)
        self.events.append(f"block {self.led.height}: mined, +{self.rules.fmt(cb.vout[0].value)}"
                           + (f", {len(txs)} tx" if txs else ""))
        return cb

    def mine_until_mature(self):
        """Mine enough blocks that the earliest coinbase is spendable."""
        for _ in range(self.led.maturity):
            self.mine()

    def balance(self) -> int:
        return self.w.get_balance()

    # -- payments --------------------------------------------------------------
    def pay(self, dest_spk: list, amount: int, fee: int = 0):
        tx, coins, (change, change_spk) = self.w.create_transaction(dest_spk, amount, fee)
        self.mine([tx])                                         # settle the payment in a block
        self.w.mark_spent(coins)
        if change > 0 and change_spk:
            self.w.add_coin(txid(tx), 1, change, change_spk)
        self.events.append(f"paid {self.rules.fmt(amount)} (fee {fee}) to {describe_spk(dest_spk)}")
        return tx

    # -- a full-vocabulary contract (BTC could not run this) -------------------
    def create_hashlock(self, secret: bytes, amount: int):
        """Lock `amount` under an OP_CAT hash-lock (two halves must recombine)."""
        h1, h2 = secret[: len(secret) // 2], secret[len(secret) // 2:]
        lock = _sha256(h1 + h2)
        spk = ["OP_CAT", "OP_SHA256", lock, "OP_EQUAL"]
        tx = self.pay(spk, amount)
        self.events.append(f"locked {self.rules.fmt(amount)} under an OP_CAT hash-lock")
        return (txid(tx), 0), (h1, h2)

    def spend_hashlock(self, outpoint, halves, dest_spk):
        tid, n = outpoint
        h1, h2 = halves
        value = self.led.utxos[(tid, n)].value
        spend = Tx(1, [TxIn(tid, n, assemble([h1, h2]), 0xFFFFFFFF)],
                   [TxOut(value, assemble(dest_spk))], 0)
        self.mine([spend])
        self.events.append(f"spent the hash-lock by revealing the preimage ({self.rules.fmt(value)})")
        return spend

    # -- the marketplace layer (off-chain, alongside the node) -----------------
    def list_product(self, name: str, price: int):
        p = make_product(self.priv, self.key, name, price)
        assert p.verify()
        self.products.append(p)
        self.events.append(f"listed product '{name}' @ {price} (signed, verified)")
        return p

    def receive_review(self, product, text: str):
        priv, pub = self.w.map_keys[self.key], self.key  # a reviewer (reuse a key for the demo)
        r = make_review(priv, pub, product.user_hash(), text)
        assert r.verify()
        self.market.link(r.user_hash(), product.user_hash())
        self.market.add_atoms_and_propagate(product.user_hash(), [1], fOrigin=True)
        self.events.append(f"review accepted; seller reputation = "
                           f"{self.market.user(product.user_hash()).atom_count()} atoms")
        return r

    # -- views / evidence ------------------------------------------------------
    def utxo_view(self):
        rows = [("outpoint", "value", "kind")]
        for (tid, n), c in self.led.utxos.items():
            rows.append((f"{tid[::-1].hex()[:12]}:{n}", self.rules.fmt(c.value),
                         ("coinbase " if c.coinbase else "") + describe_spk(c.spk)))
        return rows

    def export(self, path):
        bundle = {
            "network": self.name,
            "profile": self.rules.profile,
            "constitution": {"COIN": self.rules.COIN, "subsidy_coins": self.rules.subsidy_base // self.rules.COIN,
                             "coinbase_rule": self.rules.coinbase_rule, "pow": self.rules.pow_encoding},
            "height": self.led.height,
            "wallet_balance": self.balance(),
            "utxo_count": len(self.led.utxos),
            "utxos": [{"txid": tid[::-1].hex(), "n": n, "value": c.value,
                       "coinbase": c.coinbase, "kind": describe_spk(c.spk)}
                      for (tid, n), c in self.led.utxos.items()],
            "products": [{"name": p.fields["name"], "price": p.fields["price"],
                          "verified": p.verify()} for p in self.products],
            "events": self.events,
        }
        pathlib.Path(path).write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
        return bundle


def run_session(rules: Rules, name: str, export_path=None):
    """Drive a full session on one chain: mine, pay, a hash-lock contract, a signed
    marketplace listing + reputation, and (optionally) export the evidence bundle."""
    c = XConsole(rules, name)
    c.mine_until_mature()                                       # coinbases to spend
    c.mine()
    dest = p2pk(Wallet().new_key())
    c.pay(dest, rules.get_block_value(-1) // 4)                 # a payment
    (op, halves) = c.create_hashlock(b"secret-preimage-halves", rules.get_block_value(-1) // 5)
    c.mine()                                                    # let the lock sit a block
    c.spend_hashlock(op, halves, p2pk(Wallet().new_key()))      # spend it (full vocabulary)
    prod = c.list_product("timechain widget", 100)
    c.receive_review(prod, "works great")
    if export_path:
        c.export(export_path)
    return c


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    for prof, label in [("nov08", "NOV08-X (NOV08-Full machine)"), ("jan09", "JAN09-X")]:
        c = run_session(Rules.load(prof), label)
        print(f"\n=== {label} — height {c.led.height}, {len(c.led.utxos)} UTXOs, "
              f"balance {c.rules.fmt(c.balance())} ===")
        for e in c.events:
            print("  •", e)
    # a script trace from the studio, over the full vocabulary
    print("\n" + trace_render([b"\x11", b"\x22", "OP_CAT"], title="studio trace:"))
