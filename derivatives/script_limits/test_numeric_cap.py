"""The numeric-operand cap, executed: v0.1's unbounded CBigNum accepts a 9-byte operand that the
2010 four-byte cap (nMaxNumSize = 4, 4bd188c43) rejects. Added 20 September 2026 after a clean-room
reproduction observed that this suite had no numeric case. Evidence: MODEL."""

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent / "model"))

from script_limits import (                                              # noqa: E402
    MAX_NUM_SIZE_2010, measure_numeric, numeric_cap_check, oversize_numeric_script, v01_valid,
)


def test_v01_accepts_a_nine_byte_operand():
    s = oversize_numeric_script(9)
    assert v01_valid(s)
    ok, peak = measure_numeric(s)
    assert ok and peak == 9


def test_the_2010_cap_rejects_it():
    ok, why = numeric_cap_check(oversize_numeric_script(9))
    assert not ok and "9 bytes > 4" in why


def test_the_cap_bites_exactly_at_five_bytes():
    assert numeric_cap_check(oversize_numeric_script(4)) == (True, "ok")
    assert numeric_cap_check(oversize_numeric_script(5))[0] is False
    assert MAX_NUM_SIZE_2010 == 4


def test_the_cap_reads_operands_not_results():
    # 1 << 64 produces a 9-byte result from 1-byte operands; the 2010 check sits inside the read,
    # so the result is not capped (the clean-room reproducer's observation, confirmed upstream)
    s = [bytes([1]), bytes([64]), "OP_LSHIFT", "OP_SIZE", bytes([9]), "OP_NUMEQUAL"]
    assert v01_valid(s)
    assert numeric_cap_check(s) == (True, "ok")


def test_a_structural_failure_is_reported_as_v01s_own():
    ok, why = numeric_cap_check(["OP_ADD"])          # underflow: v0.1 rejects before any cap applies
    assert not ok and why.startswith("structural error")
