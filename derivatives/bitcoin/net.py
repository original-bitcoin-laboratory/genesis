"""Bitcoin (Aug 2026) — network identity + the fixed genesis, for the hardened netnode transport.

This chain is NOT one of the lab's X-chains. NOV08-X / JAN09-X *mint* a fresh regtest-easy genesis
on demand so demos mine instantly; this one has a single, already-mined genesis at the ORIGINAL
difficulty-1 (nBits 0x1d00ffff), hardcoded here exactly the way a real client hardcodes block 0.
It is the same genesis the patched v0.1.0 client asserts on startup (`make_chain.py`), so the 2009
binary and this node agree on block 0 byte-for-byte or neither starts.

  genesis   00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a
  coinbase  The Times 03/Aug/2026 Toll of schooling 'straitjacket'
            -- the front page of the day it was mined: a proof of time, the same function Satoshi's
               headline served for his, rather than a copy of his words
  output    50 -> P2PK 04c0414c…  (the author's key; no value assigned)
  nTime     1785781375 = 2026-08-03 18:22:55 UTC        nNonce 33394338

Network identity is the ONLY thing separating this from mainnet's wire: distinct magic and port, as
NOV08-X (f00ba708/18008) and JAN09-X (f00ba709/18009) do. Consensus is untouched v0.1.0.

Not money. Experimental.
"""

from __future__ import annotations

import hashlib
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "p2p"))
sys.path.insert(0, str(_HERE.parent / "model"))
sys.path.insert(0, str(_HERE.parent / "nov08x"))
from chainsync import Chain                                  # noqa: E402
from consensus import Rules                                  # noqa: E402

# ---- network identity (this is what makes it a separate network) -------------
BITCOIN_MAGIC = b"\xf0\x0b\xa7\x26"       # mainnet f9beb4d9 · NOV08-X f00ba708 · JAN09-X f00ba709
BITCOIN_PORT = 18026
BITCOIN_GENESIS_MESSAGE = b"The Times 03/Aug/2026 Toll of schooling 'straitjacket'"

# ---- the genesis, fixed forever ---------------------------------------------
BITCOIN_GENESIS_HASH = "00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a"
BITCOIN_GENESIS_TIME = 1785781375
BITCOIN_GENESIS_NONCE = 33394338
BITCOIN_GENESIS_BITS = 0x1D00FFFF          # real difficulty-1, as Satoshi's was
BITCOIN_PUBKEY = ("04c0414cfdcc009830708543b06e43a03570dc1ffa45ddf98657045e594a815eba7"
                  "94ca0602e8527d7ba3197e53c0c2f226892212aa99b827e8e2fd95fcea2f834")

GENESIS_RAW = bytes.fromhex(
    "01000000"                                                          # version 1
    "0000000000000000000000000000000000000000000000000000000000000000"  # prev = 0
    "8580a3211e4e3a77f12db073dd7fc6815751b8aa7599db46a675406cfdbda5aa"  # merkle (internal order)
    "7fdc706a"                                                          # nTime  1785781375
    "ffff001d"                                                          # nBits  0x1d00ffff
    "a28efd01"                                                          # nNonce 33394338
    "01"                                                                # 1 transaction
    "01000000010000000000000000000000000000000000000000000000000000000000000000ffffffff"
    "3e04ffff001d0104365468652054696d65732030332f4175672f3230323620546f6c6c206f66207363"
    "686f6f6c696e6720277374726169746a61636b657427ffffffff0100f2052a010000004341"
    "04c0414cfdcc009830708543b06e43a03570dc1ffa45ddf98657045e594a815eba794ca0602e8527d7b"
    "a3197e53c0c2f226892212aa99b827e8e2fd95fcea2f834ac00000000")

_RULES = Rules.load("jan09")               # v0.1.0's released constitution, unmodified


def _dsha(b: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


def mint_genesis() -> bytes:
    """The genesis block. Not mined on demand -- it was mined once, at real difficulty-1, and is
    fixed. Re-verified here on every call so a corrupted constant can never reach the network."""
    h = _dsha(GENESIS_RAW[:80])[::-1].hex()
    if h != BITCOIN_GENESIS_HASH:
        raise SystemExit(f"genesis constant corrupted: hashes to {h}")
    target = (BITCOIN_GENESIS_BITS & 0xFFFFFF) << (8 * ((BITCOIN_GENESIS_BITS >> 24) - 3))
    if int(h, 16) > target:
        raise SystemExit("genesis does not meet its own difficulty-1 target")
    return GENESIS_RAW


def new_chain() -> Chain:
    return Chain()                          # v0.1.0 compact PoW, unmodified


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    g = mint_genesis()
    print(f"chain    : Bitcoin (Aug 2026)")
    print(f"genesis  : {BITCOIN_GENESIS_HASH}  ✓ verified, meets difficulty-1")
    print(f"coinbase : {BITCOIN_GENESIS_MESSAGE.decode()}")
    print(f"magic    : {BITCOIN_MAGIC.hex()}   port {BITCOIN_PORT}   block {len(g)} bytes")
