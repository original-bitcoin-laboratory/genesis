"""Rules-parameterised UTXO ledger (ConnectInputs / ConnectBlock) — MODEL.

The Python counterpart of `../node/chain_port.cpp`, but driven by a `consensus.Rules`
so it enforces *whichever* chain's constitution — NOV08-X or JAN09-X. It reuses the
lab's executed pieces: `model/spend.verify_spend` (the v0.1 VerifySignature path,
EvalScript over scriptSig + OP_CODESEPARATOR + scriptPubKey, **full vocabulary**) for
input validation, and `consensus.Rules.coinbase_ok` for the coinbase value rule.

Guarantees enforced (main.cpp ConnectInputs / ConnectBlock):
- no double-spend (spent inputs leave the UTXO set),
- no inflation (sum inputs >= sum outputs),
- coinbase maturity (COINBASE_MATURITY, main.h),
- the chain's coinbase value rule (NOV08 `==`, JAN09 `<=`),
- every input's spending script satisfies its output's scriptPubKey — including
  scripts BTC cannot express (e.g. an `OP_CAT` hash-lock).

Evidence level: MODEL.
"""

from __future__ import annotations

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "model"))
sys.path.insert(0, str(_HERE.parent / "nov08x"))
from cscript import assemble, parse                                   # noqa: E402
from spend import verify_spend                                       # noqa: E402
from tx_sighash import Tx, TxIn, TxOut, dsha256, serialize as ser_tx  # noqa: E402
from consensus import Rules                                          # noqa: E402

COINBASE_MATURITY = 100                       # main.h (both editions)
ZERO = b"\x00" * 32


def txid(tx: Tx) -> bytes:
    return dsha256(ser_tx(tx))


class Coin:
    """A UTXO."""
    __slots__ = ("txid", "n", "value", "spk", "height", "coinbase")

    def __init__(self, txid, n, value, spk, height, coinbase=False):
        self.txid = txid; self.n = n; self.value = value; self.spk = spk
        self.height = height; self.coinbase = coinbase


class LedgerError(Exception):
    pass


class Ledger:
    """A UTXO set under a chain's Rules. Coinbases mature; spends are validated
    through the v0.1 VerifySignature path."""

    def __init__(self, rules: Rules, maturity: int = COINBASE_MATURITY):
        self.rules = rules
        self.maturity = maturity
        self.utxos: dict[tuple[bytes, int], Coin] = {}
        self.height = -1                       # global best height (subsidy quirk, both editions)

    # -- coinbase (ConnectBlock's subsidy + value check) -----------------------
    def connect_coinbase(self, spk_tokens: list, claim: int | None = None, fees: int = 0):
        block_value = self.rules.get_block_value(self.height, fees)
        claim = block_value if claim is None else claim
        if not self.rules.coinbase_ok(claim, block_value):
            raise LedgerError(f"coinbase rule ({self.rules.coinbase_rule}): "
                              f"claim {claim} vs block value {block_value}")
        self.height += 1
        cb = Tx(1, [TxIn(ZERO, 0xFFFFFFFF, bytes([2, self.height & 0xFF]), 0xFFFFFFFF)],
                [TxOut(claim, assemble(spk_tokens))], 0)
        tid = txid(cb)
        self.utxos[(tid, 0)] = Coin(tid, 0, claim, spk_tokens, self.height, coinbase=True)
        return cb, tid

    def advance(self, n: int = 1):
        """Extend the chain by n empty blocks (lets coinbases mature)."""
        self.height += n

    def balance(self) -> int:
        return sum(c.value for c in self.utxos.values())

    # -- ConnectInputs (spend validation) --------------------------------------
    def connect_tx(self, tx: Tx, spent: list[Coin]):
        """Validate + apply a transaction spending `spent` (one Coin per vin, in
        order). tx.vin[i].script holds the signed/satisfying scriptSig bytes."""
        if len(spent) != len(tx.vin):
            raise LedgerError("input count mismatch")
        value_in = 0
        for i, coin in enumerate(spent):
            key = (coin.txid, coin.n)
            if key not in self.utxos:
                raise LedgerError(f"input {i} missing or already spent (double-spend)")
            if coin.coinbase and (self.height - coin.height) < self.maturity:
                raise LedgerError(f"input {i} spends immature coinbase "
                                  f"({self.height - coin.height} < {self.maturity})")
            ss_tokens = parse(tx.vin[i].script)                # the satisfying scriptSig
            if not verify_spend(ss_tokens, coin.spk, tx, i):   # VerifySignature (full vocabulary)
                raise LedgerError(f"input {i} script/signature does not satisfy scriptPubKey")
            value_in += coin.value
        value_out = sum(o.value for o in tx.vout)
        if value_in < value_out:
            raise LedgerError(f"inflation: inputs {value_in} < outputs {value_out}")

        # apply: remove spent, add new outputs
        for coin in spent:
            del self.utxos[(coin.txid, coin.n)]
        tid = txid(tx)
        for n, o in enumerate(tx.vout):
            self.utxos[(tid, n)] = Coin(tid, n, o.value, parse(o.script), self.height)
        return tid, value_in - value_out                       # (txid, fee)
