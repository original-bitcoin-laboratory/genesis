#!/usr/bin/env python3
"""What a 2009-shaped base layer can settle per day under post-quantum signatures, and how long a
population of outputs takes to move -- computed from the sizes docs/PQ-SIGNATURE-COST.md measured.

    python verify/pq_settlement_capacity.py            # the tables
    python verify/pq_settlement_capacity.py --json     # the same as JSON

The first half of the question (docs/PQ-SIGNATURE-COST.md) measured signature and key sizes and
found that size, not verification, binds. This is the second half: at those sizes, how many spends
fit a block, how many settle in a day at 2009 pacing, and how long it takes for N outputs to each
spend once -- which is the arithmetic behind the statement that state must move off the base layer,
and the arithmetic behind its limit: an output whose public key is already on the chain can only be
moved by a signature under the old scheme, so a second layer does nothing for it.

Two block ceilings are computed, and the January 2009 one comes first: MAX_SIZE = 0x02000000
(32 MiB), the rule v0.1 itself enforces in CheckBlock (OBL-F-0016), and the 1 MB rule Bitcoin
acquired in September 2010 (OBL-C-0001). Until 20 September 2026 this script computed the 1 MB
table only, in a repository whose own register records that rule as a retrofit; an adversarial
review pointed that out.

Inputs are the measured signature and key sizes of the note (FIPS 204/205 sizes, matched exactly);
the transaction sizes come from the SAME serialisation model the note uses (verify/pq_signature_cost.py,
model_p2pk_spend), so the two scripts cannot disagree on a byte. NOT money: this computes costs and
takes no position on any scheme or any chain.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pq_signature_cost import COINBASE_BYTES, model_p2pk_spend   # noqa: E402  (one model for both notes)

BLOCKS = {                               # ceiling name: bytes
    "v0.1 (32 MiB, MAX_SIZE)": 0x02000000,   # main.h:17, tested in CheckBlock; the January 2009 rule
    "2010 rule (1 MB)": 1_000_000,           # MAX_BLOCK_SIZE, a block-validity rule from block 79,401
}
BLOCKS_PER_DAY = 144                     # 600 s target spacing; 2009 pacing (600.30 s executed makes it 143.9)
OLD_SIG_BYTES = 71                       # secp256k1 ECDSA/DER, the mode of the measured distribution
OLD_PK_BYTES = 65                        # secp256k1 uncompressed public key, the v0.1 output form

# docs/PQ-SIGNATURE-COST.md §1 (measured): scheme -> (signature B, raw public key B)
SCHEMES = {
    "secp256k1-ECDSA":   (71,    65),
    "ML-DSA-44":         (2420,  1312),
    "ML-DSA-65":         (3309,  1952),
    "ML-DSA-87":         (4627,  2592),
    "SLH-DSA-SHA2-128s": (7856,  32),
    "SLH-DSA-SHA2-128f": (17088, 32),
    "SLH-DSA-SHA2-192s": (16224, 48),
}
POPULATIONS = (1_000_000, 10_000_000, 100_000_000)      # outputs that must each spend once


def per_block(block_bytes: int, tx_bytes: int) -> int:
    """One coinbase, then as many spends as fit."""
    return (block_bytes - COINBASE_BYTES) // tx_bytes


def migration_tx_bytes(new_pk: int) -> int:
    """One spend of an old pay-to-pubkey output into one new output that carries a post-quantum key:
    signed under the OLD scheme (the exposed key's), so the input carries the ECDSA signature and the
    output carries the new key. Same model as every other row."""
    return model_p2pk_spend(OLD_SIG_BYTES, new_pk)


def compute() -> dict:
    out = {"not_money": True, "blocks_per_day": BLOCKS_PER_DAY, "coinbase_bytes": COINBASE_BYTES,
           "source": "docs/PQ-SIGNATURE-COST.md (measured sizes); verify/pq_signature_cost.py (serialisation model); this script (arithmetic)",
           "ceilings": {}}
    for label, block_bytes in BLOCKS.items():
        rows = {}
        for name, (sig, pk) in SCHEMES.items():
            tx1 = model_p2pk_spend(sig, pk)
            pb = per_block(block_bytes, tx1)
            pd = pb * BLOCKS_PER_DAY
            mig = migration_tx_bytes(pk)
            mig_pb = per_block(block_bytes, mig)
            mig_pd = mig_pb * BLOCKS_PER_DAY
            rows[name] = {
                "sig_bytes": sig, "pk_bytes": pk, "tx_1in1out_bytes": tx1,
                "spends_per_block": pb, "spends_per_day": pd,
                "migration_tx_bytes": mig, "migrations_per_block": mig_pb, "migrations_per_day": mig_pd,
                "days_for_population_to_spend_once": {str(n): round(n / pd, 1) for n in POPULATIONS},
                "days_for_population_to_migrate": {str(n): round(n / mig_pd, 1) for n in POPULATIONS},
            }
        out["ceilings"][label] = {"block_bytes": block_bytes, "schemes": rows}
    return out


def report(d: dict) -> None:
    print("SETTLEMENT CAPACITY OF A 2009-SHAPED BASE LAYER -- computed from measured sizes (NOT money)")
    print(f"  {d['blocks_per_day']} blocks/day; one coinbase ({d['coinbase_bytes']} B) then one-input one-output pay-to-pubkey spends\n")
    for label, c in d["ceilings"].items():
        print(f"  == {label}: block {c['block_bytes']:,} B ==")
        print(f"  {'scheme':<20} {'tx B':>6} {'/block':>9} {'/day':>11} | {'migrate B':>9} {'/day':>11} | days for 1e6 / 1e7 / 1e8 outputs to spend once")
        print("  " + "-" * 122)
        for name, r in c["schemes"].items():
            days = r["days_for_population_to_spend_once"]
            print(f"  {name:<20} {r['tx_1in1out_bytes']:>6} {r['spends_per_block']:>9,} {r['spends_per_day']:>11,} | "
                  f"{r['migration_tx_bytes']:>9,} {r['migrations_per_day']:>11,} | "
                  f"{days['1000000']:>8,} / {days['10000000']:>8,} / {days['100000000']:>9,}")
        print()
    print("  Reading the last three columns: with every block full of nothing but these spends, this is how many")
    print("  days pass before a population of that many outputs has each moved once. 3,650 days is ten years.")
    print("  The migration column is the spend that moves an exposed key to a post-quantum one: it is signed under")
    print("  the OLD scheme, so its size is the old signature plus the NEW key, and no second layer can do it.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    d = compute()
    print(json.dumps(d, indent=1)) if a.json else report(d)
