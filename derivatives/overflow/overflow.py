"""Executable reproduction of v0.1's value-overflow surface -- MODEL.

Makes the sharpest finding of ../../../common/conformance/CONSENSUS_SURFACE.md runnable.
v0.1's CheckTransaction (main.h:442) checks only `nValue < 0` per output -- no upper
bound, and no check on the output *sum*. In C++ signed 64-bit arithmetic two large-but-
positive outputs can sum PAST the wrap point, so the total appears small (here, negative),
and the downstream `inputs >= outputs` check passes while astronomically many coins are
minted. The fix (0.3.10, 15 Aug 2010, commit d4c6b90ca) wrote the bounds that 05454818d named
MoneyRange() four days later.

Same shape as ../crypto_conformance/ (Thread A executed): port the v0.1 rule and the
post-2010 hardened rule side by side, and exhibit the exact input one accepts and the
other rejects. The historical exploit (tx in block 74638, 15 Aug 2010) used two outputs
of 92,233,720,368.54277039 BTC; we use those exact satoshi amounts.

Every check returns (ok, clause): `clause` is the identifier of the clause that fired, from a
fixed vocabulary (CLAUSES), not a sentence. A test asserts the clause, not a substring of a
message this module wrote itself (an adversarial review, 20 September 2026, asked for that).

Evidence level: MODEL. The wrap is reproduced with explicit int64 arithmetic *because*
Python integers do not overflow -- that gap between fixed-width C++ and big-int Python is
precisely the vulnerability, so we model it rather than hand-wave it. (The lab's Python
ledger, which sums with big-ints, therefore does NOT reproduce the bug -- see the README.)
"""

from __future__ import annotations

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "model"))
from tx_sighash import Tx, TxIn, TxOut                                   # noqa: E402

# -- monetary constants (v0.1 + the 2010 fix) --------------------------------
COIN = 100_000_000                       # main.h (JAN edition): 1e8 satoshi
MAX_MONEY = 21_000_000 * COIN            # introduced with the Aug-2010 fix
ZERO = b"\x00" * 32
NULL_N = 0xFFFFFFFF

# the historical exploit outputs (tx in block 74638): 92,233,720,368.54277039 BTC each
OVERFLOW_SAT = 9_223_372_036_854_277_039  # satoshi, per output; two of them wrap int64

# the clauses a check can fail on, one identifier each (the v0.1 clauses first, then the 2010 additions)
CLAUSES = ("ok", "vin-or-vout-empty", "output-negative", "coinbase-script-size", "prevout-null",
           "output-above-max-money", "output-sum-out-of-range")

# -- signed 64-bit arithmetic (what C++ `int64 nValueOut` actually did) -------
_I64 = 1 << 64


def to_int64(x: int) -> int:
    """Reduce to a two's-complement signed 64-bit value (C++ int64 semantics)."""
    x &= _I64 - 1
    return x - _I64 if x >= (1 << 63) else x


def add_i64(a: int, b: int) -> int:
    return to_int64(a + b)


def money_range(v: int) -> bool:
    """MoneyRange() -- the check the Aug-2010 fix added: 0 <= v <= MAX_MONEY."""
    return 0 <= v <= MAX_MONEY


# -- helpers on the tx model --------------------------------------------------
def is_null(vin: TxIn) -> bool:          # COutPoint::IsNull() -- hash==0 && n==-1
    return vin.prevhash == ZERO and vin.n == NULL_N


def is_coinbase(tx: Tx) -> bool:
    return len(tx.vin) == 1 and is_null(tx.vin[0])


# -- the two rules, ported line-for-line --------------------------------------
def check_transaction_v01(tx: Tx):
    """v0.1 CTransaction::CheckTransaction() -- main.h:442, exact port. (ok, clause)."""
    if not tx.vin or not tx.vout:
        return False, "vin-or-vout-empty"
    # Check for negative values  (the ONLY value check v0.1 has)
    for o in tx.vout:
        if o.value < 0:
            return False, "output-negative"
    if is_coinbase(tx):
        if not (2 <= len(tx.vin[0].script) <= 100):
            return False, "coinbase-script-size"
    else:
        for vin in tx.vin:
            if is_null(vin):
                return False, "prevout-null"
    return True, "ok"                     # <-- NO MoneyRange, NO output-sum overflow check


def check_transaction_hardened(tx: Tx):
    """The post-Aug-2010 CheckTransaction: identical structure, plus the two bounds. (ok, clause)."""
    if not tx.vin or not tx.vout:
        return False, "vin-or-vout-empty"
    n_value_out = 0
    for o in tx.vout:
        if o.value < 0:
            return False, "output-negative"
        if o.value > MAX_MONEY:                              # ADDED 2010: per-output cap
            return False, "output-above-max-money"
        n_value_out = add_i64(n_value_out, o.value)          # summed as int64...
        if not money_range(n_value_out):                     # ...ADDED 2010: catches the wrap
            return False, "output-sum-out-of-range"
    if is_coinbase(tx):
        if not (2 <= len(tx.vin[0].script) <= 100):
            return False, "coinbase-script-size"
    else:
        for vin in tx.vin:
            if is_null(vin):
                return False, "prevout-null"
    return True, "ok"


# -- how the output total was summed downstream (ConnectInputs) ---------------
def output_total_int64(tx: Tx) -> int:
    """CTransaction::GetValueOut() (main.h:492), as C++ ran it: an int64 accumulator, which wraps.
    The only guard in the loop is `nValue < 0`, tested per output before it is added."""
    total = 0
    for o in tx.vout:
        if o.value < 0:
            raise ValueError("CTransaction::GetValueOut() : negative value")
        total = add_i64(total, o.value)
    return total


def output_total_true(tx: Tx) -> int:
    """The actual economic value created (Python big-int -- no wrap)."""
    return sum(o.value for o in tx.vout)


def connect_inputs_value_check_v01(tx: Tx, value_in: int):
    """The value clause of v0.1's ConnectInputs (main.cpp), ported: after the inputs are found and
    summed into `nValueIn`, `if (nValueIn < GetValueOut()) return error("ConnectInputs() : value in
    < value out")`. `GetValueOut` is the int64 accumulator above. (ok, clause)."""
    if value_in < output_total_int64(tx):
        return False, "value-in-below-value-out"
    return True, "ok"


# -- the exploit transaction --------------------------------------------------
def overflow_tx(prevhash: bytes = b"\x11" * 32, n: int = 0) -> Tx:
    """A spend with two large-but-positive outputs whose int64 sum wraps."""
    return Tx(1,
              [TxIn(prevhash, n, b"\x51", 0xFFFFFFFF)],              # some real input
              [TxOut(OVERFLOW_SAT, b"\x51"), TxOut(OVERFLOW_SAT, b"\x51")], 0)


def sum_overflow_tx(prevhash: bytes = b"\x11" * 32, n: int = 0) -> Tx:
    """Two outputs each inside the per-output bound whose sum is outside it: the case only the
    running-sum clause catches."""
    return Tx(1,
              [TxIn(prevhash, n, b"\x51", 0xFFFFFFFF)],
              [TxOut(MAX_MONEY, b"\x51"), TxOut(1, b"\x51")], 0)


def demo() -> None:
    tx = overflow_tx()
    ok_v01, why_v01 = check_transaction_v01(tx)
    ok_hard, why_hard = check_transaction_hardened(tx)
    i64 = output_total_int64(tx)
    true = output_total_true(tx)
    ok_ci, why_ci = connect_inputs_value_check_v01(tx, 1)
    print(f"two outputs of {OVERFLOW_SAT} sat each (~{OVERFLOW_SAT / COIN:,.2f} BTC)")
    print(f"  v0.1 CheckTransaction (main.h:442) : {'ACCEPT' if ok_v01 else 'REJECT'}  ({why_v01})")
    print(f"  2010 CheckTransaction (d4c6b90ca)  : {'ACCEPT' if ok_hard else 'REJECT'}  ({why_hard})")
    print(f"  output total as int64 (C++)  : {i64:>24} sat  <- wraps negative")
    print(f"  output total, true value     : {true:>24} sat  = {true // COIN:,} BTC minted")
    print(f"  v0.1 ConnectInputs value clause with a 1-satoshi input: {'PASSES' if ok_ci else 'fails'} ({why_ci})")
    print(f"  => v0.1's 'value in < value out' sees outputs = {i64} and passes with a tiny input.")


if __name__ == "__main__":
    demo()
