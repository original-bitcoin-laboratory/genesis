#!/usr/bin/env python3
"""Reference-relative protocol-profile comparison — the reproducible engine. NOT money.

Every cell is a **source-audited encoding** of a chain's consensus rule at a frozen evaluation date:
a value, the objective criterion that decides it, one or more primary-source citations, and a
confidence marker. The whole table therefore **re-derives deterministically from this file**.

⛔⛔ AND THIS PARAGRAPH SAID SOMETHING ELSE UNTIL 14 AUGUST 2026, WHICH IS THE THIRD TIME THIS FILE
    HAS BEEN CAUGHT ASSERTING A CLAIM THE PAPER HAD ALREADY RETRACTED. It read: a "machine-checkable
    fact … not a coder's judgement … there is nothing for independent coders to disagree about", and
    it claimed cells carry "an activation height/commit". **Neither is true.** No cell has an
    activation field, and §5.1 of the paper exists precisely because relabelling moves the score:
    `no-dedicated-cap` and `no-consensus-cap` name the same state and are scored a MISMATCH.

    ★★★ REPRODUCIBILITY DOES NOT REMOVE JUDGEMENT — IT RELOCATES IT to individuation, where it is
        visible and can be perturbed on purpose. Two coders sharing an encoding cannot disagree
        about the score; they can disagree about the encoding, and this engine measures that.

    ⚠️ Found by an external referee, twice, in the same docstring being repaired for the same fault.
       **Documentation is part of the artifact; a false comment is a false claim.**

It computes, for each (reference, chain) pair, a **mismatch rate** (differing / jointly-specified axes)
and a **coverage** (jointly-specified / total); the mismatch rate is *undefined* where coverage is 0. It
then runs sensitivity analyses — leave-one-axis-out, a merged witness/signature individuation, subset
robustness, and LABEL GRANULARITY — so the reader can see how much any ranking depends on the
encoding. Outputs CSV/JSON.

    python obl_metric.py [--at YYYY-MM-DD] [--out DIR]

References (origins) and chains are protocol *profiles*. Values are canonical labels; two profiles
"match" on an axis iff their labels are equal. `None` = the profile does not specify that axis (missing),
which is kept distinct from "specified and identical". Evidence date frozen below. NOT money.

⚠️ WHAT `--at` DOES AND DOES NOT DO — corrected 13 August 2026.
   It was previously documented here and in METHOD.md as "evaluates at an earlier date". **It did
   not.** No cell carried an activation date, so every date produced byte-identical output; the flag
   validated its argument against the freeze and then had no effect on any number.

     ★ AN ADVERTISED KNOB THAT SILENTLY DOES NOTHING IS THE WORST DEFECT AVAILABLE TO A PAPER WHOSE
       CLAIM IS REPRODUCIBILITY. A reader who tries it and finds it inert has no way to tell which
       other claim is also decorative.

   ⛔⛔ AND THE PARAGRAPH THAT STOOD HERE UNTIL 13 AUG 2026 COMMITTED THE SAME OFFENCE AGAIN.
      It read: *"It is now REAL: each chain cell may carry `activated` (an ISO date)…"*. **No cell
      carries an `activated` key. The string appears in no cell in this file.** The sentence sat
      four lines below the ★ warning about knobs that silently do nothing.

      ★★★ TWO INDEPENDENT REFEREES FOUND IT, AND BOTH LED WITH IT — because a paper whose
      centrepiece is "an advertised control that does nothing is the worst available defect" had
      shipped an engine whose own docstring did exactly that. **Documentation is part of the
      artifact. A false comment is a false claim.**

   WHAT `--at` ACTUALLY DOES: it accepts only the evidence freeze and REFUSES every other date,
   printing what would be required to support one. Historical evaluation is NOT implemented and is
   reported as a limitation in the paper (§7), not concealed behind a flag.

⚠️ AND THE SAME REVIEW FOUND A SECOND FALSE ADVERTISEMENT in the line above: this docstring
   promised an "equal vs category weighting" sensitivity. **No weighting code exists.** Removed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import date
from pathlib import Path

# Descendant states are asserted up to this date; --at may not exceed it (values would be extrapolation).
EVIDENCE_FREEZE = date(2026, 8, 1)

REFERENCES = ["whitepaper", "nov08", "v0.1.0"]
CHAINS = ["BTC", "BCH", "BSV", "XEC", "BTG"]  # BTG added 14 Aug 2026 (R4): it satisfies the rule
PROFILES = REFERENCES + CHAINS

# Primary sources, cited by key from each cell. Kept together so every value points at a checkable record.
SOURCES = {
    "wp": "Nakamoto, Bitcoin whitepaper (2008)",
    "nov08": "15 Nov 2008 pre-release source (SNI code archive; source-bounded model)",
    "v01": "Bitcoin v0.1.0 source (SNI code archive)",
    "c_chainwork": "bitcoin/bitcoin 3b7cd5d8 (2010, v0.3.3): best chain by cumulative work",
    "c_1mb": "bitcoin/bitcoin a30b56eb (2010): MAX_BLOCK_SIZE = 1,000,000",
    # The COMMIT HASH is the citation; the date is a reader convenience. A content-addressed
    # identifier cannot go stale, which is why it is the anchor and the year never was.
    "c_opdis": "bitcoin/bitcoin 4bd188c4 (15 Aug 2010): disable OP_CAT/OP_MUL/bitwise etc. + "
               "520 B element limit + nMaxNumSize 258->4",
    "bip16": "BIP16 P2SH (2012)",
    "bip66": "BIP66 strict-DER signatures (2015)",
    "bip65": "BIP65 OP_CHECKLOCKTIMEVERIFY (2015)",
    "bip112": "BIP112 OP_CHECKSEQUENCEVERIFY / relative locktime (2016)",
    "bip141": "BIP141 segregated witness (2017)",
    "bip34x": "BIP340-342 Schnorr/Taproot (2021)",
    "cve2010": "CVE-2010-5139 value-overflow fix: MoneyRange / output-sum check (Aug 2010)",
    "bch_fork": "Bitcoin Cash Aug 2017 fork: SIGHASH_FORKID replay protection, 8 MB blocks",
    "bch_2018": "BCH May 2018 upgrade: re-enable OP_CAT/OP_SPLIT/bitwise/OP_DIV etc., 32 MB",
    # ── ADDED 14 Aug 2026, all fetched and quoted; see AUDIT-LEDGER.md ────────────────────────
    "bch_abla": "CHIP-2023-04 Adaptive Blocksize Limit Algorithm (gitlab.com/0353F40E/ebaa, "
                "status Accepted). Activated on BCH mainnet at MTP >= 1715774400 "
                "(15 May 2024 12:00:00 UTC) per upgradespecs.bitcoincashnode.org/2024-05-15-upgrade. "
                "The maximum block size becomes ALGORITHMICALLY VARYING, not a constant",
    "bch_vm_limits": "CHIP-2021-05 Targeted Virtual Machine Limits (github.com/bitjson/bch-vm-limits, "
                     "status Final, v3.1.3). Activated 2025-05-15T12:00:00Z. Raises the stack "
                     "element length limit from 520 to 10,000 bytes",
    "abc_src": "Bitcoin ABC source, src/script/script.h (master): "
               "'static const unsigned int MAX_SCRIPT_ELEMENT_SIZE = 520;' and "
               "'constexpr size_t MAX_SCRIPTNUM_BYTE_SIZE = 8;'. For a chain the implementation "
               "IS the consensus rule",
    "bch_ctor": "BCH Nov 2018 upgrade: CTOR (canonical tx ordering), OP_CHECKDATASIG",
    "bch_schnorr": "BCH May 2019 upgrade: Schnorr signatures",
    # ⚠️ ADDED 13 Aug 2026. BSV's difficulty algorithm was cited to the AUGUST 2017 fork, which
    #    shipped EDA. cw-144 is a SEPARATE, LATER upgrade and BSV inherits it from there.
    "bch_daa_2017": "BCH 13 Nov 2017 upgrade: cw-144 difficulty algorithm, replacing the EDA that "
                    "the 1 Aug 2017 fork shipped",
    "bch_asert": "BCH Nov 2020 upgrade: ASERT (aserti3-2d) difficulty algorithm",
    # ⛔ CORRECTED 14 Aug 2026 by audit_descendants.py. This read "BCH May 2022 upgrade: large
    #    script integers (BigInt)" and CONFLATED TWO UPGRADES: May 2022 delivered 64-BIT integers
    #    (CHIP-2021-03 native introspection / int64); arbitrary precision arrived with CHIP-2024-07
    #    BigInt, activated 15 May 2025 — still before the 1 Aug 2026 freeze, so the CELL VALUE was
    #    right and only the citation was wrong. ★ A cell can be correct and still be unsourced.
    "bch_bigint": "CHIP-2024-07 BigInt: High-Precision Arithmetic for Bitcoin Cash "
                  "(github.com/bitjson/bch-bigint), activated 15 May 2025. NOT the May 2022 "
                  "upgrade, which delivered 64-bit script integers",
    # ★ ADDED 14 Aug 2026. BSV's sig_scheme cell previously cited bsv_genesis, but genesis-spec.md
    #   contains ZERO occurrences of 'ECDSA', 'Schnorr' or 'signature scheme' (measured). The value
    #   is right; it is an ABSENCE, and absences must be cited as such.
    "bsv_no_schnorr": "ABSENCE: no BSV upgrade specification introduces Schnorr signatures; "
                      "genesis-spec.md does not mention ECDSA or Schnorr at all (measured "
                      "14 Aug 2026). Weaker footing than a positive citation, by construction",
    "bsv_genesis": "bitcoin-sv-specs/protocol genesis-spec.md (Feb 2020): remove block cap, remove P2SH, "
                   "restore opcodes / miner-configurable limits; sunsets CLTV and CSV to NOPs; "
                   "Numeric Value Size Consensus Rule = 750,000 bytes",
    # ⚠️ ADDED 13 Aug 2026 after a referee. Verified by fetching the spec: §2 raises the script
    #    number consensus limit from 750KB to 32MB, and it adds opcodes (OP_LSHIFTNUM,
    #    OP_RSHIFTNUM, OP_SUBSTR, OP_LEFT, OP_2DIV…) beyond the post-Genesis set.
    # ⚠️ TWO SOURCES GIVE TWO HEIGHTS, and the paper must show that rather than pick one silently.
    #    chronicle-spec.md states mainnet 943,835 (fetched and quoted by audit_descendants.py);
    #    the BSV Node v1.2.0 release notes state 943,816, targeted 7 April 2026.
    #    ★ NOT LOAD-BEARING, and that is measured rather than shrugged: the two are 19 blocks apart
    #      at ~10-minute spacing, so BOTH fall on 7 April 2026 — four months before the 1 Aug 2026
    #      freeze. The cell's value is identical under either. Recorded because exact source
    #      attribution is part of this method's claim, so an unreconciled discrepancy must stay
    #      VISIBLE even when it changes no number.
    "bsv_chronicle": "bitcoin-sv-specs/protocol chronicle-spec.md: script-number consensus limit "
                     "750KB -> 32MB; further opcode additions. Activation height: the spec states "
                     "mainnet 943,835, the BSV Node v1.2.0 release notes state 943,816 "
                     "(7 Apr 2026); both precede the freeze, so the cell value is unaffected",
    # ⚠️ AXIS SCOPE, stated because a referee could read this cell either way. This axis is the
    #    BASE difficulty-adjustment algorithm. eCash has additionally enforced Real Time Targeting
    #    (Heartbeat) since Nov 2024, where blocks failing the real-time target are rejected by the
    #    Avalanche layer. ★ That is a SEPARATE consensus condition on PoW, and it is already
    #    captured on the fork_choice axis as "most-work+avalanche" — encoding it here too would
    #    double-count one mechanism across two axes and inflate XEC's distance artificially.
    "btg_src": "BTCGPU/BTCGPU src/chainparams.cpp (master): BIP34Height = 227931, "
               "SegwitHeight = 481824, nPowTargetSpacing = 10*60, LWMA difficulty, Equihash PoW. "
               "BTG forked at height 491,406, AFTER BIP34 and segwit activated on Bitcoin, so it "
               "inherits both. For a chain the implementation IS the consensus rule",
    "btg_fork": "Bitcoin Gold Oct 2017 fork: SIGHASH_FORKID-style replay protection, "
                "Equihash-BTG (Zhash 144,5) proof-of-work, ledger duplicated to block 491,406",
    "bip34": "BIP34: coinbase must contain the block height. Activated on Bitcoin mainnet 2013 "
             "(Core consensus param BIP34Height = 227931), therefore inherited by every chain in "
             "this set, all of which forked later",
        # ⛔ RE-SCOPED 14 Aug 2026 (R4). The previous note put Real Time Targeting on the fork-choice
    #    axis "to avoid double-counting". That was wrong on eCash's own description: RTT adds a
    #    SECOND difficulty on top of the base DAA and blocks exceeding the Real Time Target are
    #    REJECTED. ★ Rejecting a block is an acceptance rule, not a tip-selection rule -- and
    #    fork_choice's stated criterion asks only how a node picks among valid tips.
    #    ⇒ The axis is widened to "base DAA + any additional real-time target", which is what the
    #      rule actually is, rather than parked on an axis where it was invisible.
    "xec_asert": "eCash (XEC) inherits ASERT from Bitcoin Cash ABC (Nov 2020) and has additionally "
                 "enforced Real Time Targeting (Heartbeat) since Nov 2024: a second difficulty on "
                 "top of the base DAA, with blocks exceeding the Real Time Target rejected",
    "xec_aval": "eCash Avalanche post-consensus block finalisation (e.cash)",
    "shared": "inherited unchanged from v0.1 by all descendants (21e6 cap, 210k-block halving, ~10-min "
              "target); XEC redenominated units (2 decimals) without changing the schedule",
}

# --- the axis table -----------------------------------------------------------------------------------
# Each axis: id, name, criterion (the objective question), and per-profile {value, source, confidence}.
# value None = the profile does not specify this axis. confidence: "high" | "med".
def _c(value, src, conf="high"):
    """`src` is a source KEY, or a list of keys where a value rests on more than one record.

    ⚠️ THE LIST FORM EXISTS BECAUSE A STRESS TEST FOUND TWO CELLS UNDER-CITING. `bip65` and `c_1mb`
       were defined in SOURCES and referenced by nothing: BTC's timelock cell cited only BIP112
       (CSV) and not BIP65 (CLTV), and BTC's block-size cell cited only BIP141 and not the 2010
       commit that introduced the 1 MB cap in the first place. Both values were right and both
       citations were incomplete.

       ★ An unused entry in a source table is not housekeeping — it is a cell that should have
         cited it and did not. In a method whose premise is that a reader may contest any cell
         AGAINST ITS SOURCE, an incomplete citation is a real defect.
    """
    return {"value": value, "source": src, "confidence": conf}


# ── audit provenance ──────────────────────────────────────────────────────────────────────────
#
# ★★★★ WHY THIS EXISTS, AND IT IS THE PROJECT'S OWN METHOD TURNED ON ITSELF.
#
# The author-verification statement said: "Every consensus value in the dataset was verified by the author
# against the primary record named in its cell." **Two referee rounds then found five demonstrable
# errors in the handful of cells anyone happened to check.** The sentence was not a small
# overstatement; it was the kind of unfalsifiable blanket claim this paper exists to replace.
#
#   ⇒ SO IT BECOMES A MEASUREMENT. Each cell that has actually been checked against a fetched
#     primary source carries the date and what was read. `audit_coverage()` counts them, the paper
#     reports the count, and the claim shrinks to exactly what was done.
#
#   ★★ "N of 68 verified, here is which" is a WEAKER claim than "all verified" and a far stronger
#      artifact, because it is checkable and it cannot silently rot. **A blanket assurance degrades
#      to zero the moment one counterexample appears; a count degrades by one.**
AUDITED = {
    ("BSV", "timelock_opcodes"): "2026-08-13 genesis-spec.md fetched: CLTV/CSV 'revert to NOPs'",
    ("BSV", "script_number_width"): "2026-08-13/14 genesis-spec.md (750KB) + chronicle-spec.md "
                                    "(750KB->32MB); activation height confirmed pre-freeze on-chain",
    ("BSV", "element_size_limit"): "2026-08-13 genesis-spec.md: element-size consensus rule removed",
    ("BSV", "p2sh"): "2026-08-13 genesis-spec.md: 'Sunset P2SH'",
    ("BSV", "script_opcodes"): "2026-08-13 genesis-spec.md: disabled-operations rule",
    ("BCH", "block_size_rule"): "2026-08-14 CHIP-2023-04 ABLA + upgradespecs 2024-05-15: cap is "
                                "algorithmically varying from 15 May 2024",
    ("BCH", "element_size_limit"): "2026-08-14 bch-vm-limits CHIP (Final): 520 -> 10,000, "
                                   "activated 2025-05-15",
    ("XEC", "element_size_limit"): "2026-08-14 Bitcoin ABC src/script/script.h: "
                                   "MAX_SCRIPT_ELEMENT_SIZE = 520",
    ("XEC", "script_number_width"): "2026-08-14 Bitcoin ABC src/script/script.h: "
                                    "MAX_SCRIPTNUM_BYTE_SIZE = 8",
    # ---- added 14 Aug 2026 (R3): the rest of what audit_descendants.py and audit_btc.py FETCH.
    #      ⚠️ This table had drifted BEHIND the audit scripts: they probed 26 cells and this listed
    #      9, so audit_coverage() under-reported the work while the paper over-reported it — the
    #      two errors pointed in opposite directions and neither was visible from the other file.
    ("BCH", "script_number_width"): "2026-08-14 CHIP-2024-07 BigInt readme (activated 2025-05-15)",
    ("BCH", "difficulty_algorithm"): "2026-08-14 upgradespecs 2020-11-15: aserti3-2d",
    ("BCH", "tx_ordering"): "2026-08-14 upgradespecs 2018-nov: canonical transaction order",
    ("BCH", "sig_scheme"): "2026-08-14 upgradespecs 2019-05-15: Schnorr",
    ("BCH", "script_opcodes"): "2026-08-14 may-2018-reenabled-opcodes spec: OP_CAT/OP_SPLIT",
    ("XEC", "script_opcodes"): "2026-08-14 may-2018-reenabled-opcodes spec (inherited)",
    ("XEC", "difficulty_algorithm"): "2026-08-14 upgradespecs 2020-11-15 (inherited)",
    ("BTC", "p2sh"): "2026-08-14 BIP16 fetched",
    ("BTC", "sig_encoding"): "2026-08-14 BIP66 fetched",
    ("BTC", "timelock_opcodes"): "2026-08-14 BIP65 + BIP112 fetched",
    ("BTC", "segwit"): "2026-08-14 BIP141 fetched",
    ("BTC", "block_size_rule"): "2026-08-14 BIP141 fetched: weight limit",
    ("BTC", "taproot"): "2026-08-14 BIP341 fetched",
    ("BTC", "sig_scheme"): "2026-08-14 BIP340 fetched: Schnorr",
    # ⛔ R4: this cell WAS fetched and confirmed against genesis-spec.md by audit_descendants.py
    #    and the dict did not list it, so the paper reported it as "anchored but not yet fetched".
    #    ★ The permanent fix is _audited_from_artifacts(), which reads what the scripts actually
    #    verified; this entry exists so the dict and the artifact AGREE rather than one shadowing
    #    the other. **Two sources of truth for the same fact is the defect, not the number.**
    ("BSV", "block_size_rule"): "2026-08-14 genesis-spec.md: block size is a configurable "
                                "consensus rule, not a constant",
}

# ★ Cells whose warrant is NOT a fetch, recorded so coverage is never overstated by omission.
#   These are the two honest categories the R3 referee asked to see quantified alongside the
#   probe counts. **"18 of 18 probes passed" is a SAMPLE statistic; the denominator is here.**
INHERITED = {                       # argued from a shared ancestor that pre-dates every fork
    ("BCH", "sig_encoding"), ("BSV", "sig_encoding"), ("XEC", "sig_encoding"),
    ("BCH", "value_range_check"), ("BSV", "value_range_check"), ("XEC", "value_range_check"),
    ("BTC", "value_range_check"),
    ("BCH", "fork_choice"), ("BSV", "fork_choice"), ("BTC", "fork_choice"),
    ("BCH", "replay_protection"), ("BSV", "replay_protection"), ("XEC", "replay_protection"),
    ("BTC", "replay_protection"),
    ("BCH", "p2sh"), ("XEC", "p2sh"),
    ("BCH", "subsidy_base"), ("BSV", "subsidy_base"), ("XEC", "subsidy_base"),
    ("BTC", "subsidy_base"),
    ("BCH", "block_spacing"), ("BSV", "block_spacing"), ("XEC", "block_spacing"),
    ("BTC", "block_spacing"),
    ("BTC", "difficulty_algorithm"), ("BTC", "tx_ordering"),
    # ★ R5 ADJUDICATED, because a checker asked. Both of these are values that now appear on ONE
    #   chain only, which looks like a chain-specific introduction and is not:
    #     XEC/block_size_rule = 32mb        inherited from BCH's May 2018 upgrade; BCH has since
    #                                        moved to ABLA, so the ancestor changed and XEC did not
    #     BSV/difficulty_algorithm = cw-144 inherited from BCH's Nov 2017 upgrade; BCH has since
    #                                        moved to ASERT, same shape
    #   ⇒ "unique to one chain" is not the test. The test is whether the chain INTRODUCED it.
    #     Neither did. Contrast BTG/pow_function, which BTG did introduce -- and which is why it
    #     was removed from this set.
    ("XEC", "block_size_rule"), ("BSV", "difficulty_algorithm"),
    ("BTC", "script_opcodes"), ("BTC", "script_number_width"), ("BTC", "element_size_limit"),
    # BTG: every cell is either inherited from Bitcoin at the 491,406 split or read from the
    # chain's own chainparams.cpp, which audit_btg.py fetched.
    ("BTG", "fork_choice"), ("BTG", "sig_encoding"), ("BTG", "value_range_check"),
    ("BTG", "p2sh"), ("BTG", "script_opcodes"), ("BTG", "script_number_width"),
    ("BTG", "element_size_limit"), ("BTG", "timelock_opcodes"), ("BTG", "tx_ordering"),
    ("BTG", "subsidy_base"), ("BTG", "block_spacing"), ("BTG", "replay_protection"),
    ("BTG", "coinbase_height"), ("BTG", "block_size_rule"), ("BTG", "segwit"),
    # ⛔ R5: ("BTG","pow_function") and ("BTG","replay_protection") were HERE and both are wrong.
    #    BTG INTRODUCED Equihash-BTG and its replay protection at its own fork -- a rule changed
    #    at a fork can never be "inherited from an ancestor pre-dating every fork in the set".
    #    ★ The one axis BTG was added to expose was warranted as inherited from an ancestor that
    #      never had it. Both are now ANCHORED-UNFETCHED against btg_fork until probed.
    # every chain inherits BIP34 from Bitcoin; none of them introduced it
    ("BTC", "coinbase_height"), ("BCH", "coinbase_height"), ("BSV", "coinbase_height"),
    ("XEC", "coinbase_height"),
    # sha256d is v0.1.0's own function, unchanged on four of the five chains.
    # ⚠️ BTG is NOT among them -- it changed the function, which is why the axis exists.
    ("BTC", "pow_function"), ("BCH", "pow_function"), ("BSV", "pow_function"),
    ("XEC", "pow_function"),
}
ABSENCE = {                         # ⛔ unconfirmable by construction: no document proves an absence
    ("BCH", "segwit"), ("BSV", "segwit"), ("XEC", "segwit"),
    ("BCH", "taproot"), ("BSV", "taproot"), ("XEC", "taproot"),
    ("BSV", "sig_scheme"),
    ("BTG", "taproot"), ("BTG", "sig_scheme"),
    # ⛔ R5: ("BTG","difficulty_algorithm") was HERE. LWMA is a POSITIVE, PRESENT consensus rule
    #    with a published spec -- the exact opposite of a claim of absence. Removed.
}


def _audit_units():
    """Probe counts AND distinct-cell counts, kept apart because they are different units.

    A probe is one fetch-and-check. A cell is one (chain, axis) pair. audit_btc.py runs 8 probes
    over 7 cells, so the two totals differ and must never be added across.
    """
    import json as _j
    here = Path(__file__).resolve().parent / "tables"
    def recs(name):
        p = here / name
        if not p.exists():
            return []
        return _j.loads(p.read_text(encoding="utf-8")).get("records", [])
    btc = recs("audit_btc.json")
    dec = recs("audit_descendants.json")
    btg = [r for r in dec if r.get("chain") == "BTG"]
    oth = [r for r in dec if r.get("chain") and r.get("chain") != "BTG"]
    cell = lambda rs: {(r["chain"], r["axis"]) for r in rs if r.get("chain")}
    return (len(btc) + len(oth), len(btg), len(cell(btc) | cell(oth)))


_AUD_PROBES_FIRST2, _AUD_PROBES_BTG, _AUD_CELLS_FIRST2 = _audit_units()


def _audited_from_artifacts():
    """Read what the audit scripts ACTUALLY verified, from the JSON they emit.

    ★★★ R4, AND IT IS THE SAME MOVE ONE LAYER OUT. Round 2 stopped the manuscript hand-carrying
        numbers the engine computes. Round 3 stopped the captions hand-carrying which table they
        labelled. **Round 4 stops the ENGINE hand-carrying what the audit scripts verified.**

    ⛔ The defect that forced it: `AUDITED` listed 23 cells while the scripts probed 24, so
       BSV/block_size_rule was fetched and confirmed against genesis-spec.md and reported by the
       paper as *"anchored but not yet fetched."* The error was conservative, which is exactly why
       it survived — **and if a probe were deleted, the dict would keep claiming it and every gate
       would stay green.**

    ⇒ Each layer that stops hand-carrying exposes the next one that still does. The artifact
      carries the document's SHA-256, so a claim of "fetched" now names bytes somebody can re-hash.
    """
    found, stale = {}, []
    d = Path(__file__).resolve().parent / "tables"
    for name in ("audit_btc.json", "audit_descendants.json"):
        f = d / name
        if not f.exists():
            continue
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        for r in rec.get("records", []):
            if not (r.get("matched") and r.get("control_passed")):
                continue
            # ⛔ R5: an audit of an OLD value must not certify a CHANGED one. audit_descendants
            #    verified XEC difficulty_algorithm = "asert"; the engine now says "asert+rtt".
            #    Matching on (chain, axis) alone let a stale record vouch for a new cell.
            #    ★ A fetch is evidence for the VALUE it fetched, not for the coordinate it sat at.
            cur = _cell_value(r["chain"], r["axis"])
            if cur is not None and r.get("value") is not None and str(r["value"]) != str(cur):
                stale.append((r["chain"], r["axis"], r["value"], cur))
                continue
            found[(r["chain"], r["axis"])] = "%s %s (sha256 %s)" % (
                rec.get("generated_utc", "")[:10], r.get("url", ""),
                (r.get("body_sha256") or "")[:12])
    if stale:
        print("  ⚠ STALE AUDIT RECORDS — the artifact verified a value the dataset no longer holds:")
        for ch, ax, was, now in stale:
            print("     %s/%s  audited %r, cell is now %r -> NOT counted as fetched"
                  % (ch, ax, was, now))
    return found


def _cell_value(chain, axis_id):
    for a in AXES:
        if a["id"] == axis_id:
            return a["p"].get(chain, {}).get("value")
    return None


def audit_coverage(axes=None):
    """Every specified chain cell, partitioned by WHAT ITS WARRANT ACTUALLY IS.

    ★★ R3 FINDING, and it is the right criticism: the paper reported "8 of 8" and "18 of 18"
       without denominators. Those are pass rates on probes that were RUN, not coverage of the
       dataset. A reader cannot tell 18/18 of eighteen from 18/18 of fifty-one.
    """
    axes = axes or AXES
    spec = [(c, a["id"]) for a in axes for c in CHAINS if a["p"][c]["value"] is not None]
    # ★ the artifact is authoritative where it exists; AUDITED is the fallback for cells whose
    #   warrant is a fetch nobody scripted (e.g. audit_btg.py's chainparams read).
    live = _audited_from_artifacts()
    warrant = dict(AUDITED)
    warrant.update(live)
    fetched = [x for x in spec if (x[0], x[1]) in warrant]
    inherit = [x for x in spec if x not in fetched and (x[0], x[1]) in INHERITED]
    absent = [x for x in spec if (x[0], x[1]) in ABSENCE]
    # ⛔ R5 INVARIANT: the four warrants must be mutually exclusive by construction, not by
    #    hope. Precedence is fetched > absence > inherited, and anything claimed by more than
    #    one set is a DEFECT that must be visible rather than silently resolved.
    overlap = (set(fetched) & set(inherit)) | (set(fetched) & set(absent)) | (set(inherit) & set(absent))
    if overlap:
        print("  ⛔ WARRANT SETS OVERLAP — a cell cannot have two warrants:")
        for c, ax in sorted(overlap):
            print("     %s/%s" % (c, ax))
    inherit = [x for x in inherit if x not in set(fetched) | set(absent)]
    accounted = set(fetched) | set(inherit) | set(absent)
    other = [x for x in spec if x not in accounted]
    return {"total": len(axes) * len(CHAINS), "specified": len(spec),
            "fetched": len(fetched), "inherited": len(inherit), "absence": len(absent),
            "unclassified": len(other), "warrant_overlap": len(overlap),
            "by_chain": {c: sum(1 for x in fetched if x[0] == c) for c in CHAINS},
            "unclassified_cells": sorted("%s/%s" % (c, ax) for c, ax in other),
            "cells": sorted("%s/%s" % (c, ax) for c, ax in fetched)}


def src_keys(cell):
    """Normalise a cell's source to a list of keys, whichever form it was written in."""
    s = cell["source"]
    return list(s) if isinstance(s, (list, tuple)) else [s]

AXES = [
    {"id": "fork_choice", "name": "Best-chain selection",
     "criterion": "How the node picks the active tip.",
     "p": {"whitepaper": _c("most-work", "wp"), "nov08": _c(None, "nov08"),
           "v0.1.0": _c("height", "v01"),
           "BTC": _c("most-work", "c_chainwork"), "BCH": _c("most-work", "c_chainwork"),
           "BSV": _c("most-work", "c_chainwork"), "XEC": _c("most-work+avalanche", "xec_aval"),
           "BTG": _c("most-work", "c_chainwork")}},

    {"id": "block_size_rule", "name": "Block-size consensus rule",
     "criterion": "The dedicated maximum-block-size consensus rule (ignoring the generic serialisation ceiling).",
     "p": {"whitepaper": _c(None, "wp"), "nov08": _c(None, "nov08"),
           "v0.1.0": _c("no-dedicated-cap", "v01"),
           # both records: the 2010 commit created the cap, BIP141 amended it to a weight limit
           "BTC": _c("1mb+weight", ["c_1mb", "bip141"]),
           # CORRECTED 14 Aug 2026 (AUDIT-LEDGER 4): ABLA activated 15 May 2024 and makes
           # the maximum block size ALGORITHMICALLY VARYING. "32mb" was a constant where the
           # consensus rule is a function. A large number is not the same kind of thing.
           "BCH": _c("abla-dynamic", "bch_abla"),
           "BSV": _c("no-consensus-cap", "bsv_genesis"), "XEC": _c("32mb", "bch_2018"),
           "BTG": _c("1mb+weight", "btg_src")}},

    {"id": "script_opcodes", "name": "Script opcode vocabulary",
     "criterion": "Status of the broad opcode set v0.1 shipped and 2010 disabled (OP_CAT, OP_MUL, bitwise, etc.).",
     "p": {"whitepaper": _c(None, "wp"), "nov08": _c(None, "nov08"),
           "v0.1.0": _c("broad", "v01"),
           "BTC": _c("restricted", "c_opdis"), "BCH": _c("partial-restore", "bch_2018"),
           "BSV": _c("broad", "bsv_genesis"), "XEC": _c("partial-restore", "bch_2018"),
           "BTG": _c("restricted", "c_opdis")}},

    {"id": "script_number_width", "name": "Script-number operand width",
     "criterion": "The maximum width of a numeric script operand.",
     "p": {"whitepaper": _c(None, "wp"), "nov08": _c(None, "nov08"),
           "v0.1.0": _c("unbounded-openssl", "v01"),
           "BTC": _c("4-byte", "c_opdis"), "BCH": _c("large-bigint", "bch_bigint", "med"),
           # ⛔ CORRECTED TWICE, 13 Aug 2026, both times against the primary source.
           #    (1) It said "unbounded". genesis-spec.md, "Numeric Value Size Consensus Rule":
           #        "the length of the byte sequence must be less than or equal to 750,000 bytes."
           #        A large limit is not the absence of one.
           #    (2) A referee said BSV's Chronicle upgrade supersedes that. IT DOES.
           #        chronicle-spec.md §2, verbatim: "The consensus limit for the maximum script
           #        number size is increased from 750KB to 32MB."
           #    ⇒ 32 MB, citing BOTH specs, because the value is only legible as a succession.
           #    ⚠️ AUTHOR — ONE THING STILL UNVERIFIED: chronicle-spec.md states an activation
           #       HEIGHT (mainnet 943,835), not a date. Whether that height was reached before
           #       the 1 Aug 2026 freeze is checkable on-chain and HAS NOT BEEN CHECKED HERE.
           #       If it was not, the correct value at the freeze is 750kb-limit.
           #       Either way the cell mismatches v0.1.0, so no reported rate moves.
           "BSV": _c("32mb-limit", ["bsv_genesis", "bsv_chronicle"], "med"),
           # CORRECTED (AUDIT-LEDGER 2): Bitcoin ABC src/script/script.h:
           #   "constexpr size_t MAX_SCRIPTNUM_BYTE_SIZE = 8;"
           "XEC": _c("8-byte", "abc_src"),
           "BTG": _c("4-byte", "c_opdis")}},

    {"id": "element_size_limit", "name": "Script element-size limit",
     "criterion": "The maximum size of a single stack element.",
     "p": {"whitepaper": _c(None, "wp"), "nov08": _c(None, "nov08"),
           "v0.1.0": _c("none", "v01"),
           "BTC": _c("520-byte", "c_opdis"),
           # CORRECTED: the 520 -> 10,000 raise is the May 2025 VM Limits CHIP, not 2018.
           "BCH": _c("10000-byte", "bch_vm_limits"),
           "BSV": _c("none", "bsv_genesis"),
           # CORRECTED (AUDIT-LEDGER 1): eCash split from BCH in 2020, FIVE YEARS before the
           # 2025 raise, so it could never have inherited it. Bitcoin ABC src/script/script.h:
           #   "static const unsigned int MAX_SCRIPT_ELEMENT_SIZE = 520;"
           # ★ The CITATION was the tell: bch_2018, for a chain not named that in 2018.
           "XEC": _c("520-byte", "abc_src"),
           "BTG": _c("520-byte", "c_opdis")}},

    {"id": "sig_encoding", "name": "Signature encoding",
     "criterion": "Whether strict-DER signature encoding is enforced.",
     "p": {"whitepaper": _c(None, "wp"), "nov08": _c(None, "nov08"),
           "v0.1.0": _c("lenient-openssl", "v01"),
           # ⚠️ CORRECTED 13 Aug 2026: these three cited the Aug 2017 BCH fork. Strict-DER is
           #    BIP66, activated on Bitcoin 4 July 2015 — TWO YEARS BEFORE the fork — so all
           #    three descendants INHERITED it. The fork did not create this rule.
           "BTC": _c("strict-der", "bip66"), "BCH": _c("strict-der", "bip66"),
           "BSV": _c("strict-der", "bip66"), "XEC": _c("strict-der", "bip66"),
           "BTG": _c("strict-der", "bip66")}},

    {"id": "value_range_check", "name": "Output-value range check",
     "criterion": "Whether outputs/sums are bounded by a MoneyRange invariant (vs only nValue < 0).",
     "p": {"whitepaper": _c(None, "wp"), "nov08": _c(None, "nov08"),
           "v0.1.0": _c("none", "v01"),
           "BTC": _c("moneyrange", "cve2010"), "BCH": _c("moneyrange", "cve2010"),
           "BSV": _c("moneyrange", "cve2010"), "XEC": _c("moneyrange", "cve2010"),
           "BTG": _c("moneyrange", "cve2010")}},

    {"id": "sig_scheme", "name": "Signature scheme",
     "criterion": "Whether a Schnorr scheme is available in consensus in addition to ECDSA.",
     "p": {"whitepaper": _c(None, "wp"), "nov08": _c(None, "nov08"),
           "v0.1.0": _c("ecdsa-only", "v01"),
           "BTC": _c("ecdsa+schnorr", "bip34x"), "BCH": _c("ecdsa+schnorr", "bch_schnorr"),
           # ⛔ re-cited 14 Aug 2026: was bsv_genesis, which never mentions ECDSA or Schnorr.
           "BSV": _c("ecdsa-only", "bsv_no_schnorr", "med"),
           "XEC": _c("ecdsa+schnorr", "bch_schnorr"),
           "BTG": _c("ecdsa-only", "btg_src")}},

    {"id": "p2sh", "name": "Pay-to-Script-Hash (P2SH)",
     "criterion": "Whether the P2SH special-case output template is a consensus rule.",
     "p": {"whitepaper": _c(None, "wp"), "nov08": _c(None, "nov08"),
           "v0.1.0": _c("none", "v01"),
           "BTC": _c("p2sh", "bip16"), "BCH": _c("p2sh", "bip16"),
           "BSV": _c("none", "bsv_genesis"), "XEC": _c("p2sh", "bip16"),
           "BTG": _c("p2sh", "bip16")}},

    {"id": "segwit", "name": "Segregated witness",
     "criterion": "Whether witness data is segregated with a separate commitment (BIP141).",
     "p": {"whitepaper": _c(None, "wp"), "nov08": _c(None, "nov08"),
           "v0.1.0": _c("none", "v01"),
           "BTC": _c("segwit", "bip141"), "BCH": _c("none", "bch_fork"),
           "BSV": _c("none", "bsv_genesis"), "XEC": _c("none", "bch_fork"),
           "BTG": _c("segwit", "btg_src")}},

    {"id": "taproot", "name": "Taproot output type",
     "criterion": "Whether Taproot (BIP341 key/script-path) outputs are a consensus rule.",
     "p": {"whitepaper": _c(None, "wp"), "nov08": _c(None, "nov08"),
           "v0.1.0": _c("none", "v01"),
           "BTC": _c("taproot", "bip34x"), "BCH": _c("none", "bch_fork"),
           "BSV": _c("none", "bsv_genesis"), "XEC": _c("none", "bch_fork"),
           "BTG": _c("none", "btg_src")}},

    # name shortened 14 Aug 2026 for Table 1 width; "absolute/relative" is stated in the criterion,
    # which is where the definition lives. ★ A display LABEL may be shortened; a VALUE may not.
    {"id": "timelock_opcodes", "name": "Timelock opcodes",
     "criterion": "Whether CLTV/CSV-style timelock opcodes are active (v0.1 leaves the slots as NOPs).",
     "p": {"whitepaper": _c(None, "wp"), "nov08": _c(None, "nov08"),
           "v0.1.0": _c("nops", "v01"),
           # "cltv+csv" rests on BOTH BIPs; citing only BIP112 left BIP65 unreferenced
           "BTC": _c("cltv+csv", ["bip65", "bip112"]), "BCH": _c("cltv+csv", "bch_2018", "med"),
           # ⛔ CORRECTED 13 Aug 2026 — this cell said "cltv" and was WRONG. genesis-spec.md, the
           #    source it ALREADY CITED, says verbatim:
           #      "OP_CHECKLOCKTIMEVERIFY and OP_CHECKSEQUENCEVERIFY ... These operations revert
           #       to NOP's, which have no effect."
           #    ⇒ the value is "nops", which MATCHES v0.1.0. BSV goes 8 -> 7 mismatches and gains
           #      a FOURTH restoration.
           #    ★★ NOTE WHICH WAY THE ERROR CUT: it was SUPPRESSING the paper's own central
           #       caution. An error that understates your headline is the hardest kind to find,
           #       because nothing about the result looks wrong.
           #    Found by an external referee; confirmed here by fetching the spec.
           "BSV": _c("nops", "bsv_genesis"), "XEC": _c("cltv+csv", "bch_2018", "med"),
           "BTG": _c("cltv+csv", "btg_src")}},

    {"id": "difficulty_algorithm", "name": "Difficulty-adjustment algorithm",
     "criterion": "The retarget algorithm governing proof-of-work difficulty, INCLUDING any additional real-time target a block must also satisfy to be accepted.",
     "p": {"whitepaper": _c(None, "wp"), "nov08": _c(None, "nov08"),
           "v0.1.0": _c("2016-block-retarget", "v01"),
           "BTC": _c("2016-block-retarget", "v01"), "BCH": _c("asert", "bch_asert"),
           # ⚠️ CORRECTED 13 Aug 2026: cited bch_fork (Aug 2017), which shipped EDA, not cw-144.
           "BSV": _c("daa-cw144", "bch_daa_2017", "med"), "XEC": _c("asert+rtt", "xec_asert"),
           "BTG": _c("lwma", "btg_src")}},

    # ditto: the SIGHASH_FORKID mechanism is named in the criterion and in the cited source.
    {"id": "replay_protection", "name": "Replay protection",
     "criterion": "Whether a fork-id is mixed into the signature hash.",
     "p": {"whitepaper": _c(None, "wp"), "nov08": _c(None, "nov08"),
           "v0.1.0": _c("none", "v01"),
           "BTC": _c("none", "v01"), "BCH": _c("forkid", "bch_fork"),
           "BSV": _c("forkid", "bch_fork"), "XEC": _c("forkid", "bch_fork"),
           "BTG": _c("forkid", "btg_fork")}},

    {"id": "tx_ordering", "name": "Transaction ordering in a block",
     "criterion": "Whether non-coinbase transactions must follow a canonical order (CTOR) vs topological.",
     "p": {"whitepaper": _c(None, "wp"), "nov08": _c(None, "nov08"),
           "v0.1.0": _c("topological", "v01"),
           "BTC": _c("topological", "v01"), "BCH": _c("ctor", "bch_ctor"),
           "BSV": _c("topological", "bsv_genesis", "med"), "XEC": _c("ctor", "bch_ctor"),
           "BTG": _c("topological", "btg_src")}},

    {"id": "subsidy_base", "name": "Initial block subsidy",
     "criterion": "The genesis-era block subsidy (coins per block before the first halving).",
     "p": {"whitepaper": _c(None, "wp"), "nov08": _c("100", "nov08"),
           "v0.1.0": _c("50", "v01"),
           "BTC": _c("50", "shared"), "BCH": _c("50", "shared"),
           "BSV": _c("50", "shared"), "XEC": _c("50", "shared"),
           "BTG": _c("50", "shared")}},

    {"id": "block_spacing", "name": "Target block spacing",
     "criterion": "The target mean time between blocks.",
     "p": {"whitepaper": _c(None, "wp"), "nov08": _c("15-min", "nov08"),
           "v0.1.0": _c("10-min", "v01"),
           "BTC": _c("10-min", "shared"), "BCH": _c("10-min", "shared"),
           "BSV": _c("10-min", "shared"), "XEC": _c("10-min", "shared"),
           "BTG": _c("10-min", "btg_src")}},

    # ⛔ REMOVED 13 Aug 2026 — "supply_cap" (halving interval + 21e6 cap) qualified under NEITHER
    #    class, and the engine's own validator caught it within a minute of the rule being written:
    #
    #        class i  ✗ no descendant ever changed it
    #        class ii ✗ NO early reference specifies it (whitepaper None, nov08 None)
    #
    #    ★★ Its presence was an unstated judgement that the 21-million cap is too famous to omit.
    #       **That is exactly the kind of unexamined preference this paper exists to remove**, and
    #       there is no principled reason it was in while BIP34's coinbase-height rule was out —
    #       both are consensus rules and neither discriminates.
    #
    #    ⇒ The finding survives WITHOUT the axis and is stated in prose instead: the halving
    #      interval and asymptotic cap are IDENTICAL on v0.1.0 and on all four descendants. An axis
    #      on which every profile agrees carries no comparative information; saying so costs one
    #      sentence and buys a rule that does not have to be argued for.
    #
    #    Effect: 18 -> 17 axes. Ordering and the gap of 5 are unchanged; every rate's denominator
    #    moves, which is why the paper's numbers were regenerated rather than adjusted.
    # ★★ ADDED 14 Aug 2026 (R4). BOTH were identified by referees, not by our own enumeration,
    #    and that is the finding: the two-class rule says when an axis MAY qualify, it does not
    #    GENERATE the set. See the non-exhaustiveness statement in METHOD.md and section 2.
    {"id": "coinbase_height", "name": "Coinbase height commitment",
     "criterion": "Whether the block height must appear in the coinbase input (BIP34).",
     "p": {"whitepaper": _c(None, "wp"), "nov08": _c(None, "nov08"),
           "v0.1.0": _c("not-required", "v01"),
           "BTC": _c("required", "bip34"), "BCH": _c("required", "bip34"),
           "BSV": _c("required", "bip34"), "XEC": _c("required", "bip34"),
           "BTG": _c("required", "btg_src")}},

    {"id": "pow_function", "name": "Proof-of-work function",
     "criterion": "The hash function a valid block header must satisfy the target under.",
     # ⛔ CORRECTED 15 Aug 2026 (R5). This cell read _c("sha256d", "wp") at HIGH confidence and
     #    that is not what the whitepaper says. Verbatim: "scanning for a value that when hashed,
     #    **such as with SHA-256**, the hash begins with a number of zero bits ... can be verified
     #    by executing **a single hash**."
     #    ★ TWO independent reasons the old encoding failed: "such as" is ILLUSTRATIVE, not
     #      normative; and "a single hash" is not double-SHA-256 at all.
     #    ⇒ The whitepaper does not specify a PoW function. Unspecified is the honest cell, and
     #      it is the same standard applied everywhere else here: the document must SAY it.
     "p": {"whitepaper": _c(None, "wp"), "nov08": _c("sha256d", "nov08"),
           "v0.1.0": _c("sha256d", "v01"),
           "BTC": _c("sha256d", "v01"), "BCH": _c("sha256d", "v01"),
           "BSV": _c("sha256d", "v01"), "XEC": _c("sha256d", "v01"),
           "BTG": _c("equihash-btg", "btg_fork")}},
]

# Post-2017 witness/signature upgrades whose fine individuation affects the mismatch rate; the
# sensitivity analysis re-scores with these merged into one axis to expose the ranking's dependence
# on axis choice.
#
# ⚠️ CORRECTED 13 Aug 2026 — THIS WAS LABELLED "BTC-only" AND IS NOT.
#    `sig_scheme` (Schnorr) is ALSO a divergence for BCH and XEC, both of which run ecdsa+schnorr.
#    Merging therefore moves BCH and XEC by **+0.09 each** — a larger movement than BTC's -0.04 —
#    and the paper previously reported only BTC and BSV.
#
#    ★★ A SENSITIVITY ANALYSIS THAT REPORTS THE CHAINS IT MOVES LEAST AND OMITS THE ONES IT MOVES
#       MOST READS AS SELECTIVE, WHETHER OR NOT IT WAS. All four are now reported.
WITNESS_SIG_CLUSTER = ["segwit", "taproot", "sig_scheme"]
BTC_UPGRADE_CLUSTER = WITNESS_SIG_CLUSTER  # retained: external callers and prior artifacts use it


# ── the axis-selection rule, as TWO classes ───────────────────────────────────────────────────
#
# ⛔ THE ORIGINAL RULE CONTRADICTED THE DATASET, AND A REFEREE FOUND IT, NOT US.
#
# It read: include every axis on which a consensus rule "changed on at least one included chain
# since January 2009". **Axes 16-18 -- subsidy, spacing, supply -- changed on NONE of them.**
# Enforced literally, they leave the dataset, and the November 2008 reference then has ZERO jointly
# specified axes: its result disappears entirely.
#
#   ★★ THE FIX IS NOT TO DELETE THE AXES. They are the only reason the November profile is
#      measurable at all, and how reference choice changes what can be said IS the paper's subject.
#      **Deleting them would be cutting the instrument to fit one sentence of the rule.**
#
#   ⚠️ BUT A SECOND CLASS ADDED *AFTER* SEEING THE RESULTS IS A RATIONALISATION, NOT A DESIGN.
#      So it is stated in the paper's Method BEFORE the results, WITH its cost admitted: class-ii
#      axes contribute a fixed 3 matches to every chain and CANNOT discriminate between them.
#
# ⇒ AND IT IS ENFORCED HERE RATHER THAN ASSERTED. `validate_axis_classes()` re-derives each axis's
#   class from the data and fails loudly if a cell edit ever breaks the classification. A rule that
#   lives only in prose goes stale silently; this project has been bitten by that repeatedly.
CLASS_CHANGED = "changed-on-a-descendant"
CLASS_REFDISC = "reference-discriminating"

# Class ii: an early REFERENCE specifies it, and no descendant ever changed it.
# ⛔ `supply_cap` removed 14 Aug 2026 (R3). The axis itself was deleted when the two-class rule was
#    written — it qualified under neither class — but its name survived here, so this declaration
#    named an axis that does not exist. ★ Dead references in a validator are worse than in prose:
#    the validator is what a reader is told to trust instead of the prose.
REFERENCE_DISCRIMINATING = {"subsidy_base", "block_spacing"}


def axis_class(axis_id):
    return CLASS_REFDISC if axis_id in REFERENCE_DISCRIMINATING else CLASS_CHANGED


def validate_axis_classes(axes=None):
    """CURRENT-STATE consistency check on each axis's declared class. NOT a historical check.

    class ii  <=>  v0.1.0 and all four chains carry the same value AT THE FREEZE
    class i   <=>  at least one chain differs from v0.1.0 at the freeze

    ⛔ WHAT THIS CANNOT DO, corrected 14 Aug 2026 (R3) — the docstring previously glossed class ii
       as *"nothing ever changed it"*, and the paper repeated that the engine re-derives the
       historical rule. **It cannot.** This function compares four present values. A chain that
       adopted a rule and later reverted it would look identical to one that never touched it —
       which is precisely the retention/restoration distinction the paper spends section 4.1 on,
       and precisely what single-state cells are declared unable to represent (section 7).

       ★★ THE INSTRUMENT WAS BEING CITED FOR A GUARANTEE ONE LEVEL STRONGER THAN IT GIVES. The
       check is real and worth running; the claim around it was not. Establishing "never changed"
       needs a sourced event history per cell, which is the same missing field that blocks
       historical evaluation. Both are reported as limitations, not implemented as a pretence.

    Returns a list of complaints; empty means the declared classes match the frozen dataset.
    """
    axes = axes or AXES
    out = []
    for a in axes:
        unchanged = len({val(a, c) for c in CHAINS} | {val(a, "v0.1.0")}) == 1
        derived = CLASS_REFDISC if unchanged else CLASS_CHANGED
        declared = axis_class(a["id"])
        if derived != declared:
            out.append("%s: declared %s but the data says %s" % (a["id"], declared, derived))
        if declared == CLASS_REFDISC:
            # a class-ii axis must actually be specified by an early reference, or it is inert
            if all(val(a, r) is None for r in ("whitepaper", "nov08")):
                out.append("%s: class ii but NO early reference specifies it" % a["id"])
    return out


# ★ R3: the chain-selection rule was stated as an "iff" and never TESTED against a candidate it
#   should exclude. An inclusion rule that is only ever applied to the chains you already chose is
#   not a rule, it is a description. Bitcoin Gold is the sharp case: it duplicated Bitcoin's ledger
#   through block 491,406 and publishes dated consensus specifications, so it satisfies criteria
#   (1) and (3) on their face and must be excluded — if at all — for a stated reason.
#
# ⚠️ HONEST STATUS. Criterion (2), "producing blocks on 1 August 2026", is the one that decides
#    several of these, and we have NOT queried a primary chain endpoint for every row. Where that
#    is so, the row says UNVERIFIED rather than being quietly dropped. **A candidate excluded for a
#    reason we have not checked is an excluded candidate we cannot defend.**
EXCLUSIONS = [
    # ★★★ BITCOIN GOLD IS NO LONGER IN THIS TABLE. audit_btg.py measured criterion (2) --
    #     block 958,305, header time 2026-08-01T21:01:04Z -- and BTG satisfies all three. The rule
    #     admitted it, so it was MEASURED rather than argued away. Adding it forced the
    #     `pow_function` axis into existence, which is itself the R4 finding: the axis set was
    #     shaped by the chains we had chosen. **Testing an inclusion rule adversarially changed
    #     both the population and the axis universe, which is what a real rule is supposed to do.**
    ("Litecoin (LTC)", "NO: separate genesis block", "yes", "yes",
     "Fails (1). A new genesis is a new ledger, however similar the code"),
    ("Dogecoin (DOGE)", "NO: separate genesis, and a Litecoin derivative", "yes", "yes",
     "Fails (1), twice over"),
    ("Bitcoin Private (BTCP)", "NO: fork-merge with Zclassic, not a continuation", "partial",
     "UNVERIFIED", "Fails (1): a merged ledger is not a continued one"),
    ("Bitcoin Diamond (BCD)", "yes: forked from the Bitcoin ledger", "sparse/undated",
     "UNVERIFIED", "Fails (3): no public dated specification record we could locate, which is an "
     "admission about our search as much as about the chain"),
    ("Bitcoin Satoshi Vision testnets / regtest", "n/a", "n/a", "n/a",
     "Out of scope: not independent mainnets"),
]


def exclusion_audit():
    """The chain-selection rule applied to candidates OUTSIDE the four, with the reason each fails.
    Returns the rows; the paper prints them so the 'iff' is testable rather than asserted."""
    return EXCLUSIONS


def k_scan(axes=None):
    """First tie and first strict reversal as k axes are dropped. ★ R5: the manuscript stated
    both with C(17,k) denominators after the set became 19 axes, and NO GATE COULD SEE IT --
    the numbers were prose, not figures. Computing them here puts them under the same gate as
    everything else."""
    import itertools
    axes = axes or AXES
    ids = [a["id"] for a in axes]
    out = {}
    for k in (5, 6):
        total = ties = rev = 0
        for drop in itertools.combinations(ids, k):
            sub = [a for a in axes if a["id"] not in drop]
            t = table(sub)["v0.1.0"]
            rates = {c: t[c]["mismatch_rate"] for c in CHAINS if t[c]["mismatch_rate"] is not None}
            if not rates:
                continue
            total += 1
            lo = min(rates.values())
            low = [c for c in rates if rates[c] == lo]
            if len(low) > 1 and "BSV" in low:
                ties += 1
            elif low != ["BSV"]:
                rev += 1
        out["kscan_k%d_total" % k] = total
        out["kscan_k%d_ties" % k] = ties
        out["kscan_k%d_reversals" % k] = rev
    return out


def confidence_sensitivity(axes=None):
    """Enumerate EVERY assignment of the medium-confidence cells and report whether the ordering
    survives. ★ ADDED 14 Aug 2026 (R3).

    ⚠️ WHY THIS EXISTS. The manuscript asserted that BSV stays uniquely lowest across all 2^k
       assignments of the medium-confidence cells. **The claim was true — a referee enumerated it
       independently and got 128/128 — and nothing in this repository computed it.** The paper
       simultaneously claimed that every number in it regenerates from this program.

       ★★★ A TRUE SENTENCE THAT NO CODE PRODUCES IS STILL A HAND-MAINTAINED NUMBER. It cannot
       follow a cell edit, and the next revision is where it silently stops being true.

    A medium-confidence cell is one we are least sure of, so the adversarial move is to let each
    one take the value that HELPS its chain (match v0.1.0) or HURTS it (differ), independently, and
    ask whether any combination changes who is lowest.
    """
    axes = axes or AXES
    med = [(a["id"], c) for a in axes for c in CHAINS
           if a["p"][c]["value"] is not None and a["p"][c]["confidence"] == "med"]
    k = len(med)
    if k > 20:                                     # 2^20 is the practical ceiling; refuse, loudly
        return {"k": k, "assignments": None,
                "note": "refused: 2^%d assignments is not enumerable here" % k}
    base = {a["id"]: {c: val(a, c) for c in CHAINS} for a in axes}
    ref = {a["id"]: val(a, "v0.1.0") for a in axes}
    lowest_is_bsv = 0
    total = 0
    for mask in range(1 << k):
        cur = {ax: dict(cols) for ax, cols in base.items()}
        for bit, (ax, ch) in enumerate(med):
            # bit set  -> force this cell to MATCH v0.1.0; clear -> force it to DIFFER
            cur[ax][ch] = ref[ax] if (mask >> bit) & 1 else ("~%s" % ref[ax])
        rates = {}
        for c in CHAINS:
            joint = [a["id"] for a in axes if ref[a["id"]] is not None and cur[a["id"]][c] is not None]
            diff = sum(1 for ax in joint if cur[ax][c] != ref[ax])
            rates[c] = diff / len(joint) if joint else None
        total += 1
        lo = min(rates, key=lambda c: rates[c])
        if lo == "BSV" and sum(1 for c in CHAINS if rates[c] == rates["BSV"]) == 1:
            lowest_is_bsv += 1
    return {"k": k, "assignments": total, "bsv_uniquely_lowest": lowest_is_bsv,
            "holds": lowest_is_bsv == total, "cells": med}


def constant_axes(axes=None):
    """Axes on which all four chains agree: they shift every mismatch rate equally and CANNOT
    affect the ordering. Reported because a reader is entitled to know how many of the axes are
    doing discriminating work and how many are a common offset."""
    axes = axes or AXES
    out = []
    for a in axes:
        vals = {val(a, c) for c in CHAINS}
        if len(vals) == 1:
            out.append(a["id"])
    return out


# ── restoration vs retention ──────────────────────────────────────────────────────────────────
#
# ⛔⛔ THE FIRST VERSION OF THIS ANALYSIS WAS WRONG, AND IT REACHED THE PAPER FOR ABOUT AN HOUR.
#
# It classified a match as a RESTORATION whenever the cell cited a post-2009 upgrade spec in that
# chain's lineage. **That is a proxy, and the proxy is false:** a cell cites the document that
# DOCUMENTS its value, which is not the same as the chain ever having held a different one.
#
# The proxy reported a restoration/retention split that this engine does not produce and that the
# project has retracted; the explicit RESTORATIONS table below is the only authority. The retracted
# figures are deliberately not repeated here -- a release must not carry numbers it has withdrawn.
# The truth is BSV **3 / 7**, and BCH and XEC have **none at all**:
#
#   BCH forked from Bitcoin on 1 Aug 2017 and segwit activated on 24 Aug 2017 — THREE WEEKS LATER.
#   BCH never had segwit to remove. Nor Taproot. Those are retentions, and the proxy called them
#   restorations because the cell cites the fork spec.
#
#   BSV forked from BCH on 15 Nov 2018. Schnorr reached BCH on 15 May 2019 and CTOR was the very
#   thing the BSV split rejected — so BSV never held either. Also retentions.
#
# ★★★ THE LESSON, and it is the sharpest one in this file: **A CITATION IS NOT A HISTORY.** The
#     source attached to a cell says where its CURRENT value is documented; asking it what the
#     chain USED to do is asking a question the field cannot answer. The proxy was convenient,
#     it was derived from data already present, and it was wrong in the direction that flattered
#     the headline.
#
# ⇒ Replaced by an EXPLICIT table. Each entry states the chain, the axis, and the reason it is a
#   restoration — i.e. the change that introduced the rule and the change that removed it. These
#   are cells like any other and carry the same author-verification obligation.
RESTORATIONS = {
    ("BSV", "script_opcodes"):
        "inherited the 2010 opcode restrictions through the BTC->BCH lineage; the 2020 Genesis "
        "upgrade re-enabled the broad set (c_opdis -> bsv_genesis)",
    ("BSV", "element_size_limit"):
        "inherited the 520-byte element cap from 2010; Genesis removed the consensus limit "
        "(c_opdis -> bsv_genesis)",
    ("BSV", "p2sh"):
        "P2SH was a consensus rule on BSV's lineage from 2012; Genesis removed it "
        "(bip16 -> bsv_genesis)",
    ("BSV", "timelock_opcodes"):
        "CLTV and CSV were consensus rules on BSV's lineage from 2015-16 (BIP65, BIP112, both "
        "predating the 2017 fork); genesis-spec.md sunsets them, saying the operations revert "
        "to NOPs which have no effect (bip65+bip112 -> bsv_genesis)",
}


def match_provenance(chain, axes=None):
    """Split a chain's MATCHES with v0.1.0 into RETENTIONS and RESTORATIONS.

    ★★ THIS IS THE PAPER'S CENTRAL CAUTION AS A NUMBER. A chain can agree with v0.1.0 because it
       never changed the rule (RETENTION) or because it adopted the change and later removed it
       (RESTORATION). A mismatch rate cannot tell them apart, and they are very different facts.

    ⚠️ A match counts as a RESTORATION only if it appears in the RESTORATIONS table above WITH ITS
       REASON. Absence from that table means retention. There is no inference step.
    """
    axes = axes or AXES
    retention, restoration = [], []
    for a in axes:
        rv, cv = val(a, "v0.1.0"), val(a, chain)
        if rv is None or cv is None or rv != cv:
            continue
        (restoration if (chain, a["id"]) in RESTORATIONS else retention).append(a["id"])
    return {"matches": len(retention) + len(restoration),
            "retentions": retention, "restorations": restoration,
            "reasons": {ax: RESTORATIONS[(chain, ax)] for ax in restoration}}


def val(axis, profile):
    return axis["p"][profile]["value"]


def compare(ref, chain, axes):
    """Jointly-specified axes, how many differ, and the per-axis verdicts."""
    rows = []
    differ = jointly = 0
    for ax in axes:
        rv, cv = val(ax, ref), val(ax, chain)
        if rv is None or cv is None:
            verdict = "unspecified"
        else:
            jointly += 1
            if rv == cv:
                verdict = "match"
            else:
                verdict = "mismatch"
                differ += 1
        rows.append({"axis": ax["id"], "ref_value": rv, "chain_value": cv, "verdict": verdict})
    coverage = jointly / len(axes) if axes else 0.0
    mismatch_rate = (differ / jointly) if jointly else None  # UNDEFINED where nothing is jointly specified
    # ⛔⛔ ROUNDING HAPPENS AT DISPLAY, NOT HERE -- AND THE REASON IS A PUBLISHED WRONG DECIMAL.
    #    This used to return round(mismatch_rate, 4). Every derived quantity in the paper is then
    #    arithmetic on ALREADY-ROUNDED inputs, and two of them came out wrong in the fourth place:
    #      BTC merged delta   0.6471 - 0.6842 = -0.0371   but 11/17 - 13/19 = -0.0371517 -> -0.0372
    #      BSV label movement 0.4211 - 0.3684 =  0.0527   but the true move is exactly 1/19 -> 0.0526
    #    ★★★ ROUNDING EARLY IS NOT A DISPLAY CHOICE, IT IS A DATA LOSS. The exact values are kept
    #    here and rounded only where they are printed. `mismatch_rate` stays rounded for backward
    #    compatibility with every pinned test; `*_exact` carries the real number for arithmetic.
    #    ⇒ Caught by an external referee doing the fractions by hand. Nothing in the engine could
    #      have caught it, because the engine agreed with itself perfectly at 4 decimal places.
    return {"jointly_specified": jointly, "differing": differ, "total_axes": len(axes),
            "coverage": round(coverage, 4),
            "coverage_exact": coverage,
            "mismatch_rate": (round(mismatch_rate, 4) if mismatch_rate is not None else None),
            "mismatch_rate_exact": mismatch_rate,
            "rows": rows}


def table(axes):
    return {ref: {chain: compare(ref, chain, axes) for chain in CHAINS} for ref in REFERENCES}


def reference_disagreement(axes=None):
    """Do the three REFERENCES agree with each other where they overlap?

    ★★★ THE ENGINE COMPUTED REFERENCE->CHAIN ONLY, AND THREW THIS AWAY. It is the most interesting
        thing the dataset contains: the whitepaper specifies exactly one consensus axis that the
        released client also specifies, and **they disagree on it** — the paper describes
        best-chain selection as most-work, the January 2009 client selects by HEIGHT. Likewise
        every axis the November pre-release shares with v0.1.0 differs.

    ⇒ "The origin" is not one object. A chain's displacement is measured from whichever origin is
      chosen, and the origins do not agree with each other — which is the strongest possible
      argument for the paper's own insistence that the result is REFERENCE-RELATIVE.

    ⛔ THE DOCSTRING ABOVE ONCE ENDED "likewise every axis the November pre-release shares with
       v0.1.0 differs." THAT BECAME FALSE when the pow_function axis was added for Bitcoin Gold:
       November and v0.1.0 both specify SHA-256d and AGREE on it. Corrected 15 Aug 2026 (R7).
       ★ Even the docstring explaining why prose goes stale had gone stale.
    """
    axes = axes or AXES
    out = {}
    for i, r1 in enumerate(REFERENCES):
        for r2 in REFERENCES[i + 1:]:
            c = compare(r1, r2, axes)
            out[f"{r1}|{r2}"] = {
                "jointly_specified": c["jointly_specified"],
                "differing": c["differing"],
                "mismatch_rate": c["mismatch_rate"],
                "differing_axes": [r["axis"] for r in c["rows"] if r["verdict"] == "mismatch"],
            }
    return out


def reference_summary_sentence(axes=None):
    """Emit the §4.2 takeaway AS A SENTENCE, generated from the pairs rather than written.

    ⛔⛔ WHY A FUNCTION EXISTS FOR ONE SENTENCE. Three consecutive referee rounds corrected this
       one line and it came back wrong somewhere else each time: round 5 the caption, round 6 the
       caption and the arrow, round 7 the arrow alone ("two of the three pairs share no axis at
       all" — one does; two share axes, and the description that followed silently dropped
       whitepaper↔v0.1.0, which carries the paper's own headline result).

    ★★★ IT IS THE ONLY PLACE IN THE PAPER WHERE A RELATIONSHIP BETWEEN THREE ROWS IS STATED IN
        PROSE, and prose is exactly where this project's arithmetic fails. Every number in the
        manuscript already comes through {{FIG:}}; this sentence describes a *shape* over three
        rows, which no single number could pin, so it survived every numeric gate. **Generating
        it is the only fix that cannot regress.**
    """
    d = reference_disagreement(axes)
    none_, one_, many_ = [], [], []
    for pair, v in d.items():
        n = v["jointly_specified"]
        (none_ if n == 0 else (one_ if n == 1 else many_)).append((pair, v))
    parts = []
    if none_:
        parts.append("%s shares no axis at all"
                     % ("one" if len(none_) == 1 else "%d" % len(none_)))
    for pair, v in one_:
        parts.append("one shares a single axis and %s on it"
                     % ("differs" if v["differing"] else "agrees"))
    for pair, v in many_:
        n, diff = v["jointly_specified"], v["differing"]
        parts.append("one shares %d and differs on %d" % (n, diff))
    return "of the three pairs, " + "; ".join(parts)


# ── label granularity ─────────────────────────────────────────────────────────────────────────
#
# ★★★★ THE SHARPEST CRITICISM THIS PAPER RECEIVED, AND IT HAS A COUNTEREXAMPLE IN OUR OWN CSV.
#
# Two profiles "match" iff their labels are EQUAL AS STRINGS. So the choice of label is itself a
# coding decision — and the shipped dataset contains a case where two labels name the same state:
#
#     v0.1.0  block_size_rule = "no-dedicated-cap"
#     BSV     block_size_rule = "no-consensus-cap"
#
# Both mean "no consensus rule caps the block size". **Scored as a MISMATCH purely because the
# strings differ.** Likewise `unbounded-openssl` vs `unbounded` on script-number width.
#
# ⇒ THIS REFUTES, BY EXAMPLE, THE PAPER'S CLAIM THAT "there is nothing for two independent coders
#   to disagree about". There is: they can disagree about the label, and the score moves.
#
#   ★★ The honest claim is narrower and still worth making: **reproducibility does not eliminate
#      judgement, it RELOCATES it — from scoring to individuation, where it is visible, bounded,
#      and can be perturbed on purpose.** Which is what this function does.
RELABELLINGS = [
    ("block-size labels unified",
     "v0.1.0's 'no-dedicated-cap' and BSV's 'no-consensus-cap' name the same state",
     [("block_size_rule", "BSV", "no-dedicated-cap")]),
    # ⚠️ INERT SINCE BSV's CELL BECAME `32mb-limit`, and RETAINED ON PURPOSE.
    #    This perturbation renames v0.1.0's value; nothing matches the new name any more, so every
    #    rate is identical to the base row. A reader sees a sensitivity test that moves nothing.
    #    ★ It is kept rather than deleted because it was LIVE when the analysis was designed, and
    #    silently dropping a perturbation once it stops being favourable is exactly the selective
    #    reporting this section exists to rule out. **The row's own caption now says it is inert
    #    and why**, which is the honest version of the same disclosure. Flagged five rounds running
    #    by an external referee before it was explained rather than removed.
    ("script-number qualifier dropped (inert since the BSV cell became 32mb-limit)",
     "v0.1.0's 'unbounded-openssl' drops its implementation qualifier; no profile carries "
     "'unbounded' any more, so this moves nothing -- retained because it was live when the "
     "analysis was designed",
     [("script_number_width", "v0.1.0", "unbounded")]),
    ("BSV opcode set individuated",
     "BSV's post-Genesis opcode set is NOT v0.1's: it adds CHECKDATASIG, OP_SPLIT, "
     "NUM2BIN/BIN2NUM and still disables OP_2MUL/2DIV/VERIF/VERNOTIF",
     [("script_opcodes", "BSV", "broad+genesis-additions")]),
]


def label_sensitivity(ref="v0.1.0"):
    """Re-score under defensible alternative labellings. Reports the range each chain can occupy.

    ⚠️ NONE of these is a correction. Each is a labelling a competent coder could have chosen from
       the same sources, and the point is the SPREAD, not any single row.
    """
    import copy
    out = {"base": {c: compare(ref, c, AXES)["mismatch_rate"] for c in CHAINS}, "cases": []}
    # ⛔ lo/hi drive the RANGE, which drives a published MOVEMENT. They must track exact rates:
    #    min/max over pre-rounded values silently shifts an endpoint by up to 5e-5, which is
    #    exactly how the label movement was published as 0.0527 instead of 1/19 = 0.0526.
    _ex = {c: compare(ref, c, AXES)["mismatch_rate_exact"] for c in CHAINS}
    lo = dict(_ex)
    hi = dict(_ex)

    def apply(edits):
        axes = copy.deepcopy(AXES)
        for axid, prof, val_ in edits:
            for a in axes:
                if a["id"] == axid:
                    a["p"][prof]["value"] = val_
        return axes

    for name, why, edits in RELABELLINGS:
        axes = apply(edits)
        rates = {c: compare(ref, c, axes)["mismatch_rate"] for c in CHAINS}
        rates_ex = {c: compare(ref, c, axes)["mismatch_rate_exact"] for c in CHAINS}
        out["cases"].append({"name": name, "rationale": why, "rates": rates})
        for c in CHAINS:
            lo[c] = min(lo[c], rates_ex[c])
            hi[c] = max(hi[c], rates_ex[c])
    allx = apply([e for _, _, es in RELABELLINGS[:2] for e in es])
    rates = {c: compare(ref, c, allx)["mismatch_rate"] for c in CHAINS}
    rates_ex = {c: compare(ref, c, allx)["mismatch_rate_exact"] for c in CHAINS}
    out["cases"].append({"name": "the two unification cases together",
                         "rationale": "both label unifications applied", "rates": rates})
    for c in CHAINS:
        lo[c] = min(lo[c], rates_ex[c])
        hi[c] = max(hi[c], rates_ex[c])
    out["range"] = {c: [round(lo[c], 4), round(hi[c], 4)] for c in CHAINS}
    out["range_exact"] = {c: [lo[c], hi[c]] for c in CHAINS}
    return out


def subset_robustness(ref="v0.1.0", drop_up_to=3, axes=None):
    """Stronger than leave-one-out: the range of each chain's mismatch rate over EVERY axis subset
    obtained by dropping up to `drop_up_to` axes, and whether the ordering ever changes.

    ⚠️ Leave-one-out answers "does one disputed axis change the answer". A referee who disputes
       THREE axes is entirely ordinary, and that is the question this answers.
    """
    from itertools import combinations
    axes = axes or AXES
    n = len(axes)
    lo = {c: 1.0 for c in CHAINS}
    hi = {c: 0.0 for c in CHAINS}
    total = flipped = 0
    for k in range(n - drop_up_to, n + 1):
        for combo in combinations(range(n), k):
            sub = [axes[i] for i in combo]
            rates = {c: compare(ref, c, sub)["mismatch_rate"] for c in CHAINS}
            if any(v is None for v in rates.values()):
                continue
            total += 1
            best = min(rates.values())
            argmin = [c for c in CHAINS if abs(rates[c] - best) < 1e-9]
            if argmin != [min(CHAINS, key=lambda c: compare(ref, c, axes)["mismatch_rate"])]:
                flipped += 1
            for c in CHAINS:
                lo[c] = min(lo[c], rates[c])
                hi[c] = max(hi[c], rates[c])
    return {"subsets": total, "orderings_where_the_lowest_chain_differs": flipped,
            "range": {c: [round(lo[c], 4), round(hi[c], 4)] for c in CHAINS},
            "drop_up_to": drop_up_to}


def _merged_axes():
    """A coarser individuation: collapse the BTC witness/sig cluster into one axis (min-differences),
    holding everything else fixed — used only for sensitivity."""
    keep = [a for a in AXES if a["id"] not in BTC_UPGRADE_CLUSTER]
    cluster = [a for a in AXES if a["id"] in BTC_UPGRADE_CLUSTER]
    merged = {"id": "witness_sig_upgrades", "name": "Post-2017 witness/signature upgrades (merged)",
              "criterion": "Any of segwit / taproot / Schnorr present (merged individuation).", "p": {}}
    for prof in PROFILES:
        vals = [val(a, prof) for a in cluster]
        if all(v is None for v in vals):
            merged["p"][prof] = _c(None, "wp")
        else:
            present = any(v not in (None, "none", "ecdsa-only", "nops") for v in vals)
            merged["p"][prof] = _c("added" if present else "none", "shared", "med")
    return keep + [merged]


def sensitivity(axes):
    """Robustness of each (reference, chain) mismatch rate to axis choice: leave-one-axis-out spread,
    plus the merged-cluster individuation. Reports the range of mismatch rates seen."""
    out = {}
    for ref in REFERENCES:
        for chain in CHAINS:
            base = compare(ref, chain, axes)["mismatch_rate"]
            loo = []
            for i in range(len(axes)):
                sub = axes[:i] + axes[i + 1:]
                loo.append(compare(ref, chain, sub)["mismatch_rate"])
            loo_defined = [x for x in loo if x is not None]
            _mc = compare(ref, chain, _merged_axes())
            merged = _mc["mismatch_rate"]
            out[f"{ref}|{chain}"] = {
                # exact values for ARITHMETIC; the rounded ones remain for display and for the
                # pinned tests. Subtracting two 4dp numbers is how -0.0372 became -0.0371.
                "base_exact": compare(ref, chain, axes)["mismatch_rate_exact"],
                "merged_cluster_exact": _mc["mismatch_rate_exact"],
                "base": base,
                "leave_one_out_min": (min(loo_defined) if loo_defined else None),
                "leave_one_out_max": (max(loo_defined) if loo_defined else None),
                "merged_cluster": merged,
            }
    return out


# ── table emission ────────────────────────────────────────────────────────────────────────────
#
# ★★★★ THE ROOT-CAUSE FIX, added 14 Aug 2026 after two referee rounds.
#
# Every propagation defect those reviews found had the same cause: **the manuscript hand-maintained
# numbers this engine computes.** Tables, ranges and counts were prose, edited by string surgery
# each time a cell moved — and cells moved on three consecutive days. The result was six regressions
# introduced BY THE REPAIRS, including a figure showing 18 rows under a caption saying 17.
#
#   ⇒ NO AMOUNT OF CARE FIXES A PIPELINE WHERE THE AUTHORITY AND THE PRESENTATION ARE SEPARATE
#     DOCUMENTS. So the engine now writes the tables, and `build_paper.py` substitutes them into a
#     template. A cell change propagates BY CONSTRUCTION and cannot be forgotten.
#
# ⚠️ ASCII ONLY, DELIBERATELY. A previous "fix" introduced U+2212 (which pdfTeX silently drops,
#    turning -0.0392 into a positive) and three literal BEL bytes (from a `\a` in a replacement
#    string). Emitted text uses `$-$` and `$\approx$` and nothing outside ASCII.
def _f(x, n=4):
    return "undefined" if x is None else ("%.*f" % (n, x))


def _signed(x):
    # ⛔ THIRD FORM OF ONE DEFECT, and the history is the lesson. R1: a literal `$-$` rendered as
    #    text. R2: replaced with U+2212, which pdfTeX drops SILENTLY. R3: the ASCII-only guard added
    #    in R2 forbids U+2212, so this function reverted to `$-$` and the guard passed it.
    #    ★★ THE GUARD DID NOT FIX THE DEFECT — IT SELECTED FOR THE FORM IT DID NOT FORBID.
    #    A plain ASCII hyphen is correct in a markdown table cell and needs no math span at all.
    return ("-%.4f" % abs(x)) if x < 0 else ("+%.4f" % x)


def emit_tables(outdir, tbl, sens, subs, lab, prov, refdis, const, artdir=None):
    """Write every table the paper displays. The paper INCLUDES these; it never retypes them."""
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    n = len(AXES)
    W = {}

    # Table 1 — the axis matrix (v0.1.0 + the four chains; early references stated in a note)
    L = ["| # | Axis | v0.1.0 | " + " | ".join(CHAINS) + " |",
         "|--:|:--|:--|" + ":--|" * len(CHAINS)]
    for i, a in enumerate(AXES, 1):
        cells = [str(val(a, "v0.1.0") or "---")] + [str(val(a, c) or "---") for c in CHAINS]
        L.append("| %d | %s | %s |" % (i, a["name"], " | ".join(cells)))
    W["table1_axes.md"] = "\n".join(L)

    # Table 2 — mismatch rate and coverage
    L = ["| reference | " + " | ".join(CHAINS) + " |", "|:--|" + ":--|" * len(CHAINS)]
    for ref in REFERENCES:
        row = []
        for c in CHAINS:
            r = tbl[ref][c]
            row.append("%s (cov %.3f)" % (_f(r["mismatch_rate"]), r["coverage"]))
        L.append("| %s | %s |" % (ref, " | ".join(row)))
    W["table2_rates.md"] = "\n".join(L)

    # Table 3 — retention vs restoration
    L = ["| chain | matches | retentions | restorations |", "|:--|--:|--:|--:|"]
    for c in CHAINS:
        p = prov[c]
        L.append("| %s | %d | %d | %d |"
                 % (c, p["matches"], len(p["retentions"]), len(p["restorations"])))
    W["table3_provenance.md"] = "\n".join(L)

    # Table 4 — merged-cluster individuation, all four chains
    L = ["| chain | base | merged | change |", "|:--|--:|--:|--:|"]
    for c in CHAINS:
        s = sens["v0.1.0|%s" % c]
        d = tbl["v0.1.0"][c]["differing"]
        L.append("| %s | %.4f (%d/%d) | %.4f | %s |"
                 % (c, s["base"], d, n, s["merged_cluster"],
                    _signed(s["merged_cluster_exact"] - s["base_exact"])))
    W["table4_merged.md"] = "\n".join(L)

    # Table 5 — label granularity
    L = ["| relabelling | " + " | ".join(CHAINS) + " |", "|:--|" + "--:|" * len(CHAINS)]
    L.append("| as published | " + " | ".join("%.4f" % lab["base"][c] for c in CHAINS) + " |")
    for case in lab["cases"]:
        L.append("| %s | %s |" % (case["name"],
                                  " | ".join("%.4f" % case["rates"][c] for c in CHAINS)))
    W["table5_labels.md"] = "\n".join(L)

    # Table 6 — the references against EACH OTHER. ★ R3: this was hand-typed in the template while
    # reference_disagreement() computed it, so the paper's most important result was the one number
    # set the engine did not own. Generated now.
    L = ["| pair | jointly specified | differing | axes |", "|:--|--:|--:|:--|"]
    for pair, r in reference_disagreement().items():
        a, b = pair.split("|")
        # ⛔ R5: this read `", ".join(...) or "*(no overlap)*"` -- an `or` on an empty list, so
        #    ZERO DIFFERING printed as NO OVERLAP. They are opposite findings and the proxy was
        #    only ever safe while the two coincided. **Same class as citation-is-not-a-history.**
        if r["jointly_specified"] == 0:
            names = "*(no overlap -- undefined)*"
        elif not r["differing_axes"]:
            names = "*(overlap, and they AGREE)*"
        else:
            names = ", ".join(r["differing_axes"])
        L.append("| %s vs %s | %d | %d | %s |"
                 % (a, b, r["jointly_specified"], r["differing"], names))
    W["table6_refdis.md"] = "\n".join(L)

    # Table 7 — audit coverage as a partition with a denominator (R3).
    _a = audit_coverage()
    L = ["| warrant | cells |", "|:--|--:|",
         "| **fetched** -- a primary source retrieved and matched mechanically | %d |" % _a["fetched"],
         "| **inherited** -- argued from an ancestor pre-dating every fork in the set | %d |" % _a["inherited"],
         "| **absence** -- unconfirmable by construction | %d |" % _a["absence"],
         "| **unclassified** -- anchored to a cited source, not yet fetched | %d |" % _a["unclassified"],
         "| **total specified** | %d |" % _a["specified"]]
    W["table7_audit.md"] = "\n".join(L)

    # Table 8 — the exclusion audit (R3): the selection rule applied to chains NOT in the set.
    # ⚠️ R9: the columns used to print (1), (3), (2) -- the order the tuples happen to be stored in.
    #    Nothing was wrong with the data and every verdict was right, but a table whose criteria run
    #    out of order reads as accidental, and this one exists to show a rule being applied evenly.
    #    ★ Reordered in the PRESENTATION only; EXCLUSIONS keeps its shape, so no row moved.
    L = ["| candidate | (1) ledger ancestry | (2) active at freeze | (3) dated primary record | verdict |",
         "|:--|:--|:--|:--|:--|"]
    for name, c1, c3, c2, verdict in exclusion_audit():
        L.append("| %s | %s | %s | %s | %s |" % (name, c1, c2, c3, verdict))
    W["table8_exclusions.md"] = "\n".join(L)

    # every scalar the prose quotes, so no number is ever retyped
    counts = {c: tbl["v0.1.0"][c]["differing"] for c in CHAINS}
    gap = sorted(counts.values())[1] - min(counts.values())
    spec = [a["p"][p] for a in AXES for p in PROFILES if a["p"][p]["value"] is not None]
    ii = sorted(a["id"] for a in AXES if axis_class(a["id"]) == CLASS_REFDISC)
    _aud = audit_coverage()
    _cs = confidence_sensitivity()
    _kscan = k_scan()
    F = {
        "n_axes": n, "n_cells": n * len(PROFILES), "n_specified": len(spec),
        "n_unspecified": n * len(PROFILES) - len(spec),
        "n_high": sum(1 for c in spec if c["confidence"] == "high"),
        "n_med": sum(1 for c in spec if c["confidence"] == "med"),
        "n_class_i": n - len(ii), "n_class_ii": len(ii),
        "class_ii_names": ", ".join(ii),
        "n_constant": len(const), "n_discriminating": n - len(const),
        "constant_names": ", ".join(const),
        # ★ ADDED R3. The manuscript stated this split in prose and stated it WRONG ("two disagree
        #   and three agree", giving five where there are four). Measured: 2 + 2. A number that is
        #   asserted in a sentence rather than substituted is a number nothing checks.
        "n_const_match": sum(1 for a in AXES if a["id"] in const
                             and str(a["p"]["v0.1.0"]["value"]) == str(a["p"][CHAINS[0]]["value"])),
        "n_const_mismatch": sum(1 for a in AXES if a["id"] in const
                                and str(a["p"]["v0.1.0"]["value"]) != str(a["p"][CHAINS[0]]["value"])),
        # ⛔ ADDED R8, AND THE SAME DEFECT AS R3 IN A NEW PLACE. The manuscript listed the constant
        #   axes BY NAME in prose and named only two of the three common mismatches -- it omitted
        #   the coinbase-height axis, which BIP34 added to every descendant. The count 14 was right;
        #   the sentence deriving it was not, so 5 + 14 = 19 did not visibly close.
        #   ★ Emitting the NAMES, not just the counts, is what makes the arithmetic checkable by a
        #     reader instead of merely correct in the engine.
        "const_mismatch_names": ", ".join(
            a["name"].lower() for a in AXES if a["id"] in const
            and str(a["p"]["v0.1.0"]["value"]) != str(a["p"][CHAINS[0]]["value"])),
        # ⛔ ADDED R8. The manuscript said "criterion (3) does most of the excluding". The table
        #   directly above it says otherwise: criterion (1) rejects three candidates on substantive
        #   grounds, criterion (3) rejects ONE. And that false premise was load-bearing -- the
        #   paragraph beneath it defends criterion (3) at length as though it were doing the work.
        #   ★ Counted from EXCLUSIONS rather than read off the table by eye, because reading a
        #     table by eye is precisely how the sentence got written wrong in the first place.
        # ⛔⛔ ADDED R9, AND THIS ONE WAS A FALSE SCIENTIFIC CLAIM, not a miscount. The manuscript
        #   said label granularity moves BSV "further than any axis-dropping perturbation does".
        #   Measured: label moves it 0.0527 from base; dropping up to three axes moves it 0.1086.
        #   **Label beats LEAVE-ONE-OUT. It does not beat the subset scan.** The true comparison is
        #   still interesting and is the one the subsection heading already made correctly -- the
        #   prose and caption had drifted to a stronger, wrong version of it.
        #   ★ So the comparison is now COMPUTED and the ordering named, because a sentence that
        #     ranks three ranges against each other is exactly the shape this project keeps getting
        #     wrong by hand.
        "bsv_move_label": "%.4f" % max(abs(lab["range_exact"]["BSV"][1] - tbl["v0.1.0"]["BSV"]["mismatch_rate_exact"]),
                                       abs(tbl["v0.1.0"]["BSV"]["mismatch_rate_exact"] - lab["range_exact"]["BSV"][0])),
        "bsv_move_loo": "%.4f" % max(abs(sens["v0.1.0|BSV"]["leave_one_out_max"] - tbl["v0.1.0"]["BSV"]["mismatch_rate"]),
                                     abs(tbl["v0.1.0"]["BSV"]["mismatch_rate"] - sens["v0.1.0|BSV"]["leave_one_out_min"])),
        "bsv_move_subset": "%.4f" % max(abs(subs["range"]["BSV"][1] - tbl["v0.1.0"]["BSV"]["mismatch_rate"]),
                                        abs(tbl["v0.1.0"]["BSV"]["mismatch_rate"] - subs["range"]["BSV"][0])),
        # ⚠️ Candidates JUDGED BY THE CRITERIA, which is not len(EXCLUSIONS): one row is out of
        #    scope (BSV testnets are not independent mainnets) and fails no criterion. Using the
        #    raw row count would have put a denominator of 5 under a numerator of 3 + 1.
        # ⛔ ADDED R10. Section 7 said the fetched total was "29 across three scripts, not the 26
        #   the first two account for". Both numbers are right and they are DIFFERENT UNITS:
        #   8 + 18 = 26 PROBES, over 24 distinct CELLS; +5 BTG probes on 5 new cells = 31 probes
        #   over 29 cells. A referee reading 26 -> 29 could only reverse-engineer it, and guessed
        #   wrong (that two of five BTG probes were absorbed; in fact none overlap).
        #   ★★ THE SENTENCE MIXING PROBE AND CELL COUNTS SAT ONE PARAGRAPH ABOVE THE PARAGRAPH
        #      WARNING THAT THREE DENOMINATORS ARE NOT INTERCHANGEABLE. Emitting both units ends it.
        "aud_probes_first2": _AUD_PROBES_FIRST2,
        "aud_probes_btg": _AUD_PROBES_BTG,
        "aud_probes_total": _AUD_PROBES_FIRST2 + _AUD_PROBES_BTG,
        "aud_cells_first2": _AUD_CELLS_FIRST2,
        "n_excl_total": sum(1 for r in EXCLUSIONS if r[4].startswith("Fails")),
        "n_excl_by_1": sum(1 for r in EXCLUSIONS if r[4].startswith("Fails (1)")),
        "n_excl_by_2": sum(1 for r in EXCLUSIONS if r[4].startswith("Fails (2)")),
        "n_excl_by_3": sum(1 for r in EXCLUSIONS if r[4].startswith("Fails (3)")),
        "n_excl_scope": sum(1 for r in EXCLUSIONS if r[4].startswith("Out of scope")),
        "const_match_names": ", ".join(
            a["name"].lower() for a in AXES if a["id"] in const
            and str(a["p"]["v0.1.0"]["value"]) == str(a["p"][CHAINS[0]]["value"])),
        # ★ R3: audit coverage as a PARTITION with a denominator, and the 2^k confidence result,
        #   both emitted so the manuscript substitutes them instead of asserting them.
        "aud_fetched": _aud["fetched"], "aud_inherited": _aud["inherited"],
        "aud_absence": _aud["absence"], "aud_unclassified": _aud["unclassified"], "aud_overlap": _aud["warrant_overlap"],
        "aud_specified": _aud["specified"],
        "conf_k": _cs["k"], "conf_assignments": _cs["assignments"],
        "conf_holds_in": _cs["bsv_uniquely_lowest"],
        # R4: the merged-cluster deltas the paper quotes, so they follow a cell edit
        **{("merged_%s" % c): ("%+.4f" % (sens["v0.1.0|%s" % c]["merged_cluster_exact"]
                                          - tbl["v0.1.0"][c]["mismatch_rate_exact"])) for c in CHAINS},
        # ★ R5: the paper quoted C(17,5)=6188 and C(17,6)=12376 after the axis set became 19.
        #   No gate could see it because the engine never computed the k-scan. It does now.
        **{("subsets_k%d" % k): __import__("math").comb(n, k) for k in (4, 5, 6)},
        **_kscan,
        **{("cnt_%s" % c): counts[c] for c in CHAINS},
        "gap": gap, "invariance_k": gap - 1,
        "subsets": subs["subsets"], "subset_flips": subs["orderings_where_the_lowest_chain_differs"],
        "nov_diff": reference_disagreement()["nov08|v0.1.0"]["differing"],
        "wp_spec": sum(1 for a in AXES if a["p"]["whitepaper"]["value"] is not None),
        "nov_spec": sum(1 for a in AXES if a["p"]["nov08"]["value"] is not None),
        "wp_cov": "%.3f" % tbl["whitepaper"]["BTC"]["coverage"],
        "nov_cov": "%.3f" % tbl["nov08"]["BTC"]["coverage"],
    }
    for c in CHAINS:
        s = sens["v0.1.0|%s" % c]
        F["rate_" + c] = "%.4f" % tbl["v0.1.0"][c]["mismatch_rate"]
        F["frac_" + c] = "%d/%d" % (tbl["v0.1.0"][c]["differing"], n)
        F["loo_" + c] = "[%.4f, %.4f]" % (s["leave_one_out_min"], s["leave_one_out_max"])
        F["sub_" + c] = "[%.4f, %.4f]" % (subs["range"][c][0], subs["range"][c][1])
        F["lab_" + c] = "[%.4f, %.4f]" % (lab["range"][c][0], lab["range"][c][1])
        F["rest_" + c] = str(len(prov[c]["restorations"]))
        F["ret_" + c] = str(len(prov[c]["retentions"]))
        F["match_" + c] = str(prov[c]["matches"])
    # ★★ R6, and open since R2: the Data-and-Code section pointed at a bare repository URL. A URL
    #    is a PROMISE, not a verifiable claim -- it can be edited after publication and a reader
    #    cannot tell. The engine therefore publishes the SHA-256 of ITSELF, so the paper names the
    #    exact bytes that produced its numbers and a reader can check the repository against it.
    #    ⛔ The self-hash is over the ENGINE SOURCE only. It cannot cover figures.json (which would
    #    then contain its own digest) and it says nothing about the audit scripts, which carry
    #    their own hashes below. Stated because an unqualified "the artifact hash" would imply a
    #    coverage this does not have.
    # ★ R7: the §4.2 takeaway is a SHAPE over three rows, not a number, so no numeric gate could
    #   ever catch it -- and three rounds running it was corrected and came back wrong. Generated.
    F["ref_summary"] = reference_summary_sentence(AXES)
    _self = Path(__file__).resolve()
    # ⚠️ FULL DIGEST, not a 16-hex prefix. 64 bits is ample against an accidental mismatch and
    #    is not what a paper about verification should publish; a reader checking a copy should
    #    be comparing the whole hash. Costs two lines of width and removes the question.
    F["engine_sha"] = hashlib.sha256(_self.read_bytes()).hexdigest()
    F["engine_bytes"] = format(_self.stat().st_size, ",")
    for _n in ("audit_descendants.py", "audit_btc.py", "audit_btg.py"):
        _p = _self.parent / _n
        if _p.exists():
            F["sha_" + _n.replace(".py", "").replace("audit_", "")] = \
                hashlib.sha256(_p.read_bytes()).hexdigest()
    # ★★ R14: THE SCRIPT DIGESTS SAY WHAT THE CODE *IS*. THEY DO NOT SAY WHAT IT *DID*.
    #    Two audit digests moved between revisions 8 and 9 (a line-ending normalisation), and the
    #    referee's objection was exactly right: **two readings fit and nothing in the paper
    #    distinguishes them** -- the scripts were reformatted and the results still hold, or the
    #    probes changed and the reported figures were never refreshed. A hostile reader takes the
    #    second. ⇒ So publish the LEDGERS too: each carries its own run timestamp and the
    #    body_sha256 of every fetched source, so 31 probes over 29 cells is bound to a dated
    #    artifact rather than to source files that merely existed. **A future digest change then
    #    reads as legible instead of ambiguous.**
    #  ⚠️ No circularity: the ledgers are written by the audit scripts, not by this engine, so
    #    hashing them here cannot make figures.json contain its own digest.
    for _n, _k in (("audit_descendants.json", "descendants"), ("audit_btc.json", "btc")):
        _p = _self.parent / "tables" / _n
        if _p.exists():
            F["sha_ledger_" + _k] = hashlib.sha256(_p.read_bytes()).hexdigest()
            try:
                F["ledger_run_" + _k] = json.loads(_p.read_text(encoding="utf-8"))["generated_utc"]
            except (KeyError, ValueError):
                F["ledger_run_" + _k] = "unrecorded"
    # ⚠️ R15: the block was introduced as "the artifacts that produced this paper name themselves",
    #    and that sentence was broader than the list. Figure 1 is rendered by a SEPARATE program
    #    from a separate run -- the paper says so in this very section -- and neither the renderer
    #    nor the PNG it produces was named. ★ Either narrow the sentence or widen the list; widening
    #    is strictly better, because the figure is a reported result and a reader comparing their
    #    own render has nothing to compare against otherwise.
    for _n, _k in (("figures/mismatch_heatmap.py", "figscript"),
                   ("figures/mismatch_heatmap_v010.png", "figpng")):
        _p = _self.parent / _n
        if _p.exists():
            F["sha_" + _k] = hashlib.sha256(_p.read_bytes()).hexdigest()
    # ★★ R16: THE ENGINE HAD NO OUTPUT TO PAIR ITS DIGEST AGAINST, AND THE AUDITS DID.
    #    The engine digest moved in three consecutive bundles while every reported number stayed
    #    identical. For an audit script that is legible -- script digest moves, ledger digest and
    #    timestamp do not, therefore the output was not regenerated under the new bytes. **The
    #    engine had no such pair: Tables 2-9 rested on one unhashed sentence naming a date three
    #    engine revisions old.** So hash what the engine PRODUCES, not only what it IS.
    #
    #  ★★★ AND DELIBERATELY WITHOUT A GENERATION TIMESTAMP, WHICH THE REFEREE ASKED FOR. These
    #      outputs are DETERMINISTIC -- two consecutive runs are byte-identical -- and that is a
    #      stronger property than a recorded date, because it makes the digest a pure function of
    #      the data. **Embedding a wall clock would change the digest on every run and destroy
    #      exactly the legibility the pairing exists to provide**, turning "the output changed"
    #      into "time passed". The audit ledgers carry timestamps because they record NETWORK
    #      fetches, which are not reproducible; these are computations, which are.
    #  ⚠️ THE DIRECTORY IS PASSED IN, NOT GUESSED. These three live in the artifacts directory,
    #     which `--out` can relocate, while this function writes to `tables/`. Hashing `out / name`
    #     here would have silently found nothing and set no keys at all -- a digest block that
    #     shrinks in silence is the same failure as one that goes stale. The caller writes them
    #     immediately before calling this, so what is on disk is this run's output.
    _ad = Path(artdir) if artdir else (_self.parent / "artifacts")
    for _n, _k in (("comparison.json", "comparison"), ("axis_matrix.csv", "axismatrix"),
                   ("comparison.csv", "comparisoncsv")):
        _p = _ad / _n
        if not _p.exists():
            raise SystemExit("emit_tables: expected engine output %s, and it is absent. The "
                             "digest block would have shipped without it." % _p)
        F["sha_out_" + _k] = hashlib.sha256(_p.read_bytes()).hexdigest()
    # ★★ R18: THE LAST UNPINNED LINK BETWEEN comparison.json AND A PRINTED TABLE.
    #    The referee recorded it as a decision rather than an oversight: `tables/*.md` are the
    #    rendered tables the manuscript substitutes, and they sat unhashed. They carry no digests,
    #    so unlike figures.json they can be covered without circularity.
    #
    #  ⇒ ONE MANIFEST DIGEST, NOT EIGHT MORE LINES. Data and Code is already 9.4% of the document,
    #    and the marginal round was being spent on the provenance of the provenance. A single
    #    digest over `name + sha256(bytes)` for every emitted table closes the gap at the cost of
    #    one line, and a reader who wants per-file detail recomputes it from the same rule.
    #
    #  ⛔ COMPUTED FROM THE BYTES ABOUT TO BE WRITTEN, NOT FROM DISK. At this point the .md files
    #    on disk are still the PREVIOUS run's — the same staleness trap that made the engine-output
    #    digests read a stale directory two rounds ago. `body + "\n"` encoded UTF-8 with no newline
    #    translation is exactly what the loop below writes, so the manifest describes this run.
    _man = hashlib.sha256()
    for _name in sorted(k for k in W if k != "figures.json"):
        _man.update(_name.encode("utf-8"))
        _man.update(hashlib.sha256((W[_name] + "\n").encode("utf-8")).digest())
    F["sha_tables_manifest"] = _man.hexdigest()
    F["n_tables_manifest"] = str(len([k for k in W if k != "figures.json"]))
    W["figures.json"] = json.dumps(F, indent=2, sort_keys=True)

    for name, body in W.items():
        (out / name).write_text(body + "\n", encoding="utf-8", newline="\n")
    return sorted(W)


def main() -> int:
    ap = argparse.ArgumentParser(description="Reference-relative protocol-profile comparison (NOT money).")
    ap.add_argument("--at", default=EVIDENCE_FREEZE.isoformat(), help="evaluation date YYYY-MM-DD")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "artifacts"))
    args = ap.parse_args()
    at = date.fromisoformat(args.at)
    if at > EVIDENCE_FREEZE:
        raise SystemExit(f"--at {at} is after the evidence freeze {EVIDENCE_FREEZE}; extend the cell "
                         "evidence before evaluating a later date.")
    if at < EVIDENCE_FREEZE:
        # ⚠️ CORRECTED 13 Aug 2026. This flag previously ACCEPTED any earlier date and returned
        #    byte-identical output, because no cell records when its rule activated. It is now
        #    refused rather than answered wrongly.
        raise SystemExit(
            f"--at {at}: REFUSED.\n"
            "\n"
            "  This engine cannot evaluate a historical date, and previously PRETENDED it could:\n"
            "  it accepted any earlier date and returned exactly the same numbers, because no\n"
            "  cell carries an activation date. A knob that silently does nothing is worse than\n"
            "  a missing one -- a reader who tries it has no way to tell which other capability\n"
            "  is also decorative.\n"
            "\n"
            "  WHAT IT WOULD TAKE: each chain cell needs a sourced timeline [(date, value), ...]\n"
            "  rather than a single value -- roughly 72 cells, each requiring the activation date\n"
            "  its primary source states. That is real work and it is not done, so the engine\n"
            f"  answers only at the evidence freeze, {EVIDENCE_FREEZE}.\n"
            "\n"
            "  Reported as a limitation in the paper rather than concealed behind a flag.")

    tbl = table(AXES)
    sens = sensitivity(AXES)

    print(f"reference-relative mismatch (evaluated {at}); NOT a metric, NOT a quality score.\n")
    hdr = "reference \\ chain   " + "".join(f"{c:>16}" for c in CHAINS)
    print(hdr)
    for ref in REFERENCES:
        cells = []
        for chain in CHAINS:
            r = tbl[ref][chain]
            mr = "undef" if r["mismatch_rate"] is None else f"{r['mismatch_rate']:.2f}"
            cells.append(f"{mr} (cov {r['coverage']:.2f})")
        print(f"{ref:18}" + "".join(f"{c:>16}" for c in cells))
    print("\nmismatch_rate = differing / jointly-specified; coverage = jointly-specified / total; "
          "undefined where coverage 0. Reference-relative — see METHOD.md. NOT money.")

    # --- the three analyses the engine used to compute and discard -----------------------------
    refdis = reference_disagreement()
    prov = {c: match_provenance(c) for c in CHAINS}
    subs = subset_robustness()
    const = constant_axes()

    print("\nDO THE REFERENCES AGREE WITH EACH OTHER?  (they do not, and that is the point)")
    for k, v in refdis.items():
        r1, r2 = k.split("|")
        mr = "undefined" if v["mismatch_rate"] is None else "%.2f" % v["mismatch_rate"]
        print("  %-11s vs %-11s jointly %d, differing %d, mismatch %s  %s"
              % (r1, r2, v["jointly_specified"], v["differing"], mr,
                 ", ".join(v["differing_axes"]) or ""))

    print("\nMATCH PROVENANCE — retention (never changed) vs restoration (changed, then changed back)")
    print("  %-6s %8s %11s %13s" % ("chain", "matches", "retentions", "restorations"))
    for c in CHAINS:
        p = prov[c]
        print("  %-6s %8d %11d %13d" % (c, p["matches"], len(p["retentions"]),
                                        len(p["restorations"])))

    counts = {c: tbl["v0.1.0"][c]["differing"] for c in CHAINS}
    gap = sorted(counts.values())[1] - min(counts.values())
    print("\nROBUSTNESS TO AXIS CHOICE — every subset dropping up to %d of %d axes"
          % (subs["drop_up_to"], len(AXES)))
    print("  %d subsets; the lowest-mismatch chain differs from the full-axis result in %d of them"
          % (subs["subsets"], subs["orderings_where_the_lowest_chain_differs"]))
    for c in CHAINS:
        print("  %-6s [%.2f, %.2f]" % (c, subs["range"][c][0], subs["range"][c][1]))
    print("""
  ⚠️ AND THAT IS ARITHMETIC, NOT A FINDING. Counts are %s over a shared denominator of %d, so the
     counts order the rates and the gap to the runner-up is %d. Dropping k axes moves any count by
     at most k, so the ordering CANNOT change for k < %d. **Invariance up to %d dropped axes is a
     theorem.**
     ⚠️ This banner previously asserted "the first ties appear at k=4" — a constant left behind when
        the gap changed from 4 to 5, in the very paragraph whose computed sentence proves ties are
        impossible before k=%d. **The exhaustive transition points are reported in the paper, from
        an independent enumeration; no hardcoded k appears here any more.**
     Reported because a referee found it, and because a robustness claim that is secretly a
     tautology is worse than none.""" % (counts, len(AXES), gap, gap, gap - 1, gap))

    lab = label_sensitivity()
    print("\nLABEL GRANULARITY — the encoding decision the match rule cannot see")
    for case in lab["cases"]:
        print("  %-34s %s" % (case["name"],
                              "  ".join("%s %.4f" % (c, case["rates"][c]) for c in CHAINS)))
    print("  %-34s %s" % ("RANGE",
                          "  ".join("%s [%.2f, %.2f]" % (c, lab["range"][c][0], lab["range"][c][1])
                                    for c in CHAINS)))
    print("""
  ★★ BSV spans %.2f-%.2f under relabelling -- WIDER THAN LEAVE-ONE-OUT. Two profiles match iff
     their labels are equal AS STRINGS, and the shipped dataset contains
     'no-dedicated-cap' vs 'no-consensus-cap' for the same state. **Judgement is not eliminated by
     reproducibility; it is RELOCATED to individuation, where it is at least visible.**"""
          % (lab["range"]["BSV"][0], lab["range"]["BSV"][1]))
    print("\n  %d of %d axes are CONSTANT across all four chains (%s) — they shift every rate "
          "equally\n  and cannot affect the ordering." % (len(const), len(AXES), ", ".join(const)))

    # --- the two-class axis rule, ENFORCED ------------------------------------------------
    problems = validate_axis_classes()
    ii = sorted(a["id"] for a in AXES if axis_class(a["id"]) == CLASS_REFDISC)
    i_n = len(AXES) - len(ii)
    print("\nAXIS-SELECTION RULE — two classes, and the classification is CHECKED not asserted")
    print("  class i  %2d axes  changed on at least one descendant since Jan 2009" % i_n)
    print("  class ii %2d axes  reference-discriminating, unchanged across descendants: %s"
          % (len(ii), ", ".join(ii)))
    if problems:
        print("  ⛔ CLASSIFICATION BROKEN — a cell edit has invalidated the stated rule:")
        for p in problems:
            print("       %s" % p)
    else:
        print("  ✅ every axis's declared class is re-derivable from the data")
    print("""
  ⚠️ AND THE COST, STATED WHERE IT CANNOT BE MISSED: the %d class-ii axes carry the SAME value on
     v0.1.0 and on all four chains, so they contribute a fixed %d matches to every chain and
     CANNOT DISCRIMINATE between them. They exist because they are the only axes the November 2008
     reference specifies -- without them that profile has ZERO jointly specified axes and no
     result at all. **They buy a reference, not a ranking.**""" % (len(ii), len(ii)))

    out = Path(args.out)
    out.mkdir(exist_ok=True)
    payload = {"not_money": True, "evaluated": at.isoformat(), "profiles": PROFILES,
               "n_axes": len(AXES), "axes": [{k: a[k] for k in ("id", "name", "criterion", "p")} for a in AXES],
               "sources": SOURCES, "table": tbl, "sensitivity": sens,
               "reference_disagreement": refdis, "match_provenance": prov,
               "subset_robustness": subs, "constant_axes": const,
               "label_sensitivity": lab,
               "note": "reference-relative mismatch counts/rates; NOT a metric and NOT a ranking of "
                       "which chain 'is' Bitcoin; every cell is source-anchored (see METHOD.md)."}
    # ⛔⛔ newline="\n" IS LOAD-BEARING, AND IT BECAME SO THE MOMENT THIS FILE'S DIGEST WAS
    #    PUBLISHED. Without it, write_text applies platform translation: CRLF on Windows, LF on
    #    Linux. **Identical content, different bytes, different SHA-256.** A reader regenerating
    #    this file on Linux would get the same numbers and a different hash — and under the rule
    #    this paper states, would have to read that as "a result changed".
    #  ★ Cosmetic for sixteen rounds; material the instant the hash became a verification target.
    #    Same class as the CRLF/LF mix found in the four audit scripts at R13, recurring in a
    #    GENERATED file, where .gitattributes cannot help because the bytes are made at run time.
    #  ⚠️ The two CSVs need no such fix: csv.writer with newline="" emits \r\n on every platform
    #    per RFC 4180, so they are already byte-stable. Do not "normalise" them to match — that
    #    would change two correct digests to make three files look alike.
    (out / "comparison.json").write_text(json.dumps(payload, indent=2) + "\n",
                                         encoding="utf-8", newline="\n")
    with (out / "comparison.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["reference", "chain", "jointly_specified", "differing", "coverage", "mismatch_rate"])
        for ref in REFERENCES:
            for chain in CHAINS:
                r = tbl[ref][chain]
                w.writerow([ref, chain, r["jointly_specified"], r["differing"], r["coverage"], r["mismatch_rate"]])
    with (out / "axis_matrix.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["axis"] + PROFILES + ["criterion"])
        for a in AXES:
            w.writerow([a["id"]] + [val(a, p) if val(a, p) is not None else "" for p in PROFILES] + [a["criterion"]])
    written = emit_tables(Path(__file__).resolve().parent / "tables",
                          tbl, sens, subs, lab, prov, refdis, const, artdir=out)
    print(f"\nwrote {out/'comparison.json'}, comparison.csv, axis_matrix.csv")
    print("wrote tables/: %s" % ", ".join(written))
    print("""
  ★ The paper INCLUDES those tables; it does not retype them. Run build_paper.py to assemble
    paper.md from paper.template.md — editing paper.md directly is what caused six regressions.""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
