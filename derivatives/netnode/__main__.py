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
from version import __version__    # noqa: E402


def _hostport(s: str, default_host: str) -> tuple[str, int]:
    if ":" in s:
        host, port = s.rsplit(":", 1)
        return (host or default_host, int(port))
    return (default_host, int(s))


async def _serve(cfg, datadir, listen, connect, advertise, mine, mine_interval, min_bits,
                 wallet, rpc):
    def log(m):
        print(f"[{cfg.key}] {m}", flush=True)

    node = Node(cfg, datadir, listen=listen, advertise_host=advertise, mine=mine,
                mine_interval=mine_interval, min_bits=min_bits, wallet=wallet, log=log)
    print(f"[{cfg.key}] netnode {__version__} up — NOT money — magic={cfg.magic.hex()} "
          f"height={node.height} datadir={datadir}", flush=True)
    if node.wallet is not None:
        print(f"[{cfg.key}] wallet receive address: {node.wallet.addresses()[0].hex()}", flush=True)
    rpc_server = None
    if rpc is not None:
        from rpc import RpcServer
        rpc_host, rpc_port = rpc
        rpc_server = RpcServer(node, host=rpc_host, port=rpc_port, log=log)
        await rpc_server.start()
    await node.start(connect=connect)
    try:
        await asyncio.Event().wait()                 # run until Ctrl-C
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        if rpc_server is not None:
            await rpc_server.stop()
        await node.stop()


def _ctl(argv):
    """Client for a running node's --rpc control interface (one request, print the result)."""
    import json
    import socket
    ap = argparse.ArgumentParser(prog="netnode ctl",
                                 description="Control a running node over its localhost RPC.")
    ap.add_argument("--rpc", required=True, metavar="[HOST:]PORT", help="the node's --rpc address")
    ap.add_argument("method", choices=["getinfo", "getnewaddress", "getprimaryaddress",
                                       "getbalance", "send"])
    ap.add_argument("args", nargs="*", help="send: <to_address_or_pubkey_hex> <amount> [fee]")
    a = ap.parse_args(argv)
    host, port = _hostport(a.rpc, "127.0.0.1")
    req = {"method": a.method, "params": a.args}
    with socket.create_connection((host, port), timeout=15) as s:
        s.sendall((json.dumps(req) + "\n").encode())
        buf = b""
        while b"\n" not in buf:
            chunk = s.recv(4096)
            if not chunk:
                break
            buf += chunk
    resp = json.loads(buf.decode() or "{}")
    if "error" in resp:
        print(f"error: {resp['error']}", file=sys.stderr)
        return 1
    r = resp.get("result")
    print(r if isinstance(r, str) else json.dumps(r, indent=2))
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "ctl":                        # `netnode ctl ...` talks to a running node
        return _ctl(argv[1:])
    ap = argparse.ArgumentParser(prog="netnode",
                                 description="Experimental X-chain node (NOT money).")
    ap.add_argument("--version", action="version",
                    version=f"netnode {__version__} — experimental research node, NOT money")
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
    ap.add_argument("--min-difficulty", default=None, metavar="NBITS",
                    help="network difficulty floor as a compact nBits hex (e.g. 0x1f00ffff); "
                         "harder than the easy genesis, so a live network requires real work. "
                         "All nodes on a network MUST agree on this value.")
    ap.add_argument("--wallet", action="store_true",
                    help="enable an experimental wallet in the datadir; a mining node earns its "
                         "coinbase to it (NOT money)")
    ap.add_argument("--rpc", default=None, metavar="[HOST:]PORT",
                    help="start a localhost control interface on this port (see `netnode ctl`); "
                         "loopback only, no auth — do not expose it")
    args = ap.parse_args(argv)

    cfg = CHAINS[args.chain]
    listen = None if args.no_listen else _hostport(args.listen or str(cfg.port), "0.0.0.0")
    connect = [_hostport(c, "127.0.0.1") for c in args.connect]
    min_bits = int(args.min_difficulty, 0) if args.min_difficulty else None
    rpc = _hostport(args.rpc, "127.0.0.1") if args.rpc else None

    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(_serve(cfg, args.datadir, listen, connect, args.advertise,
                           args.mine, args.mine_interval, min_bits, args.wallet, rpc))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
