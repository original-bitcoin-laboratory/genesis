"""Executable reproduction of v0.1's missing Script resource limits -- MODEL.

Makes runnable the other CONSENSUS_SURFACE.md finding: v0.1's EvalScript enforces
**no** resource ceilings -- no per-element size limit (520 bytes), no op-count limit
(201), no stack-size limit (1000). The v0.1 interpreter (`../model/evalscript_model.py`,
the same one differential-tested against the C++/OpenSSL PORT) has only *underflow*
guards (`if stack.size() < N`), never an upper bound; the modern/2010 ceilings are absent.

Same shape as ../overflow/ and ../crypto_conformance/: one engine, the v0.1 rule vs the
later hardened rule, side by side. We run each script on the REAL v0.1 model -- it completes
and validates -- while MEASURING (through the model's trace hook) the peak element size,
op count, and peak stack it actually reached; then we apply the documented 2010 limits and
show they reject exactly what v0.1 accepted.

Evidence level: MODEL (the executed v0.1 interpreter; the ceilings are the documented
constants introduced in the 2010 Script hardening). Not a live-exploit claim.
"""

from __future__ import annotations

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "model"))
import evalscript_model as evalmodel                                     # noqa: E402
from evalscript_model import num, valid                                  # noqa: E402

# -- the ceilings the 2010 Script hardening added (all ABSENT in v0.1) --------
MAX_SCRIPT_ELEMENT_SIZE = 520     # bytes, per stack element
MAX_OPS_PER_SCRIPT = 201          # opcodes past OP_16 (pushes don't count)
MAX_STACK_SIZE = 1000             # stack + altstack elements


def _counts_as_op(op) -> bool:
    """Modern nOpCount: an opcode with value > OP_16 (data pushes / OP_0..OP_16 don't)."""
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
    """Apply the 2010 resource limits to a genuine v0.1 execution. (ok, reason)."""
    ok, peak_elem, op_count, peak_stack = measure(script)
    if not ok:
        return False, "structural error (v0.1 itself rejects)"
    if op_count > MAX_OPS_PER_SCRIPT:
        return False, f"op count {op_count} > {MAX_OPS_PER_SCRIPT}"
    if peak_elem > MAX_SCRIPT_ELEMENT_SIZE:
        return False, f"element size {peak_elem} > {MAX_SCRIPT_ELEMENT_SIZE}"
    if peak_stack > MAX_STACK_SIZE:
        return False, f"stack size {peak_stack} > {MAX_STACK_SIZE}"
    return True, "ok"


def v01_valid(script: list) -> bool:
    """The v0.1 verdict: EvalScript ran without structural error and left true -- no limits."""
    return valid(script)


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
        print(f"  2010 hardened rule          : {'accept' if hard_ok else 'REJECT'}  ({why})")


if __name__ == "__main__":
    demo()
