#!/usr/bin/env python3
"""Bench inputs for the four open witness cells, built under the January 2009 rules so the unmodified
2009 binary accepts them, and rejected by v0.3.13 for the exact reasons its source states.

    python make_big_block.py --case all --prev <tip hash, display order> --height <tip height + 1> \
        --out bench-inputs/ [--nbits 1d00ffff] [--ntime N] [--miner PATH] [--threads N]
    python make_big_block.py --case big-tx --state results/<run>/state.json --out bench-inputs/
    python make_big_block.py --submit HOST:PORT --magic f9beb4d9 --genesis <hash> --send bench-inputs/big-block.hex

Cases (each a file of raw hex plus a manifest line with its sha256, size and the expected verdicts):

  big-block   a block over 1 MB and under 32 MiB: one coinbase paying 50 coins to OP_TRUE plus enough
              zero-value OP_TRUE outputs to reach --size bytes.
                2009      accepts: CheckBlock tests MAX_SIZE = 32 MiB (main.cpp:1160)        OBL-F-0016
                v0.3.13   rejects: "CheckBlock() : size limits failed" (main.cpp:1415)       OBL-C-0001
                v0.3.12   the same test is gated `nHeight > 79400` (main.cpp:1422): on an isolated chain
                          at low height 0.3.12 ACCEPTS; the gate is a fact of the record, not a witness
  sigops      a small block whose coinbase carries 21 outputs of 1,001 OP_CHECKSIG bytes each
              (21,021 sigops > MAX_BLOCK_SIGOPS = 20,000) plus the 50-coin output.
                2009      accepts (no sigop rule)
                v0.3.13   rejects: "CheckBlock() : too many nonstandard transactions" (main.cpp:1439)  OBL-C-0004
                v0.3.12   gated as above (main.cpp:1426)
  big-tx      a loose transaction over 1 MB spending one of the replay's P2PK funding outputs (key
              "blocks-a", from --state), paying to many zero-value OP_TRUE outputs, no fee.
                2009      relays (no size rule, no relay fee rule: OBL-C-0017)
                v0.3.13   rejects: "CTransaction::CheckTransaction() : size limits failed" (main.cpp:498)  OBL-C-0010
              (0.3.13 predates IsStandard, 7 Dec 2010, and the relay fee gate, 12 Dec 2010, so the size
              rule is the only one that fires.)

The DER probes for OBL-C-0014 need no input from here: `replay.py --phase checksig` frames them.

--submit sends one file to a node over the v0.1 wire (wire01.Peer) and reads the same two signals the
replay reads: is it served back by getdata, and did the main chain advance to it. ONLY ever point this
at an ISOLATED node. NOT money.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import recipes                                                  # noqa: E402
import verify_vectors as spec                                   # noqa: E402
from miner import make_miner, default_exe                       # noqa: E402
from wire01 import MSG_BLOCK, MSG_TX, Peer                      # noqa: E402

OP_TRUE = recipes.OP_TRUE_SCRIPT
OP_CHECKSIG = bytes([0xAC])
SUBSIDY = 50 * 100_000_000
MAX_BLOCK_SIGOPS_2010 = 1_000_000 // 50

EXPECT = {
    "big-block": {"2009": "accept (CheckBlock tests MAX_SIZE = 32 MiB, main.cpp:1160; OBL-F-0016)",
                  "v0.3.13": "reject: CheckBlock() : size limits failed (main.cpp:1415; OBL-C-0001)",
                  "v0.3.12": "accept at low height: the 1 MB test is gated nHeight > 79400 (main.cpp:1422)"},
    "sigops": {"2009": "accept (no sigop rule)",
               "v0.3.13": "reject: CheckBlock() : too many nonstandard transactions (main.cpp:1439; OBL-C-0004)",
               "v0.3.12": "accept at low height: gated nHeight > 79400 (main.cpp:1426)"},
    "big-tx": {"2009": "relay (no transaction-size rule; no relay fee rule, OBL-C-0017)",
               "v0.3.13": "reject: CTransaction::CheckTransaction() : size limits failed (main.cpp:498; OBL-C-0010)"},
}


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def coinbase_with_padding(height: int, size: int, tag: bytes) -> dict:
    """A coinbase whose serialised size reaches `size` bytes with zero-value OP_TRUE outputs (10 B each)."""
    cb = recipes.make_coinbase(height, [(SUBSIDY, OP_TRUE)], tag)
    base = len(spec.ser_tx(cb))
    n_pad = max(0, (size - base + 9) // 10)
    cb["vout"].extend({"value": 0, "script": OP_TRUE} for _ in range(n_pad))
    return cb


def build_big_block(a, mine) -> tuple[bytes, dict]:
    cb = coinbase_with_padding(a.height, a.size, b"obl-bench-size")
    txs = [cb]
    raw = recipes.assemble_block(a.prev, txs, a.ntime, a.nbits, mine)
    return raw, {"txs": 1, "coinbase_outputs": len(cb["vout"])}


def build_sigops_block(a, mine) -> tuple[bytes, dict]:
    heavy = OP_CHECKSIG * 1001
    outs = [(SUBSIDY, OP_TRUE)] + [(0, heavy) for _ in range(21)]
    cb = recipes.make_coinbase(a.height, outs, b"obl-bench-sigops")
    raw = recipes.assemble_block(a.prev, [cb], a.ntime, a.nbits, mine)
    return raw, {"txs": 1, "sigops": 21 * 1001, "limit_2010": MAX_BLOCK_SIGOPS_2010}


def build_big_tx(a) -> tuple[bytes, dict]:
    state = json.loads(pathlib.Path(a.state).read_text(encoding="utf-8"))
    f = state["funding"]
    label = a.funding_label
    txid = bytes.fromhex(f["txid"])[::-1]
    n, value = f["index"][label], f["values"][label]
    key = recipes.key_from_label("blocks-a")
    spk = recipes.p2pk(key["sec"])
    tx = recipes.make_tx([(txid, n, b"", 0xFFFFFFFF)], [(value, OP_TRUE)])
    base = len(spec.ser_tx(tx)) + 75                          # the signature push, added below
    n_pad = max(0, (a.size - base + 9) // 10)
    tx["vout"].extend({"value": 0, "script": OP_TRUE} for _ in range(n_pad))
    der, _ = recipes.sign_p2pk(key, tx, 0, spk, recipes.SIGHASH_ALL)
    tx["vin"][0]["script"] = recipes.push(der + bytes([recipes.SIGHASH_ALL]))
    raw = spec.ser_tx(tx)
    return raw, {"spends": f"{f['txid']}:{n}", "value": value, "outputs": len(tx["vout"]),
                 "note": "the funding output's scriptPubKey is assumed to be p2pk(blocks-a) as the replay's fund phase writes it"}


def submit(a) -> int:
    raw = bytes.fromhex(pathlib.Path(a.send).read_text().strip())
    host, port = a.submit.rsplit(":", 1)
    peer = Peer(host, int(port), bytes.fromhex(a.magic), timeout=a.timeout)
    genesis = bytes.fromhex(a.genesis)[::-1]
    is_block = len(raw) > 80 and a.send.endswith(("block.hex", "sigops.hex")) or a.kind == "block"
    if is_block:
        h = spec.dsha256(raw[:80])
        prev = raw[4:36]
        peer.send("block", raw)
        served = peer.probe(MSG_BLOCK, h, genesis, timeout=a.timeout)
        in_main = False
        for _ in range(4):
            after = peer.main_chain_after([prev], timeout=max(2.0, a.timeout / 10))
            if after:
                in_main = h in after
                break
            time.sleep(1.0)
        print(json.dumps({"hash": h[::-1].hex(), "in_index": served, "in_main": in_main}))
    else:
        h = spec.dsha256(raw)
        peer.send("tx", raw)
        served = peer.probe(MSG_TX, h, genesis, timeout=a.timeout)
        print(json.dumps({"txid": h[::-1].hex(), "accepted_to_relay_pool": served}))
    peer.close()
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--case", choices=["big-block", "sigops", "big-tx", "all"], default="all")
    ap.add_argument("--prev", help="tip hash, display order (hex)")
    ap.add_argument("--height", type=int, help="height of the block being built (tip + 1)")
    ap.add_argument("--nbits", default="1d00ffff")
    ap.add_argument("--ntime", type=int, default=None, help="header time; must exceed the node's median-time-past")
    ap.add_argument("--size", type=int, default=1_100_000, help="target serialised size for big-block / big-tx")
    ap.add_argument("--state", help="replay state.json, for the big-tx funding output")
    ap.add_argument("--funding-label", default="p2pk:0")
    ap.add_argument("--miner", default=None, help="native miner path (default: ./miner-rs build if present)")
    ap.add_argument("--threads", type=int, default=None)
    ap.add_argument("--dry", action="store_true", help="build without mining (nonce 0): for size checks only")
    ap.add_argument("--out", default="bench-inputs")
    ap.add_argument("--submit", metavar="HOST:PORT")
    ap.add_argument("--send", help="the .hex file to send with --submit")
    ap.add_argument("--kind", choices=["block", "tx"], default="block")
    ap.add_argument("--magic", default="f9beb4d9")
    ap.add_argument("--genesis", help="genesis hash, display order: the sentinel block for the served-probe")
    ap.add_argument("--timeout", type=float, default=60.0,
                    help="seconds to wait for the node's answer (the 2009 binary answers in milliseconds; "
                         "the pure-Python stand-in needs minutes for a 1 MB block)")
    a = ap.parse_args(argv)

    if a.submit:
        if not (a.send and a.genesis):
            ap.error("--submit needs --send and --genesis")
        return submit(a)

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "cases": {}}
    a.nbits = int(a.nbits, 16)
    a.ntime = a.ntime or int(time.time())
    cases = ["big-block", "sigops", "big-tx"] if a.case == "all" else [a.case]

    mine = (lambda prefix, nbits: 0) if a.dry else make_miner(a.miner or default_exe(), a.threads, print)
    if any(c in ("big-block", "sigops") for c in cases):
        if not (a.prev and a.height):
            ap.error("block cases need --prev and --height")
        a.prev = bytes.fromhex(a.prev)[::-1]

    for c in cases:
        t0 = time.time()
        if c == "big-block":
            raw, info = build_big_block(a, mine)
        elif c == "sigops":
            raw, info = build_sigops_block(a, mine)
        else:
            if not a.state:
                print("big-tx: --state (a replay state.json with the funding outputs) is required; skipped")
                continue
            raw, info = build_big_tx(a)
        name = {"big-block": "big-block.hex", "sigops": "sigops.hex", "big-tx": "big-tx.hex"}[c]
        (out / name).write_text(raw.hex() + "\n", encoding="ascii")
        entry = {"file": name, "bytes": len(raw), "sha256": sha256(raw), "expect": EXPECT[c],
                 "mined": not a.dry and c != "big-tx", "seconds": round(time.time() - t0, 1), **info}
        if c != "big-tx":
            entry["hash"] = spec.dsha256(raw[:80])[::-1].hex()
            entry["header"] = {"prev": a.prev[::-1].hex(), "height": a.height, "nbits": hex(a.nbits), "ntime": a.ntime}
            ok_size = (c != "big-block") or (1_000_000 < len(raw) <= 0x02000000)
            entry["size_in_band_1MB_32MiB"] = ok_size
        else:
            entry["txid"] = spec.dsha256(raw)[::-1].hex()
            entry["size_over_1MB"] = len(raw) > 1_000_000
        manifest["cases"][c] = entry
        print(f"  {c:<10} {len(raw):>10,} B  sha256 {entry['sha256'][:16]}  {entry.get('hash', entry.get('txid', ''))[:16]}")
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"  wrote {out / 'MANIFEST.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
