#!/usr/bin/env python3
"""Watch the Bitcoin (2026) chain's height against the first retarget, height 2016.

`WHY-THE-CHAIN-CONTINUES.md` states the experiment's height; `CONSENSUS_BEHAVIORS.md` states what
the retarget is expected to do at difficulty 1 (a no-op: the target cannot fall further). The
finding the height exists for is the executed retarget under abnormal forcing, and it has to be
sealed within days of the event, not months. This script is the watch: it reads the height the
scheduled status probe publishes (or a local status.json), reports the distance, and exits 2 once
the height is at or past the target so a caller can act on it.

    python scripts/height_watch.py                       # read the published status.json
    python scripts/height_watch.py --status /tmp/status.json
    python scripts/height_watch.py --target 2016         # the default

Exit codes: 0 below the target, 2 at or past it, 1 when the status cannot be read. Standard
library only. NOT money.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone

STATUS_URL = "https://raw.githubusercontent.com/original-bitcoin-laboratory/genesis/status/status.json"
CHAIN = "bitcoin"
TARGET = 2016


def load(path: str | None) -> dict:
    if path:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    req = urllib.request.Request(STATUS_URL, headers={"User-Agent": "obl height watch (stdlib)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--status", help="a local status.json instead of the published one")
    ap.add_argument("--target", type=int, default=TARGET)
    a = ap.parse_args()
    try:
        d = load(a.status)
        chain = d["chains"][CHAIN]
        height = int(chain["height"])
    except Exception as e:  # noqa: BLE001 - any failure to read is the same answer: no height
        print(f"height watch: cannot read the status ({e.__class__.__name__}: {e})")
        return 1
    updated = d.get("updated", "?")
    recent = chain.get("recent") or []
    rate = ""
    times = sorted(int(b["time"]) for b in recent if isinstance(b, dict) and "time" in b)
    if len(times) >= 2 and times[-1] > times[0]:
        per_block = (times[-1] - times[0]) / (len(times) - 1)
        remaining = max(a.target - height, 0)
        eta = datetime.fromtimestamp(times[-1] + remaining * per_block, tz=timezone.utc)
        rate = f"; recent spacing {per_block / 60:.1f} min/block, at that rate the target lands about {eta:%Y-%m-%d} UTC"
    print(f"height watch: {CHAIN} at height {height} (status updated {updated}); target {a.target}; "
          f"{max(a.target - height, 0)} block(s) to go{rate}")
    if height >= a.target:
        print("height watch: TARGET REACHED -- seal the retarget findings set (raw block bytes, the "
              "measured interval series across the window) at the standard of the other sets")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
