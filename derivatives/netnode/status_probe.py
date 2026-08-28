"""Probe the public X-chain anchors over their own P2P protocol and emit a status.json — anchor
reachability, each chain's tip height, and the most recent blocks — for the public status page and
lightweight explorer. Read-only; uses the lab's own wire code; needs no RPC, no box access, no
secrets. Runs in CI (scheduled) or locally. NOT money.

    python status_probe.py --out status.json \
        --chain jan09x:18009 --chain nov08x:18008 \
        --anchor 143.110.255.205 --anchor 178.62.236.102
"""

from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import sys
from datetime import datetime, timezone

_HERE = pathlib.Path(__file__).resolve().parent
for _p in ("model", "p2p", "nov08x"):
    sys.path.insert(0, str(_HERE.parent / _p))
sys.path.insert(0, str(_HERE))

from chains import CHAINS                                              # noqa: E402
from chainsync import block_hash, locator_payload, read_compact       # noqa: E402
from p2p import MSG_BLOCK, inv_payload, parse_inv, version_payload    # noqa: E402
from wire import frame, read_message                                  # noqa: E402


# ~500 hashes per inv, so this must comfortably exceed tip_height/500 for the longest chain
# we run. jan09x passed 90,000 blocks in August 2026; 200 pages was already too tight.
MAX_WALK_PAGES = 4000


async def _read_until(reader, magic, want_command, timeout, tries=12, ck=True):
    """Read framed messages until one matches `want_command` (skipping version/addr/tx/…)."""
    for _ in range(tries):
        command, payload = await asyncio.wait_for(read_message(reader, magic, checksum=ck), timeout)
        if command == want_command:
            return payload
    return None


async def _walk_height(reader, writer, magic, genesis, timeout, ck=True):
    """getblocks-walk from genesis. Returns (hashes, complete).

    ⛔ THE OLD VERSION TREATED A TIMEOUT AS "reached the tip -- not a failure", AND PUBLISHED THE
       RESULT AS A HEIGHT. On 28 Aug 2026 that made status.json report jan09x height 0 and nov08x
       height 0 while the nodes were in fact at 90,246 and 67,347 and actively mining -- because a
       first-read timeout returns an empty list and len([]) is 0. An empty chain and an unread
       chain were written identically, so the public page understated a month of mining as nothing.

       A timeout is NOT evidence of a tip. The only sound tip signal is the peer ANSWERING with an
       inv that carries no hash we have not already seen. Anything else -- a timeout, a dropped
       connection, or exhausting the iteration bound -- leaves the height UNMEASURED, and an
       unmeasured height must not be published as a number.

       The bound also has to fit the chains we actually run: at ~500 hashes per inv a 90k-block
       chain needs ~181 pages, so 200 left no margin at all on a node that mines every 30s and
       drops peers under load.
    """
    hashes: list = []
    seen: set = set()
    locator = [genesis]
    complete = False
    for _ in range(MAX_WALK_PAGES):
        writer.write(frame("getblocks", locator_payload(locator), magic, checksum=ck))
        await writer.drain()
        try:
            payload = await _read_until(reader, magic, "inv", timeout, ck=ck)
        except asyncio.TimeoutError:
            # This server sends NOTHING when it has no blocks to offer (livenode.py: `if invs:`),
            # so a timeout after we have already received a page IS the tip -- the original
            # docstring was right about that. What it got wrong is the case below: a timeout with
            # ZERO pages received means we never read the chain at all, and that is not a height.
            complete = bool(hashes)
            break
        if payload is None:
            break                                            # peer never sent an inv
        page = [h for (t, h) in parse_inv(payload) if t == MSG_BLOCK and h not in seen]
        if not page:
            complete = True                                  # peer answered, nothing new: the tip
            break
        seen.update(page)
        hashes += page
        locator = [page[-1]]
    return hashes, complete


async def _recent(reader, writer, magic, want, tip_height, timeout, ck=True):
    """getdata the last blocks and summarise them (height/hash/time/ntx), newest first."""
    if not want:
        return []
    writer.write(frame("getdata", inv_payload([(MSG_BLOCK, h) for h in want]), magic, checksum=ck))
    await writer.drain()
    got: dict = {}
    for _ in range(len(want) * 2 + 8):
        try:
            command, payload = await asyncio.wait_for(read_message(reader, magic, checksum=ck), timeout)
        except asyncio.TimeoutError:
            break
        if command == "block":
            got[block_hash(payload)] = payload
            if len(got) >= len(want):
                break
    out = []
    for i, h in enumerate(want):
        raw = got.get(h)
        if not raw:
            continue
        try:
            ntx, _ = read_compact(raw, 80)
        except (IndexError, ValueError):
            ntx = 0
        out.append({"height": tip_height - (len(want) - 1 - i), "hash": h[::-1].hex(),
                    "time": int.from_bytes(raw[68:72], "little"), "ntx": int(ntx), "bytes": len(raw)})
    out.reverse()                                            # newest first
    return out


async def _probe_anchor(host, port, magic, genesis, recent_n, timeout, ck=True):
    """Handshake + height-walk + recent blocks from one anchor. Returns (hashes, recent) or None."""
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout)
    except (OSError, asyncio.TimeoutError):
        return None
    try:
        writer.write(frame("version", version_payload(), magic, checksum=ck))
        await writer.drain()
        if await _read_until(reader, magic, "version", timeout, ck=ck) is None:
            return None                                      # wrong chain / not a node
        hashes, complete = await _walk_height(reader, writer, magic, genesis, timeout, ck=ck)
        recent = await _recent(reader, writer, magic, hashes[-recent_n:], len(hashes), timeout, ck=ck)
        return hashes, recent, complete
    except (OSError, asyncio.TimeoutError, ValueError, ConnectionError):
        return None
    finally:
        try:
            writer.close()
        except OSError:
            pass


async def probe_chain(name, port, anchors, recent_n, timeout):
    cfg = CHAINS[name]
    genesis = block_hash(cfg.mint_genesis())
    entry = {"chain": name, "p2p_port": port, "genesis": genesis[::-1].hex(),
             "anchors": [], "online": False, "money": False}
    ck = getattr(cfg, "wire_checksum", True)      # a v0.1-framed chain has no checksum field
    results = await asyncio.gather(*(_probe_anchor(a, port, cfg.magic, genesis, recent_n, timeout, ck=ck)
                                     for a in anchors))
    best, any_reachable = None, False
    for a, res in zip(anchors, results):
        entry["anchors"].append({"ip": a, "reachable": res is not None,
                                 "walk_complete": bool(res[2]) if res is not None else False})
        if res is not None:
            any_reachable = True
            # only a COMPLETED walk may set the height; among completed walks take the longest
            if res[2] and (best is None or len(res[0]) > len(best[0])):
                best = res
    entry["reachable_anchors"] = sum(1 for a in entry["anchors"] if a["reachable"])
    entry["online"] = any_reachable
    if best is not None:
        hashes, recent, _ = best
        entry.update({"height": len(hashes),
                      "tip": hashes[-1][::-1].hex() if hashes else genesis[::-1].hex(),
                      "recent": recent})
    elif any_reachable:
        # ⛔ The node answered but we could not read it to the end. Publishing len(hashes) here is
        #    what reported 90,246 blocks as 0. Omit `height` entirely: the status page writes a
        #    number only when `typeof height === "number"`, so it renders an em dash instead of a
        #    figure that is not a measurement.
        entry["height_unmeasured"] = True
    return entry


async def _run(chains, anchors, recent_n, timeout):
    out = {}
    for name, port, pinned in chains:
        out[name] = await probe_chain(name, port, pinned or anchors, recent_n, timeout)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="probe X-chain anchors, emit status.json (NOT money)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--chain", action="append", required=True, metavar="name:p2pport[@ip,ip]",
                    help="e.g. jan09x:18009, or bitcoin:18026@168.144.27.117 to probe a chain only "
                         "on its own anchors (repeatable)")
    ap.add_argument("--anchor", action="append", required=True, help="anchor IP (repeatable)")
    ap.add_argument("--recent", type=int, default=15)
    ap.add_argument("--timeout", type=float, default=90.0,
                    help="per-read timeout. blocks_after() sends the ENTIRE remainder of "
                         "the chain in ONE inv (no paging), so at 90k blocks that is a "
                         "~3.1 MB message; 10s was not enough to receive it and the walk "
                         "timed out into a false height of 0.")
    a = ap.parse_args(argv)
    # A chain may pin its own anchors with @ip[,ip]. Without it, the chain is probed on every
    # --anchor. Chains that do not share hosts (an independent chain on its own seed) must pin
    # theirs, or every other anchor reports it unreachable and the page shows a false outage.
    chains = []
    for c in a.chain:
        spec, _, pinned = c.partition("@")
        name, port = spec.split(":")
        chains.append((name, int(port), [x for x in pinned.split(",") if x] or None))

    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    chain_status = asyncio.run(_run(chains, a.anchor, a.recent, a.timeout))

    status = {"not_money": True,
              "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "anchors": a.anchor, "chains": chain_status}
    p = pathlib.Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(status, indent=2), encoding="utf-8")
    tmp.replace(p)
    summary = ", ".join(f"{n}={'h' + str(c['height']) if c.get('online') else 'offline'}"
                        for n, c in chain_status.items())
    print(f"wrote {a.out}: {summary}")


if __name__ == "__main__":
    main()
