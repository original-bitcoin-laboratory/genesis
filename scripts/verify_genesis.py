#!/usr/bin/env python3
"""The genesis recipes — re-derive the genesis blocks from source and verify them against pinned hashes.

Two different things are verified, and the output names which is which:

  LABORATORY   NOV08-X and JAN09-X, the laboratory's own experimental genesis blocks: fixed coinbase
               message, fixed timestamp, fixed difficulty, a nonce search from zero. Re-minting them
               and matching the pinned hashes shows the recipe is deterministic. It says nothing about
               Bitcoin's own genesis.
  HISTORICAL   Bitcoin's 3 January 2009 genesis, 000000000019d668…, re-derived here in pure Python from
               its raw parameters (the headline as pushed in the coinbase, the 50-coin pay-to-pubkey
               output, nTime 1231006505, nBits 0x1d00ffff, nNonce 2083236893) under v0.1's
               serialisation, and compared to the published hash and merkle root. The unmodified 2009
               binary witnesses the same block (JAN09-EXECUTED, r3-findings/); the C++ port re-derives
               it too (derivatives/node/run.sh). This mode is the pure-Python third derivation.

    python scripts/verify_genesis.py               # both laboratory blocks
    python scripts/verify_genesis.py --historical  # the historical block as well
    python scripts/verify_genesis.py --all --json  # everything, as data (commit, platform included)

An earlier text of this file's docstring said only "our genesis blocks"; three outside reviewers
read a transcript of this script as a re-derivation of Bitcoin's genesis, which it was not. The
output now labels what it verified. Exit 0 iff every requested block reproduces. These chains are
experimental lab artifacts — "not money" (it is stamped in the coinbase).
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import pathlib
import platform
import subprocess
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

# Bitcoin's genesis, 3 January 2009, as v0.1's LoadBlockIndex() builds it (main.cpp): the coinbase's
# scriptSig is CScript() << 486604799 << CBigNum(4) << "The Times 03/Jan/2009 ...", the output pays
# 50 coins to the published 65-byte key with OP_CHECKSIG; header nTime 1231006505, nBits 0x1d00ffff,
# nNonce 2083236893. Both expected values are the published ones anyone can check against any node.
HISTORICAL = {
    "headline": b"The Times 03/Jan/2009 Chancellor on brink of second bailout for banks",
    "pubkey": bytes.fromhex("04678afdb0fe5548271967f1a67130b7105cd6a828e03909a67962e0ea1f61deb6"
                            "49f6bc3f4cef38c4f35504e51ec112de5c384df7ba0b8d578a4c702b6bf11d5f"),
    "ntime": 1231006505, "nbits": 0x1D00FFFF, "nonce": 2083236893,
    "expected_hash": "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f",
    "expected_merkle": "4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b",
}


def _load(path: pathlib.Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def regenerate() -> dict[str, dict]:
    """Re-mint each laboratory genesis twice; return {label: {hash, deterministic, matches, message}}."""
    nov = _load(DERIV / "nov08x" / "net.py", "nov08x_net")
    jan = _load(DERIV / "jan09x" / "net.py", "jan09x_net")
    out = {}
    for label, mod, msg in [("NOV08-X", nov, nov.NOV08X_GENESIS_MESSAGE),
                            ("JAN09-X", jan, jan.JAN09X_GENESIS_MESSAGE)]:
        h1 = mod.block_hash(mod.mint_genesis())[::-1].hex()
        h2 = mod.block_hash(mod.mint_genesis())[::-1].hex()
        out[label] = {"kind": "laboratory", "hash": h1, "deterministic": h1 == h2,
                      "matches": h1 == PINNED[label], "message": msg.decode()}
    return out


def _dsha(b: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


def _varint(n: int) -> bytes:
    if n < 0xFD:
        return bytes([n])
    if n <= 0xFFFF:
        return b"\xfd" + n.to_bytes(2, "little")
    return b"\xfe" + n.to_bytes(4, "little")


def _push(b: bytes) -> bytes:
    assert len(b) <= 75
    return bytes([len(b)]) + b


def _script_num(n: int) -> bytes:
    """CScript << int64: CBigNum's sign-magnitude little-endian form, minimal, pushed."""
    if n == 0:
        return b"\x00"                                   # OP_0
    if 1 <= n <= 16:
        return bytes([0x50 + n])                         # OP_1..OP_16
    out, v = bytearray(), abs(n)
    while v:
        out.append(v & 0xFF)
        v >>= 8
    if out[-1] & 0x80:
        out.append(0x80 if n < 0 else 0x00)
    elif n < 0:
        out[-1] |= 0x80
    return _push(bytes(out))


def historical() -> dict:
    """Re-derive Bitcoin's genesis from its raw parameters under v0.1's serialisation."""
    p = HISTORICAL
    # v0.1 writes CScript() << 486604799 << CBigNum(4) << vector(headline). 486604799 = 0x1d00ffff
    # serialises as a 4-byte push ff ff 00 1d; CBigNum(4) as OP_4? No: CBigNum serialises as a byte
    # vector (04), pushed -- the genesis scriptSig is 04ffff001d 0104 45<headline>, as the block shows.
    script_sig = _push((0x1D00FFFF).to_bytes(4, "little")) + _push(b"\x04") + _push(p["headline"])
    script_pub = _push(p["pubkey"]) + b"\xac"            # <65-byte key> OP_CHECKSIG
    tx = (b"\x01\x00\x00\x00"                             # version
          + b"\x01" + b"\x00" * 32 + b"\xff\xff\xff\xff"  # one input: null prevout
          + _varint(len(script_sig)) + script_sig + b"\xff\xff\xff\xff"
          + b"\x01" + (50 * 100_000_000).to_bytes(8, "little")
          + _varint(len(script_pub)) + script_pub
          + b"\x00\x00\x00\x00")                          # locktime
    merkle = _dsha(tx)                                    # one transaction: the merkle root is its hash
    header = (b"\x01\x00\x00\x00" + b"\x00" * 32 + merkle + p["ntime"].to_bytes(4, "little")
              + p["nbits"].to_bytes(4, "little") + p["nonce"].to_bytes(4, "little"))
    h = _dsha(header)[::-1].hex()
    return {"kind": "historical", "hash": h, "merkle": merkle[::-1].hex(),
            "matches": h == p["expected_hash"] and merkle[::-1].hex() == p["expected_merkle"],
            "deterministic": True, "message": p["headline"].decode(),
            "coinbase_scriptSig_hex": script_sig.hex(), "header_hex": header.hex()}


def provenance() -> dict:
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    except OSError:
        commit = None
    return {"commit": commit or None, "python": sys.version.split()[0], "platform": platform.platform(),
            "machine": platform.machine()}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--historical", action="store_true", help="also re-derive Bitcoin's 3 January 2009 genesis")
    ap.add_argument("--all", action="store_true", help="laboratory blocks and the historical block")
    ap.add_argument("--json", action="store_true", help="print the result as JSON (with commit and platform)")
    a = ap.parse_args()
    res = regenerate()
    if a.historical or a.all:
        res["Bitcoin 2009 genesis"] = historical()
    ok = all(r["deterministic"] and r["matches"] for r in res.values())
    if a.json:
        print(json.dumps({"provenance": provenance(), "blocks": res, "ok": ok}, indent=2))
        return 0 if ok else 1
    pv = provenance()
    print(f"commit {(pv['commit'] or '?')[:12]}  python {pv['python']}  {pv['platform']}")
    for label, r in res.items():
        good = r["deterministic"] and r["matches"]
        print(f"[{'OK' if good else 'FAIL'}] {r['kind'].upper():11} {label}: {r['hash']}")
        print(f"        deterministic={r['deterministic']}  matches_pinned={r['matches']}")
        print(f"        coinbase: \"{r['message']}\"")
    if not (a.historical or a.all):
        print("\nLABORATORY RECIPE VERIFIED — both experimental genesis blocks re-derive from source."
              if ok else "\nMISMATCH — a genesis did not reproduce.")
        print("(This is the laboratory's own genesis pair, not Bitcoin's. For Bitcoin's 2009 genesis: --historical.)")
    else:
        print("\nVERIFIED — every requested block re-derives and matches its published hash."
              if ok else "\nMISMATCH — a block did not reproduce.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
