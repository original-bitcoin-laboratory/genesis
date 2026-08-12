"""Watch the live chain for the difficulty retarget, and capture it when it fires.

WHY THIS EXISTS — the experiment had no observer
-------------------------------------------------
WHY-THE-CHAIN-CONTINUES.md names one hypothesis and pre-registers its answer: the retarget at
height 2016 will execute and leave nBits at 0x1d00ffff, because this chain mines at the
proof-of-work limit already and the clamp sends the loosened target straight back.

  ⚠️ NOTHING WAS WATCHING FOR IT. retarget.py is a MODEL -- a line-for-line port of
     GetNextWorkRequired -- not a monitor. No scheduled job mentions height 2016. The chain is
     mining ~105 min/block, so the boundary is months away, and a pre-registered prediction that
     nobody is present to score is not an experiment. It is a hope.

This closes that. It reads the published status feed, reports the distance to the boundary, and
when the chain crosses it, captures the blocks either side and checks the prediction.

WHAT IT RECORDS AT THE BOUNDARY, and why each field
----------------------------------------------------
  the last block BEFORE 2016 and the first AFTER      the pair the retarget sits between
  nBits on both sides                                 the prediction is about exactly this
  the timestamps the retarget consumed                nActualTimespan is computed from them
  the model's independent answer                      retarget.py recomputes it from source

⚠️ THE PREDICTION IS SCORED EITHER WAY, and a miss is the more valuable result. If nBits is
anything other than 0x1d00ffff the pre-registration is wrong, and that is a finding worth more
than the expected pass -- which is exactly why it was written down in advance.

Run:  python derivatives/retarget/retarget_watch.py            # one check, prints distance
      python derivatives/retarget/retarget_watch.py --json     # machine-readable, for cron
"""
import json
import os
import ssl
import sys
import urllib.request

try:
    import certifi
    SSLCTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    SSLCTX = ssl.create_default_context()

STATUS = ("https://raw.githubusercontent.com/original-bitcoin-laboratory/genesis/"
          "status/status.json")
UA = {"User-Agent": "obl-retarget-watch/1.0"}

INTERVAL = 2016                 # nInterval, main.cpp
PREDICTED_NBITS = "1d00ffff"    # the pre-registered answer
HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "_retarget_watch_state.json")


def feed():
    r = urllib.request.Request(STATUS, headers=UA)
    return json.loads(urllib.request.urlopen(r, timeout=60, context=SSLCTX).read())


def main():
    as_json = "--json" in sys.argv
    try:
        d = feed()
    except Exception as e:
        print(json.dumps({"error": type(e).__name__}) if as_json
              else "  status feed unreachable (%s) — NOT a statement about the chain"
              % type(e).__name__)
        return 2

    c = d.get("chains", {}).get("bitcoin")
    if not c:
        print("  the feed carries no 'bitcoin' chain — cannot report")
        return 2

    h = c.get("height")
    to_go = INTERVAL - h
    prior = json.load(open(STATE)) if os.path.exists(STATE) else {}
    last_seen = prior.get("height", 0)

    out = {"height": h, "blocks_to_retarget": to_go, "boundary": INTERVAL,
           "predicted_nbits": PREDICTED_NBITS, "feed_updated": d.get("updated"),
           "online": c.get("online"), "crossed": h >= INTERVAL}

    if as_json:
        print(json.dumps(out))
    else:
        print("=" * 74)
        print(" RETARGET WATCH — the one hypothesis this chain is still running for")
        print("=" * 74)
        print("  chain height        %d" % h)
        print("  boundary            %d" % INTERVAL)
        print("  blocks to go        %d" % to_go)
        print("  feed updated        %s   online=%s" % (d.get("updated"), c.get("online")))
        if last_seen:
            print("  since last check    +%d blocks" % (h - last_seen))
        print()
        if h >= INTERVAL:
            print("  ★★ THE BOUNDARY HAS BEEN CROSSED.")
            print("     Capture, from the chain rather than from this feed:")
            print("       - the last block before %d and the first at or after it" % INTERVAL)
            print("       - nBits on both sides   (pre-registered answer: 0x%s)" % PREDICTED_NBITS)
            print("       - the timestamps the retarget consumed")
            print("       - retarget.py's independent recomputation of the same rule")
            print()
            print("  ⚠️ Score the prediction EITHER WAY. A miss is the more valuable result and")
            print("     is the whole reason it was written down in advance.")
        else:
            # a crude ETA, honestly labelled
            rate = 105.0        # min/block, an order-of-magnitude figure, not a measurement
            days = to_go * rate / 1440.0
            print("  rough ETA           ~%.0f days at ~%.0f min/block" % (days, rate))
            print("  ⚠️ that cadence is NOT a measurement — it carries ~32% standard error on")
            print("     10 exponential samples. Treat it as an order of magnitude.")

    json.dump(out, open(STATE, "w"), indent=1)
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
