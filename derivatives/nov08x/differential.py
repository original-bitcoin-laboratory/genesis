"""NOV08-X vs JAN09 — the counterfactual, side by side.

Runs the same parameterised engine under both rule sets and prints the four places
they diverge (subsidy, proof-of-work, retarget, coinbase rule) plus denomination.
Also writes PROVENANCE.json (the N-ORIG rule ledger) so the "November wins"
invariant is machine-checkable. No mining needed — these are the consensus
functions themselves.
"""

from __future__ import annotations

import json
import pathlib

from consensus import Rules

_HERE = pathlib.Path(__file__).resolve().parent


def rows_subsidy(nov, jan, heights):
    out = []
    for h in heights:
        out.append((h, nov.get_block_value(h) // nov.COIN, jan.get_block_value(h) // jan.COIN))
    return out


def build_report():
    nov = Rules.load("nov08")
    jan = Rules.load("jan09")
    L = ["# NOV08-X vs JAN09 — differential", "",
         "Same engine, two rule sets. NOV08 values are N-ORIG (read from the surviving",
         "November source); JAN09 is the differential baseline.", "",
         "## 1. Subsidy schedule (coins per block, by global best height)", "",
         "| best height | NOV08-X | JAN09 |", "|---|--:|--:|"]
    for h, n, j in rows_subsidy(nov, jan, [0, 99_999, 100_000, 200_000, 209_999, 210_000, 420_000]):
        L.append(f"| {h:,} | {n} | {j} |")
    L += ["",
          f"NOV08-X starts at **{nov.subsidy_base // nov.COIN} coins**, halving every "
          f"**{nov.halving:,}** blocks; JAN09 at {jan.subsidy_base // jan.COIN}, halving every "
          f"{jan.halving:,}.", "",
          "## 2. Proof-of-work encoding", "",
          f"- **NOV08-X:** `nBits` = **leading zero bits**; target = `(~0) >> nBits`. "
          f"MINPROOFOFWORK = **{nov.min_pow}** ('ridiculously easy for testing'). "
          f"e.g. nBits=20 → target has 20 leading zero bits.",
          f"- **JAN09:** `nBits` = **compact** mantissa/exponent (e.g. `0x1d00ffff`); "
          f"target = mantissa·256^(exp-3).",
          "",
          "## 3. Retarget (one full window)", ""]
    # too-slow window (actual = 3x target) and too-fast (actual = target/3)
    for label, actual in [("blocks came 3x too SLOW", nov.timespan * 3),
                          ("blocks came 3x too FAST", nov.timespan // 3)]:
        n_nb, n_how = nov.next_work(24, actual)
        _, j_how = jan.next_work(0x1d00ffff, actual)
        L.append(f"- **{label}:** NOV08-X → {n_how};  JAN09 → {j_how}.")
    L += ["",
          f"NOV08-X nudges by **±1 bit** (max one change per {nov.timespan // 86400}-day window); "
          f"JAN09 scales the target **proportionally** over its "
          f"{jan.timespan // 86400}-day window.", "",
          "## 4. Coinbase value rule", "",
          "A coinbase paying **one unit less** than subsidy+fees:", ""]
    bv_n = nov.get_block_value(0)
    bv_j = jan.get_block_value(0)
    L.append(f"- **NOV08-X:** claim {bv_n - 1} vs block value {bv_n} → "
             f"**{'ACCEPT' if nov.coinbase_ok(bv_n - 1, bv_n) else 'REJECT'}** (rule: exact equality).")
    L.append(f"- **JAN09:** claim {bv_j - 1} vs block value {bv_j} → "
             f"**{'ACCEPT' if jan.coinbase_ok(bv_j - 1, bv_j) else 'REJECT'}** (rule: upper bound).")
    L += ["",
          "## 5. Denomination & fee", "",
          f"- **NOV08-X:** COIN = {nov.COIN:,} units (no 'satoshi'); fixed fee = "
          f"{nov.fee_fixed:,} units ({nov.fee_fixed / nov.COIN} coin).",
          f"- **JAN09:** COIN = {jan.COIN:,} units (1 'satoshi' = 1 unit); dynamic fee.",
          "",
          "## 6. Nothing disabled", "",
          "NOV08-X's Script engine (reconstructed from the interface NOV08 references) "
          "carries the **full original opcode vocabulary** — see `test_nov08x.py`, which "
          "runs `OP_CAT`/`OP_MUL`/… live. November never had a Script file to disable "
          "anything in.", ""]
    return "\n".join(L) + "\n", nov


def write_provenance(nov: Rules):
    rows = nov.provenance_rows()
    doc = {"profile": "NOV08-X", "authority": nov.doc["authority"],
           "classes": {"N-ORIG": "verbatim from the surviving NOV08 source",
                       "N-IFACE": "reconstructed from an interface NOV08 references",
                       "J-DONOR": "imported from JAN09 where NOV08 is silent",
                       "NEW-EXP": "new experimental decision (never a semantics change)"},
           "n_orig_rules": rows,
           "reconstructed_substrate": [
               {"component": "Script engine (full vocabulary, nothing disabled)", "class": "N-IFACE",
                "from": "derivatives/model + derivatives/port"},
               {"component": "keys / ECDSA / sighash", "class": "N-IFACE", "from": "derivatives/model"},
               {"component": "persistence (CDiskBlockIndex)", "class": "J-DONOR", "from": "derivatives/persist"},
               {"component": "block plumbing / PoW loop", "class": "J-DONOR", "from": "derivatives/p2p/chainsync"}],
           "network_identity": {"class": "NEW-EXP",
                                "items": ["new genesis", "new magic", "new ports",
                                          "new address version", "no inherited balances"]}}
    (_HERE / "PROVENANCE.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8",
                                           newline="\n")
    return len(rows)


def main():
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    report, nov = build_report()
    (_HERE / "DIFFERENTIAL.md").write_text(report, encoding="utf-8", newline="\n")
    n = write_provenance(nov)
    print(report)
    print(f"wrote DIFFERENTIAL.md + PROVENANCE.json ({n} N-ORIG rules)")


if __name__ == "__main__":
    main()
