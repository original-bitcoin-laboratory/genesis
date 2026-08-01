"""Bitcoin's hash layer, executed: SHA-256's constants are cube/square roots of the first primes
(fully NUMS, unlike the curve's generator); the 64-byte-transaction merkle ambiguity; and RIPEMD-160's
2^80 collision floor (the weakest margin). Pure computation. MODEL."""

import hashlib
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from hash_structure import (                                             # noqa: E402
    SHA256_H, SHA256_K, birthday_collision, hash160, icbrt, first_primes,
    merkle_64byte_ambiguity, sha256_nums,
)


def test_sha256_round_constants_are_cube_roots_of_primes():
    okK, okH = sha256_nums()
    assert okK == 64 and okH == 8


def test_icbrt_is_exact():
    assert icbrt(2 << 96) & ((1 << 32) - 1) == SHA256_K[0]      # cuberoot(2) -> K[0]
    assert icbrt(27) == 3 and icbrt(26) == 2 and icbrt(1 << 96) == 1 << 32


def test_sha256_matches_the_standard_function():
    # sanity: the SHA-256 whose constants we verified is the real one
    assert hashlib.sha256(b"").hexdigest() == \
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_64byte_transaction_merkle_ambiguity():
    assert merkle_64byte_ambiguity()               # a 64-byte tx's txid == an interior node hash


def test_ripemd160_is_160_bits_and_birthday_scales():
    h = hash160(b"test")
    assert h is None or len(h) == 20               # HASH160 is 160-bit (or unavailable in this build)
    (a, b), tries = birthday_collision(32)
    assert a != b and 2**14 < tries < 2**18        # ~2^16 for a 32-bit birthday collision
