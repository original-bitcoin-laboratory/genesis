"""Watch each chain in status.json for a height that stops advancing. NOT money.

⛔ WHY THIS EXISTS. From about 31 Oct to 18 Nov 2026 the jan09x miner on obl-node (1 GB, no swap)
was killed for lack of memory during start-up, over and over; systemd kept restarting it, its
restart counter stood at 15,250 on 18 Nov, and it reported the service "active" throughout. The
published jan09x height stopped advancing at its normal rate (a block every 30 s) and moved only
three more times, in jumps (to 273,098, 274,065 and 276,065), when the replica caught a page between
kills. Nothing raised an alarm, because nothing watched for a height that does not move. A service
state is the wrong signal: the right one is the chain itself.

This script compares the status.json the probe just wrote with the one published by the previous
run. For each chain it records, in the new file:

    height_seen          the highest height measured so far (an unmeasured run keeps the last one)
    height_advanced_at   when height_seen last went up (UTC)

and reports a chain as STALLED when its threshold (--stall-hours chain=hours) has passed since
height_advanced_at. A chain whose height could not be measured counts as not advancing, which is
the right answer: an unmeasured chain for that long needs a look too.

Thresholds must exceed both the chain's own quiet spells and the gap between scheduled runs
(median ~6 h, up to ~17 h). Replaying the 100 published statuses from 25 Oct to 18 Nov 2026:
jan09x and nov08x mine every 30 s, so 18 h (about three runs) tolerates a run or two that cannot
measure; the Bitcoin (2026) chain is mined in bursts with quiet spells of up to 51.5 h, so it needs
72 h. With those values the replay raises jan09x alone, from 1 Nov.

height_seen is a high-water mark, so a single low reading (a lagging anchor) is ignored. The same
rule means that after a deliberate RESET of a chain to a lower height, the watch reports it
STALLED until it passes the old height again; that is expected, and the issue can be closed.

    python stall_watch.py --status /tmp/status.json --prev /tmp/prev-status.json \\
        --stall-hours jan09x=18 --stall-hours nov08x=18 --stall-hours bitcoin=72

Exit codes: 0 nothing stalled, 2 at least one chain stalled (one line `STALLED <chain> ...` each),
1 when the new status cannot be read. A missing or unreadable previous status is not an error: the
first run starts every clock at its own time. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone


def _ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def annotate(new: dict, prev: dict) -> None:
    """Add height_seen / height_advanced_at to every chain of `new`, carried forward from `prev`."""
    now = new["updated"]
    prev_chains = (prev or {}).get("chains", {})
    for name, c in new.get("chains", {}).items():
        p = prev_chains.get(name, {})
        prev_seen = p.get("height_seen", p.get("height"))
        prev_at = p.get("height_advanced_at") or (prev or {}).get("updated")
        cur = c.get("height") if isinstance(c.get("height"), int) else None
        if cur is not None and (not isinstance(prev_seen, int) or cur > prev_seen):
            c["height_seen"], c["height_advanced_at"] = cur, now
        else:
            c["height_seen"] = prev_seen if isinstance(prev_seen, int) else cur
            c["height_advanced_at"] = prev_at or now


def stalled(new: dict, hours: dict) -> list:
    """[(chain, hours since it last advanced, height_seen)] for chains past their threshold."""
    now = _ts(new["updated"])
    out = []
    for name, limit in hours.items():
        c = new.get("chains", {}).get(name)
        if c is None:
            out.append((name, None, None))                      # a watched chain the probe did not report
            continue
        since = (now - _ts(c["height_advanced_at"])).total_seconds() / 3600
        if since > limit:
            out.append((name, since, c.get("height_seen")))
    return out


def _hours(specs):
    out = {}
    for s in specs:
        name, _, h = s.partition("=")
        out[name] = float(h)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--status", required=True, help="status.json just written by status_probe.py (annotated in place)")
    ap.add_argument("--prev", help="the previously published status.json, if any")
    ap.add_argument("--stall-hours", action="append", default=[], metavar="chain=hours")
    a = ap.parse_args(argv)
    try:
        with open(a.status, encoding="utf-8") as f:
            new = json.load(f)
        _ts(new["updated"])
    except Exception as e:  # noqa: BLE001 - any failure to read is the same answer
        print(f"stall watch: cannot read {a.status} ({e.__class__.__name__}: {e})")
        return 1
    prev = {}
    if a.prev:
        try:
            with open(a.prev, encoding="utf-8") as f:
                prev = json.load(f)
        except Exception:  # noqa: BLE001 - no previous state: every clock starts now
            prev = {}
    annotate(new, prev)
    tmp = a.status + ".tmp"                                     # the publish step copies this file:
    with open(tmp, "w", encoding="utf-8") as f:                 # never leave it half-written
        json.dump(new, f, indent=2)
    os.replace(tmp, a.status)
    for name, c in new.get("chains", {}).items():
        print(f"stall watch: {name} height_seen={c['height_seen']} advanced_at={c['height_advanced_at']}")
    bad = stalled(new, _hours(a.stall_hours))
    for name, since, seen in bad:
        if since is None:
            print(f"STALLED {name} not present in the status")
        else:
            print(f"STALLED {name} has not advanced for {since:.1f} h (height {seen}, "
                  f"last advanced {new['chains'][name]['height_advanced_at']})")
    return 2 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
