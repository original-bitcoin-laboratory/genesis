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

Inputs are the measured figures of the note (OpenSSL 3.5.4, FIPS 204/205 sizes), restated here as
constants with their source line, so this script has no dependency on a network or a library. NOT
money: this computes costs and takes no position on any scheme or any chain.
"""
from __future__ import annotations

import argparse
import json

BLOCK_BYTES = 1_000_000                 # MAX_BLOCK_SIZE, 1 MB (the 2010 rule; v0.1's own cap is 32 MiB)
BLOCKS_PER_DAY = 144                    # 600 s target spacing; 2009 pacing (600.30 s executed makes it 143.9)
COINBASE_BYTES = 135                    # mean coinbase parsed from a live v0.1-format chain (PQ-SIGNATURE-COST §0)
OLD_PK_BYTES = 65                       # secp256k1 uncompressed public key, the v0.1 output form

# docs/PQ-SIGNATURE-COST.md §1 (measured) and §2 (computed from v0.1 serialization):
#   scheme: (signature B, raw public key B, 1-in-1-out pay-to-pubkey tx B, 1-in-2-out tx B)
SCHEMES = {
    "secp256k1-ECDSA":   (71,    65,   200,   276),
    "ML-DSA-44":         (2420,  1312, 3800,  5125),
    "ML-DSA-65":         (3309,  1952, 5329,  7294),
    "ML-DSA-87":         (4627,  2592, 7287,  9892),
    "SLH-DSA-SHA2-128s": (7856,  32,   7954,  7997),
    "SLH-DSA-SHA2-128f": (17088, 32,   17186, 17229),
    "SLH-DSA-SHA2-192s": (16224, 48,   16338, 16397),
}
POPULATIONS = (1_000_000, 10_000_000, 100_000_000)      # outputs that must each spend once


def per_block(tx_bytes: int) -> int:
    return (BLOCK_BYTES - COINBASE_BYTES) // tx_bytes


def migration_tx_bytes(new_pk: int) -> int:
    """One spend of an old pay-to-pubkey output into one new output that carries a post-quantum key:
    the measured ECDSA 1-in-1-out transaction with the old 65-byte key in its output replaced."""
    return SCHEMES["secp256k1-ECDSA"][2] - OLD_PK_BYTES + new_pk


def compute() -> dict:
    rows = {}
    for name, (sig, pk, tx1, tx2) in SCHEMES.items():
        pb = per_block(tx1)
        pd = pb * BLOCKS_PER_DAY
        mig = migration_tx_bytes(pk)
        mig_pb = per_block(mig)
        mig_pd = mig_pb * BLOCKS_PER_DAY
        rows[name] = {
            "sig_bytes": sig, "pk_bytes": pk, "tx_1in1out_bytes": tx1,
            "spends_per_block": pb, "spends_per_day": pd,
            "migration_tx_bytes": mig, "migrations_per_block": mig_pb, "migrations_per_day": mig_pd,
            "days_for_population_to_spend_once": {str(n): round(n / pd, 1) for n in POPULATIONS},
            "days_for_population_to_migrate": {str(n): round(n / mig_pd, 1) for n in POPULATIONS},
        }
    return {"not_money": True, "block_bytes": BLOCK_BYTES, "blocks_per_day": BLOCKS_PER_DAY,
            "source": "docs/PQ-SIGNATURE-COST.md (measured sizes); this script (arithmetic)", "schemes": rows}


def report(d: dict) -> None:
    print("SETTLEMENT CAPACITY OF A 2009-SHAPED BASE LAYER -- computed from measured sizes (NOT money)")
    print(f"  block {d['block_bytes']:,} B, {d['blocks_per_day']} blocks/day; one-input one-output pay-to-pubkey spends\n")
    print(f"  {'scheme':<20} {'tx B':>6} {'/block':>7} {'/day':>9} | {'migrate B':>9} {'/day':>9} | days for 1e6 / 1e7 / 1e8 outputs to spend once")
    print("  " + "-" * 118)
    for name, r in d["schemes"].items():
        days = r["days_for_population_to_spend_once"]
        print(f"  {name:<20} {r['tx_1in1out_bytes']:>6} {r['spends_per_block']:>7,} {r['spends_per_day']:>9,} | "
              f"{r['migration_tx_bytes']:>9,} {r['migrations_per_day']:>9,} | "
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
