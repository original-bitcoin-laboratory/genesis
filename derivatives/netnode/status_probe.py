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


async def _read_until(reader, magic, want_command, timeout, tries=12, ck=True):
    """Read framed messages until one matches `want_command` (skipping version/addr/tx/…)."""
    for _ in range(tries):
        command, payload = await asyncio.wait_for(read_message(reader, magic, checksum=ck), timeout)
        if command == want_command:
            return payload
    return None


async def _walk_height(reader, writer, magic, genesis, timeout, ck=True):
    """getblocks-walk from genesis to the tip; return the ordered block hashes after genesis.
    The node answers a getblocks with an `inv` only when it has blocks to offer, so 'no inv' (a
    timeout) means we've reached the tip — not a failure."""
    hashes: list = []
    seen: set = set()
    locator = [genesis]
    for _ in range(200):                                     # safety bound
        writer.write(frame("getblocks", locator_payload(locator), magic, checksum=ck))
        await writer.drain()
        try:
            payload = await _read_until(reader, magic, "inv", timeout, ck=ck)
        except asyncio.TimeoutError:
            break                                            # no more blocks -> reached the tip
        page = [h for (t, h) in parse_inv(payload or b"") if t == MSG_BLOCK and h not in seen]
        if not page:
            break
        seen.update(page)
        hashes += page
        locator = [page[-1]]
    return hashes


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
        hashes = await _walk_height(reader, writer, magic, genesis, timeout, ck=ck)
        recent = await _recent(reader, writer, magic, hashes[-recent_n:], len(hashes), timeout, ck=ck)
        return hashes, recent
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
    best = None
    for a, res in zip(anchors, results):
        entry["anchors"].append({"ip": a, "reachable": res is not None})
        if res is not None and (best is None or len(res[0]) > len(best[0])):
            best = res
    entry["reachable_anchors"] = sum(1 for a in entry["anchors"] if a["reachable"])
    if best is not None:
        hashes, recent = best
        entry.update({"online": True, "height": len(hashes),
                      "tip": hashes[-1][::-1].hex() if hashes else genesis[::-1].hex(),
                      "recent": recent})
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
    ap.add_argument("--timeout", type=float, default=10.0)
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
