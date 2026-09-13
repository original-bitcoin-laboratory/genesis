#!/usr/bin/env python3
"""Test criterion (2) against Bitcoin Gold at the evidence freeze. NOT money.

★ WHY THIS EXISTS. The paper states chain selection as an "iff" over three criteria. An inclusion
  rule only ever applied to the chains already chosen is a description, not a rule — so R3 asked
  for it to be tested against a candidate that should fail. **Bitcoin Gold is the sharp case**: it
  duplicated Bitcoin's ledger through block 491,406 and publishes dated hard-fork specifications,
  so it satisfies (1) ledger ancestry and (3) a dated spec record on their face. Its exclusion
  rests entirely on (2): **was it producing blocks on 1 August 2026?**

⛔ THE ANSWER IS NOT ASSUMED. If BTG was producing blocks at the freeze it satisfies all three
   criteria as currently written, and the honest consequences are: either it belongs in the set, or
   the rule needs a fourth criterion — stated in advance and applied to everything, not invented to
   exclude one chain. **A rule bent after seeing the answer is not a rule.**

⚠️ EVERY FETCH CARRIES A CONTROL. An endpoint must prove it is serving BITCOIN GOLD — not Bitcoin,
   not a parked domain, not a challenge page — or its answer is VOID rather than negative. The
   control is the BTG genesis hash, which is Bitcoin's own genesis (the ledger was duplicated), so
   the discriminating control is the chain/network name plus a height beyond the 491,406 split.

Run:  python audit_btg.py
"""
import io
import json
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

try:
    import certifi
    CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    CTX = ssl.create_default_context()
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
UA = {"User-Agent": "Mozilla/5.0 obl-research/1.0 (academic; chain-liveness probe)"}

FREEZE = datetime(2026, 8, 1, tzinfo=timezone.utc)
FORK_HEIGHT = 491406          # BTG's stated duplication point

ENDPOINTS = [
    ("btgexplorer api/blocks", "https://btgexplorer.com/api/blocks?limit=1"),
    ("btgexplorer api/status", "https://btgexplorer.com/api/status"),
    ("explorer.bitcoingold insight", "https://explorer.bitcoingold.org/insight-api/status"),
    ("explorer.bitcoingold blocks", "https://explorer.bitcoingold.org/insight-api/blocks?limit=1"),
    ("blockchair btg stats", "https://api.blockchair.com/bitcoin-gold/stats"),
]


def get(u):
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=45, context=CTX)
        return r.getcode(), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return None, str(e)[:120]


def as_utc(ts):
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc)
    except Exception:
        return None


print("=" * 100)
print(" CRITERION (2) vs BITCOIN GOLD — was it producing blocks at the 1 Aug 2026 freeze?")
print("=" * 100)
print("  ⚠️ control on every fetch: the payload must be BTG chain data, or the probe is VOID.\n")

answers = []
for label, url in ENDPOINTS:
    code, body = get(url)
    print("  %-30s HTTP %-5s %7s B" % (label, code, len(body) if body else 0))
    if code != 200 or not body:
        print("       UNRESOLVED — not a negative")
        time.sleep(0.4)
        continue
    try:
        j = json.loads(body)
    except Exception:
        print("       payload is not JSON — VOID (a rendered page is not an API answer)")
        time.sleep(0.4)
        continue
    # ⛔ MY PARSER WAS WRONG, NOT THE ENDPOINT — the eleventh time this session.
    #    btgexplorer runs Blockbook, which nests everything under a "blockbook" key, so a
    #    top-level scan found nothing and printed "200 but no height/time field found". The
    #    payload had the complete answer in it the whole time.
    #    ★★ AND THE SHAPE OF THE MISREAD WAS THE CLUE I ALMOST MISSED: two DIFFERENT endpoints
    #    returned IDENTICAL 777-byte bodies, which reads exactly like a bot-wall — and would have
    #    been recorded as one. It was a shared status envelope. **Open the payload before naming
    #    the failure**, because "the host is blocking us" and "we are reading the wrong key" look
    #    the same from the outside and have opposite remedies.
    height = tstamp = None
    scopes = [j]
    if isinstance(j, dict):
        for k in ("blockbook", "data", "backend", "info"):
            if isinstance(j.get(k), dict):
                scopes.append(j[k])
    for d in scopes:
        if not isinstance(d, dict):
            continue
        for k in ("bestHeight", "blocks", "best_block_height", "height"):
            if isinstance(d.get(k), int) and height is None:
                height = d[k]
        for k in ("lastBlockTime", "bestBlockTime", "best_block_time", "time", "timestamp"):
            if d.get(k) and tstamp is None:
                tstamp = d[k]
    if height is None and tstamp is None:
        print("       200 but no height/time field found — VOID for this question")
        time.sleep(0.4)
        continue
    dt = as_utc(tstamp) if tstamp else None
    if isinstance(tstamp, str) and dt is None:
        try:
            dt = datetime.fromisoformat(tstamp.replace("Z", "+00:00"))
        except Exception:
            dt = None
    print("       height=%s  tip_time=%s" % (height, dt.isoformat() if dt else tstamp))
    if height is not None and height <= FORK_HEIGHT:
        print("       ⚠ height is at/below the %d split — this is NOT post-fork BTG data" % FORK_HEIGHT)
        time.sleep(0.4)
        continue
    answers.append((label, height, dt))
    time.sleep(0.4)

print("\n" + "-" * 100)
if not answers:
    print("""  VERDICT: UNRESOLVED. No endpoint answered with post-fork BTG chain data.

  ⛔ AND THAT IS NOT THE SAME AS 'BTG WAS INACTIVE'. An unreachable explorer is a fact about
     explorers. **The paper must keep saying UNVERIFIED**, because a negative we cannot source is
     exactly the kind of claim this method exists to refuse.""")
    sys.exit(2)

for label, h, dt in answers:
    if dt is None:
        print("  %-30s height %s, tip time unknown" % (label, h))
        continue
    live_at_freeze = dt >= FREEZE
    print("  %-30s height %-10s tip %s  -> chain %s at/after the freeze"
          % (label, h, dt.date(), "WAS producing" if live_at_freeze else "tip PREDATES the freeze"))

# ── the decisive test: a block AT the freeze, not merely a live tip today ─────────────────────
print("\n" + "-" * 100)
print("  A LIVE TIP TODAY IS NOT PRODUCTION ON 1 AUGUST 2026. Fetching a block at the freeze.\n")
best = next((h for _, h, _ in answers if h), None)
if best:
    # ~10-minute target spacing; step back from the tip to land near 1 Aug 2026, then read the
    # block's own header timestamp. The block's time is the evidence; our arithmetic only aims.
    now = datetime.now(timezone.utc)
    guess = max(FORK_HEIGHT + 1, best - int((now - FREEZE).total_seconds() // 600))
    for probe in (guess, guess - 144, guess + 144):
        c, b = get("https://btgexplorer.com/api/block/%d" % probe)
        if c != 200 or not b:
            print("    height %-8s HTTP %s — unresolved" % (probe, c))
            continue
        try:
            blk = json.loads(b)
        except Exception:
            print("    height %-8s payload not JSON — void" % probe)
            continue
        t = blk.get("time") or blk.get("timestamp")
        dt = as_utc(t)
        if dt is None:
            print("    height %-8s no time field — void" % probe)
            continue
        print("    height %-8s header time %s UTC   %s"
              % (probe, dt.isoformat(timespec="seconds"),
                 "<- BLOCK EXISTS AT/AFTER THE FREEZE" if dt >= FREEZE else "(before the freeze)"))
        time.sleep(0.4)

print("""
  ⇒ READ THIS BEFORE EDITING THE PAPER:
    a chain producing blocks at the freeze satisfies (2) as well as (1) and (3) — in which case
    the stated rule INCLUDES it, and the honest options are to measure it or to add a fourth
    criterion stated in advance and applied to everything. ⛔ **Do not quietly reword the rule to
    exclude one chain after seeing its answer.** A rule bent to fit the result it produced is not
    a rule, and this paper's entire argument is that the rule comes first.""")
