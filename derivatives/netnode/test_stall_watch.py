"""The stall watch must raise the 31 Oct - 18 Nov 2026 case -- a chain whose height stops advancing
for days while its service reports "active" -- and must not fire on a healthy chain, on a single
unmeasured run, on one low reading, or on the first run with no history."""
import json
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import stall_watch as sw                                    # noqa: E402


def _status(updated, **heights):
    chains = {}
    for name, h in heights.items():
        chains[name] = {"online": h is not None, **({"height": h} if h is not None else {"height_unmeasured": True})}
    return {"updated": updated, "chains": chains}


def test_first_run_starts_every_clock_now():
    new = _status("2026-11-18T12:00:00Z", jan09x=100)
    sw.annotate(new, {})
    assert new["chains"]["jan09x"] == {"online": True, "height": 100, "height_seen": 100,
                                       "height_advanced_at": "2026-11-18T12:00:00Z"}
    assert sw.stalled(new, {"jan09x": 6}) == []


def test_advancing_chain_moves_its_clock():
    prev = _status("2026-11-18T06:00:00Z", jan09x=100)
    sw.annotate(prev, {})
    new = _status("2026-11-18T13:00:00Z", jan09x=900)
    sw.annotate(new, prev)
    assert new["chains"]["jan09x"]["height_advanced_at"] == "2026-11-18T13:00:00Z"
    assert sw.stalled(new, {"jan09x": 6}) == []


def test_the_november_case_is_reported():
    # 276,065 was first published on 14 Nov 2026 and was still the height on 18 Nov
    prev = {"updated": "2026-11-15T01:01:45Z",
            "chains": {"jan09x": {"height": 276065, "height_seen": 276065,
                                  "height_advanced_at": "2026-11-14T10:56:00Z"}}}
    new = _status("2026-11-18T12:16:56Z", jan09x=276065)
    sw.annotate(new, prev)
    assert new["chains"]["jan09x"]["height_advanced_at"] == "2026-11-14T10:56:00Z"
    (name, since, seen), = sw.stalled(new, {"jan09x": 18})
    assert name == "jan09x" and seen == 276065 and since > 24 * 3


def test_an_unmeasured_run_keeps_the_last_height_and_clock():
    prev = _status("2026-11-18T06:00:00Z", jan09x=100)
    sw.annotate(prev, {})
    new = _status("2026-11-18T13:00:00Z", jan09x=None)          # online, walk incomplete, one run later
    sw.annotate(new, prev)
    c = new["chains"]["jan09x"]
    assert c["height_seen"] == 100 and c["height_advanced_at"] == "2026-11-18T06:00:00Z"
    assert "height" not in c                                     # nothing invents a measured height
    assert sw.stalled(new, {"jan09x": 18}) == []                 # a 7 h run gap with one bad run: no alarm


def test_a_lower_reading_does_not_move_the_clock():
    # 30 Oct 2026: one run published jan09x 118,002 between 271,296 and 272,238 (a lagging anchor)
    prev = _status("2026-10-30T13:37:56Z", jan09x=271296)
    sw.annotate(prev, {})
    new = _status("2026-10-30T18:52:35Z", jan09x=118002)
    sw.annotate(new, prev)
    assert new["chains"]["jan09x"]["height_seen"] == 271296
    assert new["chains"]["jan09x"]["height_advanced_at"] == "2026-10-30T13:37:56Z"


def test_history_without_the_new_fields_counts_from_the_previous_run():
    prev = _status("2026-11-18T00:00:00Z", nov08x=500)           # a status.json from before this script
    new = _status("2026-11-18T07:00:00Z", nov08x=500)
    sw.annotate(new, prev)
    assert new["chains"]["nov08x"]["height_advanced_at"] == "2026-11-18T00:00:00Z"
    assert [s[0] for s in sw.stalled(new, {"nov08x": 6})] == ["nov08x"]


def test_main_annotates_in_place_and_exits_2(tmp_path, capsys):
    prev = tmp_path / "prev.json"
    prev.write_text(json.dumps({"updated": "2026-11-17T00:00:00Z",
                                "chains": {"bitcoin": {"height": 1700, "height_seen": 1700,
                                                       "height_advanced_at": "2026-11-17T00:00:00Z"},
                                           "jan09x": {"height": 5}}}), encoding="utf-8")
    new = tmp_path / "status.json"
    new.write_text(json.dumps(_status("2026-11-18T06:00:00Z", bitcoin=1700, jan09x=9)), encoding="utf-8")
    rc = sw.main(["--status", str(new), "--prev", str(prev),
                  "--stall-hours", "bitcoin=24", "--stall-hours", "jan09x=18"])
    out = capsys.readouterr().out
    assert rc == 2 and "STALLED bitcoin" in out and "STALLED jan09x" not in out
    data = json.loads(new.read_text(encoding="utf-8"))
    assert data["chains"]["jan09x"]["height_seen"] == 9


def test_main_tolerates_a_missing_previous_status(tmp_path):
    new = tmp_path / "status.json"
    new.write_text(json.dumps(_status("2026-11-18T06:00:00Z", jan09x=9)), encoding="utf-8")
    assert sw.main(["--status", str(new), "--prev", str(tmp_path / "absent.json"),
                    "--stall-hours", "jan09x=6"]) == 0


def test_a_watched_chain_missing_from_the_status_is_reported():
    new = _status("2026-11-18T06:00:00Z", jan09x=9)
    sw.annotate(new, {})
    assert sw.stalled(new, {"nov08x": 6}) == [("nov08x", None, None)]
