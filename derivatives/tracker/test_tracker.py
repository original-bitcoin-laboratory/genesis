"""Reference-selectable origin-distance tracker: pick any origin + any date, measure each
version's distance from it. Distance = # axes where both specify a value and differ (neutral).
The reference is a parameter because 'the origin' is a choice. Evidence: v0.1.0/nov08 values
[S], chain events [D]."""

import pathlib
import sys
from datetime import date

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from tracker import (  # noqa: E402
    AXES, AXIS_DEFS, CHAINS, distance, differing_axes, references,
    robustness, state_of, subset_lattice, track,
)


# ---- the whitepaper does not discriminate ------------------------------------

def test_whitepaper_reference_gives_zero_for_everyone():
    # the design constrains none of the 11 implementation axes -> distance 0 for all
    for name, row in track("whitepaper", date(2026, 8, 1)).items():
        assert row["distance"] == 0, name


# ---- v0.1.0 is itself diverged from the earlier nov08 anchor -----------------

def test_v010_is_nonzero_distance_from_nov08():
    # under the Nov-2008 anchor, v0.1.0 already differs on monetary + PoW (the only axes nov08 fixes)
    assert distance("nov08", "v0.1.0", date(2009, 1, 3)) == 2
    assert set(track("nov08", date(2009, 1, 3))["v0.1.0"]["differs_on"]) == {"monetary", "pow_algo"}


def test_btc_distance_depends_on_the_chosen_origin():
    at = date(2016, 6, 1)
    d_wp = distance("whitepaper", "BTC", at)      # design: 0
    d_nov = distance("nov08", "BTC", at)          # nov08 fixes only monetary+pow: 2
    d_v01 = distance("v0.1.0", "BTC", at)         # v0.1.0 fixes all eleven: 7 by 2016
    assert d_wp == 0 and d_nov == 2 and d_v01 == 7
    assert d_wp < d_nov < d_v01                   # the same chain, three different distances


# ---- the v0.1.0 anchor reproduces the earlier tracker's numbers --------------

def test_genesis_chain_is_zero_from_v010_then_drifts():
    assert distance("v0.1.0", "BTC", date(2009, 1, 4)) == 0     # BTC starts AS v0.1.0
    d11 = distance("v0.1.0", "BTC", date(2011, 1, 1))
    d16 = distance("v0.1.0", "BTC", date(2016, 6, 1))
    assert 0 < d11 < d16 == 7


def test_only_monetary_and_pow_stay_at_v010_for_btc():
    st = state_of("BTC", date(2016, 6, 1))
    v = state_of("v0.1.0", date(2009, 1, 3))
    assert st["monetary"] == v["monetary"] and st["pow_algo"] == v["pow_algo"]


# ---- forks, births, and moving back toward the anchor ------------------------

def test_a_version_is_absent_before_it_exists():
    assert "BCH" not in track("v0.1.0", date(2015, 1, 1))       # BCH born 2017
    assert "BCH" in track("v0.1.0", date(2017, 9, 1))


def test_fork_inherits_parent_distance_at_birth():
    assert distance("v0.1.0", "BCH", date(2017, 8, 2)) == distance("v0.1.0", "BTC", date(2017, 8, 1))


def test_bsv_moves_back_toward_v010_on_script_limits():
    # BSV's 2020 Genesis sets script_limits back to "none" (== v0.1.0) -> that axis stops differing
    before = track("v0.1.0", date(2020, 1, 1))["BSV"]["differs_on"]
    after = track("v0.1.0", date(2020, 3, 1))["BSV"]["differs_on"]
    assert "script_limits" in before and "script_limits" not in after
    # but restored vocabulary is "near-full" != "full", so that axis still differs (honest)
    assert "script_vocabulary" in after


def test_references_are_the_named_origins():
    assert references() == ["whitepaper", "nov08", "v0.1.0"]
    assert len(AXES) == 11 and len(CHAINS) == 4


# ---- the newer axes (SegWit, Schnorr/Taproot) widen the picture --------------

def test_segwit_and_taproot_widen_btc_distance_from_v010():
    # BTC adopted SegWit (2017) + Taproot/Schnorr (2021) -> two more axes off v0.1.0
    d = track("v0.1.0", date(2022, 6, 1))["BTC"]
    assert "witness" in d["differs_on"] and "sig_scheme" in d["differs_on"]
    assert distance("v0.1.0", "BTC", date(2026, 8, 1)) == 9      # 7 (by 2016) + segwit + schnorr


def test_bsv_is_the_closest_big_chain_to_v010():
    at = date(2026, 8, 1)
    dbsv = distance("v0.1.0", "BSV", at)                         # rejected SegWit/Schnorr, restored script
    dbtc = distance("v0.1.0", "BTC", at)
    dbch = distance("v0.1.0", "BCH", at)
    assert dbsv < dbch < dbtc                                    # 6 < 8 < 9 — neutral, not "better"


# ---- the lab's reconstructions, added to the candidate set -------------------

def test_reconstructions_appear_only_from_the_build_date():
    assert "JAN09-X" not in track("v0.1.0", date(2026, 7, 1))       # not yet built
    assert "JAN09-X" in track("v0.1.0", date(2026, 8, 1))
    assert "NOV08-X" in track("nov08", date(2026, 8, 1))


def test_nov08x_is_a_faithful_reconstruction_of_the_november_constitution():
    # NOV08-X matches the two axes the pre-release fixes -> distance 0 from the nov08 anchor
    assert distance("nov08", "NOV08-X", date(2026, 8, 1)) == 0


def test_jan09x_is_one_axis_from_v010_because_it_re_enables_op_notequal():
    # JAN09-X reconstructs the genesis but re-opens OP_NOTEQUAL ("nothing disabled") -> +1 on vocab
    assert distance("v0.1.0", "JAN09-X", date(2026, 8, 1)) == 1
    assert track("v0.1.0", date(2026, 8, 1))["JAN09-X"]["differs_on"] == ["script_vocabulary"]
    assert distance("v0.1.0", "NOV08-X", date(2026, 8, 1)) == 3    # + monetary + PoW


# ---- each axis is operationally defined; conclusions self-report their robustness ----

def test_axis_defs_cover_exactly_the_axes():
    # every axis has an operational definition -> a value is contestable against evidence, not opinion
    assert set(AXIS_DEFS) == set(AXES)


def test_bsv_closer_than_btc_is_robust_to_the_axis_choice():
    # BSV's differing-axis set is a subset of BTC's, so the ordering holds under EVERY axis subset:
    # the conclusion is structural, not an artifact of which axes were chosen.
    r = robustness("v0.1.0", "BSV", "BTC", date(2026, 8, 1))
    assert r["structural_subset"] is True
    assert r["holds"] == r["total"]                            # 100% of non-empty axis subsets
    assert set(differing_axes("v0.1.0", "BSV", date(2026, 8, 1))) <= \
           set(differing_axes("v0.1.0", "BTC", date(2026, 8, 1)))


def test_whitepaper_zero_is_analytic_not_axis_dependent():
    # the whitepaper specifies no axis, so distance 0 for all is independent of the axis set chosen
    wp = state_of("whitepaper", date(2008, 10, 31))
    assert all(wp[ax] is None for ax in AXES)


def test_subset_lattice_orders_the_genesis_chains():
    # BSV's differing set is contained in BTC's (and BCH's) -> reported in the lattice
    lat = subset_lattice("v0.1.0", date(2026, 8, 1))
    assert "BTC" in lat["BSV"] and "BCH" in lat["BSV"]
