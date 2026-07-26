"""Transaction Studio (R7) — a headless script debugger / stack tracer.

The first R7 tool: step a v0.1 Script through the lab's own EvalScript and show the
stack after every opcode, then the verdict. Works over the **full vocabulary**, so
you can watch `OP_CAT` concatenate or `OP_MUL` multiply — the ops BTC disabled.

    from studio import render
    print(render([b"\x11", b"\x22", "OP_CAT", "OP_SHA256", h, "OP_EQUAL"]))

It reads scripts as token lists (bytes = data push, "OP_NAME" = opcode) or from raw
bytes via `disasm`. For a spend it traces the exact v0.1 VerifySignature script
(scriptSig + OP_CODESEPARATOR + scriptPubKey). Evidence level: MODEL.
"""

from __future__ import annotations

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "model"))
from cscript import parse                                # noqa: E402
from evalscript_model import cast_to_bool, run           # noqa: E402


def _short(b: bytes) -> str:
    if not b:
        return "∅"
    hx = b.hex()
    return hx if len(hx) <= 16 else f"{hx[:16]}…({len(b)}B)"


def _op_repr(op) -> str:
    if isinstance(op, (bytes, bytearray)):
        return f"push {_short(op)}"
    return op


def _stack_repr(stk) -> str:
    return "[" + " ".join(_short(b) for b in stk) + "]"


def trace(tokens: list, checker=None):
    """Returns (rows, ok, is_valid) where rows = [(op_repr, stack_after)]."""
    steps = []
    ok, final = run(tokens, checker, trace=lambda pc, op, stk, alt: steps.append((op, stk)))
    rows = []
    for i, (op, _before) in enumerate(steps):
        after = steps[i + 1][1] if i + 1 < len(steps) else final     # after(op i) = before(op i+1)
        rows.append((_op_repr(op), _stack_repr(after)))
    is_valid = ok and len(final) > 0 and cast_to_bool(final[-1])
    return rows, ok, is_valid


def render(tokens: list, checker=None, title: str | None = None) -> str:
    rows, ok, is_valid = trace(tokens, checker)
    w = max((len(op) for op, _ in rows), default=6)
    out = ([title] if title else []) + [
        f"  {'op':<{w}}   stack (after)",
        f"  {'-' * w}   {'-' * 24}",
    ]
    out += [f"  {op:<{w}}   {st}" for op, st in rows]
    verdict = ("VALID — true on top" if is_valid
               else "ran — top not true" if ok
               else "FAILED — structural error")
    out.append(f"  => {verdict}")
    return "\n".join(out)


def disasm(script_bytes: bytes) -> list:
    """Raw script bytes -> token list (for tracing an on-the-wire script)."""
    return parse(script_bytes)


def trace_spend(script_sig_tokens: list, script_pubkey_tokens: list, tx, n_in: int):
    """Trace the v0.1 VerifySignature script for a spend (scriptSig +
    OP_CODESEPARATOR + scriptPubKey), with a signature checker."""
    sys.path.insert(0, str(_HERE.parent / "model"))
    from tx_sighash import SigChecker
    combined = list(script_sig_tokens) + ["OP_CODESEPARATOR"] + list(script_pubkey_tokens)
    return trace(combined, SigChecker(tx, n_in))


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    import hashlib
    from evalscript_model import num

    h1, h2 = b"\x11\x22", b"\x33\x44"
    lock = hashlib.sha256(h1 + h2).digest()
    print(render([h1, h2, "OP_CAT", "OP_SHA256", lock, "OP_EQUAL"],
                 title="OP_CAT hash-lock (BTC-disabled OP_CAT runs here):"))
    print()
    print(render([num(6), num(7), "OP_MUL", num(2), "OP_ADD"],
                 title="arithmetic 6*7+2 (OP_MUL is BTC-disabled):"))
