"""Regression vectors for the SignatureHash MODEL (tx_sighash.py).

The pinned digests were verified byte-for-byte against the C++/OpenSSL port
(derivatives/port/sighash.cpp) via run_sighash.sh. Evidence level: MODEL.
"""

import pytest

from tx_sighash import demo_tx, signature_hash

# nIn x SIGHASH type -> expected double-SHA256 signature hash (hex), cross-checked
# against real OpenSSL.
PINNED = {
    (0, 0x01): "25a913b29dbb8980b5f3c2208422ce0fc86c75333504e5739b06c7309dff2f67",
    (0, 0x02): "b36a0591192737d69d48fa4ac339092a33c8e176a461c5f34f53f9b10e4f0256",
    (0, 0x03): "463a846b68a24f5becb7a83a7c85923b410d2389a7b0b3286bb0f7ccb7231c2c",
    (0, 0x81): "f2b2c372a651c0830768138084755abc04d190cf7ec9e04a571b54f49b41b3a7",
    (0, 0x82): "99b1e305276afdd5f1aec3a8127df56fdc1bed5cd4cb2d10937e7612234fdf86",
    (0, 0x83): "473bbae1f6b4db3165f6f79376729247146ca077ee29b9a52b02aa0e616adbc2",
    (1, 0x01): "548d93e27d4a62bc16f3b5c493a1398e1f2107114217c1415f8b9d14d2d066a3",
    (1, 0x02): "da9860bbadee1024677b094028ff78c82f59943ec0ac25e100e4a2ff35d21da7",
    (1, 0x03): "3f4b2868be58fcfb29b0f82dad453c4869780b93b2c1c44650471eb9654c5e67",
    (1, 0x81): "7b46531de60959c80dd5dff4096b625a2db47682d9fae2501783c79a176480a7",
    (1, 0x82): "c19ae9d062a356bcbd84700379dee111f6d3fa870528d5bb298557d226cfd199",
    (1, 0x83): "32d7714dd77bdad621f1aa75e66975a9ffdb0b5c9f00b6b3fd8baaab3f430381",
}


@pytest.mark.parametrize("key,expected", list(PINNED.items()))
def test_signature_hash_pinned(key, expected):
    tx, script_code = demo_tx()
    n_in, ht = key
    assert signature_hash(script_code, tx, n_in, ht).hex() == expected


def test_sighash_modes_differ():
    tx, sc = demo_tx()
    hashes = {signature_hash(sc, tx, 0, ht) for ht in (0x01, 0x02, 0x03, 0x81, 0x82, 0x83)}
    assert len(hashes) == 6            # every mode yields a distinct digest


def test_single_out_of_range_returns_one():
    tx, sc = demo_tx()
    tx.vout = tx.vout[:1]              # only 1 output; nIn=1 -> nOut=1 out of range
    assert signature_hash(sc, tx, 1, 0x03) == (1).to_bytes(32, "little")
