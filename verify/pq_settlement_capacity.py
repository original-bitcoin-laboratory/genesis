#!/usr/bin/env python3
"""What a 2009-shaped base layer can settle per day under post-quantum signatures, and how long a
population of outputs takes to move -- computed from the sizes docs/PQ-SIGNATURE-COST.md measured.

    python verify/pq_settlement_capacity.py            # the tables
    python verify/pq_settlement_capacity.py --json     # the same as JSON

The first half of the question (docs/PQ-SIGNATURE-COST.md) measured signature and key sizes and
found that, in the model studied, size is the directly resolvable constraint. (This sentence read
"size, not verification, binds" until 28 September 2026. That was a stronger claim than the
measurement supports -- it ranks two costs against each other, where what was measured is that one
of them can be settled from the sizes alone -- and it is withdrawn here as it was in the paper that
cites this file.) This is the second half: at those sizes, how many spends
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
from pq_signature_cost import COINBASE_BYTES, model_p2pk_spend, push_len, spends_per_block, varint_len   # noqa: E402  (one model for both notes)

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
    """The header, the transaction count and one coinbase, then as many spends as fit (shared with
    verify/pq_signature_cost.py, so the two scripts count the same block)."""
    return spends_per_block(block_bytes, tx_bytes)


def migration_tx_bytes(new_pk: int) -> int:
    """One spend of an old pay-to-pubkey output into one new output that carries a post-quantum key:
    signed under the OLD scheme (the exposed key's), so the input carries the ECDSA signature and the
    output carries the new key. Same model as every other row."""
    return model_p2pk_spend(OLD_SIG_BYTES, new_pk)


P2PKH_SCRIPT_BYTES = 25                  # OP_DUP OP_HASH160 <20> OP_EQUALVERIFY OP_CHECKSIG, v0.1's address form
FAN_OUT = range(1, 7)


def model_p2pkh_spend(sig_len: int, pk_len: int, n_out: int = 1) -> int:
    """One spend of a pay-to-pubkey-hash output into `n_out` pay-to-pubkey-hash outputs: the scriptSig
    pushes the signature (with its hash-type byte) and then the key; every output is the 25-byte script.
    The same framing as model_p2pk_spend, which a real v0.1 spend validates."""
    ss = push_len(sig_len + 1) + sig_len + 1 + push_len(pk_len) + pk_len
    inp = 36 + varint_len(ss) + ss + 4
    out = 8 + varint_len(P2PKH_SCRIPT_BYTES) + P2PKH_SCRIPT_BYTES
    return 4 + 1 + inp + 1 + out * n_out + 4


def output_type() -> dict:
    """Per-transaction size by output type and fan-out. Under pay-to-pubkey every output carries a
    key, so a transaction's size grows with its outputs by the key size, and a scheme with small
    signatures and large keys (ML-DSA) loses to one with large signatures and small keys (SLH-DSA-128s)
    once a spend creates enough outputs. Under pay-to-pubkey-hash every output is 25 bytes whatever the
    scheme and the key is carried once, in the spending input, so fan-out does not move the ranking.
    Per coin over its life both forms carry one signature and one key; they differ in which
    transaction carries the key."""
    rows = {}
    for name, (sig, pk) in SCHEMES.items():
        rows[name] = {"p2pk": {str(n): model_p2pk_spend(sig, pk, n) for n in FAN_OUT},
                      "p2pkh": {str(n): model_p2pkh_spend(sig, pk, n) for n in FAN_OUT}}
    ref = "SLH-DSA-SHA2-128s"
    cross = {}
    for name in ("ML-DSA-44", "ML-DSA-65", "ML-DSA-87"):
        for form in ("p2pk", "p2pkh"):
            first = next((n for n in FAN_OUT if rows[name][form][str(n)] > rows[ref][form][str(n)]), None)
            cross.setdefault(name, {})[form] = first
    return {"fan_out": list(FAN_OUT), "sizes": rows,
            "first_fan_out_where_larger_than_" + ref: cross}


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
    out["output_type"] = output_type()
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
    ot = d["output_type"]
    print("\n  == output type and fan-out: one-input spends, bytes ==")
    print(f"  {'scheme':<20} {'form':<6} " + " ".join(f"{n:>4}-out" for n in ot["fan_out"]))
    for name, r in ot["sizes"].items():
        for form in ("p2pk", "p2pkh"):
            print(f"  {name:<20} {form:<6} " + " ".join(f"{r[form][str(n)]:>8,}" for n in ot["fan_out"]))
    key = [k for k in ot if k.startswith("first_fan_out")][0]
    for name, c in ot[key].items():
        print(f"  {name}: larger than SLH-DSA-SHA2-128s from {c['p2pk']} outputs under p2pk; "
              f"{'from ' + str(c['p2pkh']) + ' outputs' if c['p2pkh'] else 'at no fan-out up to ' + str(ot['fan_out'][-1])} under p2pkh")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    d = compute()
    print(json.dumps(d, indent=1)) if a.json else report(d)
