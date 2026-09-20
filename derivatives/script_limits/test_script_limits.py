"""The missing Script resource limits, executed: v0.1's EvalScript validates scripts that
exceed the 2010 ceilings (520-byte element, 201 ops, 1000-deep stack), each of which the
hardened rule rejects. Uses the lab's real v0.1 interpreter to measure the peaks reached.
Evidence: MODEL.

The ceilings are written here as literals (the values the dated commits carry), independently of
the module; every verdict is asserted by the clause identifier that fired."""

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent / "model"))

from script_limits import (                                              # noqa: E402
    CLAUSES, MAX_OPS_PER_SCRIPT, MAX_SCRIPT_ELEMENT_SIZE, MAX_STACK_SIZE,
    hardened_check, measure, oversize_element_script, oversize_stack_script,
    too_many_ops_script, v01_valid,
)
from evalscript_model import num                                         # noqa: E402

ELEMENT_CAP = 520      # 4bd188c43, 15 Aug 2010
OP_CAP = 201           # 6ff5f718b (`nOpCount++ > 200`), 31 Jul 2010; f1e1fb4bd form 7 Sep 2010
STACK_CAP = 1000       # 757f0769d, 29 Jul 2010


# ---- the finding: v0.1 accepts each, the 2010 rule rejects each ---------------

def test_oversize_element_v01_accepts_hardened_rejects():
    s = oversize_element_script(600)
    assert v01_valid(s)                                  # v0.1: valid
    ok, elem, _, _ = measure(s)
    assert ok and elem == 600 > ELEMENT_CAP              # a 600-byte element really lived
    assert hardened_check(s) == (False, "element-size")


def test_too_many_ops_v01_accepts_hardened_rejects():
    s = too_many_ops_script(250)
    assert v01_valid(s)                                  # v0.1: valid
    ok, _, ops, _ = measure(s)
    assert ok and ops == 250 > OP_CAP
    assert hardened_check(s) == (False, "op-count")


def test_oversize_stack_v01_accepts_hardened_rejects():
    s = oversize_stack_script(1500)
    assert v01_valid(s)                                  # v0.1: valid
    ok, _, ops, depth = measure(s)
    assert ok and depth == 1500 > STACK_CAP
    assert ops == 0                                      # grown by pushes: isolates the stack limit
    assert hardened_check(s) == (False, "stack-size")


# ---- controls: agree where v0.1 is within the limits -------------------------

def test_normal_script_passes_both():
    s = [num(2), num(3), "OP_ADD", num(5), "OP_EQUAL"]   # 2+3==5
    assert v01_valid(s)
    assert hardened_check(s) == (True, "ok")


def test_structural_failure_rejected_by_both():
    s = ["OP_ADD"]                                        # underflow: no operands
    assert not v01_valid(s)
    assert hardened_check(s) == (False, "structural")


# ---- boundary fidelity: exactly at the ceiling passes, one over fails ---------

def test_op_count_boundary_is_exact():
    assert hardened_check(too_many_ops_script(OP_CAP)) == (True, "ok")             # 201 ok
    assert hardened_check(too_many_ops_script(OP_CAP + 1)) == (False, "op-count")  # 202 rejected


def test_element_boundary_is_exact():
    assert hardened_check(oversize_element_script(ELEMENT_CAP)) == (True, "ok")
    assert hardened_check(oversize_element_script(ELEMENT_CAP + 1)) == (False, "element-size")


def test_stack_boundary_is_exact():
    assert hardened_check(oversize_stack_script(STACK_CAP)) == (True, "ok")
    assert hardened_check(oversize_stack_script(STACK_CAP + 1)) == (False, "stack-size")


def test_module_constants_equal_the_dated_values_written_here():
    assert (MAX_SCRIPT_ELEMENT_SIZE, MAX_OPS_PER_SCRIPT, MAX_STACK_SIZE) == (ELEMENT_CAP, OP_CAP, STACK_CAP)
    assert set(CLAUSES) == {"ok", "structural", "op-count", "element-size", "stack-size", "numeric-operand"}


# ---- the peaks are measured from a genuine v0.1 execution --------------------

def test_pushes_do_not_count_as_ops():
    # OP_1..OP_16 and data pushes must NOT count toward the op limit (`opcode > OP_16`, f1e1fb4bd).
    _, _, ops, _ = measure([num(7), b"\x01\x02", "OP_1", "OP_16"])
    assert ops == 0
    _, _, ops2, _ = measure(["OP_DUP", "OP_DROP", "OP_1"])   # DUP + DROP count; OP_1 doesn't
    assert ops2 == 2
