"""Headless v0.1 persistence: save the block index + wallet to disk, shut down,
reload, and resume at the same tip with the same spendable wallet. No VM.

Faithful CDiskBlockIndex record + LoadBlockIndex reconstruction (db.cpp / main.h);
the private keys survive a DER round-trip and still sign. Evidence level: MODEL."""

import pathlib
import random
import sys

# resolve sibling model/p2p/wallet modules
_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "model"))
sys.path.insert(0, str(_HERE.parent / "p2p"))
sys.path.insert(0, str(_HERE.parent / "wallet"))

from chainsync import build_chain, block_hash, mine
from wallet import COIN, Wallet, p2pk, p2pkh, verify_transaction
from persist import (DiskStore, decode_diskblockindex, encode_diskblockindex,
                     load_chain, load_wallet, save_chain, save_wallet)


# ---- CDiskBlockIndex record ---------------------------------------------------

def test_diskblockindex_record_is_128_bytes_and_roundtrips():
    c, _ = build_chain(1)
    idx = c.by_hash[c.tip]
    rec = encode_diskblockindex(idx, b"\x00" * 32)
    assert len(rec) == 128
    d = decode_diskblockindex(rec)
    assert d["nHeight"] == idx.height
    assert d["hashPrev"] == idx.prev


# ---- chain persistence --------------------------------------------------------

def _assert_same_chain(a, b):
    assert a.tip == b.tip
    assert a.best_height == b.best_height
    assert a.genesis == b.genesis
    assert a.main_chain() == b.main_chain()
    for h, idx in a.by_hash.items():
        assert h in b.by_hash
        assert b.by_hash[h].height == idx.height
        assert b.by_hash[h].raw == idx.raw            # exact block bytes
        assert b.by_hash[h].in_main == idx.in_main


def test_chain_survives_save_and_reload():
    c, _ = build_chain(6)
    store = save_chain(c)
    reloaded = load_chain(DiskStore.from_bytes(store.to_bytes()))   # simulate a restart
    _assert_same_chain(c, reloaded)
    assert reloaded.best_height == 6


def test_chain_persists_to_an_actual_file(tmp_path):
    c, _ = build_chain(4)
    path = tmp_path / "blkindex.dat"
    save_chain(c).save(path)
    assert path.exists()
    reloaded = load_chain(DiskStore.load(path))
    _assert_same_chain(c, reloaded)


def test_reorged_chain_persists_main_and_side_branches():
    c, raws = build_chain(3)                            # main g,b1,b2,b3
    _, b1, b2, b3 = raws
    h1 = block_hash(b1)
    c2 = mine(h1, 2, tag=9); c3 = mine(block_hash(c2), 3, tag=9); c4 = mine(block_hash(c3), 4, tag=9)
    for r in (c2, c3, c4):
        c.process_block(r)
    assert c.tip == block_hash(c4)                      # reorged onto the longer branch
    reloaded = load_chain(DiskStore.from_bytes(save_chain(c).to_bytes()))
    _assert_same_chain(c, reloaded)
    # new main survived; old tip blocks stayed off-chain
    assert reloaded.main_chain() == [c.genesis, h1, block_hash(c2), block_hash(c3), block_hash(c4)]
    assert not reloaded.by_hash[block_hash(b2)].in_main
    assert not reloaded.by_hash[block_hash(b3)].in_main


# ---- wallet persistence -------------------------------------------------------

def test_wallet_keys_and_coins_survive_reload():
    w = Wallet(random.Random(1))
    s1 = w.new_key(); s2 = w.new_key()
    w.add_coin(b"\x01" * 32, 0, 50 * COIN, p2pk(s1))
    w.add_coin(b"\x02" * 32, 1, 10 * COIN, p2pkh(s2))
    w.coins[1].spent = True
    reloaded = load_wallet(DiskStore.from_bytes(save_wallet(w).to_bytes()))
    assert set(reloaded.map_keys) == set(w.map_keys)
    assert reloaded.map_pubkeys == w.map_pubkeys
    assert reloaded.get_balance() == 50 * COIN         # spent coin excluded
    assert len(reloaded.coins) == 2


def test_reloaded_key_can_still_sign_a_spend():
    """The whole point of wallet.dat: a private key restored from disk must still
    produce a valid signature."""
    w = Wallet(random.Random(2))
    sec = w.new_key()
    w.add_coin(b"\x07" * 32, 0, 50 * COIN, p2pk(sec))
    reloaded = load_wallet(DiskStore.from_bytes(save_wallet(w).to_bytes()))
    dest = p2pk(Wallet().new_key())
    tx, coins, _ = reloaded.create_transaction(dest, 30 * COIN)
    assert verify_transaction(reloaded, tx, coins)     # signed with the DER-reloaded key


def test_wallet_persists_to_an_actual_file(tmp_path):
    w = Wallet(random.Random(3))
    sec = w.new_key()
    w.add_coin(b"\x05" * 32, 0, 42 * COIN, p2pk(sec))
    path = tmp_path / "wallet.dat"
    save_wallet(w).save(path)
    reloaded = load_wallet(DiskStore.load(path))
    assert reloaded.get_balance() == 42 * COIN
    tx, coins, _ = reloaded.create_transaction(p2pk(Wallet().new_key()), 20 * COIN)
    assert verify_transaction(reloaded, tx, coins)


if __name__ == "__main__":
    c, _ = build_chain(6)
    store = save_chain(c)
    print("chain blob:", len(store.to_bytes()), "bytes;",
          "reload height:", load_chain(DiskStore.from_bytes(store.to_bytes())).best_height)
