"""Three policies of the origin and what 2010 did to them, executed: transaction replacement by
sequence number (shipped, then disabled 19 Aug 2010), hard-coded checkpoints (absent, then added
17 Jul 2010), and the fee rule (a build-and-send policy, then a relay gate 12 Dec 2010).
Evidence: MODEL. NOT money."""

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent / "model"))

from checkpoints import (                                                 # noqa: E402
    CHECKPOINTS_20100717, CHECKPOINTS_20100815, accept_block_checkpointed, accept_block_v01,
)
from fees import (                                                        # noqa: E402
    CENT, FREE_BYTES_PER_10_MIN, FreeRelayLimiter, accept_v01 as fee_accept_v01,
    get_min_fee_20101212, get_min_fee_v01,
)
from replacement import (                                                 # noqa: E402
    PREV, MemPool, accept_0311, accept_v01, is_newer_than, txid, version,
)
from tx_sighash import Tx, TxIn, TxOut, dsha256                           # noqa: E402


# ---- replacement --------------------------------------------------------------------------------

def test_v01_replaces_with_a_newer_version():
    pool = MemPool()
    assert accept_v01(pool, version(0, 40)) == (True, "accepted")
    ok, why = accept_v01(pool, version(1, 45))
    assert ok and why == "replaced"
    assert list(pool.txs.values())[0].vout[0].value == 45 and len(pool.txs) == 1


def test_v01_refuses_an_older_or_equal_version():
    pool = MemPool()
    accept_v01(pool, version(5, 40))
    assert accept_v01(pool, version(5, 41))[0] is False       # same sequence: not newer
    assert accept_v01(pool, version(4, 41))[0] is False       # lower sequence: not newer
    assert len(pool.txs) == 1


def test_v01_refuses_a_conflict_that_is_not_the_same_transaction():
    pool = MemPool()
    accept_v01(pool, version(0, 40))
    other = Tx(1, [TxIn(PREV, 0, b"\x51", 9), TxIn(dsha256(b"x"), 0, b"\x51", 9)], [TxOut(1, b"\x51")], 0)
    assert accept_v01(pool, other)[0] is False                # different input set


def test_0311_refuses_every_conflict():
    pool = MemPool()
    assert accept_0311(pool, version(0, 40))[0]
    ok, why = accept_0311(pool, version(1, 45))
    assert not ok and "replacement disabled" in why
    assert list(pool.txs.values())[0].vout[0].value == 40


def test_is_newer_than_is_the_source_rule():
    assert is_newer_than(version(1, 0), version(0, 0))
    assert not is_newer_than(version(0, 0), version(1, 0))
    assert not is_newer_than(version(3, 0), version(3, 0))


# ---- checkpoints --------------------------------------------------------------------------------

OTHER = "00000000004a3b7e5f6c9d2a1b0e8f7d6c5b4a39281706f5e4d3c2b1a0f9e8d7"


def test_v01_has_no_checkpoint():
    assert accept_block_v01(11111, OTHER) == (True, "ok")
    assert accept_block_v01(74000, OTHER) == (True, "ok")


def test_2010_rule_rejects_a_different_hash_at_a_checkpointed_height():
    ok, why = accept_block_checkpointed(11111, OTHER)
    assert not ok and why.startswith("rejected by checkpoint lockin")
    assert accept_block_checkpointed(74000, OTHER)[0] is False


def test_2010_rule_accepts_the_checkpointed_hash_and_other_heights():
    assert accept_block_checkpointed(11111, CHECKPOINTS_20100815[11111]) == (True, "ok")
    assert accept_block_checkpointed(11112, OTHER) == (True, "ok")


def test_the_july_rule_had_three_checkpoints_and_august_five():
    assert len(CHECKPOINTS_20100717) == 3 and len(CHECKPOINTS_20100815) == 5
    assert accept_block_checkpointed(74000, OTHER, CHECKPOINTS_20100717) == (True, "ok")


# ---- fees ---------------------------------------------------------------------------------------

def test_january_fee_arithmetic():
    assert get_min_fee_v01(250) == CENT
    assert get_min_fee_v01(999) == CENT and get_min_fee_v01(1000) == 2 * CENT
    assert get_min_fee_v01(9_999, True) == 0 and get_min_fee_v01(10_000, True) == 11 * CENT


def test_december_2010_fee_arithmetic():
    assert get_min_fee_20101212(9_999, 1) == 0 and get_min_fee_20101212(10_000, 1) == 11 * CENT
    assert get_min_fee_20101212(25_000, 1000) == 0            # 26,000 < 27,000: the free area
    assert get_min_fee_20101212(26_500, 1000) == 27 * CENT    # past it: one cent per started KB
    assert get_min_fee_20101212(250, 1000, vout_values=(CENT - 1,)) == CENT      # the dust clause
    assert get_min_fee_20101212(250, 1000, vout_values=(CENT,)) == 0
    assert get_min_fee_20101212(1_000, 300_000) == 2 * CENT * (500_000 // 199_000)   # price rises past half full
    assert get_min_fee_20101212(1_000, 499_500) == 21_000_000 * 100_000_000          # a full block: MAX_MONEY


def test_january_relays_anything_and_december_gates_relay():
    assert fee_accept_v01(26_500, 0) == (True, "ok")
    lim = FreeRelayLimiter()
    assert lim.accept(0, 26_500, 0) == (False, "not enough fees")
    assert lim.accept(0, 250, 0) == (True, "ok")


def test_free_relay_is_rate_limited_per_ten_minutes():
    lim = FreeRelayLimiter()
    n = 0
    while lim.accept(100, 250, 0)[0]:
        n += 1
    assert n == FREE_BYTES_PER_10_MIN // 250 + 1
    assert lim.accept(100, 250, 0) == (False, "free transaction rejected by rate limiter")
    assert lim.accept(100, 250, 0, from_me=True)[0]           # "!IsFromMe()"
    assert lim.accept(100 + 601, 250, 0)[0]                    # the window resets
    assert FreeRelayLimiter(enabled=False).accept(100, 250, 0)[0]
