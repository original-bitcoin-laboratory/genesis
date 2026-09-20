"""Executable reproduction of v0.1's missing Script resource limits -- MODEL.

Makes runnable the other CONSENSUS_SURFACE.md finding: v0.1's EvalScript enforces
**no** resource ceilings -- no per-element size limit, no op-count limit, no stack-size limit,
no numeric-operand cap. The v0.1 interpreter (`../model/evalscript_model.py`, the same one
differential-tested against the C++/OpenSSL PORT) has only *underflow* guards
(`if stack.size() < N`), no upper bound; the 2010 ceilings are absent.

Same shape as ../overflow/ and ../crypto_conformance/: one engine, the v0.1 rule vs the
later hardened rule, side by side. We run each script on the REAL v0.1 model -- it completes
and validates -- while MEASURING (through the model's trace hook) the peak element size,
op count, and peak stack it actually reached; then we apply the dated 2010 limits and
show they reject exactly what v0.1 accepted.

The ceilings, each dated to the commit that installed it (docs/CONSENSUS-ATLAS.md, OBL-C-0002):

    element size   5000 in 757f0769d (29 Jul 2010, 0.3.6) -> 520 in 4bd188c43 (15 Aug 2010, 0.3.10)
    stack depth    1000 (stack + altstack) in 757f0769d
    numeric cap    258 in 757f0769d -> 4 in 4bd188c43
    script size    20000 in 757f0769d -> 10000 in 6ff5f718b (31 Jul 2010, 0.3.7)
    op count       `nOpCount++ > 200` in 6ff5f718b ("additional security limits"), i.e. 201 allowed;
                   `opcode > OP_16 && ++nOpCount > 201` in f1e1fb4bd (7 Sep 2010), same boundary,
                   pushes and OP_1..OP_16 excluded from the count (the form modelled here)

(Until 20 September 2026 this module's README dated the op-count limit to the 29 July and 15 August
commits; neither carries it. An adversarial review caught that, and the atlas now dates it.)

Every check returns (ok, clause), where `clause` is one identifier from CLAUSES, so a test asserts
the clause that fired and not a substring of a sentence this module wrote.

Evidence level: MODEL (the executed v0.1 interpreter; the ceilings are the dated constants of the
2010 Script hardening). Not a live-exploit claim.
"""

from __future__ import annotations

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "model"))
import evalscript_model as evalmodel                                     # noqa: E402
from evalscript_model import num, valid                                  # noqa: E402

# -- the ceilings the 2010 Script hardening added (all ABSENT in v0.1) --------
MAX_SCRIPT_ELEMENT_SIZE = 520     # bytes, per stack element (4bd188c43; 5000 in 757f0769d)
MAX_OPS_PER_SCRIPT = 201          # opcodes past OP_16 (6ff5f718b as `nOpCount++ > 200`; f1e1fb4bd form)
MAX_STACK_SIZE = 1000             # stack + altstack elements (757f0769d)
MAX_NUM_SIZE_JULY_2010 = 258      # nMaxNumSize in 757f0769d (29 Jul 2010)
MAX_NUM_SIZE_2010 = 4             # nMaxNumSize in 4bd188c43 (15 Aug 2010)

CLAUSES = ("ok", "structural", "op-count", "element-size", "stack-size", "numeric-operand")


def _counts_as_op(op) -> bool:
    """nOpCount as f1e1fb4bd counts it: an opcode with value > OP_16 (data pushes / OP_0..OP_16 don't)."""
    return isinstance(op, str) and op not in evalmodel._PUSH_NUM


def measure(script: list):
    """Run the REAL v0.1 model, recording (ok, peak_element, op_count, peak_stack).

    The trace hook fires with the stack state *before* each op (= state after the
    previous op); we also fold in the final returned stack, so the peaks are exact.
    """
    peak_elem = 0
    peak_stack = 0

    def tr(pc, op, stack, altstack):
        nonlocal peak_elem, peak_stack
        peak_stack = max(peak_stack, len(stack) + len(altstack))
        for e in stack:
            peak_elem = max(peak_elem, len(e))
        for e in altstack:
            peak_elem = max(peak_elem, len(e))

    ok, stack = evalmodel.run(script, trace=tr)
    peak_stack = max(peak_stack, len(stack))
    for e in stack:
        peak_elem = max(peak_elem, len(e))
    op_count = sum(1 for op in script if _counts_as_op(op))
    return ok, peak_elem, op_count, peak_stack


def hardened_check(script: list):
    """Apply the 2010 resource limits to a genuine v0.1 execution. (ok, clause)."""
    ok, peak_elem, op_count, peak_stack = measure(script)
    if not ok:
        return False, "structural"                       # v0.1 itself rejects: no ceiling applies
    if op_count > MAX_OPS_PER_SCRIPT:
        return False, "op-count"
    if peak_elem > MAX_SCRIPT_ELEMENT_SIZE:
        return False, "element-size"
    if peak_stack > MAX_STACK_SIZE:
        return False, "stack-size"
    return True, "ok"


def v01_valid(script: list) -> bool:
    """The v0.1 verdict: EvalScript ran without structural error and left true -- no limits."""
    return valid(script)


# -- the numeric-operand cap (added 20 September 2026, after a clean-room reproduction asked for it) --
# opcodes whose operands v0.1 reads through CBigNum(vch), with how many stack elements they read that way;
# in 757f0769d that read is guarded by `stacktop(-k).size() > nMaxNumSize` (258) and in 4bd188c43 it
# becomes CastToBigNum, which throws when the element is over nMaxNumSize (4); EvalScript catches the
# throw and fails the script
_NUMERIC_ARITY = {
    "OP_1ADD": 1, "OP_1SUB": 1, "OP_2MUL": 1, "OP_2DIV": 1, "OP_NEGATE": 1, "OP_ABS": 1, "OP_NOT": 1,
    "OP_0NOTEQUAL": 1,
    "OP_ADD": 2, "OP_SUB": 2, "OP_MUL": 2, "OP_DIV": 2, "OP_MOD": 2, "OP_LSHIFT": 2, "OP_RSHIFT": 2,
    "OP_BOOLAND": 2, "OP_BOOLOR": 2, "OP_NUMEQUAL": 2, "OP_NUMEQUALVERIFY": 2, "OP_NUMNOTEQUAL": 2,
    "OP_LESSTHAN": 2, "OP_GREATERTHAN": 2, "OP_LESSTHANOREQUAL": 2, "OP_GREATERTHANOREQUAL": 2,
    "OP_MIN": 2, "OP_MAX": 2, "OP_WITHIN": 3,
    "OP_PICK": 1, "OP_ROLL": 1, "OP_SUBSTR": 2, "OP_LEFT": 1, "OP_RIGHT": 1,
}


def measure_numeric(script: list):
    """Run the REAL v0.1 model and record the largest element a numeric opcode read as a number."""
    peak_num = 0

    def tr(pc, op, stack, altstack):
        nonlocal peak_num
        k = _NUMERIC_ARITY.get(op)
        if k and len(stack) >= k:
            for e in stack[-k:]:
                peak_num = max(peak_num, len(e))

    ok, _stack = evalmodel.run(script, trace=tr)
    return ok, peak_num


def numeric_cap_check(script: list, cap: int = MAX_NUM_SIZE_2010):
    """The 2010 cap applied to a genuine v0.1 execution: (ok, clause). `cap` selects the July (258)
    or August (4) value."""
    ok, peak_num = measure_numeric(script)
    if not ok:
        return False, "structural"
    if peak_num > cap:
        return False, "numeric-operand"
    return True, "ok"


def oversize_numeric_script(nbytes: int = 9) -> list:
    """Adds two `nbytes`-byte little-endian numbers (5 and 5, padded) and checks the sum is 10:
    valid on v0.1, whose CBigNum is unbounded; over the 2010 four-byte cap."""
    five = bytes([5]) + bytes(nbytes - 1)
    return [five, five, "OP_ADD", bytes([10]), "OP_NUMEQUAL"]


# -- three scripts, each valid on v0.1 but over a 2010 ceiling ----------------
def oversize_element_script(size: int = 600) -> list:
    """Pushes a `size`-byte element (> 520), drops it, leaves true."""
    return [b"\xab" * size, "OP_DROP", "OP_1"]


def too_many_ops_script(n: int = 250) -> list:
    """`n` counted opcodes (OP_NOP), then true. Pushes wouldn't count; NOPs do."""
    return ["OP_NOP"] * n + ["OP_1"]


def oversize_stack_script(n: int = 1500) -> list:
    """Grows the stack to `n` elements with pushes (op_count stays 0), top stays true."""
    return ["OP_1"] * n


def demo() -> None:
    cases = [
        ("600-byte element (> 520)", oversize_element_script()),
        ("250 opcodes (> 201)",      too_many_ops_script()),
        ("1500-deep stack (> 1000)", oversize_stack_script()),
    ]
    for label, script in cases:
        ok, elem, ops, depth = measure(script)
        hard_ok, why = hardened_check(script)
        print(f"{label}")
        print(f"  v0.1 EvalScript (no limits) : {'VALID' if v01_valid(script) else 'invalid'}"
              f"   (peak elem {elem}B, ops {ops}, stack {depth})")
        print(f"  2010 hardened rule          : {'accept' if hard_ok else 'REJECT'}  (clause: {why})")
    s = oversize_numeric_script(9)
    print("9-byte numeric operand")
    print(f"  v0.1 EvalScript (no cap)    : {'VALID' if v01_valid(s) else 'invalid'}")
    print(f"  29 Jul 2010 cap (258)       : {numeric_cap_check(s, MAX_NUM_SIZE_JULY_2010)}")
    print(f"  15 Aug 2010 cap (4)         : {numeric_cap_check(s)}")


if __name__ == "__main__":
    demo()
