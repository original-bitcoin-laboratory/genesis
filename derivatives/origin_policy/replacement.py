"""Transaction replacement by sequence number, executed -- MODEL.

The January 2009 client accepts, into its memory pool, a transaction that conflicts with one it
already holds, provided the newcomer is a newer version of the same transaction: identical inputs
(same prevouts, in order) and a higher sequence number where they differ (`CTransaction::IsNewerThan`,
main.h:408; the conflict logic in `AcceptTransaction`, main.cpp:428-446). The old version is erased
and the new one takes its place. That is the machinery behind the author's contract ideas (a
transaction revised by its parties before it is final; the December 2010 post describing fee-based
replacement), and it shipped in the first release.

Commit 05454818d (19 August 2010, "block index checking on load, extra redundant checks, misc
refactoring") adds two lines at the top of the conflict branch:

    // Disable replacement feature for now
    return false;

so from 0.3.11 any conflicting transaction is refused, whatever its sequence numbers. The code after
the `return` is left in place, unreachable. Constitution row OBL-C-0015.

This module ports both versions of the conflict decision line for line and exhibits the transaction
that January accepts as a replacement and 0.3.11 refuses. Evidence level: MODEL. The memory pool is
a dictionary; ConnectInputs (the fee and signature checks) is out of scope, as it is for the
decision under test. NOT money.
"""
from __future__ import annotations

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "model"))
from tx_sighash import Tx, TxIn, TxOut, dsha256, serialize  # noqa: E402

UINT_MAX = 0xFFFFFFFF


def txid(tx: Tx) -> bytes:
    return dsha256(serialize(tx))


def is_newer_than(new: Tx, old: Tx) -> bool:
    """CTransaction::IsNewerThan (main.h:408), line for line."""
    if len(new.vin) != len(old.vin):
        return False
    for i in range(len(new.vin)):
        if (new.vin[i].prevhash, new.vin[i].n) != (old.vin[i].prevhash, old.vin[i].n):
            return False
    f_newer = False
    n_lowest = UINT_MAX
    for i in range(len(new.vin)):
        if new.vin[i].seq != old.vin[i].seq:
            if new.vin[i].seq <= n_lowest:
                f_newer = False
                n_lowest = new.vin[i].seq
            if old.vin[i].seq < n_lowest:
                f_newer = True
                n_lowest = old.vin[i].seq
    return f_newer


class MemPool:
    """mapTransactions + mapNextTx, as far as the conflict decision reads them."""

    def __init__(self):
        self.txs: dict[bytes, Tx] = {}
        self.next: dict[tuple, bytes] = {}          # prevout -> txid of the spender

    def add(self, tx: Tx) -> None:
        h = txid(tx)
        self.txs[h] = tx
        for vin in tx.vin:
            self.next[(vin.prevhash, vin.n)] = h

    def remove(self, h: bytes) -> None:
        tx = self.txs.pop(h)
        for vin in tx.vin:
            self.next.pop((vin.prevhash, vin.n), None)


def accept_v01(pool: MemPool, tx: Tx):
    """The conflict branch of v0.1 AcceptTransaction (main.cpp:428-446) and the replacement it performs."""
    h = txid(tx)
    if h in pool.txs:
        return False, "already have it"
    ptx_old = None
    for i, vin in enumerate(tx.vin):
        outpoint = (vin.prevhash, vin.n)
        if outpoint in pool.next:
            # Allow replacing with a newer version of the same transaction
            if i != 0:
                return False, "conflict on an input other than the first"
            ptx_old = pool.txs[pool.next[outpoint]]
            if not is_newer_than(tx, ptx_old):
                return False, "not newer than the conflicting transaction"
            for vin2 in tx.vin:
                op2 = (vin2.prevhash, vin2.n)
                if op2 not in pool.next or pool.txs[pool.next[op2]] is not ptx_old:
                    return False, "inputs do not all conflict with the same transaction"
            break
    if ptx_old is not None:
        pool.remove(txid(ptx_old))          # "mapTransaction.erase(...) replacing with new version"
    pool.add(tx)
    return True, "replaced" if ptx_old is not None else "accepted"


def accept_0311(pool: MemPool, tx: Tx):
    """The same branch after 05454818d: `// Disable replacement feature for now` / `return false;`."""
    h = txid(tx)
    if h in pool.txs:
        return False, "already have it"
    for vin in tx.vin:
        if (vin.prevhash, vin.n) in pool.next:
            return False, "conflict: replacement disabled"
    pool.add(tx)
    return True, "accepted"


# -- the exhibit --------------------------------------------------------------------------------
PREV = dsha256(b"a funded output")


def version(seq: int, value: int) -> Tx:
    """Two versions of one transaction: same input, a different sequence number and payout."""
    return Tx(1, [TxIn(PREV, 0, b"\x51", seq)], [TxOut(value, b"\x51")], 0)


def report() -> None:
    v1, v2 = version(0, 40), version(1, 45)
    for name, accept in (("v0.1  (January 2009)", accept_v01), ("0.3.11 (05454818d)", accept_0311)):
        pool = MemPool()
        r1 = accept(pool, v1)
        r2 = accept(pool, v2)
        held = [txid(t) == txid(v2) for t in pool.txs.values()]
        print(f"  {name:<22} first version {r1}   newer version {r2}   pool holds the newer: {any(held)}")
    print("  => the January client replaces a held transaction with a newer version of itself (higher nSequence,")
    print("     same inputs); from 19 August 2010 any conflicting transaction is refused. NOT money.")


if __name__ == "__main__":
    print("TRANSACTION REPLACEMENT BY SEQUENCE NUMBER -- executed side by side (MODEL)")
    report()
