"""A stand-in for the frozen 2009 node: the from-spec validator behind the 2009 wire protocol.

    python fake2009.py [--port 18333] [--easy] [--log debug.log]

It speaks exactly what wire01.Peer speaks, validates with verify_vectors.Chain2009, keeps a relay
pool the way mapRelay does, answers getblocks/getdata as main.cpp:1795-1866 do, and writes 2009-style
lines to a debug.log. It exists so the replay harness can be run end-to-end here before it is pointed at
the real bitcoin.exe in the VM; it is NOT the binary and proves nothing about it. NOT money.
"""
from __future__ import annotations

import argparse
import pathlib
import socket
import sys
import threading
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import verify_vectors as spec                                  # noqa: E402
import recipes                                                 # noqa: E402
from wire01 import (MAGIC_2009, MSG_BLOCK, MSG_TX, frame, getblocks_payload, inv_payload, parse_inv,   # noqa: E402
                    read_varint, version_payload)


def model_spend_verifier():
    """The lab's full-vocabulary EvalScript (../model) as a VerifySignature hook, when importable; None
    otherwise, in which case the from-spec subset applies and full-vocabulary spends are rejected as
    'unsupported' rather than graded."""
    try:
        sys.path.insert(0, str(HERE.parent.parent / "model"))
        import cscript                                                  # noqa: E402
        from spend import verify_spend as model_verify_spend            # noqa: E402
        from tx_sighash import Tx, TxIn, TxOut                          # noqa: E402
    except Exception:                                                   # noqa: BLE001
        return None

    def verifier(script_sig: bytes, script_pubkey: bytes, tx: dict, n_in: int) -> bool:
        ltx = Tx(tx["version"], [TxIn(v["prevhash"], v["n"], v["script"], v["seq"]) for v in tx["vin"]],
                 [TxOut(o["value"], o["script"]) for o in tx["vout"]], tx["locktime"])
        try:
            return bool(model_verify_spend(cscript.parse(script_sig), cscript.parse(script_pubkey), ltx, n_in))
        except Exception:                                               # noqa: BLE001 — a parse failure is "invalid"
            return False
    return verifier


class Fake2009:
    def __init__(self, genesis_raw: bytes, pow_limit_nbits: int, log_path: pathlib.Path | None = None,
                 port: int = 0, host: str = "127.0.0.1"):
        gh = spec.dsha256(genesis_raw[:80])
        self.chain = spec.Chain2009(pow_limit_nbits, gh)
        self.chain.spend_verifier = model_spend_verifier()
        r = self.chain.process_block(genesis_raw)
        assert r["verdict"] == "accept", r
        self.relay: dict[bytes, bytes] = {}                # txid -> raw tx (mapRelay)
        self.blocks: dict[bytes, bytes] = {}               # every block in the index, raw
        self.blocks[gh] = genesis_raw
        self.lock = threading.Lock()
        self.peers: list[socket.socket] = []
        self.log_path = log_path
        self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind((host, port))
        self.srv.listen(8)
        self.port = self.srv.getsockname()[1]
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._accept_loop, daemon=True)
        self.thread.start()

    # ---- logging in the 2009 style ----------------------------------------------------------
    def _flush_log(self) -> None:
        if self.log_path and self.chain.log:
            with open(self.log_path, "a", encoding="utf-8") as f:
                for line in self.chain.log:
                    f.write(line + "\n")
            self.chain.log.clear()

    # ---- networking ---------------------------------------------------------------------------
    def _accept_loop(self) -> None:
        self.srv.settimeout(0.5)
        while not self.stop.is_set():
            try:
                c, _ = self.srv.accept()
            except socket.timeout:
                continue
            threading.Thread(target=self._serve, args=(c,), daemon=True).start()

    def _send(self, c: socket.socket, cmd: str, payload: bytes) -> None:
        try:
            c.sendall(frame(cmd, payload))
        except OSError:
            pass

    def _broadcast_inv(self, items, exclude) -> None:
        for p in list(self.peers):
            if p is not exclude:
                self._send(p, "inv", inv_payload(items))

    def _serve(self, c: socket.socket) -> None:
        with self.lock:
            self.peers.append(c)
        self._send(c, "version", version_payload(int(time.time())))
        buf = b""
        have_version = False
        try:
            while not self.stop.is_set():
                c.settimeout(0.5)
                try:
                    chunk = c.recv(1 << 16)
                except socket.timeout:
                    continue
                if not chunk:
                    break
                buf += chunk
                while len(buf) >= 20:
                    if buf[:4] != MAGIC_2009:
                        return
                    size = int.from_bytes(buf[16:20], "little")
                    if len(buf) < 20 + size:
                        break
                    cmd = buf[4:16].rstrip(b"\x00").decode("latin-1")
                    payload = buf[20:20 + size]
                    buf = buf[20 + size:]
                    if cmd == "version":
                        have_version = True
                    elif not have_version:
                        continue
                    else:
                        self._handle(c, cmd, payload)
        finally:
            with self.lock:
                if c in self.peers:
                    self.peers.remove(c)
            c.close()

    def _handle(self, c: socket.socket, cmd: str, payload: bytes) -> None:
        with self.lock:
            if cmd == "getdata":
                for typ, h in parse_inv(payload):
                    if typ == MSG_BLOCK and h in self.blocks:
                        self._send(c, "block", self.blocks[h])
                    elif typ == MSG_TX and h in self.relay:
                        self._send(c, "tx", self.relay[h])
            elif cmd == "getblocks":
                # CBlockLocator: nVersion + vector<uint256>, then hashStop
                n, i = read_varint(payload, 4)
                locator = [payload[i + 32 * k:i + 32 * (k + 1)] for k in range(n)]
                start = 0
                for h in locator:
                    e = self.chain.index.get(h)
                    if e and e["main"]:
                        start = e["height"] + 1
                        break
                after = self.chain.main[start:]
                if after:
                    self._send(c, "inv", inv_payload([(MSG_BLOCK, h) for h in after]))
            elif cmd == "tx":
                try:
                    ok, _reason = self.chain.accept_tx(payload)
                except spec.Unsupported as e:
                    ok = False
                    self.chain.log.append(f"ERROR: fake2009 cannot evaluate this script ({e})")
                self._flush_log()
                if ok:
                    h = spec.dsha256(payload)
                    self.relay[h] = payload
                    self._broadcast_inv([(MSG_TX, h)], exclude=c)
            elif cmd == "block":
                try:
                    r = self.chain.process_block(payload)
                except spec.Unsupported as e:
                    self.chain.log.append(f"ERROR: fake2009 cannot evaluate this block ({e})")
                    self._flush_log()
                    return
                self._flush_log()
                if r["verdict"] in ("accept", "side") or r["stage"] == "ConnectBlock":
                    self.blocks[r["hash"]] = payload             # in mapBlockIndex even when ConnectBlock failed
                if r["verdict"] == "accept":
                    self._broadcast_inv([(MSG_BLOCK, r["hash"])], exclude=c)

    def close(self) -> None:
        self.stop.set()
        self.thread.join(timeout=2)
        self.srv.close()


def easy_genesis(nbits: int = 0x207FFFFF, t0: int = 1_700_000_000) -> bytes:
    cb = recipes.make_coinbase(0, [(50 * spec.COIN, recipes.OP_TRUE_SCRIPT)], b"fake2009 genesis")
    return recipes.assemble_block(recipes.ZERO32, [cb], t0, nbits, recipes.easy_mine)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=18333)
    ap.add_argument("--easy", action="store_true", help="pow limit 0x207fffff (default: 0x1d00ffff)")
    ap.add_argument("--log", default="fake2009-debug.log")
    a = ap.parse_args()
    nb = 0x207FFFFF if a.easy else 0x1D00FFFF
    node = Fake2009(easy_genesis(nb), nb, pathlib.Path(a.log), a.port)
    print(f"fake2009 listening on {node.port}, genesis {node.chain.genesis_hash[::-1].hex()}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        node.close()
