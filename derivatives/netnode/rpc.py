"""A minimal localhost control interface (RPC) for an X-chain node — Path B usability. NOT money.

So a person can operate a running node without writing Python. Line-delimited JSON over a
**127.0.0.1-only** TCP socket: each request is one line `{"method": ..., "params": [...]}` and the
reply is one line `{"result": ...}` or `{"error": ...}`.

**No authentication.** It is bound to loopback only and intended for a *trusted local machine*
(comparable to a cookie-less regtest RPC). Do not expose the RPC port to a network. Methods:

- `getinfo` → chain / height / tip / peers / mempool size / wallet? / money:false
- `getnewaddress` → a fresh receive address (SEC pubkey hex)              [needs --wallet]
- `getbalance` → spendable balance (mature, owned)                        [needs --wallet]
- `send [to_hex, amount, fee?]` → build + submit + broadcast a payment, returns the txid  [--wallet]

Evidence: MODEL / NEW-EXP.
"""

from __future__ import annotations

import asyncio
import json


class RpcServer:
    def __init__(self, node, host: str = "127.0.0.1", port: int = 0, log=None):
        self.node = node
        self.host = host
        self.port = port
        self._log = log or (lambda m: None)
        self._server = None

    async def start(self):
        self._server = await asyncio.start_server(self._handle, self.host, self.port)
        self.port = self._server.sockets[0].getsockname()[1]
        self._log(f"rpc control on {self.host}:{self.port} (localhost only — NOT money)")

    async def stop(self):
        if self._server:
            self._server.close()

    async def _handle(self, reader, writer):
        try:
            while True:
                line = await reader.readline()
                if not line:
                    break
                try:
                    req = json.loads(line)
                    resp = {"result": await self._dispatch(req.get("method"), req.get("params") or [])}
                except Exception as e:                      # noqa: BLE001 — report any error to the caller
                    resp = {"error": str(e)}
                writer.write((json.dumps(resp) + "\n").encode())
                await writer.drain()
        except (ConnectionError, OSError):
            pass
        finally:
            try:
                writer.close()
            except OSError:
                pass

    async def _dispatch(self, method, params):
        n = self.node
        if method == "getinfo":
            return {"chain": n.cfg.key, "height": n.height,
                    "tip": n.tip[::-1].hex() if n.tip else None,
                    "peers": len(n._writers), "mempool": len(n.mempool),
                    "wallet": n.wallet is not None, "money": False}
        if method == "getnewaddress":
            self._need_wallet()
            return n.wallet_new_address().hex()
        if method == "getbalance":
            self._need_wallet()
            return n.wallet_balance()
        if method == "send":
            self._need_wallet()
            if len(params) < 2:
                raise ValueError("send needs [to_hex, amount, fee?]")
            fee = int(params[2]) if len(params) > 2 else 0
            entry = await n.wallet_send(bytes.fromhex(params[0]), int(params[1]), fee)
            return entry.txid[::-1].hex()
        raise ValueError(f"unknown method: {method!r}")

    def _need_wallet(self):
        if self.node.wallet is None:
            raise ValueError("no wallet — start the node with --wallet")
