"""JAN09-X full-vocabulary Script — nothing disabled.

The released v0.1.0 EvalScript already runs the broad vocabulary that BTC later
removed (`OP_CAT`, `OP_MUL`, `OP_DIV`, `OP_LSHIFT`, `OP_INVERT`, `OP_2MUL`, …). The
**one** functional opcode Satoshi disabled in v0.1 is **`OP_NOTEQUAL`** (byte-level
inequality), commented out at `script.cpp:486` with the reason (`script.cpp:494`):

    "OP_NOTEQUAL is disabled because it would be too easy to say something like
     n != 1 and have some wiseguy pass in 1 with extra zero bytes after it
     (numerically, 0x01 == 0x0001 == 0x000001)"

JAN09-X **re-opens it** (the lab's "nothing disabled" mandate) — a **NEW-EXP**
decision, disclosed here *with* Satoshi's malleability caveat. Semantically
`OP_NOTEQUAL(x1 x2 -> bool)` is byte-level `!(x1 == x2)`, i.e. exactly
`OP_EQUAL` followed by `OP_NOT` (both live in v0.1), so it is realised on the lab's
own executed engine without inventing new behaviour. Evidence level: MODEL.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "model"))
from evalscript_model import run, valid                # noqa: E402

# The only functional opcode v0.1's EvalScript disables (inventory/OPCODES.md).
DISABLED_IN_V01 = {"OP_NOTEQUAL"}
NOTEQUAL_CAVEAT = (
    "byte-level inequality; v0.1 disabled it (script.cpp:494) because byte-unequal "
    "values can be numerically equal (0x01 == 0x0001) — use OP_NUMNOTEQUAL for numbers"
)


def _expand(tokens: list) -> list:
    """OP_NOTEQUAL == OP_EQUAL then OP_NOT (byte-equal, negated)."""
    out = []
    for t in tokens:
        if t == "OP_NOTEQUAL":
            out += ["OP_EQUAL", "OP_NOT"]
        else:
            out.append(t)
    return out


def run_full(tokens: list, *checker):
    """Run under JAN09-X's full vocabulary (nothing disabled). Re-enables
    OP_NOTEQUAL. Same signature as the model's run()."""
    return run(_expand(tokens), *checker)


def valid_full(tokens: list, *checker) -> bool:
    return valid(_expand(tokens), *checker)


def op_notequal(x1: bytes, x2: bytes) -> bool:
    """Direct byte-level OP_NOTEQUAL, for reference/tests."""
    return x1 != x2
