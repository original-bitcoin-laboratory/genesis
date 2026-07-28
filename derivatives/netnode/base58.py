"""Base58Check 'Bitcoin address' encoding — the v0.1.0 address format. NOT money.

v0.1.0 (`base58.h` / `main.cpp`) turns a public key into an address as
Base58Check([version][hash160(pubkey)][4-byte double-SHA256 checksum]), version **0x00** giving the
familiar `1...` address (`OP_DUP OP_HASH160 <hash> OP_EQUALVERIFY OP_CHECKSIG`, i.e. P2PKH). This is a
**recognisability / UX** layer only: the miner still pays its coinbase as bare P2PK, exactly as v0.1
does. The address format is faithful to the original client; the chains remain valueless experiments
with their own genesis/magic, so an address here can never be a live-Bitcoin address. **Not money.**
"""

from __future__ import annotations

import hashlib

_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_INDEX = {c: i for i, c in enumerate(_ALPHABET)}

ADDRESS_VERSION = 0x00                       # v0.1 pubkey-hash version byte -> '1...' addresses


def _dsha(b: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


def hash160(b: bytes) -> bytes:
    return hashlib.new("ripemd160", hashlib.sha256(b).digest()).digest()


def b58encode(b: bytes) -> str:
    n = int.from_bytes(b, "big")
    out = ""
    while n > 0:
        n, r = divmod(n, 58)
        out = _ALPHABET[r] + out
    pad = len(b) - len(b.lstrip(b"\x00"))    # each leading 0x00 byte -> a leading '1'
    return "1" * pad + out


def b58decode(s: str) -> bytes:
    n = 0
    for ch in s:
        if ch not in _INDEX:
            raise ValueError(f"invalid base58 character {ch!r}")
        n = n * 58 + _INDEX[ch]
    body = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    pad = len(s) - len(s.lstrip("1"))
    return b"\x00" * pad + body


def base58check_encode(version: int, payload: bytes) -> str:
    body = bytes([version]) + payload
    return b58encode(body + _dsha(body)[:4])


def base58check_decode(s: str) -> tuple[int, bytes]:
    raw = b58decode(s)
    if len(raw) < 5:
        raise ValueError("address too short")
    body, checksum = raw[:-4], raw[-4:]
    if _dsha(body)[:4] != checksum:
        raise ValueError("bad address checksum")
    return body[0], body[1:]


def pubkey_to_address(sec: bytes) -> str:
    """A SEC public key -> its '1...' P2PKH address."""
    return base58check_encode(ADDRESS_VERSION, hash160(sec))


def address_to_hash160(addr: str) -> bytes:
    """A '1...' P2PKH address -> the 20-byte hash160 it commits to (raises if malformed)."""
    ver, h160 = base58check_decode(addr)
    if ver != ADDRESS_VERSION:
        raise ValueError(f"unexpected address version 0x{ver:02x} (want 0x{ADDRESS_VERSION:02x})")
    if len(h160) != 20:
        raise ValueError("not a 20-byte pubkey-hash address")
    return h160


def is_p2pkh_address(s: str) -> bool:
    """True iff `s` parses as a valid version-0x00 P2PKH address (checksum + length)."""
    try:
        address_to_hash160(s)
        return True
    except (ValueError, KeyError):
        return False
