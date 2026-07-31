"""A minimal localhost control interface (RPC) for an X-chain node — Path B usability. NOT money.

So a person can operate a running node without writing Python. Line-delimited JSON over a
**127.0.0.1-only** TCP socket: each request is one line `{"method": ..., "params": [...]}` and the
reply is one line `{"result": ...}` or `{"error": ...}`.

**No authentication.** It is bound to loopback only and intended for a *trusted local machine*
(comparable to a cookie-less regtest RPC). Do not expose the RPC port to a network. Methods:

- `getinfo` → chain / height / tip / peers / mempool size / wallet? / money:false
- `getnewaddress` → a fresh receive address (SEC pubkey hex)              [needs --wallet]
- `getprimaryaddress` → your existing primary key (pubkey + '1...' address), mints nothing  [--wallet]
- `getbalance` → spendable balance (mature, owned)                        [needs --wallet]
- `getrecentblocks [count]` → the last N validated blocks (height/hash/time/ntx) — status/explorer
- `send [to, amount, fee?]` → pay a '1...' address (P2PKH) or a pubkey hex (P2PK); returns txid  [--wallet]
- `sendtoscript [script, amount, fee?]` → fund an ARBITRARY scriptPubKey from the wallet; `script`
  is a JSON array of `OP_` names and hex data literals (e.g. a hash-lock or escrow output). returns
  txid  [--wallet]
- `sendrawtransaction [hexstring]` → validate + broadcast a fully signed raw transaction (any script);
  the same submit path a peer's tx takes. returns txid  [no wallet needed]

Together `sendtoscript` (create a contract output from the wallet) and `sendrawtransaction` (submit any
signed spend) let a participant put the full opcode vocabulary on-chain, not only P2PK/P2PKH `send`.

Evidence: MODEL / NEW-EXP.
"""

from __future__ import annotations

import asyncio
import json


def _resolve_recipient(to: str) -> list:
    """A recipient string -> scriptPubKey tokens: a '1...' Base58 address -> P2PKH, otherwise a
    33/65-byte SEC pubkey hex -> bare P2PK. Both are faithful v0.1 payment forms."""
    from base58 import address_to_hash160, is_p2pkh_address
    to = to.strip()
    if is_p2pkh_address(to):
        return ["OP_DUP", "OP_HASH160", address_to_hash160(to), "OP_EQUALVERIFY", "OP_CHECKSIG"]
    try:
        pub = bytes.fromhex(to)
    except ValueError as e:
        raise ValueError("recipient is neither a '1...' address nor a pubkey hex") from e
    if len(pub) not in (33, 65):
        raise ValueError("pubkey must be 33 (compressed) or 65 (uncompressed) bytes")
    return [bytes(pub), "OP_CHECKSIG"]


def _parse_script_tokens(script) -> list:
    """A JSON script -> the internal token list `cscript.assemble` consumes: each element is either an
    `OP_` name (kept as a string) or a hex data literal (decoded to bytes). Accepts a real JSON array
    or, for the CLI, a JSON-encoded string. So any scriptPubKey the interpreter accepts is expressible
    over the wire without writing Python."""
    if isinstance(script, str):
        try:
            script = json.loads(script)
        except json.JSONDecodeError as e:
            raise ValueError("script must be a JSON array of OP_ names and hex data literals") from e
    if not isinstance(script, list) or not script:
        raise ValueError("script must be a non-empty JSON array of OP_ names and hex data literals")
    from cscript import NAME_TO_OP                        # opcode byte table (from the generated inventory)
    out: list = []
    for t in script:
        if not isinstance(t, str):
            raise ValueError(f"script token must be a string, got {type(t).__name__}")
        if t in NAME_TO_OP:
            out.append(t)                                 # an opcode name
        else:
            try:
                out.append(bytes.fromhex(t))              # otherwise a hex data push
            except ValueError as e:
                raise ValueError(f"token {t!r} is neither an OP_ name nor hex data") from e
    return out


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
        if method == "getprimaryaddress":
            self._need_wallet()
            from base58 import hash160, pubkey_to_address
            pub = n.wallet_primary_pubkey()
            return {"pubkey": pub.hex(), "address": pubkey_to_address(pub),
                    "hash160": hash160(pub).hex(), "not_money": True}
        if method == "getrecentblocks":
            count = int(params[0]) if params else 15
            return n.recent_blocks(min(max(count, 1), 100))
        if method == "getbalance":
            self._need_wallet()
            return n.wallet_balance()
        if method == "send":
            self._need_wallet()
            if len(params) < 2:
                raise ValueError("send needs [to, amount, fee?] — to = a '1...' address or a pubkey hex")
            fee = int(params[2]) if len(params) > 2 else 0
            spk = _resolve_recipient(str(params[0]))
            entry = await n.wallet_send_to_script(spk, int(params[1]), fee)
            return entry.txid[::-1].hex()
        if method == "sendtoscript":
            self._need_wallet()
            if len(params) < 2:
                raise ValueError("sendtoscript needs [script, amount, fee?] — script = a JSON array "
                                 "of OP_ names and hex data literals")
            spk = _parse_script_tokens(params[0])
            fee = int(params[2]) if len(params) > 2 else 0
            entry = await n.wallet_send_to_script(spk, int(params[1]), fee)
            return entry.txid[::-1].hex()
        if method == "sendrawtransaction":
            if not params:
                raise ValueError("sendrawtransaction needs [hexstring] — a fully signed raw transaction")
            try:
                raw = bytes.fromhex(str(params[0]).strip())
            except ValueError as e:
                raise ValueError("hexstring is not valid hex") from e
            entry = await n.accept_and_broadcast(raw)
            return entry.txid[::-1].hex()
        raise ValueError(f"unknown method: {method!r}")

    def _need_wallet(self):
        if self.node.wallet is None:
            raise ValueError("no wallet — start the node with --wallet")
