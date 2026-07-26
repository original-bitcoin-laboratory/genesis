"""NOV08-X consensus — one parameterised engine, two profiles.

Loads a rule set (`rules_nov08.json` / `rules_jan09.json`) and implements the four
places where November and January actually diverge, each faithful to its source:

- subsidy schedule   GetBlockValue           NOV08 main.cpp:652 / JAN09 main.cpp:675
- proof-of-work      difficulty encoding     NOV08 main.h:875   / JAN09 bignum.h SetCompact
- retarget           GetNextWorkRequired     NOV08 main.cpp:660 / JAN09 proportional
- coinbase value     block acceptance check  NOV08 main.cpp:739 / JAN09 main.cpp:953

"November wins": the NOV08 rules are read verbatim from the surviving pre-release
source (class N-ORIG in DESIGN_LEDGER.md). JAN09 is the differential baseline only.
Evidence level: MODEL.
"""

from __future__ import annotations

import json
import pathlib

_HERE = pathlib.Path(__file__).resolve().parent


class Rules:
    def __init__(self, doc: dict):
        self.doc = doc
        self.profile = doc["profile"]
        m, t, p = doc["monetary"], doc["timing"], doc["pow"]
        self.COIN = m["COIN"]["units"]
        self.CENT = m["CENT"]["units"]
        self.subsidy_base = m["subsidy_base"]["units"]
        self.halving = m["halving_interval"]["blocks"]
        self.fee_fixed = m.get("tx_fee_fixed", {}).get("units", 0)
        self.spacing = t["target_spacing_sec"]["value"]
        self.timespan = t["target_timespan_sec"]["value"]
        self.retarget_algo = t["retarget_algo"]["value"]          # "nudge" | "proportional"
        self.pow_encoding = p["encoding"]["value"]                # "leading-zero-bits" | "compact"
        self.min_pow = p["min_proof_of_work"]["value"]
        self.coinbase_rule = doc["coinbase_value_rule"]["value"]  # "equal" | "le"

    @classmethod
    def load(cls, name: str) -> "Rules":
        return cls(json.loads((_HERE / f"rules_{name}.json").read_text(encoding="utf-8")))

    # ---- GetBlockValue (subsidy + fees) --------------------------------------
    def get_block_value(self, best_height: int, fees: int = 0) -> int:
        """Faithful to each edition's halving. NOTE both use the GLOBAL best height,
        not the block's own height (a real quirk preserved on both sides)."""
        subsidy = self.subsidy_base
        if self.profile == "NOV08":                # main.cpp:655 — explicit loop
            i = self.halving
            while i <= best_height:
                subsidy //= 2
                i += self.halving
        else:                                      # JAN09 main.cpp:680 — bit shift
            # C++ integer division truncates toward zero; nBestHeight=-1 (genesis) -> 0
            subsidy >>= (max(0, best_height) // self.halving)
        return subsidy + fees

    # ---- proof-of-work encoding ----------------------------------------------
    def pow_target(self, nBits: int) -> int:
        if self.pow_encoding == "leading-zero-bits":   # NOV08 main.h:875: (~0) >> nBits
            return (1 << (256 - nBits)) - 1
        # JAN09 compact mantissa/exponent
        exp, mant = nBits >> 24, nBits & 0x007FFFFF
        return mant * (1 << (8 * (exp - 3))) if exp > 3 else mant >> (8 * (3 - exp))

    def pow_ok(self, header_hash: bytes, nBits: int) -> bool:
        if self.pow_encoding == "leading-zero-bits" and nBits < self.min_pow:
            return False                               # main.h:875 / main.cpp:1172
        return int.from_bytes(header_hash, "little") <= self.pow_target(nBits)

    # ---- GetNextWorkRequired --------------------------------------------------
    def next_work(self, nBits_last: int, actual_timespan: int):
        """Returns (new_nBits_or_target, human) for a full retarget window."""
        if self.retarget_algo == "nudge":              # NOV08 main.cpp:690-698 (±1 bit)
            nb = nBits_last
            if actual_timespan > self.timespan * 2 and nBits_last >= self.min_pow:
                nb = nBits_last - 1                     # too slow -> fewer zero bits -> EASIER
                how = f"nBits {nBits_last}->{nb} (one bit EASIER)"
            elif actual_timespan < self.timespan // 2:
                nb = nBits_last + 1                     # too fast -> more zero bits -> HARDER
                how = f"nBits {nBits_last}->{nb} (one bit HARDER)"
            else:
                how = f"nBits {nBits_last} (unchanged)"
            return nb, how
        # JAN09 proportional: target *= clamp(actual, timespan/4, timespan*4) / timespan
        actual = max(self.timespan // 4, min(self.timespan * 4, actual_timespan))
        old = self.pow_target(nBits_last)
        new = old * actual // self.timespan
        return new, f"target x{actual/self.timespan:.2f} (proportional, clamped 4x)"

    # ---- coinbase value acceptance -------------------------------------------
    def coinbase_ok(self, claimed: int, block_value: int) -> bool:
        if self.coinbase_rule == "equal":              # NOV08 main.cpp:739 (!= rejects)
            return claimed == block_value
        return claimed <= block_value                  # JAN09 main.cpp:953 (> rejects)

    # ---- denomination ---------------------------------------------------------
    def fmt(self, units: int) -> str:
        return f"{units / self.COIN:.6f} coins ({units} units, COIN={self.COIN:g})"

    # ---- provenance ----------------------------------------------------------
    def provenance_rows(self):
        """(rule, value, source, class) for every N-ORIG rule — feeds PROVENANCE.json."""
        d = self.doc
        rows = []
        for sect in ("monetary", "timing", "pow"):
            for k, v in d[sect].items():
                rows.append({"rule": f"{sect}.{k}",
                             "value": v.get("units", v.get("blocks", v.get("value"))),
                             "source": v.get("source"), "class": v.get("class")})
        for k in ("coinbase_value_rule", "orphan_root_return"):
            v = d[k]
            rows.append({"rule": k, "value": v.get("value"), "source": v.get("source"),
                         "class": v.get("class")})
        return rows
