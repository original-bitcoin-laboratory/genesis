"""C3 evidence on the FAITHFUL, source-bounded profiles only — no experimental X network involved.

Loads `jan09-faithful` and `nov08-source-bounded`, derives each profile's consensus (monetary) rules from
the hash-matched source, and asserts that all five monetary parameters differ between the November 2008
constitution and the January 2009 release. It records both profile hashes and (when run directly) writes the
paper artifact `paper-artifacts/monetary-difference.json`. It never imports or runs the isolated `jan09-x` /
`nov08-x` experimental networks, so this check honours the paper's boundary ("neither experimental profile
supplies any evidence for this paper"). Evidence level: source-bounded. NOT money.
"""
from __future__ import annotations

import json
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_ROOT = _HERE.parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import profiles as P  # noqa: E402

PARAMS = ("COIN", "subsidy_base", "halving", "spacing", "coinbase_rule")


def _jsonable(v):
    try:
        json.dumps(v)
        return v
    except TypeError:
        return str(v)


def _params(rules) -> dict:
    return {k: getattr(rules, k) for k in PARAMS}


def monetary_difference() -> dict:
    """Derive the five-parameter difference from the two faithful profiles' source-derived rules."""
    jan, nov = P.load("jan09-faithful"), P.load("nov08-source-bounded")
    jp, np_ = _params(jan.rules()), _params(nov.rules())
    return {
        "not_money": True,
        "claim": "The five monetary parameters differ between the November 2008 preview and the January 2009 release",
        "profiles": {
            "january": {"name": jan.name, "consensus_rules": jan.consensus_rules, "profile_hash": jan.profile_hash()},
            "november": {"name": nov.name, "consensus_rules": nov.consensus_rules, "profile_hash": nov.profile_hash()},
        },
        "parameters": {k: {"november": _jsonable(np_[k]), "january": _jsonable(jp[k]), "differs": np_[k] != jp[k]} for k in PARAMS},
        "all_five_differ": all(np_[k] != jp[k] for k in PARAMS),
        "source_witness": "consensus.Rules for 'nov08' vs 'jan09', derived from the hash-matched source "
                          "(see common/NOV08_JAN09_DIFF.md); no experimental X network involved",
    }


def test_five_monetary_parameters_differ_source_bounded():
    d = monetary_difference()
    assert d["all_five_differ"], d["parameters"]
    # each profile identity is recorded and stable
    assert len(d["profiles"]["january"]["profile_hash"]) == 64
    assert len(d["profiles"]["november"]["profile_hash"]) == 64


def write_artifact() -> pathlib.Path:
    out = _ROOT / "paper-artifacts"
    out.mkdir(exist_ok=True)
    path = out / "monetary-difference.json"
    path.write_text(json.dumps(monetary_difference(), indent=2) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    p = write_artifact()
    d = json.loads(p.read_text())
    print(f"wrote {p.name}: all five parameters differ = {d['all_five_differ']} (source-bounded, no X network)")
