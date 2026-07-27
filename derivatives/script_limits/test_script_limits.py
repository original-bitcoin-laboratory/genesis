"""The missing Script resource limits, executed: v0.1's EvalScript validates scripts that
exceed the 2010 ceilings (520-byte element, 201 ops, 1000-deep stack), each of which the
hardened rule rejects. Uses the lab's real v0.1 interpreter to measure the peaks reached.
Evidence: MODEL."""

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent / "model"))

from script_limits import (                                              # noqa: E402
    MAX_OPS_PER_SCRIPT, MAX_SCRIPT_ELEMENT_SIZE, MAX_STACK_SIZE,
    hardened_check, measure, oversize_element_script, oversize_stack_script,
    too_many_ops_script, v01_valid,
)
from evalscript_model import num                                         # noqa: E402


# ---- the finding: v0.1 accepts each, the 2010 rule rejects each ---------------

def test_oversize_element_v01_accepts_hardened_rejects():
    s = oversize_element_script(600)
    assert v01_valid(s)                                  # v0.1: valid
    ok, elem, _, _ = measure(s)
    assert ok and elem == 600 > MAX_SCRIPT_ELEMENT_SIZE  # a 600-byte element really lived
    hard_ok, why = hardened_check(s)
    assert not hard_ok and "element size" in why


def test_too_many_ops_v01_accepts_hardened_rejects():
    s = too_many_ops_script(250)
    assert v01_valid(s)                                  # v0.1: valid
    ok, _, ops, _ = measure(s)
    assert ok and ops == 250 > MAX_OPS_PER_SCRIPT
    hard_ok, why = hardened_check(s)
    assert not hard_ok and "op count" in why


def test_oversize_stack_v01_accepts_hardened_rejects():
    s = oversize_stack_script(1500)
    assert v01_valid(s)                                  # v0.1: valid
    ok, _, ops, depth = measure(s)
    assert ok and depth == 1500 > MAX_STACK_SIZE
    assert ops == 0                                      # grown by pushes: isolates the stack limit
    hard_ok, why = hardened_check(s)
    assert not hard_ok and "stack size" in why


# ---- controls: agree where v0.1 is within the limits -------------------------

def test_normal_script_passes_both():
    s = [num(2), num(3), "OP_ADD", num(5), "OP_EQUAL"]   # 2+3==5
    assert v01_valid(s)
    assert hardened_check(s)[0]


def test_structural_failure_rejected_by_both():
    s = ["OP_ADD"]                                        # underflow: no operands
    assert not v01_valid(s)
    assert not hardened_check(s)[0]


# ---- boundary fidelity: exactly at the ceiling passes, one over fails ---------

def test_op_count_boundary_is_exact():
    at = too_many_ops_script(MAX_OPS_PER_SCRIPT)         # exactly 201 counted ops
    over = too_many_ops_script(MAX_OPS_PER_SCRIPT + 1)   # 202
    assert hardened_check(at)[0]                          # 201 ok
    assert not hardened_check(over)[0]                    # 202 rejected


def test_element_boundary_is_exact():
    at = oversize_element_script(MAX_SCRIPT_ELEMENT_SIZE)      # 520 bytes
    over = oversize_element_script(MAX_SCRIPT_ELEMENT_SIZE + 1)  # 521
    assert hardened_check(at)[0]
    assert not hardened_check(over)[0]


def test_stack_boundary_is_exact():
    at = oversize_stack_script(MAX_STACK_SIZE)           # 1000 deep
    over = oversize_stack_script(MAX_STACK_SIZE + 1)     # 1001
    assert hardened_check(at)[0]
    assert not hardened_check(over)[0]


# ---- the peaks are measured from a genuine v0.1 execution --------------------

def test_pushes_do_not_count_as_ops():
    # OP_1..OP_16 and data pushes must NOT count toward the op limit (modern nOpCount).
    _, _, ops, _ = measure([num(7), b"\x01\x02", "OP_1", "OP_16"])
    assert ops == 0
    _, _, ops2, _ = measure(["OP_DUP", "OP_DROP", "OP_1"])   # DUP + DROP count; OP_1 doesn't
    assert ops2 == 2
