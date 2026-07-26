#!/usr/bin/env python3
"""The eternal recipe — regenerate both experimental genesis blocks from source and
verify they match their pinned hashes.

Our genesis blocks are *deterministic*: fixed coinbase message, fixed timestamp,
fixed difficulty, and a nonce search from zero. So anyone, anywhere, forever, can run
this and re-derive the identical NOV08-X and JAN09-X genesis — no live node required.
The permanence is in the reproducible recipe, not in a chain someone has to keep
online.

    python scripts/verify_genesis.py       # re-mint both, check determinism + pinned hash

Exit 0 iff both regenerate deterministically and match. These chains are experimental
lab artifacts — "not money" (it is stamped in the coinbase).
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent          # genesis/
DERIV = ROOT / "derivatives"
for sub in ("model", "p2p", "nov08x", "jan09x"):
    sys.path.insert(0, str(DERIV / sub))

# Pinned genesis hashes (display / big-endian). Re-derived from source below.
PINNED = {
    "NOV08-X": "00000f088c16f6dbc9e64870125fca75012f51c6d5638c6eda66490a271caec6",
    "JAN09-X": "51eec236b4faf743b621f5b6bddbce272ac33904b2872cf537a2a4cb2234c6f2",
}


def _load(path: pathlib.Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def regenerate() -> dict[str, dict]:
    """Re-mint each genesis twice; return {label: {hash, deterministic, matches, message}}."""
    nov = _load(DERIV / "nov08x" / "net.py", "nov08x_net")
    jan = _load(DERIV / "jan09x" / "net.py", "jan09x_net")
    out = {}
    for label, mod, msg in [("NOV08-X", nov, nov.NOV08X_GENESIS_MESSAGE),
                            ("JAN09-X", jan, jan.JAN09X_GENESIS_MESSAGE)]:
        h1 = mod.block_hash(mod.mint_genesis())[::-1].hex()
        h2 = mod.block_hash(mod.mint_genesis())[::-1].hex()
        out[label] = {"hash": h1, "deterministic": h1 == h2,
                      "matches": h1 == PINNED[label], "message": msg.decode()}
    return out


def main() -> int:
    res = regenerate()
    ok = True
    for label, r in res.items():
        good = r["deterministic"] and r["matches"]
        ok = ok and good
        print(f"[{'OK' if good else 'FAIL'}] {label}: {r['hash']}")
        print(f"        deterministic={r['deterministic']}  matches_pinned={r['matches']}")
        print(f"        coinbase: \"{r['message']}\"")
    print("\nETERNAL RECIPE VERIFIED — both genesis blocks re-derive from source."
          if ok else "\nMISMATCH — a genesis did not reproduce.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
