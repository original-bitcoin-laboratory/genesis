"""Reference-distance tracker — how far each Bitcoin claimant has drifted from a fixed
reference, over time.

This operationalises WHAT_IS_BITCOIN §9 and DEFINITIONAL_FIDELITY. It does **not** identify
"the real Bitcoin" at a timestamp — that is convention, with no fact of the matter (see the
docs). It fixes a **chosen reference** and measures, at any date, how far each claimant has
moved from it. **Distance is neutral**: a safety fix (adding MoneyRange) and a feature removal
(disabling opcodes) both *increase* it; the tracker ranks nothing as better or worse — it only
measures displacement from the reference.

The reference here is **v0.1.0** — and this is a *choice, not a certain fact*: "the origin" is
itself a definitional choice (WHAT_IS_BITCOIN §8). v0.1.0 is the principled choice **for this
tracker** because the tracked chains (BTC/BCH/BSV/XEC) are its genesis-*sharing* continuations
— v0.1.0 is their *actual common root-state*, and their history begins at the genesis block,
not at anything earlier. Fix the reference earlier and you get a different, equally valid
tracker: relative to the **Nov-2008 pre-release**, v0.1.0 is *itself* already diverged
(COIN 1e6→1e8, subsidy 100→50, 15→10 min, leading-zero-bit → compact PoW); relative to the
**whitepaper** (the design), v0.1.0's opcode set / COIN / hash / DB are choices it didn't
mandate. So v0.1.0 is the zero point *only under this anchor*. See the README.

Epistemics (same discipline as DEPENDENCY_MATRIX):
- the origin **axes** are `[S]` — from the lab's executed v0.1.0 conformance work;
- the dated **events** are `[D]` — curated from the public record, refinable; this is a
  scaffold demonstrating the method, not an authoritative complete history.

Two states move an axis off the origin:
- `diverged`  — changed away from v0.1.0 (weight 1.0);
- `restored`  — later changed *back toward* v0.1.0, though not proven byte-identical (weight 0.5).

Distance(chain, date) = Σ weights over its axes. 0.0 ⇔ indistinguishable from the origin here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

# The reference this tracker measures FROM. A chosen anchor, not a certain fact (see docstring
# + README): earlier candidates (the Nov-2008 pre-release, the whitepaper, the upstream
# primitives it cites) would each yield a different, equally valid tracker — and under an
# earlier anchor v0.1.0 itself is no longer the zero point.
REFERENCE = "v0.1.0 (3 Jan 2009 genesis client)"

# --- the reference axes: properties that define v0.1.0-conformance  ([S]) -------
AXES: dict[str, str] = {
    "script_vocabulary": "full v0.1 opcode set enabled (only OP_NOTEQUAL disabled)",
    "value_bounds":      "no MoneyRange / output-sum overflow check",
    "block_size":        "no MAX_BLOCK_SIZE cap (32 MB serialization only)",
    "script_limits":     "no element / op-count / stack ceilings (underflow guards only)",
    "sig_encoding":      "lenient (non-strict-DER) signature parsing",
    "crypto_lib":        "OpenSSL EC for ECDSA-on-secp256k1",
    "pow_algo":          "SHA-256d, compact target",
    "monetary":          "COIN=1e8, 50-coin subsidy, 210k halving, 10-min spacing",
    "consensus_db":      "Berkeley DB for the chainstate",
}
ORIGIN = date(2009, 1, 3)                       # the genesis block's date

_WEIGHT = {"origin": 0.0, "restored": 0.5, "diverged": 1.0}


@dataclass(frozen=True)
class Chain:
    name: str
    born: date
    forked_from: str | None = None              # inherits the parent's state at `born`
    note: str = ""


# genesis-SHARING continuations of the origin chain, + the lab's living reference.
# (Separate-genesis instances like LTC/DOGE are a different category — see the README.)
CHAINS: dict[str, Chain] = {
    "BTC":     Chain("BTC",     date(2009, 1, 3),  None,  "the continuous origin chain"),
    "BCH":     Chain("BCH",     date(2017, 8, 1),  "BTC", "fork of BTC"),
    "BSV":     Chain("BSV",     date(2018, 11, 15),"BCH", "fork of BCH"),
    "XEC":     Chain("XEC",     date(2020, 11, 15),"BCH", "eCash; fork of BCH"),
    "JAN09-X": Chain("JAN09-X", date(2026, 7, 1),  None,  "lab reconstruction: full origin profile (MODEL)"),
}


@dataclass(frozen=True)
class Event:
    when: date
    chain: str
    axis: str
    state: str                                  # "diverged" | "restored"
    note: str


# --- dated divergence events  ([D], public record; curated & refinable) --------
EVENTS: list[Event] = [
    Event(date(2010, 8, 1),  "BTC", "script_vocabulary", "diverged", "broad opcode set disabled"),
    Event(date(2010, 8, 1),  "BTC", "value_bounds",      "diverged", "MoneyRange added (0.3.1) after the value-overflow"),
    Event(date(2010, 8, 1),  "BTC", "script_limits",     "diverged", "520-byte / op-count / stack ceilings added"),
    Event(date(2010, 9, 1),  "BTC", "block_size",        "diverged", "1 MB MAX_BLOCK_SIZE cap added"),
    Event(date(2013, 3, 1),  "BTC", "consensus_db",      "diverged", "chainstate moved to LevelDB (0.8)"),
    Event(date(2015, 7, 4),  "BTC", "sig_encoding",      "diverged", "BIP66 strict-DER activated (block 363725)"),
    Event(date(2016, 2, 1),  "BTC", "crypto_lib",        "diverged", "libsecp256k1 for consensus verification (0.12)"),
    Event(date(2018, 5, 15), "BCH", "script_vocabulary", "restored", "re-enabled a subset of disabled opcodes"),
    Event(date(2020, 2, 4),  "BSV", "script_vocabulary", "restored", "Genesis upgrade: near-original vocabulary (minus 2MUL/2DIV)"),
    Event(date(2020, 2, 4),  "BSV", "script_limits",     "restored", "Genesis upgrade: removed script number/size limits"),
]


# --- state, distance, tracking -------------------------------------------------
def state_of(name: str, at: date) -> dict[str, str]:
    """Each axis's state for `name` as of `at`: forks inherit the parent's state at the
    moment of the fork, then apply their own events."""
    ch = CHAINS[name]
    st = {ax: "origin" for ax in AXES}
    if ch.forked_from:
        st = state_of(ch.forked_from, ch.born)          # inherit parent state at fork date
    for e in sorted(EVENTS, key=lambda e: e.when):
        if e.chain == name and ch.born <= e.when <= at:
            st[e.axis] = e.state
    return st


def distance(name: str, at: date) -> float:
    return round(sum(_WEIGHT[s] for s in state_of(name, at).values()), 3)


def track(at: date) -> dict[str, dict]:
    """Every claimant that exists at `at`, with its origin-distance and moved axes."""
    out = {}
    for name, ch in CHAINS.items():
        if ch.born <= at:
            st = state_of(name, at)
            out[name] = {
                "distance": distance(name, at),
                "diverged": sorted(a for a, s in st.items() if s == "diverged"),
                "restored": sorted(a for a, s in st.items() if s == "restored"),
            }
    return out


def define() -> dict[str, str]:
    """The chosen reference (REFERENCE = v0.1.0) this tracker measures against — a definitional
    choice, not a certain 'origin' (see the module docstring)."""
    return dict(AXES)


_MILESTONES = [
    (date(2009, 1, 3),  "genesis"),
    (date(2011, 1, 1),  "after the 2010 hardening"),
    (date(2016, 1, 1),  "after BIP66 + libsecp256k1"),
    (date(2018, 1, 1),  "after the BTC/BCH split"),
    (date(2021, 1, 1),  "after the BSV Genesis upgrade"),
    (date(2026, 8, 1),  "today"),
]


def demo() -> None:
    print("origin reference (distance 0) = v0.1.0 on", len(AXES), "axes\n")
    for when, label in _MILESTONES:
        print(f"{when}  — {label}")
        for name, row in sorted(track(when).items(), key=lambda kv: kv[1]["distance"]):
            moved = ", ".join(row["diverged"] + [a + "*" for a in row["restored"]]) or "none"
            print(f"   {name:8} distance {row['distance']:>4}   moved: {moved}")
        print()
    print("* = restored toward origin (weight 0.5). Distance is neutral — not a quality score.")


if __name__ == "__main__":
    demo()
