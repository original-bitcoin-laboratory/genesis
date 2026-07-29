"""Bind the declared rule profiles to what the engine and inventory actually do. NOT money."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import profiles as P


def test_all_profiles_load():
    names = [p.name for p in P.all_profiles()]
    assert {"jan09-faithful", "jan09-x", "nov08-source-bounded", "nov08-x"} <= set(names)


def test_verify_is_clean():
    problems = P.verify()
    assert problems == [], problems


def test_faithful_disables_op_notequal():
    p = P.load("jan09-faithful")
    assert p.disabled_opcodes == ["OP_NOTEQUAL"]
    ok, _ = p.runner()(["OP_1", "OP_1", "OP_NOTEQUAL"])
    assert ok is False                                   # disabled -> structural failure


def test_experimental_reopens_op_notequal():
    p = P.load("jan09-x")
    assert p.reopened_opcodes == ["OP_NOTEQUAL"] and p.disabled_opcodes == []
    ok_ne, st_ne = p.runner()(["OP_1", "OP_2", "OP_NOTEQUAL"])
    ok_eq, st_eq = p.runner()(["OP_1", "OP_1", "OP_NOTEQUAL"])
    assert ok_ne and P.cast_to_bool(st_ne[-1])           # 1 != 2 -> true
    assert ok_eq and not P.cast_to_bool(st_eq[-1])       # 1 != 1 -> false


def test_disabled_set_matches_inventory():
    inv = P._inventory_disabled()
    assert inv == ["OP_NOTEQUAL"]
    assert P.load("jan09-faithful").disabled_opcodes == inv
    assert P.load("jan09-x").reopened_opcodes == inv


def test_consensus_axis_is_faithful_to_each_edition():
    jf = P.load("jan09-faithful").rules()
    nf = P.load("nov08-source-bounded").rules()
    # the genesis-born monetary constitution (jan09) vs the November constitution
    assert jf.COIN == 100_000_000 and nf.COIN == 1_000_000
    assert jf.halving == 210_000 and nf.halving == 100_000
    assert jf.subsidy_base == 50 * jf.COIN and nf.subsidy_base == 100 * nf.COIN
    assert jf.coinbase_rule == "le" and nf.coinbase_rule == "equal"


def test_same_consensus_across_script_postures():
    # jan09-faithful and jan09-x share consensus; they differ only in script vocabulary
    assert P.load("jan09-faithful").consensus_rules == P.load("jan09-x").consensus_rules
    assert P.load("jan09-faithful").script_posture != P.load("jan09-x").script_posture
