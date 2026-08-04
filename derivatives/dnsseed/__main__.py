"""Run a DNS seed for an experimental X-chain.  **NOT money.**

    python -m dnsseed --chain jan09x --zone seed.example.test \
                      --seed SEED_HOST:18009 --listen 0.0.0.0:5354

Crawls the network from the given seed node(s), keeps a live set of reachable peers, and answers
`A` queries for `--zone` with their IPs — the bootstrap a fresh node uses to find its first peers.
Port 53 needs privileges; a high port behind an NS delegation works for a real deployment.
"""

from __future__ import annotations

import argparse
import asyncio
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent / "netnode"))

from chains import CHAINS                          # noqa: E402
from crawler import Crawler                        # noqa: E402
from server import serve                           # noqa: E402


def _hostport(s: str, default_host: str, default_port: int):
    if ":" in s:
        host, port = s.rsplit(":", 1)
        return (host or default_host, int(port))
    return (default_host, int(s)) if s.isdigit() else (s, default_port)


async def _run(cfg, zone, seeds, listen, interval):
    def log(m):
        print(f"[dnsseed:{cfg.key}] {m}", flush=True)

    crawler = Crawler(cfg.magic, cfg.port, seeds)
    # Bind each requested address. A dual-stack seed needs one endpoint per family: binding
    # `::` would also claim IPv4 on this host and collide with systemd-resolved's 127.0.0.53.
    transports = []
    for host in listen[0]:
        transports.append(await serve(host, listen[1], zone, crawler.healthy_hosts, log=log))
    transport = transports[0]
    where = ", ".join(f"{t.get_extra_info('sockname')[0]}:{t.get_extra_info('sockname')[1]}"
                      for t in transports)
    log(f"authoritative for {zone!r} on {where} — NOT money")

    async def crawl_loop():
        while True:
            healthy = await crawler.crawl_once()
            log(f"crawl: {len(healthy)} healthy / {len(crawler.known)} known")
            await asyncio.sleep(interval)

    task = asyncio.create_task(crawl_loop())
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        task.cancel()
        transport.close()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="dnsseed", description="Experimental X-chain DNS seed (NOT money).")
    ap.add_argument("--chain", required=True, choices=list(CHAINS))
    ap.add_argument("--zone", required=True, help="the seed hostname we answer A/AAAA queries for")
    ap.add_argument("--seed", action="append", default=[], required=True,
                    help="host:port of a known node to crawl from (repeatable)")
    ap.add_argument("--listen", default="0.0.0.0:5354",
                    help="UDP host:port to bind; comma-separate hosts to serve both families, "
                         "e.g. 203.0.113.9,2001:db8::9:53")
    ap.add_argument("--interval", type=float, default=60.0, help="seconds between crawls")
    args = ap.parse_args(argv)

    cfg = CHAINS[args.chain]
    seeds = [_hostport(s, "127.0.0.1", cfg.port) for s in args.seed]
    lh, lp = args.listen.rsplit(":", 1)
    listen = ([h.strip() for h in lh.split(",") if h.strip()] or ["0.0.0.0"], int(lp))

    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(_run(cfg, args.zone.lower().rstrip("."), seeds, listen, args.interval))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
