"""Chain configuration + a generic miner for the experimental X-chain nodes.

Reuses each X-chain's own identity and consensus (magic, port, genesis, PoW) from
`../nov08x/net.py` and `../jan09x/net.py` — the netnode only adds the *hardened transport*
and *persistence* around that faithful consensus. The two `net.py` files share a name, so
they are loaded under distinct module names via importlib. `mine_next` brute-forces a nonce
at the **genesis difficulty** (regtest-easy — a real retarget is Stage 2), building a unique
coinbase block on the tip. Evidence: MODEL / NEW-EXP.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import time

_HERE = pathlib.Path(__file__).resolve().parent
_DERIV = _HERE.parent
for _p in ("model", "p2p", "nov08x"):
    sys.path.insert(0, str(_DERIV / _p))

from tx_sighash import Tx, TxIn, TxOut          # noqa: E402
from p2p import block_bytes, merkle_root        # noqa: E402
from chainsync import ZERO                      # noqa: E402
from consensus import Rules                     # noqa: E402


def _load(name: str, relpath: str):
    spec = importlib.util.spec_from_file_location(name, _DERIV / relpath)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_NX = _load("obl_nov08x_net", "nov08x/net.py")
_JX = _load("obl_jan09x_net", "jan09x/net.py")


class ChainConfig:
    def __init__(self, key, magic, port, new_chain, mint_genesis, genesis_msg, rules):
        self.key = key
        self.magic = magic
        self.port = port
        self._new_chain = new_chain
        self._mint = mint_genesis
        self.genesis_msg = genesis_msg
        self.rules = rules                    # consensus.Rules — for the difficulty retarget math

    def new_chain(self):
        return self._new_chain()

    def mint_genesis(self):
        return self._mint()


CHAINS: dict[str, ChainConfig] = {
    "nov08x": ChainConfig("nov08x", _NX.NOV08X_MAGIC, _NX.NOV08X_PORT,
                          _NX.new_chain, _NX.mint_genesis, _NX.NOV08X_GENESIS_MESSAGE,
                          Rules.load("nov08")),
    "jan09x": ChainConfig("jan09x", _JX.JAN09X_MAGIC, _JX.JAN09X_PORT,
                          _JX.new_chain, _JX.mint_genesis, _JX.JAN09X_GENESIS_MESSAGE,
                          Rules.load("jan09")),
}

_tag = [0]


def mine_next(prev: bytes, height: int, nbits: int, check_fn,
              subsidy: int = 50 * 100_000_000, msg: bytes = b"") -> bytes:
    """Pure miner (safe to run in an executor): build a unique coinbase block on `prev` at
    `nbits` difficulty, claiming exactly `subsidy` in the coinbase (so it passes the chain's
    coinbase-value rule), and brute-force a nonce until `check_fn(raw)` (the chain's PoW)."""
    _tag[0] = (_tag[0] + 1) & 0xFFFFFF
    cb = Tx(1, [], [], 0)
    script = (bytes([len(msg)]) + msg if msg else b"") + bytes(
        [height & 0xFF, (height >> 8) & 0xFF, _tag[0] & 0xFF, (_tag[0] >> 8) & 0xFF])
    cb.vin.append(TxIn(ZERO, 0xFFFFFFFF, script, 0xFFFFFFFF))
    cb.vout.append(TxOut(subsidy, b"\x51"))                   # OP_1 placeholder; claims the subsidy
    mr = merkle_root([cb])
    t = int(time.time())
    for nonce in range(1 << 28):
        raw = block_bytes(1, prev, mr, t, nbits, nonce, [cb])
        if check_fn(raw):
            return raw
    raise RuntimeError("no nonce found in range")
