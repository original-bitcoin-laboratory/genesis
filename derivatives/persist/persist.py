"""MODEL of Bitcoin v0.1 persistence (derivative) — the save/reload that lets a
node shut down and resume at the same tip with the same wallet. Anchored to
db.cpp / db.h / main.h of the v0.1.0 release:

- block index on disk = `CDiskBlockIndex` keyed by `("blockindex", hashBlock)`
  (db.cpp:282), plus the best-chain pointer `"hashBestChain"` (db.cpp:297). The
  record layout is faithful (main.h:1151):
      [nVersion:i32][hashNext:u256][nFile:u32][nBlockPos:u32][nHeight:i32]
      [block nVersion:i32][hashPrev:u256][hashMerkleRoot:u256][nTime:u32]
      [nBits:u32][nNonce:u32]                              (= 128 bytes)
- `CTxDB::LoadBlockIndex` (db.cpp:322) rebuilds the tree: InsertBlockIndex per hash,
  re-wire `pprev`/`pnext` by hash, then `pindexBest = mapBlockIndex[hashBestChain]`,
  `nBestHeight = pindexBest->nHeight`.
- wallet keys = `CWalletDB` records `("key", vchPubKey) -> CPrivKey` (db.h:378-384,
  written by AddKey, main.cpp:72).

What is faithful here: the **record key/value contents** and the LoadBlockIndex
reconstruction. What is NOT reproduced: the Berkeley DB 4.x engine and its `.dat`
container — records live in a simple length-prefixed key/value file (`DiskStore`),
and blocks are kept in a `("block", hash)` record standing in for `blk*.dat` at
`(nFile, nBlockPos)`. Evidence level: MODEL.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "p2p"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "wallet"))
from chainsync import ZERO, BlockIndex, Chain, block_hash, nbits_of, prev_hash  # noqa: E402
from wallet import Coin, Wallet, hash160                                        # noqa: E402


def _u32(n: int) -> bytes:
    return int(n).to_bytes(4, "little")


def _i32(n: int) -> bytes:
    return int(n).to_bytes(4, "little", signed=True)


# ---- a length-prefixed key/value container (stands in for the BDB file) -------

class DiskStore:
    """[keylen:u32][key][vallen:u32][val] records. Keys are bytes; the typed
    record keys below mirror the v0.1 DB keys (a serialized ("type", id) pair)."""

    def __init__(self):
        self.recs: dict[bytes, bytes] = {}

    def put(self, key: bytes, val: bytes):
        self.recs[key] = val

    def get(self, key: bytes):
        return self.recs.get(key)

    def items_of_type(self, prefix: bytes):
        return [(k, v) for k, v in self.recs.items() if k.startswith(prefix)]

    def to_bytes(self) -> bytes:
        out = bytearray()
        for k, v in self.recs.items():
            out += _u32(len(k)) + k + _u32(len(v)) + v
        return bytes(out)

    @classmethod
    def from_bytes(cls, blob: bytes) -> "DiskStore":
        s = cls(); i = 0
        while i < len(blob):
            kl = int.from_bytes(blob[i:i + 4], "little"); i += 4
            k = blob[i:i + kl]; i += kl
            vl = int.from_bytes(blob[i:i + 4], "little"); i += 4
            v = blob[i:i + vl]; i += vl
            s.recs[k] = v
        return s

    def save(self, path):
        pathlib.Path(path).write_bytes(self.to_bytes())

    @classmethod
    def load(cls, path) -> "DiskStore":
        return cls.from_bytes(pathlib.Path(path).read_bytes())


# ---- typed keys (mirror v0.1 ("type", id) DB keys) ----------------------------

def _key_blockindex(h: bytes) -> bytes:
    return b"blockindex:" + h


def _key_block(h: bytes) -> bytes:
    return b"block:" + h


KEY_BEST = b"hashBestChain"


def _key_wkey(pub: bytes) -> bytes:
    return b"key:" + pub


def _key_coin(txid: bytes, n: int) -> bytes:
    return b"coin:" + txid + _u32(n)


# ---- CDiskBlockIndex serialization (faithful, main.h:1151) --------------------

def encode_diskblockindex(idx: BlockIndex, hash_next: bytes) -> bytes:
    raw = idx.raw
    b_version = raw[0:4]                       # block header nVersion (LE i32)
    merkle = raw[36:68]
    ntime = raw[68:72]
    nbits = raw[72:76]
    nonce = raw[76:80]
    return (_i32(101)                          # CDataStream nVersion (VERSION)
            + hash_next                        # hashNext (u256)
            + _u32(1)                          # nFile   (blk0001.dat)
            + _u32(0)                          # nBlockPos (stand-in)
            + _i32(idx.height)                 # nHeight
            + b_version                        # block nVersion
            + idx.prev                         # hashPrev (u256)
            + merkle                           # hashMerkleRoot
            + ntime + nbits + nonce)


def decode_diskblockindex(rec: bytes):
    # [nVer 0:4][hashNext 4:36][nFile 36:40][nBlockPos 40:44][nHeight 44:48]
    # [block nVer 48:52][hashPrev 52:84][merkle 84:116][time 116:120][bits 120:124][nonce 124:128]
    hash_next = rec[4:36]
    n_height = int.from_bytes(rec[44:48], "little", signed=True)
    hash_prev = rec[52:84]
    return {"hashNext": hash_next, "nHeight": n_height, "hashPrev": hash_prev}


# ---- save / load the chain (WriteBlockIndex + LoadBlockIndex) -----------------

def save_chain(chain: Chain, store: DiskStore | None = None) -> DiskStore:
    store = store or DiskStore()
    for h, idx in chain.by_hash.items():
        hash_next = idx.pnext if idx.pnext is not None else ZERO
        store.put(_key_blockindex(h), encode_diskblockindex(idx, hash_next))
        store.put(_key_block(h), idx.raw)      # blk*.dat stand-in
    store.put(KEY_BEST, chain.tip)
    return store


def load_chain(store: DiskStore) -> Chain:
    c = Chain()
    next_of: dict[bytes, bytes] = {}
    # first pass: rebuild every CBlockIndex from its record + block bytes
    for k, rec in store.items_of_type(b"blockindex:"):
        h = k[len(b"blockindex:"):]
        d = decode_diskblockindex(rec)
        raw = store.get(_key_block(h))
        if raw is None or block_hash(raw) != h:
            raise ValueError("missing/corrupt block for index %s" % h.hex())
        idx = BlockIndex(h, d["hashPrev"], d["nHeight"], raw, nbits_of(raw))
        c.by_hash[h] = idx
        next_of[h] = d["hashNext"]
    # re-wire pnext and locate genesis
    for h, idx in c.by_hash.items():
        nxt = next_of[h]
        idx.pnext = nxt if nxt != ZERO else None
        if idx.prev not in c.by_hash:
            c.genesis = h
    # pindexBest / nBestHeight, then mark the main chain from genesis via pnext
    c.tip = store.get(KEY_BEST)
    if c.tip not in c.by_hash:
        raise ValueError("hashBestChain not found in block index")
    cur = c.genesis
    while cur is not None:
        c.by_hash[cur].in_main = True
        cur = c.by_hash[cur].pnext
    return c


# ---- save / load the wallet (CWalletDB keys + coins) --------------------------

def _priv_to_der(priv) -> bytes:
    from cryptography.hazmat.primitives import serialization
    return priv.private_bytes(serialization.Encoding.DER,
                              serialization.PrivateFormat.PKCS8,
                              serialization.NoEncryption())


def _der_to_priv(der: bytes):
    from cryptography.hazmat.primitives import serialization
    return serialization.load_der_private_key(der, password=None)


def _spk_to_bytes(spk_tokens) -> bytes:
    from cscript import assemble
    return assemble(spk_tokens)


def _bytes_to_spk(b: bytes):
    from cscript import parse
    return parse(b)


def save_wallet(wallet: Wallet, store: DiskStore | None = None) -> DiskStore:
    store = store or DiskStore()
    for pub, priv in wallet.map_keys.items():
        store.put(_key_wkey(pub), _priv_to_der(priv))   # CWalletDB ("key", pubkey) -> CPrivKey
    for c in wallet.coins:
        # value:i64 | spent:1 | spk bytes
        spk = _spk_to_bytes(c.spk)
        store.put(_key_coin(c.txid, c.n),
                  int(c.value).to_bytes(8, "little") + bytes([1 if c.spent else 0]) + spk)
    return store


def load_wallet(store: DiskStore) -> Wallet:
    w = Wallet()
    for k, der in store.items_of_type(b"key:"):
        pub = k[len(b"key:"):]
        priv = _der_to_priv(der)
        w.map_keys[pub] = priv
        w.map_pubkeys[hash160(pub)] = pub
    for k, rec in store.items_of_type(b"coin:"):
        rest = k[len(b"coin:"):]
        txid, n = rest[:32], int.from_bytes(rest[32:36], "little")
        value = int.from_bytes(rec[0:8], "little")
        spent = rec[8] == 1
        spk = _bytes_to_spk(rec[9:])
        coin = Coin(txid, n, value, spk)
        coin.spent = spent
        w.coins.append(coin)
    return w
