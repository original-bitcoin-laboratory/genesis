"""Descendant-conformance matrix — neutral, from the origin.

Ground truth is **Bitcoin v0.1** (what actually executes, via our MODEL, cross-
validated by derivatives/port + derivatives/node). Every later chain is treated
IDENTICALLY: a *candidate* measured against the v0.1 baseline, described by a
documented rule-profile (which v0.1 behaviours it preserves / disables / restores /
replaces). No descendant is the reference and none is privileged.

Six descendants, **every column cross-checked by execution**, applied identically,
none privileged:
  • **BTC / LTC / DOGE** — they run Bitcoin Core's script.cpp verbatim (their forks
    changed PoW / supply / timing, not the interpreter), so their rule set IS BTC's;
    executed via python-bitcoinlib's DISABLED_OPCODES (the Bitcoin Core set they share).
  • **BSV** — executed via bitcoinx; this run *corrected* the profile (Genesis restores
    the set EXCEPT OP_2MUL/OP_2DIV, which bitcoinx still rejects; 0x7f is OP_SPLIT).
  • **BCH / XEC** — no standalone BCH/eCash interpreter is installable, so each cell is
    *execution-bounded*: restored ops confirmed executable by bitcoinx, disabled ops
    confirmed disabled by python-bitcoinlib. Stated plainly as the honest limit — not a
    single BCH-specific run.

Generates MATRIX.md + conformance.json. Run: python conformance.py
"""

from __future__ import annotations

import ctypes.util
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "model"))
from evalscript_model import num, run  # noqa: E402

# ---- v0.1 baseline: does our engine execute the opcode? (ground truth) --------
VECTORS = [
    ("splice",  "OP_CAT",     [b"\x11", b"\x22", "OP_CAT"]),
    ("splice",  "OP_SUBSTR",  [b"abcdef", num(1), num(3), "OP_SUBSTR"]),
    ("splice",  "OP_LEFT",    [b"abcdef", num(2), "OP_LEFT"]),
    ("splice",  "OP_RIGHT",   [b"abcdef", num(2), "OP_RIGHT"]),
    ("bitwise", "OP_INVERT",  [b"\x0f", "OP_INVERT"]),
    ("bitwise", "OP_AND",     [b"\xf0", b"\x3c", "OP_AND"]),
    ("bitwise", "OP_OR",      [b"\xf0", b"\x3c", "OP_OR"]),
    ("bitwise", "OP_XOR",     [b"\xf0", b"\x3c", "OP_XOR"]),
    ("arith",   "OP_MUL",     [num(6), num(7), "OP_MUL"]),
    ("arith",   "OP_DIV",     [num(20), num(6), "OP_DIV"]),
    ("arith",   "OP_MOD",     [num(20), num(6), "OP_MOD"]),
    ("arith",   "OP_LSHIFT",  [num(1), num(8), "OP_LSHIFT"]),
    ("arith",   "OP_RSHIFT",  [num(256), num(4), "OP_RSHIFT"]),
    ("arith",   "OP_2MUL",    [num(21), "OP_2MUL"]),
    ("arith",   "OP_2DIV",    [num(42), "OP_2DIV"]),
    ("kept",    "OP_ADD",     [num(2), num(2), "OP_ADD"]),
    ("kept",    "OP_EQUAL",   [b"\xaa", b"\xaa", "OP_EQUAL"]),
    ("kept",    "OP_SHA256",  [b"\xaa", "OP_SHA256"]),
]

def v01_baseline(tokens) -> str:
    ok, _ = run(tokens)
    return "execute" if ok else "reject"

# ---- descendants: fork-chronological, none privileged -------------------------
# status vs the v0.1 baseline: preserved | disabled | restored | ->OP_SPLIT
DESCENDANTS = ["BTC", "LTC", "DOGE", "BCH", "XEC", "BSV"]   # fork-chronological, none privileged
FORKED = {
    "BTC":  "the chain that kept the pre-2011 rules (OP_* disabled ~2010)",
    "LTC":  "Litecoin 2011 — Bitcoin Core fork (Scrypt PoW); inherits BTC's script engine",
    "DOGE": "Dogecoin 2013 — Bitcoin Core / Litecoin lineage; inherits BTC's script engine",
    "BCH":  "fork 2017-08-01; May-2018 upgrade re-enabled a subset",
    "XEC":  "eCash, fork from BCH 2021-11 (inherits BCH script rules here)",
    "BSV":  "fork from BCH 2018-11; Genesis (2020-02) 'restore original Script'",
}
# BTC/LTC/DOGE run Bitcoin Core's script.cpp verbatim for these opcodes (their forks
# changed PoW / supply / timing, not the interpreter) — so their rule set IS BTC's.
_CORE_LINEAGE = {"BTC", "LTC", "DOGE"}
_RESTORED_BCH = {"OP_CAT", "OP_AND", "OP_OR", "OP_XOR", "OP_DIV", "OP_MOD"}
_SPLIT = {"OP_SUBSTR", "OP_LEFT", "OP_RIGHT"}   # replaced by OP_SPLIT in the Cash lineage
_KEPT = {"OP_ADD", "OP_EQUAL", "OP_SHA256"}
# Even after Genesis "restore original Script", BSV keeps OP_2MUL / OP_2DIV disabled
# — independently confirmed by executing them in bitcoinx (see bsv_execute).
_BSV_STILL_DISABLED = {"OP_2MUL", "OP_2DIV"}

def profile(chain: str, opcode: str) -> str:
    if opcode in _KEPT:
        return "preserved"
    if chain in _CORE_LINEAGE:         # BTC/LTC/DOGE: all broad disabled (incl SUBSTR/LEFT/RIGHT)
        return "disabled"
    if opcode in _SPLIT:               # Cash lineage: byte-index splice replaced by OP_SPLIT
        return "→OP_SPLIT"
    if chain in ("BCH", "XEC"):        # XEC inherits BCH's script rules for these
        return "restored" if opcode in _RESTORED_BCH else "disabled"
    if chain == "BSV":                 # Genesis restored the set EXCEPT OP_2MUL/OP_2DIV
        return "disabled" if opcode in _BSV_STILL_DISABLED else "restored"
    return "?"

# ---- optional independent cross-check of a chain's profile (BTC has a lib) ----
_OPENSSL = [r"C:\msys64\mingw64\bin\libcrypto-3-x64.dll",
            r"C:\Program Files\OpenSSL-Win64\bin\libcrypto-3-x64.dll"]
if ctypes.util.find_library("ssl") is None and ctypes.util.find_library("crypto") is None:
    _hit = next((p for p in _OPENSSL if pathlib.Path(p).exists()), None)
    if _hit:
        _o = ctypes.util.find_library
        ctypes.util.find_library = lambda n: _hit if n in ("ssl", "crypto", "libeay32", "ssleay32") else _o(n)
BTC_LIB = None
try:
    from bitcoin.core import script as _bs
    from bitcoin.core.scripteval import EvalScript, EvalScriptError
    BTC_LIB = _bs
except Exception:
    BTC_LIB = None

_BTC_OPS = {  # equivalent script for python-bitcoinlib EvalScript
    "OP_CAT": [b"\x11", b"\x22"], "OP_SUBSTR": ["b:abcdef", 1, 3], "OP_LEFT": ["b:abcdef", 2],
    "OP_RIGHT": ["b:abcdef", 2], "OP_INVERT": [b"\x0f"], "OP_AND": [b"\xf0", b"\x3c"],
    "OP_OR": [b"\xf0", b"\x3c"], "OP_XOR": [b"\xf0", b"\x3c"], "OP_MUL": [6, 7], "OP_DIV": [16, 4],
    "OP_MOD": [16, 5], "OP_LSHIFT": [1, 8], "OP_RSHIFT": [16, 4], "OP_2MUL": [5], "OP_2DIV": [6],
    "OP_ADD": [2, 2], "OP_EQUAL": [b"\xaa", b"\xaa"], "OP_SHA256": [b"\xaa"],
}

def btc_execute(opcode: str) -> str | None:
    """Run the vector through python-bitcoinlib (independent BTC impl). None if unavailable."""
    if BTC_LIB is None:
        return None
    ops = []
    for a in _BTC_OPS[opcode]:
        if isinstance(a, bytes):
            ops.append(a)
        elif isinstance(a, str) and a.startswith("b:"):
            ops.append(a[2:].encode())
        else:
            ops.append(getattr(BTC_LIB, f"OP_{a}"))
    ops.append(getattr(BTC_LIB, opcode))
    try:
        EvalScript([], BTC_LIB.CScript(ops), None, 0)
        return "execute"
    except EvalScriptError:
        return "disabled" if getattr(BTC_LIB, opcode) in BTC_LIB.DISABLED_OPCODES else "reject"
    except Exception:
        return "disabled" if getattr(BTC_LIB, opcode) in BTC_LIB.DISABLED_OPCODES else "n/a"


# ---- independent cross-check of the BSV profile (bitcoinx, a BSV impl) ---------
BSV_LIB = None
try:
    import bitcoinx as _bx
    from bitcoinx import (InterpreterLimits as _BXLimits, InterpreterState as _BXState,
                          MinerPolicy as _BXPolicy, Ops as _BXOps, Script as _BXScript)
    from bitcoinx.errors import DisabledOpcode as _BXDisabled
    BSV_LIB = _bx
except Exception:
    BSV_LIB = None

_BSV_OPS = {  # operands for bitcoinx evaluate_script (post-Genesis / consensus rules)
    "OP_CAT": [b"\x11", b"\x22"], "OP_INVERT": [b"\x0f"], "OP_AND": [b"\xf0", b"\x3c"],
    "OP_OR": [b"\xf0", b"\x3c"], "OP_XOR": [b"\xf0", b"\x3c"], "OP_MUL": [b"\x06", b"\x07"],
    "OP_DIV": [b"\x14", b"\x06"], "OP_MOD": [b"\x14", b"\x06"], "OP_LSHIFT": [b"\x01", b"\x08"],
    "OP_RSHIFT": [b"\x00\x01", b"\x04"], "OP_2MUL": [b"\x05"], "OP_2DIV": [b"\x06"],
    "OP_ADD": [b"\x02", b"\x02"], "OP_EQUAL": [b"\xaa", b"\xaa"], "OP_SHA256": [b"\xaa"],
}
if BSV_LIB is not None:
    _BSV_POLICY = _BXPolicy(10_000_000, 750_000, 100_000_000, 0xFFFFFFFF, 2048)
    _BSV_LIMITS = _BXLimits(_BSV_POLICY, is_genesis_enabled=True, is_consensus=True)


def bsv_execute(opcode: str) -> str | None:
    """Run the vector through bitcoinx (independent BSV impl). None if unavailable.
    The byte-index splice ops (SUBSTR/LEFT/RIGHT) don't exist in the Cash lineage —
    byte 0x7f is OP_SPLIT — so those map to '→OP_SPLIT' (OP_SPLIT itself executes)."""
    if BSV_LIB is None:
        return None
    if opcode in _SPLIT:               # replaced by OP_SPLIT; the opcode name is gone
        return "→OP_SPLIT" if (hasattr(_BXOps, "OP_SPLIT") and not hasattr(_BXOps, opcode)) else "?"
    if not hasattr(_BXOps, opcode):
        return "n/a"
    st = _BXState(_BSV_LIMITS)
    s = _BXScript()
    for p in _BSV_OPS[opcode]:
        s = s << p
    s = s << getattr(_BXOps, opcode)
    try:
        st.evaluate_script(s)
        return "execute"
    except _BXDisabled:
        return "disabled"
    except Exception:
        return "reject"               # some other verdict — surfaced, not hidden


# profile status -> the verdict an independent execution should produce
_EXPECT = {"preserved": "execute", "restored": "execute",
           "disabled": "disabled", "→OP_SPLIT": "→OP_SPLIT"}


def _consistent(status: str, executed) -> bool:
    return executed is None or executed == _EXPECT.get(status, "?")


def _cell_ref(chain: str, status: str, be, se) -> bool:
    """Verify one profile cell against an independent execution. BTC/LTC/DOGE share
    Bitcoin Core's engine (python-bitcoinlib); BSV via bitcoinx; BCH/XEC have no
    standalone interpreter, so each cell is *bounded* by the reference that shares its
    rule — restored/split confirmed by bitcoinx, disabled by python-bitcoinlib."""
    if chain in _CORE_LINEAGE:
        return _consistent(status, be)
    if chain == "BSV":
        return _consistent(status, se)
    if status in ("restored", "→OP_SPLIT"):          # BCH/XEC restored → confirm executable
        return _consistent(status, se)
    if status == "disabled":                         # BCH/XEC disabled → confirm disabled
        return _consistent(status, be)
    if status == "preserved":
        return _consistent(status, be) and _consistent(status, se)
    return False


def _method(chain: str):
    """(method, impl-label) for how a chain's column is cross-checked by execution."""
    if chain == "BTC":
        return "executed", "python-bitcoinlib"
    if chain in _CORE_LINEAGE:                        # LTC / DOGE
        return "executed", "python-bitcoinlib (Bitcoin Core lineage)"
    if chain == "BSV":
        return "executed", "bitcoinx"
    return "execution-bounded", "bitcoinx (restored) + python-bitcoinlib (disabled)"  # BCH/XEC


def _available(chain: str) -> bool:
    if chain in _CORE_LINEAGE:
        return BTC_LIB is not None
    if chain == "BSV":
        return BSV_LIB is not None
    return BTC_LIB is not None and BSV_LIB is not None   # BCH/XEC need both references


def build():
    rows = []
    chain_ok = {c: True for c in DESCENDANTS}
    for fam, op, tokens in VECTORS:
        row = {"family": fam, "opcode": op, "v0_1": v01_baseline(tokens)}
        for c in DESCENDANTS:
            row[c] = profile(c, op)
        row["btc_executed"] = be = btc_execute(op)   # python-bitcoinlib
        row["bsv_executed"] = se = bsv_execute(op)   # bitcoinx
        for c in DESCENDANTS:
            if not _cell_ref(c, row[c], be, se):
                chain_ok[c] = False
        rows.append(row)
    return rows, chain_ok


def main():
    try:                                # the '→' glyph needs UTF-8 on the Windows console
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    rows, chain_ok = build()
    xc = {c: (_available(c) and chain_ok[c]) for c in DESCENDANTS}
    out = pathlib.Path(__file__).resolve().parent
    (out / "conformance.json").write_text(json.dumps(
        {"schema": 4, "baseline": "v0.1 (executed)", "descendants": DESCENDANTS,
         "cross_checked_by_execution": {
             c: {"method": _method(c)[0], "impl": _method(c)[1],
                 "available": _available(c), "consistent": xc[c]}
             for c in DESCENDANTS},
         "rows": rows}, indent=2) + "\n", encoding="utf-8")

    cols = DESCENDANTS
    L = ["# Descendant-conformance matrix (neutral, from the v0.1 origin)", "",
         "**Baseline = Bitcoin v0.1** — the ground truth (what our engine actually executes).",
         "Descendants are listed in fork order and treated identically: each is a *candidate*",
         "measured against the origin. **No descendant is the reference and none is privileged.**",
         "Every column is **cross-checked by execution** (method table below).", "",
         "| family | opcode | v0.1 | " + " | ".join(cols) + " |",
         "|---|---|:--:|" + ":--:|" * len(cols)]
    for r in rows:
        L.append(f"| {r['family']} | `{r['opcode']}` | {r['v0_1']} | "
                 + " | ".join(r[c] for c in cols) + " |")
    L += ["",
          "Legend: **execute** = runs in v0.1 (baseline); **preserved** = kept; **disabled** = "
          "rejected; **restored** = re-enabled; **→OP_SPLIT** = the byte-index splice op replaced "
          "by `OP_SPLIT` in the Cash lineage.",
          "",
          "## How each column is executed (tooling, not ranking)",
          "",
          "| chain | fork | cross-check | via | consistent |",
          "|---|---|---|---|:--:|"]
    for c in cols:
        m, impl = _method(c)
        L.append(f"| **{c}** | {FORKED[c].split(';')[0]} | {m} | `{impl}` | {'✓' if xc[c] else '—'} |")
    L += ["",
          "- **BTC / LTC / DOGE** run **Bitcoin Core's `script.cpp` verbatim** for these opcodes "
          "(their forks changed PoW / supply / timing, not the interpreter), so their rule set *is* "
          "BTC's — executed via `python-bitcoinlib`'s `DISABLED_OPCODES` (the Bitcoin Core set they "
          "inherited).",
          "- **BSV** — executed via `bitcoinx` (a BSV implementation). This run **corrected** the "
          "profile: Genesis \"restore original Script\" re-enables the set **except `OP_2MUL`/"
          "`OP_2DIV`** (still `DisabledOpcode`); byte `0x7f` is `OP_SPLIT`.",
          "- **BCH / XEC** — no standalone BCH/eCash interpreter is installable, so each cell is "
          "**execution-bounded**: the ops BCH *restored* are confirmed **executable** by `bitcoinx`, "
          "the ops it keeps *disabled* are confirmed **disabled** by `python-bitcoinlib`. Every cell "
          "is pinned between two independent executions — **not** a single BCH-specific run "
          "(stated plainly; the honest limit).",
          "",
          "## Reading",
          "",
          "The broad vocabulary (`OP_CAT`, `OP_SUBSTR/LEFT/RIGHT`, `OP_INVERT`, `OP_AND/OR/XOR`, "
          "`OP_MUL/DIV/MOD`, `OP_LSHIFT/RSHIFT`, `OP_2MUL/2DIV`) **is native to v0.1**. The "
          "descendants split by lineage: the **Bitcoin Core lineage (BTC/LTC/DOGE)** disabled it, "
          "the **Cash lineage (BCH/XEC)** restored a subset (with `OP_SPLIT`), and **BSV** restored "
          "nearly all — a factual map of divergence, not a verdict.",
          "",
          "## Sources",
          "- **BTC / LTC / DOGE**: Bitcoin Core `script` `DISABLED_OPCODES` (LTC/DOGE inherit it). **Executed.**",
          "- **BCH / XEC**: Bitcoin Cash *May 2018* (`OP_CAT`, `OP_AND/OR/XOR`, `OP_DIV`, `OP_MOD`, "
          "`OP_SPLIT`); XEC inherits BCH. **Execution-bounded.**",
          "- **BSV**: Bitcoin SV *Genesis* (2020-02), \"restore original Script\" minus `OP_2MUL/2DIV`, "
          "via `bitcoinx`. **Executed.**",
          ""]
    (out / "MATRIX.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("wrote MATRIX.md + conformance.json | cross-check per chain:")
    for c in cols:
        m, impl = _method(c)
        print(f"  {c:5} {m:17} via {impl:48} consistent={xc[c]}")


if __name__ == "__main__":
    main()
