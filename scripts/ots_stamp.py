#!/usr/bin/env python3
"""Create an OpenTimestamps proof for a file, through the public calendars, without the `ots` CLI.

    python scripts/ots_stamp.py <file> [<file> ...]     # writes <file>.ots beside each file

A fresh proof attests to NOW: it proves the bytes existed by today. It never back-dates anything.
The proof is written pending; run scripts/ots_upgrade.py hours later to complete it once a calendar
has put the commitment in a Bitcoin block. Needs `pip install opentimestamps-client` (the pure-python
library only; the command-line tool it ships is not used).
"""
import hashlib, ssl, sys, urllib.request, pathlib
from opentimestamps.core.timestamp import DetachedTimestampFile, Timestamp
from opentimestamps.core.op import OpSHA256
from opentimestamps.core.serialize import BytesSerializationContext
from opentimestamps.calendar import RemoteCalendar

CALENDARS = ["https://alice.btc.calendar.opentimestamps.org",
             "https://bob.btc.calendar.opentimestamps.org",
             "https://finney.calendar.eternitywall.com"]
try:
    import certifi
    _CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _CTX = ssl.create_default_context()
urllib.request.install_opener(urllib.request.build_opener(urllib.request.HTTPSHandler(context=_CTX)))

def stamp(path: str) -> int:
    digest = hashlib.sha256(pathlib.Path(path).read_bytes()).digest()
    ts = Timestamp(digest); reached = []
    for url in CALENDARS:
        try:
            ts.merge(RemoteCalendar(url).submit(digest)); reached.append(url.split("//")[1].split(".")[0])
        except Exception as exc:
            print(f"  {url}: {type(exc).__name__}")
    if not reached:
        print(f"{path}: no calendar reachable, no proof written"); return 1
    ctx = BytesSerializationContext(); DetachedTimestampFile(OpSHA256(), ts).serialize(ctx)
    out = pathlib.Path(path + ".ots"); out.write_bytes(ctx.getbytes())
    print(f"{path}: stamped with {len(reached)} calendar(s) [{', '.join(reached)}] -> {out.name} ({out.stat().st_size} B, pending)")
    return 0

if __name__ == "__main__":
    if len(sys.argv) < 2: print(__doc__); sys.exit(2)
    sys.exit(max(stamp(p) for p in sys.argv[1:]))
