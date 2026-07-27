"""The origin-distance tracker: genesis sits at 0, claimants drift over time, forks inherit
their parent's drift, and a restoration (BSV Genesis) moves a chain back toward the origin.
Distance is neutral (displacement from v0.1.0), not a quality score. Evidence: origin axes [S],
dated events [D]."""

import pathlib
import sys
from datetime import date

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from tracker import AXES, CHAINS, define, distance, state_of, track  # noqa: E402


def test_genesis_is_distance_zero():
    assert distance("BTC", date(2009, 1, 4)) == 0.0
    assert track(date(2009, 1, 4))["BTC"]["distance"] == 0.0


def test_only_the_origin_chain_exists_at_genesis():
    at = date(2009, 6, 1)
    assert set(track(at)) == {"BTC"}                      # BCH/BSV/XEC/JAN09-X not born yet


def test_btc_drifts_monotonically_through_2016():
    d09 = distance("BTC", date(2009, 6, 1))
    d11 = distance("BTC", date(2011, 1, 1))               # after 2010 hardening (4 axes)
    d16 = distance("BTC", date(2016, 6, 1))               # + LevelDB, BIP66, libsecp256k1
    assert d09 == 0.0 < d11 < d16
    assert d16 == 7.0                                     # 7 axes diverged by 2016


def test_only_monetary_and_pow_stay_at_origin_for_btc():
    st = state_of("BTC", date(2016, 6, 1))
    assert st["monetary"] == "origin" and st["pow_algo"] == "origin"


def test_a_chain_is_absent_before_its_birth():
    assert "BCH" not in track(date(2015, 1, 1))           # BCH born 2017
    assert "BCH" in track(date(2017, 9, 1))


def test_fork_inherits_parent_drift_at_birth():
    # BCH at its fork inherits all of BTC's accumulated divergence (nonzero immediately)
    assert distance("BCH", date(2017, 8, 2)) == distance("BTC", date(2017, 8, 1)) == 7.0


def test_restoration_moves_a_chain_back_toward_origin():
    # BCH re-enabling opcodes (2018) reduces its distance
    assert distance("BCH", date(2018, 1, 1)) > distance("BCH", date(2018, 6, 1))
    # BSV's Genesis upgrade (2020) reduces it further (script_limits diverged -> restored)
    assert distance("BSV", date(2020, 1, 1)) > distance("BSV", date(2020, 3, 1))


def test_bsv_is_closest_to_origin_on_script_among_the_forks():
    # after Genesis, BSV has restored both script axes; BTC has restored neither
    bsv = state_of("BSV", date(2021, 1, 1))
    btc = state_of("BTC", date(2021, 1, 1))
    assert bsv["script_vocabulary"] == "restored" and bsv["script_limits"] == "restored"
    assert btc["script_vocabulary"] == "diverged" and btc["script_limits"] == "diverged"


def test_lab_reconstruction_is_the_only_living_zero_distance_thing_today():
    t = track(date(2026, 8, 1))
    assert t["JAN09-X"]["distance"] == 0.0                # full origin profile, by construction
    assert t["BTC"]["distance"] > 0.0                     # the name-bearing chain has drifted
    zeros = [c for c, r in t.items() if r["distance"] == 0.0]
    assert zeros == ["JAN09-X"]                           # nothing else living sits at the origin


def test_define_returns_the_full_axis_reference():
    assert set(define()) == set(AXES) and len(define()) == 9

