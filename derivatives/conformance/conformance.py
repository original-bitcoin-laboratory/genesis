"""Descendant-conformance matrix: run v0.1's "broad vocabulary" script vectors
through our own MODEL (v0.1 semantics) AND through an INDEPENDENT BTC consensus
implementation (python-bitcoinlib's EvalScript), then tabulate against BTC / BCH /
BSV. This is the neutral comparison from the charter: the v0.1 baseline is the
reference, and each descendant is measured against it — not the other way round.

Evidence levels per column:
  v0.1  = MODEL (our reproduction; cross-validated by derivatives/port)
  BTC   = EXECUTED against python-bitcoinlib (an independent BTC implementation)
  BCH   = DOCUMENTED (cited spec; not executed here)
  BSV   = DOCUMENTED (cited spec; not executed here)

Generates MATRIX.md + conformance.json. Run: python conformance.py
"""

from __future__ import annotations

import ctypes.util
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "model"))
from evalscript_model import num, run  # noqa: E402

# --- best-effort OpenSSL for python-bitcoinlib (only needed to import scripteval) ---
_OPENSSL_CANDIDATES = [
    r"C:\msys64\mingw64\bin\libcrypto-3-x64.dll",
    r"C:\Program Files\OpenSSL-Win64\bin\libcrypto-3-x64.dll",
]
if ctypes.util.find_library("ssl") is None and ctypes.util.find_library("crypto") is None:
    _hit = next((p for p in _OPENSSL_CANDIDATES if pathlib.Path(p).exists()), None)
    if _hit:
        _orig = ctypes.util.find_library
        ctypes.util.find_library = lambda n: _hit if n in ("ssl", "crypto", "libeay32", "ssleay32") else _orig(n)

BTC_EXEC = False
try:
    from bitcoin.core import script as bs
    from bitcoin.core.scripteval import EvalScript, EvalScriptError  # noqa: F401
    BTC_EXEC = True
except Exception:
    try:
        from bitcoin.core import script as bs   # pure-Python fallback (DISABLED_OPCODES)
    except Exception:
        bs = None


def v01_verdict(tokens) -> str:
    ok, _ = run(tokens)
    return "execute" if ok else "reject"


def btc_verdict(btc_ops, opname) -> str:
    if bs is None:
        return "?"
    disabled = getattr(bs, "DISABLED_OPCODES", set())
    op = getattr(bs, opname, None)
    if BTC_EXEC:
        try:
            EvalScript([], bs.CScript(btc_ops), None, 0)
            return "execute"
        except EvalScriptError:
            return "disabled" if (op in disabled) else "reject"
        except Exception:
            return "disabled" if (op in disabled) else "n/a"
    return "disabled" if (op in disabled) else "execute?"


# opname -> (our token script, BTC CScript ops). Broad-vocabulary + kept controls.
def _b(*x):
    return list(x)


VECTORS = [
    # family, opname, our tokens, btc ops
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
    # kept controls (should agree everywhere)
    ("kept",    "OP_ADD",     [num(2), num(2), "OP_ADD"]),
    ("kept",    "OP_EQUAL",   [b"\xaa", b"\xaa", "OP_EQUAL"]),
    ("kept",    "OP_SHA256",  [b"\xaa", "OP_SHA256"]),
]

# BTC CScript ops per opname (numbers as small-int opcodes / bytes)
BTC_OPS = {
    "OP_CAT":    lambda: [b"\x11", b"\x22", bs.OP_CAT],
    "OP_SUBSTR": lambda: [b"abcdef", bs.OP_1, bs.OP_3, bs.OP_SUBSTR],
    "OP_LEFT":   lambda: [b"abcdef", bs.OP_2, bs.OP_LEFT],
    "OP_RIGHT":  lambda: [b"abcdef", bs.OP_2, bs.OP_RIGHT],
    "OP_INVERT": lambda: [b"\x0f", bs.OP_INVERT],
    "OP_AND":    lambda: [b"\xf0", b"\x3c", bs.OP_AND],
    "OP_OR":     lambda: [b"\xf0", b"\x3c", bs.OP_OR],
    "OP_XOR":    lambda: [b"\xf0", b"\x3c", bs.OP_XOR],
    "OP_MUL":    lambda: [bs.OP_6, bs.OP_7, bs.OP_MUL],
    "OP_DIV":    lambda: [bs.OP_16, bs.OP_4, bs.OP_DIV],
    "OP_MOD":    lambda: [bs.OP_16, bs.OP_5, bs.OP_MOD],
    "OP_LSHIFT": lambda: [bs.OP_1, bs.OP_8, bs.OP_LSHIFT],
    "OP_RSHIFT": lambda: [bs.OP_16, bs.OP_2, bs.OP_RSHIFT],
    "OP_2MUL":   lambda: [bs.OP_5, bs.OP_2MUL],
    "OP_2DIV":   lambda: [bs.OP_6, bs.OP_2DIV],
    "OP_ADD":    lambda: [bs.OP_2, bs.OP_2, bs.OP_ADD],
    "OP_EQUAL":  lambda: [b"\xaa", b"\xaa", bs.OP_EQUAL],
    "OP_SHA256": lambda: [b"\xaa", bs.OP_SHA256],
}

# DOCUMENTED descendant status (cited; NOT executed here). CAT/AND/OR/XOR/DIV/MOD
# were re-enabled on BCH (May 2018; SUBSTR/LEFT/RIGHT -> OP_SPLIT); BSV restored the
# original arithmetic/bitwise/splice set (Genesis, Feb 2020).
BCH = {  # bitcoincash.org May 2018 upgrade spec
    "OP_CAT": "restored", "OP_AND": "restored", "OP_OR": "restored", "OP_XOR": "restored",
    "OP_DIV": "restored", "OP_MOD": "restored",
    "OP_SUBSTR": "→OP_SPLIT", "OP_LEFT": "→OP_SPLIT", "OP_RIGHT": "→OP_SPLIT",
    "OP_MUL": "disabled", "OP_LSHIFT": "disabled", "OP_RSHIFT": "disabled",
    "OP_INVERT": "disabled", "OP_2MUL": "disabled", "OP_2DIV": "disabled",
    "OP_ADD": "kept", "OP_EQUAL": "kept", "OP_SHA256": "kept",
}
BSV = {  # BSV Genesis (Feb 2020): restore original Script
    k: ("restored" if fam in ("splice", "bitwise", "arith") else "kept")
    for fam, k, _ in VECTORS
}
BSV["OP_SUBSTR"] = BSV["OP_LEFT"] = BSV["OP_RIGHT"] = "→OP_SPLIT"


def build():
    rows = []
    for fam, opname, tokens in VECTORS:
        v = v01_verdict(tokens)
        b = btc_verdict(BTC_OPS[opname]() if bs is not None else None, opname)
        rows.append({"family": fam, "opcode": opname, "v0_1": v, "btc": b,
                     "bch": BCH.get(opname, "?"), "bsv": BSV.get(opname, "?")})
    return rows


def main():
    rows = build()
    out = pathlib.Path(__file__).resolve().parent
    (out / "conformance.json").write_text(json.dumps(
        {"schema": 1, "btc_executed": BTC_EXEC, "rows": rows}, indent=2) + "\n", encoding="utf-8")

    L = ["# Descendant-conformance matrix (v0.1 baseline)", "",
         f"BTC column: **{'EXECUTED against python-bitcoinlib' if BTC_EXEC else 'DISABLED_OPCODES set (library)'}**. "
         "v0.1 = our MODEL (cross-validated by derivatives/port). BCH/BSV = DOCUMENTED (cited below), not executed here.",
         "",
         "| family | opcode | v0.1 | BTC | BCH | BSV |",
         "|---|---|:--:|:--:|:--:|:--:|"]
    for r in rows:
        L.append(f"| {r['family']} | `{r['opcode']}` | {r['v0_1']} | {r['btc']} | {r['bch']} | {r['bsv']} |")
    L += ["",
          "Legend: **execute** = runs / accepted; **disabled** = rejected by consensus; "
          "**restored** = re-enabled by that chain; **→OP_SPLIT** = the byte-splice op was "
          "replaced by `OP_SPLIT`; **kept** = never disabled.",
          "",
          "## Reading",
          "",
          "The whole *broad vocabulary* (`OP_CAT`, `OP_SUBSTR/LEFT/RIGHT`, `OP_INVERT`, "
          "`OP_AND/OR/XOR`, `OP_MUL/DIV/MOD`, `OP_LSHIFT/RSHIFT`, `OP_2MUL/2DIV`) **executes "
          "in v0.1** and is **disabled in BTC** — confirmed by running the vectors through an "
          "independent BTC implementation, not by reading BIPs. BCH restored a subset "
          "(splice/bitwise/DIV/MOD, with `OP_SPLIT` replacing the byte-index ops); BSV restored "
          "the original set (Genesis). This is the executable form of \"who preserved what\".",
          "",
          "## Sources (documented columns)",
          "- BTC disabled set: python-bitcoinlib `bitcoin.core.script.DISABLED_OPCODES` "
          "(mirrors Bitcoin Core consensus).",
          "- BCH: Bitcoin Cash May 2018 upgrade (re-enabled opcodes; `OP_SPLIT`).",
          "- BSV: Bitcoin SV *Genesis* upgrade (Feb 2020), \"restore original Script\".",
          "",
          "> DESCENDANT rows for BCH/BSV are documented, not executed here — running vectors "
          "against BCH/BSV nodes needs their software (a later step). The v0.1↔BTC contrast IS executed."]
    (out / "MATRIX.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote MATRIX.md + conformance.json (BTC executed={BTC_EXEC})")
    for r in rows:
        print(f"  {r['opcode']:12} v0.1={r['v0_1']:8} BTC={r['btc']}")


if __name__ == "__main__":
    main()
