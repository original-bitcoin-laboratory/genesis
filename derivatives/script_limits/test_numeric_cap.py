"""The numeric-operand cap, executed: v0.1's unbounded CBigNum accepts a 9-byte operand that the
2010 four-byte cap (nMaxNumSize = 4, 4bd188c43) rejects, and that the July 2010 cap (258,
757f0769d) still accepts. Added 20 September 2026 after a clean-room reproduction observed that this
suite had no numeric case; the July stage added the same day after an adversarial review observed
that the suite omitted the 258 -> 4 step the register records. Evidence: MODEL."""

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent / "model"))

from script_limits import (                                              # noqa: E402
    MAX_NUM_SIZE_2010, MAX_NUM_SIZE_JULY_2010, measure_numeric, numeric_cap_check,
    oversize_numeric_script, v01_valid,
)

JULY_CAP = 258     # 757f0769d, 29 Jul 2010
AUGUST_CAP = 4     # 4bd188c43, 15 Aug 2010


def test_v01_accepts_a_nine_byte_operand():
    s = oversize_numeric_script(9)
    assert v01_valid(s)
    assert measure_numeric(s) == (True, 9)


def test_the_august_2010_cap_rejects_it_and_the_july_cap_does_not():
    s = oversize_numeric_script(9)
    assert numeric_cap_check(s, AUGUST_CAP) == (False, "numeric-operand")
    assert numeric_cap_check(s, JULY_CAP) == (True, "ok")


def test_the_july_cap_bites_at_259_bytes():
    assert numeric_cap_check(oversize_numeric_script(258), JULY_CAP) == (True, "ok")
    assert numeric_cap_check(oversize_numeric_script(259), JULY_CAP) == (False, "numeric-operand")


def test_the_august_cap_bites_exactly_at_five_bytes():
    assert numeric_cap_check(oversize_numeric_script(4), AUGUST_CAP) == (True, "ok")
    assert numeric_cap_check(oversize_numeric_script(5), AUGUST_CAP) == (False, "numeric-operand")
    assert (MAX_NUM_SIZE_JULY_2010, MAX_NUM_SIZE_2010) == (JULY_CAP, AUGUST_CAP)


def test_the_cap_reads_operands_not_results():
    # 1 << 64 produces a 9-byte result from 1-byte operands; the 2010 check sits inside the read,
    # so the result is not capped (the clean-room reproducer's observation, confirmed upstream)
    s = [bytes([1]), bytes([64]), "OP_LSHIFT", "OP_SIZE", bytes([9]), "OP_NUMEQUAL"]
    assert v01_valid(s)
    assert numeric_cap_check(s, AUGUST_CAP) == (True, "ok")


def test_a_structural_failure_is_reported_as_v01s_own():
    assert numeric_cap_check(["OP_ADD"]) == (False, "structural")   # underflow: v0.1 rejects first
