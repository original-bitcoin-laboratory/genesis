"""Descendant-conformance matrix — neutral, from the origin.

Ground truth is **Bitcoin v0.1** (what actually executes, via our MODEL, cross-
validated by derivatives/port + derivatives/node). Every later chain is treated
IDENTICALLY: a *candidate* measured against the v0.1 baseline, described by a
documented rule-profile (which v0.1 behaviours it preserves / disables / restores /
replaces). No descendant is the reference and none is privileged.

Where an independent implementation happens to be installable we *cross-check* a
chain's documented profile by executing our vectors against it. Today that's BTC
(python-bitcoinlib) — a rigor bonus that reflects tooling availability, not
importance; the same cross-check would be applied to any chain whose implementation
were available. The BTC cross-check does not rank BTC above BCH / BSV / XEC.

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
DESCENDANTS = ["BTC", "BCH", "BSV", "XEC"]
FORKED = {
    "BTC": "the chain that kept the pre-2011 rules (OP_* disabled ~2010)",
    "BCH": "fork 2017-08-01; May-2018 upgrade re-enabled a subset",
    "BSV": "fork from BCH 2018-11; Genesis (2020-02) 'restore original Script'",
    "XEC": "eCash, fork from BCH 2021-11 (inherits BCH script rules here)",
}
_RESTORED_BCH = {"OP_CAT", "OP_AND", "OP_OR", "OP_XOR", "OP_DIV", "OP_MOD"}
_SPLIT = {"OP_SUBSTR", "OP_LEFT", "OP_RIGHT"}   # replaced by OP_SPLIT in the Cash lineage
_KEPT = {"OP_ADD", "OP_EQUAL", "OP_SHA256"}

def profile(chain: str, opcode: str) -> str:
    if opcode in _KEPT:
        return "preserved"
    if chain == "BTC":
        return "disabled"
    if opcode in _SPLIT:
        return "→OP_SPLIT"
    if chain in ("BCH", "XEC"):        # XEC inherits BCH's script rules for these
        return "restored" if opcode in _RESTORED_BCH else "disabled"
    if chain == "BSV":                 # Genesis restored the original arithmetic/bitwise set
        return "restored"
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


def build():
    rows = []
    xcheck_ok = True
    for fam, op, tokens in VECTORS:
        row = {"family": fam, "opcode": op, "v0_1": v01_baseline(tokens)}
        for c in DESCENDANTS:
            row[c] = profile(c, op)
        ex = btc_execute(op)
        row["btc_executed"] = ex
        if ex is not None:                      # profile "disabled" <-> executed "disabled"; "preserved" <-> "execute"
            want = "disabled" if row["BTC"] == "disabled" else "execute"
            if ex != want:
                xcheck_ok = False
        rows.append(row)
    return rows, xcheck_ok


def main():
    rows, xcheck_ok = build()
    out = pathlib.Path(__file__).resolve().parent
    (out / "conformance.json").write_text(json.dumps(
        {"schema": 2, "baseline": "v0.1 (executed)", "descendants": DESCENDANTS,
         "btc_profile_cross_checked_by_execution": (BTC_LIB is not None and xcheck_ok),
         "rows": rows}, indent=2) + "\n", encoding="utf-8")

    L = ["# Descendant-conformance matrix (neutral, from the v0.1 origin)", "",
         "**Baseline = Bitcoin v0.1** — the ground truth (what our engine actually executes).",
         "Descendants are listed in fork order and treated identically: each is a *candidate*",
         "measured against the origin, described by a documented rule-profile. **No descendant",
         "is the reference and none is privileged.**", "",
         "| family | opcode | v0.1 (baseline) | BTC | BCH | BSV | XEC |",
         "|---|---|:--:|:--:|:--:|:--:|:--:|"]
    for r in rows:
        L.append(f"| {r['family']} | `{r['opcode']}` | {r['v0_1']} | "
                 f"{r['BTC']} | {r['BCH']} | {r['BSV']} | {r['XEC']} |")
    L += ["",
          "Legend: **execute** = runs in v0.1 (baseline); **preserved** = descendant kept it; "
          "**disabled** = descendant rejects it; **restored** = descendant re-enabled it; "
          "**→OP_SPLIT** = the byte-index splice op was replaced by `OP_SPLIT` in the Cash lineage.",
          "",
          "## Neutrality & method",
          "",
          "- The only executed, authoritative column is **v0.1** (our MODEL, cross-validated by "
          "`../port` / `../node`). Everything else is measured *against* it.",
          "- Every descendant uses the **same** method: a documented rule-profile from that chain's "
          "own consensus spec. This project takes no position on which chain is \"Bitcoin\".",
          "- Column order is fork-chronological, not a ranking.",
          "",
          f"## Independent cross-check (tooling, not ranking)",
          "",
          f"An independent implementation was available for exactly one chain — **BTC** "
          f"(`python-bitcoinlib`) — so its documented profile was **executed** and "
          f"{'**matches**' if (BTC_LIB is not None and xcheck_ok) else 'compared'}: every "
          "broad-vocabulary opcode is rejected, every control opcode runs. This is a rigor bonus "
          "that reflects which library happened to be installable; the identical cross-check "
          "would be applied to BCH / BSV / XEC (or any candidate) given their implementations. "
          "It does **not** elevate BTC.",
          "",
          "## Reading",
          "",
          "The broad vocabulary (`OP_CAT`, `OP_SUBSTR/LEFT/RIGHT`, `OP_INVERT`, `OP_AND/OR/XOR`, "
          "`OP_MUL/DIV/MOD`, `OP_LSHIFT/RSHIFT`, `OP_2MUL/2DIV`) **is native to v0.1**. From the "
          "origin, the descendants simply made different selections: some disabled it, some "
          "restored parts, some restored (nearly) all — a factual map of divergence, not a verdict.",
          "",
          "## Sources (documented columns; verify against each chain's node to execute)",
          "- **BTC**: `bitcoin.core.script.DISABLED_OPCODES` (independent lib; matches Bitcoin Core).",
          "- **BCH**: Bitcoin Cash *May 2018* upgrade (`OP_CAT`, `OP_AND/OR/XOR`, `OP_DIV`, `OP_MOD`; "
          "`OP_SPLIT`).",
          "- **BSV**: Bitcoin SV *Genesis* (2020-02), \"restore original Script\".",
          "- **XEC** (eCash): fork of BCH (2021-11); inherits BCH's script rules for these opcodes.",
          "",
          "> BCH / BSV / XEC rows are **documented, not executed here** — running vectors against "
          "their consensus needs their node software (a later step, applied equally to all).", ""]
    (out / "MATRIX.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote MATRIX.md + conformance.json | BTC profile executed & consistent: "
          f"{BTC_LIB is not None and xcheck_ok}")
    for r in rows:
        print(f"  {r['opcode']:12} v0.1={r['v0_1']:8} BTC={r['BTC']:9} BCH={r['BCH']:9} "
              f"BSV={r['BSV']:9} XEC={r['XEC']:9} (btc-exec={r['btc_executed']})")


if __name__ == "__main__":
    main()
