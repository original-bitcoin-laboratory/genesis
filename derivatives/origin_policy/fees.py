"""The origin's fee policy, and the December 2010 free-transaction limit, executed -- MODEL.

The January 2009 client has one fee rule, and it is not consensus: `CTransaction::GetMinFee`
(main.h:504) returns one cent (`CENT = 1,000,000` satoshi) per started kilobyte, and zero for a
transaction under 10,000 bytes when the discount applies. The miner applies the discount to the
first 100 transactions of a block it builds (main.cpp:2250, "Under 10K (about 80 inputs) is free for
first 100 transactions") and the wallet applies it when it creates a transaction (main.cpp:2577).
A block that includes a transaction paying less is valid; the rule decides what a node builds and
sends, not what it accepts.

Commit 97ee01ad8 (12 December 2010, version 0.3.19, message "added some DoS limits, removed safe
mode") adds two things to `AcceptToMemoryPool`: a transaction is refused for relay if it pays less
than `GetMinFee(1000)`, and under `-limitfreerelay` free transactions (fee under one cent) are
rate-limited to 150,000 bytes per ten minutes, the node's own excepted. Still policy: a block
carrying such a transaction is valid. Constitution row OBL-C-0017 (kind: policy).

This module ports GetMinFee and the December 2010 relay gate line for line and exhibits the
transaction each accepts. Evidence level: MODEL. NOT money.
"""
from __future__ import annotations

CENT = 1_000_000                 # main.h:19
FREE_BYTES_PER_10_MIN = 150_000  # 97ee01ad8: "if (nFreeCount > 150000 && !IsFromMe())"


def get_min_fee_v01(n_bytes: int, f_discount: bool = False) -> int:
    """CTransaction::GetMinFee (main.h:504), line for line."""
    if f_discount and n_bytes < 10000:
        return 0
    return (1 + n_bytes // 1000) * CENT


MAX_BLOCK_SIZE_GEN = 500_000          # main.h at 97ee01ad8: MAX_BLOCK_SIZE / 2
MAX_MONEY = 21_000_000 * 100_000_000


def get_min_fee_20101212(n_bytes: int, n_block_size: int = 1, f_allow_free: bool = True,
                         vout_values: tuple = ()) -> int:
    """GetMinFee(nBlockSize, fAllowFree) as it stands in 0.3.19 (main.h:576-612 at 97ee01ad8), line for
    line: one cent per started kilobyte; with nBlockSize == 1 a transaction under 10,000 bytes is free,
    otherwise free while nBlockSize + nBytes stays under 27,000 (the "free transaction area"); a one-cent
    fee if any output is under one cent ("to limit dust spam"); and the fee multiplied as the block being
    built passes half of MAX_BLOCK_SIZE_GEN, MAX_MONEY once it is full. The relay gate calls it with
    nBlockSize = 1000."""
    n_new_block_size = n_block_size + n_bytes
    n_min_fee = (1 + n_bytes // 1000) * CENT
    if f_allow_free:
        if n_block_size == 1:
            # Transactions under 10K are free
            if n_bytes < 10000:
                n_min_fee = 0
        else:
            # Free transaction area
            if n_new_block_size < 27000:
                n_min_fee = 0
    # To limit dust spam, require a 0.01 fee if any output is less than 0.01
    if n_min_fee < CENT:
        for v in vout_values:
            if v < CENT:
                n_min_fee = CENT
    # Raise the price as the block approaches full
    if n_block_size != 1 and n_new_block_size >= MAX_BLOCK_SIZE_GEN // 2:
        if n_new_block_size >= MAX_BLOCK_SIZE_GEN:
            return MAX_MONEY
        n_min_fee *= MAX_BLOCK_SIZE_GEN // (MAX_BLOCK_SIZE_GEN - n_new_block_size)
    return n_min_fee


class FreeRelayLimiter:
    """The -limitfreerelay gate of 97ee01ad8: 150,000 bytes of free transactions per ten minutes."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.next_reset = 0
        self.free_count = 0

    def accept(self, now: int, n_bytes: int, fees: int, from_me: bool = False):
        # "Don't accept it if it can't get into a block"
        if fees < get_min_fee_20101212(n_bytes, 1000):
            return False, "not enough fees"
        # "Limit free transactions per 10 minutes"
        if fees < CENT and self.enabled:
            if now > self.next_reset:
                self.next_reset = now + 10 * 60
                self.free_count = 0
            if self.free_count > FREE_BYTES_PER_10_MIN and not from_me:
                return False, "free transaction rejected by rate limiter"
            self.free_count += n_bytes
        return True, "ok"


def accept_v01(n_bytes: int, fees: int):
    """v0.1 AcceptTransaction applies no fee test to a received transaction: the decision under test passes."""
    return True, "ok"


def report() -> None:
    print("THE ORIGIN'S FEE POLICY AND THE DECEMBER 2010 RELAY GATE -- executed side by side (MODEL)")
    for n in (250, 9_999, 10_000, 25_000):
        print(f"  {n:>6} B  GetMinFee: plain {get_min_fee_v01(n)/CENT:>5.2f} cent   with discount {get_min_fee_v01(n, True)/CENT:>5.2f} cent")
    now = 1_292_000_000
    print(f"  a 250 B free transaction        v0.1 {accept_v01(250, 0)}   0.3.19 {FreeRelayLimiter().accept(now, 250, 0)}")
    print(f"  a 25,000 B transaction, no fee  v0.1 {accept_v01(25000, 0)}   0.3.19 {FreeRelayLimiter().accept(now, 25000, 0)}   (26,000 < 27,000: free area)")
    print(f"  a 26,500 B transaction, no fee  v0.1 {accept_v01(26500, 0)}   0.3.19 {FreeRelayLimiter().accept(now, 26500, 0)}")
    lim = FreeRelayLimiter(); n_free = 0
    while lim.accept(now, 250, 0)[0]:
        n_free += 1
    print(f"  free 250 B transactions accepted in one ten-minute window under -limitfreerelay: {n_free}, then refused")
    print("  => the January client builds and sends under a one-cent-per-kilobyte rule with a 10 KB discount and")
    print("     accepts anything for relay; from 12 December 2010 relay itself requires the fee, and free")
    print("     transactions are rate-limited. Policy on both sides: no block is invalid under either. NOT money.")


if __name__ == "__main__":
    report()
