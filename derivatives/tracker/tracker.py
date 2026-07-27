"""Reference-distance tracker — pick ANY origin, pick ANY date, see every version that existed
then and how far each stood from that origin.

This operationalises WHAT_IS_BITCOIN §9 and DEFINITIONAL_FIDELITY. It does **not** identify
"the real Bitcoin" (convention — no fact of the matter). The **reference is a parameter**,
precisely because "the origin" is a *choice*, not a fact (WHAT_IS_BITCOIN §8): choose the
whitepaper, the Nov-2008 pre-release, or v0.1.0 — each gives a different, equally valid tracker.

Model: each **axis** holds a *value* per codebase; a codebase's value on an axis changes over
time via dated **events**. Distance(reference, candidate) = the number of axes on which **both
specify a value and they differ**. Axes the reference does not constrain are skipped — so, e.g.,
the whitepaper (which mandates none of these implementation axes) yields distance 0 for
everyone: the design does not discriminate. **Distance is neutral** — a safety fix and a
feature removal both change a value, hence both add distance; nothing is ranked better/worse.

Epistemics (same discipline as DEPENDENCY_MATRIX):
- v0.1.0 and nov08 axis-values are `[S]` (from the lab's executed source work);
- the whitepaper's "unspecified" is a reasoned reading (the paper fixes none of these);
- the chains' dated **events** are `[D]` (public record; a curated scaffold, refinable).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

# --- axes: the properties a codebase can take a value on ----------------------
AXES: dict[str, str] = {
    "script_vocabulary": "which Script opcodes are enabled",
    "value_bounds":      "output value / sum sanity checks",
    "block_size":        "block-size limit",
    "script_limits":     "script element / op-count / stack ceilings",
    "sig_encoding":      "signature-encoding strictness",
    "crypto_lib":        "EC library for ECDSA-on-secp256k1",
    "pow_algo":          "proof-of-work function + target format",
    "monetary":          "unit / subsidy / halving / spacing",
    "consensus_db":      "chainstate storage engine",
    "witness":           "transaction / witness format (SegWit separates the signature)",
    "sig_scheme":        "signature scheme(s) accepted (ECDSA / Schnorr)",
}
_ = None  # UNSPECIFIED: the codebase does not constrain this axis

# --- frozen reference snapshots (timeless artifacts) --------------------------
# whitepaper: the design fixes NONE of these implementation axes -> all unspecified.
# nov08: a partial 5-file pre-release snapshot -> only monetary + PoW are defined in it.
# v0.1.0: the genesis client -> all nine defined.  ([S] for nov08/v0.1.0 values)
FROZEN: dict[str, dict[str, str | None]] = {
    "whitepaper": {ax: _ for ax in AXES},
    "nov08": {
        "monetary": "nov 1e6/100/100k/15m", "pow_algo": "leading-zero-bits",
        "script_vocabulary": _, "value_bounds": _, "block_size": _, "script_limits": _,
        "sig_encoding": _, "crypto_lib": _, "consensus_db": _, "witness": _, "sig_scheme": _,
    },
    "v0.1.0": {
        "script_vocabulary": "full", "value_bounds": "none", "block_size": "no-cap",
        "script_limits": "none", "sig_encoding": "lenient", "crypto_lib": "openssl",
        "pow_algo": "sha256d-compact", "monetary": "jan 1e8/50/210k/10m", "consensus_db": "bdb",
        "witness": "inline", "sig_scheme": "ecdsa",
    },
}


# the lab's own reconstructions: frozen MODEL builds carrying the FULL original vocabulary
# ("nothing disabled" -> `full+ne` re-opens the one opcode v0.1 disabled) under each
# constitution, as isolated networks. They exist as artifacts from the lab build date;
# crypto_lib / consensus_db are left unspecified because a Python MODEL abstracts that layer.
RECON: dict[str, dict[str, str | None]] = {
    "NOV08-X": {"monetary": "nov 1e6/100/100k/15m", "pow_algo": "leading-zero-bits",
        "script_vocabulary": "full+ne", "value_bounds": "none", "block_size": "no-cap",
        "script_limits": "none", "sig_encoding": "lenient", "crypto_lib": _, "consensus_db": _,
        "witness": "inline", "sig_scheme": "ecdsa"},
    "JAN09-X": {"monetary": "jan 1e8/50/210k/10m", "pow_algo": "sha256d-compact",
        "script_vocabulary": "full+ne", "value_bounds": "none", "block_size": "no-cap",
        "script_limits": "none", "sig_encoding": "lenient", "crypto_lib": _, "consensus_db": _,
        "witness": "inline", "sig_scheme": "ecdsa"},
}


@dataclass(frozen=True)
class Chain:
    name: str
    born: date
    forked_from: str | None                     # None -> the origin chain (starts as v0.1.0)


# evolving genesis-SHARING continuations of the v0.1.0 chain.
# lineage note: "BCH" here is the majority continuation (Bitcoin ABC pre-2020, then Bitcoin Cash
# Node after the Nov-2020 split); "XEC" is eCash — the Bitcoin-ABC branch of that 2020 split,
# rebranded + redenominated in 2021. "BSV" split from BCH in the Nov-2018 hash war.
CHAINS: dict[str, Chain] = {
    "BTC": Chain("BTC", date(2009, 1, 3),  None),
    "BCH": Chain("BCH", date(2017, 8, 1),  "BTC"),
    "BSV": Chain("BSV", date(2018, 11, 15),"BCH"),
    "XEC": Chain("XEC", date(2020, 11, 15),"BCH"),
}
SINCE: dict[str, date] = {
    "whitepaper": date(2008, 10, 31), "nov08": date(2008, 11, 15), "v0.1.0": date(2009, 1, 3),
    "NOV08-X": date(2026, 7, 26), "JAN09-X": date(2026, 7, 26),
    **{n: c.born for n, c in CHAINS.items()},
}


@dataclass(frozen=True)
class Event:
    when: date
    chain: str
    axis: str
    value: str
    note: str


# --- dated events: a chain SETS an axis to a new value  ([D]) ------------------
EVENTS: list[Event] = [
    Event(date(2010, 8, 1),  "BTC", "script_vocabulary", "disabled-subset", "broad opcode set disabled"),
    Event(date(2010, 8, 1),  "BTC", "value_bounds",      "moneyrange",      "MoneyRange added after the value-overflow"),
    Event(date(2010, 8, 1),  "BTC", "script_limits",     "bounded",         "520-byte / op-count / stack ceilings"),
    Event(date(2010, 9, 1),  "BTC", "block_size",        "1mb",             "1 MB MAX_BLOCK_SIZE cap"),
    Event(date(2013, 3, 1),  "BTC", "consensus_db",      "leveldb",         "chainstate moved to LevelDB (0.8)"),
    Event(date(2015, 7, 4),  "BTC", "sig_encoding",      "strict-der",      "BIP66 strict-DER (block 363725)"),
    Event(date(2016, 2, 1),  "BTC", "crypto_lib",        "libsecp256k1",    "libsecp256k1 for consensus (0.12)"),
    Event(date(2017, 8, 24), "BTC", "witness",           "segwit",          "SegWit activated (BIP141)"),
    Event(date(2021, 11, 14),"BTC", "sig_scheme",        "ecdsa+schnorr",   "Taproot: Schnorr signatures (BIP340)"),
    Event(date(2018, 5, 15), "BCH", "script_vocabulary", "restored-subset", "re-enabled a subset of opcodes"),
    Event(date(2018, 5, 15), "BCH", "block_size",        "32mb",            "raised block-size limit"),
    Event(date(2019, 5, 15), "BCH", "sig_scheme",        "ecdsa+schnorr",   "Schnorr signatures for CHECKSIG"),
    Event(date(2020, 2, 4),  "BSV", "script_vocabulary", "near-full",       "Genesis: restored near-original vocab (minus 2MUL/2DIV)"),
    Event(date(2020, 2, 4),  "BSV", "script_limits",     "none",            "Genesis: removed script number/size limits"),
    Event(date(2020, 2, 4),  "BSV", "block_size",        "unbounded",       "Genesis: removed the block-size cap"),
    Event(date(2021, 7, 1),  "XEC", "monetary",          "ecash 2-decimal", "eCash redenomination (1e6 XEC per BCH)"),
]


# --- state, distance, tracking ------------------------------------------------
def state_of(name: str, at: date) -> dict[str, str | None]:
    """Axis-values of `name` as of `at`. Frozen artifacts are timeless; evolving chains start
    from their parent's state at the fork (the origin chain starts as v0.1.0) then apply events."""
    if name in FROZEN:
        return dict(FROZEN[name])
    if name in RECON:
        return dict(RECON[name])
    ch = CHAINS[name]
    st = dict(FROZEN["v0.1.0"]) if ch.forked_from is None else state_of(ch.forked_from, ch.born)
    for e in sorted(EVENTS, key=lambda e: e.when):
        if e.chain == name and ch.born <= e.when <= at:
            st[e.axis] = e.value
    return st


def _diff_axes(ref: dict, cand: dict) -> list[str]:
    """Axes on which BOTH specify a value and they differ (unconstrained axes are skipped)."""
    return [ax for ax in AXES
            if ref[ax] is not None and cand[ax] is not None and ref[ax] != cand[ax]]


def distance(reference: str, candidate: str, at: date) -> int:
    return len(_diff_axes(state_of(reference, SINCE.get(reference, at)), state_of(candidate, at)))


def track(reference: str, at: date) -> dict[str, dict]:
    """Every version that exists at `at` (except the reference), with its distance from
    `reference` and the axes on which it differs."""
    ref_state = state_of(reference, SINCE.get(reference, at))
    out = {}
    for name in list(FROZEN) + list(RECON) + list(CHAINS):
        if name != reference and SINCE[name] <= at:
            diff = _diff_axes(ref_state, state_of(name, at))
            out[name] = {"distance": len(diff), "differs_on": diff}
    return dict(sorted(out.items(), key=lambda kv: (kv[1]["distance"], kv[0])))


def references() -> list[str]:
    """The named origins you can measure from."""
    return list(FROZEN)


def define(reference: str = "v0.1.0") -> dict[str, str | None]:
    """The axis-values of a chosen reference (its 'definition' on these axes)."""
    return dict(FROZEN[reference]) if reference in FROZEN else state_of(reference, date.today())


def demo() -> None:
    milestones = [date(2009, 1, 3), date(2016, 1, 1), date(2021, 1, 1), date(2026, 8, 1)]
    for ref in references():
        print(f"\n===== reference (origin) = {ref} =====")
        for when in milestones:
            if when < SINCE[ref]:
                continue
            rows = track(ref, when)
            cells = "  ".join(f"{n} {r['distance']}" for n, r in rows.items())
            print(f"  {when}:  {cells or '(nothing else yet)'}")
    print("\ndistance = # axes where both specify a value and differ (neutral; not a quality score).")
    print("whitepaper -> ~0 for all: the design does not constrain these axes (it does not discriminate).")


if __name__ == "__main__":
    demo()
