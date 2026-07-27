"""Run an experimental X-chain node.  **NOT money.**

    python -m netnode --chain jan09x --datadir ./data --listen 0.0.0.0:18009
    python -m netnode --chain jan09x --datadir ./data --connect SEED_HOST:18009 --mine

Two people on different machines: one runs with `--mine` and shares its `host:port`; the
other passes it via `--connect`. See ../../docs/PUBLIC_TESTNET_SCOPE.md for the honest scope
(this is Stage 1 — experimental, non-monetary, and not production-secure).
"""

from __future__ import annotations

import argparse
import asyncio
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from chains import CHAINS          # noqa: E402
from livenode import Node          # noqa: E402


def _hostport(s: str, default_host: str) -> tuple[str, int]:
    if ":" in s:
        host, port = s.rsplit(":", 1)
        return (host or default_host, int(port))
    return (default_host, int(s))


async def _serve(cfg, datadir, listen, connect, advertise, mine, mine_interval):
    def log(m):
        print(f"[{cfg.key}] {m}", flush=True)

    node = Node(cfg, datadir, listen=listen, advertise_host=advertise,
                mine=mine, mine_interval=mine_interval, log=log)
    print(f"[{cfg.key}] node up — NOT money — magic={cfg.magic.hex()} "
          f"height={node.height} datadir={datadir}", flush=True)
    await node.start(connect=connect)
    try:
        await asyncio.Event().wait()                 # run until Ctrl-C
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await node.stop()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="netnode",
                                 description="Experimental X-chain node (NOT money).")
    ap.add_argument("--chain", required=True, choices=list(CHAINS))
    ap.add_argument("--datadir", required=True)
    ap.add_argument("--listen", default=None,
                    help="host:port to bind (default 0.0.0.0:<chain default port>)")
    ap.add_argument("--no-listen", action="store_true", help="outbound-only node")
    ap.add_argument("--connect", action="append", default=[],
                    help="host:port of a peer to connect to (repeatable)")
    ap.add_argument("--advertise", default=None,
                    help="this node's reachable host, gossiped to peers (default: the listen host)")
    ap.add_argument("--mine", action="store_true", help="mine blocks")
    ap.add_argument("--mine-interval", type=float, default=2.0)
    args = ap.parse_args(argv)

    cfg = CHAINS[args.chain]
    listen = None if args.no_listen else _hostport(args.listen or str(cfg.port), "0.0.0.0")
    connect = [_hostport(c, "127.0.0.1") for c in args.connect]

    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(_serve(cfg, args.datadir, listen, connect, args.advertise,
                           args.mine, args.mine_interval))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
