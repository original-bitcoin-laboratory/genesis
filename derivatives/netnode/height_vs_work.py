"""Freeze the discriminating height-vs-work result to a paper artifact — the numbers, not just a pass.

The strongest original experiment (paper C4 / §6): under the faithful v0.1 rule, a TALLER branch of LOWER
cumulative work displaces a SHORTER branch of HIGHER work — because the best-chain predicate is
`nHeight > nBestHeight`, never summed work (`main.cpp`). This module runs that scenario once and records
its actual state (branch heights, cumulative work, the selected tip, and the lab vs historical retarget
horizons) so the result is a frozen, checkable artifact rather than a bare "the test passed".

`scenario()` independently reproduces the fork built in
`test_chainstate.py::test_height_beats_cumulative_work_the_discriminating_fork` (both derive from the same
`Chain`/`ChainState`/difficulty code, so agreement is a cross-check) and returns its frozen numerical
state; running this file writes `paper-artifacts/height-vs-work.json`. Evidence: MODEL / NEW-EXP. NOT money.
"""
from __future__ import annotations

import json
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
for _p in ("model", "p2p", "nov08x", "wallet", "profiles"):
    sys.path.insert(0, str(_HERE.parent / _p))
sys.path.insert(0, str(_HERE))

from chainsync import Chain, block_hash                       # noqa: E402
from p2p import block_bytes, merkle_root, pow_ok              # noqa: E402
from tx_sighash import Tx, TxIn, TxOut                        # noqa: E402
from chainstate import ChainState                            # noqa: E402
from difficulty import NET_RETARGET_INTERVAL, expected_bits  # noqa: E402
import profiles                                              # noqa: E402

_ROOT = _HERE.parent.parent
ZERO = b"\x00" * 32
EASY = 0x207FFFFF
HISTORICAL_INTERVAL = 2016
FAITHFUL = profiles.load("jan09-faithful")
RULES = FAITHFUL.rules()
_tag = [0]


def _mine_at(prev, height, nbits, t):
    _tag[0] += 1
    s = bytes([height & 0xFF, (height >> 8) & 0xFF, _tag[0] & 0xFF, (_tag[0] >> 8) & 0xFF])
    cb = Tx(1, [TxIn(ZERO, 0xFFFFFFFF, s, 0xFFFFFFFF)], [TxOut(RULES.get_block_value(height - 1), b"\x51")], 0)
    mr = merkle_root([cb])
    for nonce in range(1 << 24):
        raw = block_bytes(1, prev, mr, t, nbits, nonce, [cb])
        if pow_ok(raw, nbits):
            return raw
    raise RuntimeError("no nonce")


def _chainwork(nbits):
    return (1 << 256) // (RULES.pow_target(nbits) + 1)        # per-block work = 2^256 / (target+1)


def scenario() -> dict:
    """Build the discriminating fork under jan09-faithful and return its frozen numerical state.

    Asserts the invariants so a broken result fails loudly rather than freezing a wrong number."""
    assert NET_RETARGET_INTERVAL == 60 and NET_RETARGET_INTERVAL < HISTORICAL_INTERVAL
    BASE = 1_231_006_506
    chain = Chain()
    g = _mine_at(ZERO, 0, EASY, BASE)
    chain.add_genesis(g, EASY)
    gh = block_hash(g)

    def build(gap, n):
        prev, wtot, seen = gh, 0, set()
        for h in range(1, n + 1):
            nb = expected_bits(chain, prev, RULES)             # honest difficulty
            raw = _mine_at(prev, h, nb, BASE + h * gap)
            assert chain.process_block(raw)[0] in ("accepted", "orphan")
            prev, wtot = block_hash(raw), wtot + _chainwork(nb)
            seen.add(nb)
        return prev, n, wtot, seen

    # Incumbent B: fast first window retargets HARDER, kept short. Challenger A: slow window stays at the
    # floor, grown taller.
    b_tip, b_h, b_work, b_seen = build(gap=5, n=122)
    st = ChainState(chain, RULES, maturity=1)
    st.activate_best()
    assert st.tip == b_tip and st.height == b_h                # B is the incumbent best chain
    a_tip, a_h, a_work, a_seen = build(gap=120, n=125)
    st.activate_best()

    assert a_h > b_h and a_work < b_work                       # taller yet LESS cumulative work
    assert b_seen != {EASY} and a_seen == {EASY}               # B retargeted above the floor; A stayed on it
    assert st.tip == a_tip and st.height == a_h                # node switches to the taller/lower-work branch

    return {
        "not_money": True,
        "claim": "v0.1 selects the best chain by block height, not cumulative proof-of-work",
        "profile": FAITHFUL.name,
        "profile_hash": FAITHFUL.profile_hash(),
        "incumbent_branch_B": {"height": b_h, "cumulative_work": str(b_work),
                               "difficulty_floors_seen": sorted(f"{x:#010x}" for x in b_seen)},
        "challenger_branch_A": {"height": a_h, "cumulative_work": str(a_work),
                                "difficulty_floors_seen": sorted(f"{x:#010x}" for x in a_seen)},
        "challenger_has_less_work": bool(a_work < b_work),
        "selected_tip": "challenger_branch_A",
        "selected_by": "height (nHeight > nBestHeight; never summed work)",
        "retarget_interval_used": NET_RETARGET_INTERVAL,       # lab substitution
        "historical_interval": HISTORICAL_INTERVAL,            # v0.1's 2016-block window
        "source_witness": "main.cpp best-chain update; test_chainstate.py::"
                          "test_height_beats_cumulative_work_the_discriminating_fork",
    }


def write_artifact() -> pathlib.Path:
    out = _ROOT / "paper-artifacts"
    out.mkdir(exist_ok=True)
    path = out / "height-vs-work.json"
    path.write_text(json.dumps(scenario(), indent=2) + "\n", encoding="utf-8",
                    newline="\n")   # LF, not the platform default: this file is hashed
    return path


def test_height_vs_work_result_is_frozen():
    d = scenario()
    assert d["challenger_branch_A"]["height"] > d["incumbent_branch_B"]["height"]
    assert int(d["challenger_branch_A"]["cumulative_work"]) < int(d["incumbent_branch_B"]["cumulative_work"])
    assert d["selected_tip"] == "challenger_branch_A" and d["challenger_has_less_work"]
    assert len(d["profile_hash"]) == 64


if __name__ == "__main__":
    p = write_artifact()
    d = json.loads(p.read_text())
    print(f"wrote {p.name}: A(h={d['challenger_branch_A']['height']}) beats "
          f"B(h={d['incumbent_branch_B']['height']}) with LESS work; selected={d['selected_tip']}")
