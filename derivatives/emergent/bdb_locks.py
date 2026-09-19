"""The Berkeley DB lock rule, executed -- MODEL.

The rule nobody wrote (constitution row OBL-C-0013, docs/CONSENSUS-ATLAS.md section 8): every node
before Bitcoin 0.8 stored its block index in Berkeley DB with a lock table sized by the application,
and a block that needed more locks than the table held was rejected by those nodes and accepted by
0.8's LevelDB nodes. On 11 March 2013 block 225,430 split the chain that way (BIP 50). The written
response is commit 8bd028818 (15 March 2013, 0.8.1): CheckBlock rejects a block that references more
than 4,500 distinct transaction ids when its time lies between the fork and 15 May 2013.

What this module executes, side by side:

  * the January 2009 CheckBlock's size and count clauses (main.cpp, v0.1): a block is bounded only
    by MAX_SIZE = 0x02000000 on its serialised size and its transaction count;
  * the 0.8.1 clause of 8bd028818, ported line for line, with its two timestamps;

and exhibits one block that the January rule accepts and the 0.8.1 rule rejects, the same block
accepted again once its time is past 15 May 2013, and the boundary at exactly 4,500 ids.

The lock table itself is not modelled: nobody could state it as a rule, which is the point of
the row. What is modelled is the rule written to stand in for it. Evidence level: MODEL. The block
is synthetic (no proof of work, no valid merkle root; those clauses of CheckBlock are not the ones
under test and are not ported here). NOT money.
"""
from __future__ import annotations

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "model"))
from tx_sighash import Tx, TxIn, TxOut, compact_size, dsha256, serialize  # noqa: E402

MAX_SIZE = 0x02000000                      # main.h:17 (v0.1): 32 MiB, also the transaction-count bound
FORK_BLOCK_TIME = 1363039171               # 8bd028818: "11 March 2013, timestamp of block before the big fork"
RULE_END_TIME = 1368576000                 # 8bd028818: "15 May 2013 00:00:00"
MAX_UNIQUE_TXIDS = 4500                    # 8bd028818: "Rule is: #unique txids referenced <= 4,500"

ZERO = b"\x00" * 32
NULL_N = 0xFFFFFFFF


class Block:
    """A block as the two checks see it: a time, a transaction list, and its serialised size."""

    def __init__(self, ntime: int, vtx: list):
        self.ntime = ntime
        self.vtx = vtx

    def serialized_size(self) -> int:
        return 80 + len(compact_size(len(self.vtx))) + sum(len(serialize(t)) for t in self.vtx)


def txid(tx: Tx) -> bytes:
    return dsha256(serialize(tx))


# -- the January 2009 clauses -------------------------------------------------------------------
def check_block_v01_size(block: Block):
    """CheckBlock (v0.1 main.cpp): `vtx.empty() || vtx.size() > MAX_SIZE || GetSerializeSize > MAX_SIZE`."""
    if not block.vtx or len(block.vtx) > MAX_SIZE or block.serialized_size() > MAX_SIZE:
        return False, "size limits failed"
    return True, "ok"


# -- the 0.8.1 clause, 8bd028818 -----------------------------------------------------------------
def unique_txids_referenced(block: Block) -> int:
    """`setTxIn`: every transaction's own id, plus every non-coinbase input's prevout hash."""
    s = set()
    for i, tx in enumerate(block.vtx):
        s.add(txid(tx))
        if i == 0:
            continue                       # "skip coinbase txin"
        for vin in tx.vin:
            s.add(vin.prevhash)
    return len(s)


def check_block_081_locks(block: Block):
    """The clause 8bd028818 adds to CheckBlock, in the same order."""
    if FORK_BLOCK_TIME < block.ntime < RULE_END_TIME:
        if unique_txids_referenced(block) > MAX_UNIQUE_TXIDS:
            return False, "15 May maxlocks violation"
    return True, "ok"


# -- the exhibit ---------------------------------------------------------------------------------
def coinbase(height_tag: bytes = b"\x04\x0b\x0d") -> Tx:
    return Tx(1, [TxIn(ZERO, NULL_N, height_tag)], [TxOut(50 * 100_000_000, b"\x51")], 0)


def spend(i: int) -> Tx:
    """One input spending a distinct previous transaction, one output; nothing else matters here."""
    prev = dsha256(b"prevout-" + i.to_bytes(4, "little"))
    return Tx(1, [TxIn(prev, 0, b"\x51")], [TxOut(1, b"\x51")], 0)


def block_with_unique_ids(n_ids: int, ntime: int) -> Block:
    """A coinbase plus k spends gives 1 + 2k distinct ids (k own ids, k prevouts, the coinbase's id).
    Pass n_ids odd to land exactly; an even count is rounded up to the next odd."""
    k = max(0, (n_ids - 1 + 1) // 2)
    b = Block(ntime, [coinbase()] + [spend(i) for i in range(k)])
    assert unique_txids_referenced(b) == 1 + 2 * k
    return b


def report() -> None:
    inside = 1365000000                    # 3 April 2013, inside the window
    after = 1370000000                     # 31 May 2013, after it
    big = block_with_unique_ids(4501, inside)
    n = unique_txids_referenced(big)
    print("BERKELEY DB LOCK RULE -- executed side by side (MODEL)")
    print(f"  block: {len(big.vtx)} transactions, {big.serialized_size():,} B serialised, {n} distinct txids referenced")
    print(f"  v0.1  CheckBlock size/count clauses : {check_block_v01_size(big)}")
    print(f"  0.8.1 CheckBlock 8bd028818 clause    : {check_block_081_locks(big)}   (block time inside 11 Mar..15 May 2013)")
    big.ntime = after
    print(f"  0.8.1 same block, time after 15 May  : {check_block_081_locks(big)}")
    edge = block_with_unique_ids(4499, inside)
    print(f"  0.8.1 block with {unique_txids_referenced(edge)} ids (<= 4,500)  : {check_block_081_locks(edge)}")
    print("  => a block valid under the January rules is invalid under the rule written for a database's lock table,")
    print("     for nine weeks of 2013, by a count of transaction ids that no earlier rule mentions. NOT money.")


if __name__ == "__main__":
    report()
