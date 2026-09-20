"""The two emergent rules, executed: the Berkeley DB lock rule's written stand-in (8bd028818) and
BIP 66's IsValidSignatureEncoding, each against the January 2009 side. Evidence: MODEL (one side of
the DER rule is also executed on the release build, recorded in the corpus). NOT money.

Revised 20 September 2026 after an adversarial review: the 4,500 boundary is now constructed (not
asserted from a constant); the v0.1 side's test is named for the clauses it ports; and the probes are
checked by verification -- the (r, s) a tolerant reader recovers from each probe verifies under the
vector's own key over the vector's own signature hash -- instead of by re-encoding."""

import pathlib
import sys

import pytest

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent / "model"))
sys.path.insert(0, str(_HERE.parent / "vectors"))

from bdb_locks import (                                                   # noqa: E402
    FORK_BLOCK_TIME, MAX_UNIQUE_TXIDS, RULE_END_TIME, Block, block_with_unique_ids,
    check_block_081_locks, check_block_v01_size, unique_txids_referenced,
)
from der_strictness import (                                              # noqa: E402
    corpus, encode_strict, is_valid_signature_encoding, parse_signature_tolerant,
    signature_from_script_sig,
)

INSIDE = 1365000000        # 3 April 2013
AFTER = 1370000000         # 31 May 2013
BOUNDARY = 4500            # 8bd028818: "#unique txids referenced <= 4,500", as a literal here


# ---- Berkeley DB: the January clauses accept what the 0.8.1 rule rejects ----------------------------

def test_v01_size_and_count_clauses_accept_a_block_with_4501_unique_txids():
    # only CheckBlock's size and count clauses are ported on the January side (bdb_locks docstring);
    # this test says so in its name and checks that those clauses are live, not vacuous
    b = block_with_unique_ids(4501, INSIDE)
    assert unique_txids_referenced(b) == 4501
    assert check_block_v01_size(b) == (True, "ok")
    assert check_block_v01_size(Block(INSIDE, [])) == (False, "size limits failed")    # vtx.empty()


def test_081_rejects_the_same_block_inside_the_window():
    b = block_with_unique_ids(4501, INSIDE)
    assert FORK_BLOCK_TIME < b.ntime < RULE_END_TIME
    assert check_block_081_locks(b) == (False, "15 May maxlocks violation")


def test_081_accepts_the_same_block_after_15_may_2013():
    b = block_with_unique_ids(4501, AFTER)
    assert check_block_081_locks(b) == (True, "ok")


def test_081_boundary_is_exactly_4500_constructed():
    at = block_with_unique_ids(BOUNDARY, INSIDE)             # an even count: one prevout referenced twice
    over = block_with_unique_ids(BOUNDARY + 1, INSIDE)
    assert unique_txids_referenced(at) == 4500
    assert unique_txids_referenced(over) == 4501
    assert check_block_081_locks(at) == (True, "ok")          # 4,500 passes ("<= 4,500")
    assert check_block_081_locks(over) == (False, "15 May maxlocks violation")
    assert MAX_UNIQUE_TXIDS == BOUNDARY                       # the module's constant against the literal


def test_the_count_is_distinct_ids_not_transactions():
    # the coinbase's own id counts; each spend adds its own id and one prevout
    b = block_with_unique_ids(11, INSIDE)
    assert len(b.vtx) == 6 and unique_txids_referenced(b) == 11
    e = block_with_unique_ids(10, INSIDE)                     # even: 6 transactions, one shared prevout
    assert len(e.vtx) == 6 and unique_txids_referenced(e) == 10


# ---- DER: BIP 66 over the corpus --------------------------------------------------------------------

def _sigs():
    out = []
    for v in corpus():
        sig = signature_from_script_sig(v["script_sig_hex"])
        if sig is not None:
            out.append((v, sig))
    assert out, "no pay-to-pubkey signatures found in the corpus"
    return out


def _verifies(v: dict, sig: bytes) -> bool:
    """Does `sig` (DER || hash type) verify under the vector's pay-to-pubkey key over the vector's
    own signature hash? Uses the laboratory's SignatureHash model and an ECDSA verifier."""
    from tx_sighash import SigChecker, Tx, TxIn, TxOut
    from verify_vectors import parse_tx
    d, _ = parse_tx(bytes.fromhex(v["tx_hex"]))
    tx = Tx(d["version"], [TxIn(i["prevhash"], i["n"], i["script"], i["seq"]) for i in d["vin"]],
            [TxOut(o["value"], o["script"]) for o in d["vout"]], d["locktime"])
    spk = bytes.fromhex(v["script_pubkey_hex"])
    n = spk[0]                                        # one push (33 or 65 bytes), then OP_CHECKSIG
    assert 1 <= n <= 75 and len(spk) == 1 + n + 1 and spk[-1] == 0xac, "a pay-to-pubkey scriptPubKey"
    pubkey = spk[1:1 + n]
    return SigChecker(tx, int(v["n_in"]), spk).check_sig(sig, pubkey)


def test_every_strict_signature_in_the_corpus_passes_bip66():
    n = 0
    for v, sig in _sigs():
        if v.get("expected_strict_der") is True:
            assert is_valid_signature_encoding(sig), v["note"]
            n += 1
    assert n >= 5


def test_every_probe_fails_bip66_and_reads_under_a_tolerant_parser():
    probes = [(v, sig) for v, sig in _sigs() if v.get("expected_binary") is None]
    assert len(probes) == 3, [v["note"] for v, _ in probes]
    for v, sig in probes:
        assert v.get("expected_strict_der") is False
        assert not is_valid_signature_encoding(sig), v["note"]
        r, s, flag = parse_signature_tolerant(sig)
        assert r > 0 and s > 0 and flag in (1, 2, 3, 0x81, 0x82, 0x83), v["note"]


def test_the_probes_recover_a_signature_that_verifies_under_the_vectors_key():
    # the independently-known pair: the (r, s) the tolerant reader recovers from each probe, encoded
    # strictly, VERIFIES under the vector's key over the vector's signature hash; the probe bytes
    # themselves fail the strict encoding check. That is what "the same signature, another
    # encoding" means, and it cannot pass for an (r, s) the reader made up.
    pytest.importorskip("cryptography")
    for v, sig in _sigs():
        if v.get("expected_binary") is None:
            r, s, flag = parse_signature_tolerant(sig)
            strict = encode_strict(r, s, flag)
            assert is_valid_signature_encoding(strict), v["note"]
            assert strict != sig
            assert _verifies(v, strict), v["note"]
            assert not _verifies(v, encode_strict(r, s ^ 1, flag)), v["note"]     # control: one bit off fails


def test_strict_signatures_round_trip_through_both_readers_and_verify():
    pytest.importorskip("cryptography")
    for v, sig in _sigs():
        if is_valid_signature_encoding(sig):
            r, s, flag = parse_signature_tolerant(sig)
            assert encode_strict(r, s, flag) == sig, v["note"]
            if v.get("expected_model") is True and v.get("kind") == "p2pk":
                assert _verifies(v, sig), v["note"]


def test_bip66_rejects_what_no_parser_should_accept_either():
    # a negative r (high bit set, no pad) fails both readers
    bad = bytes([0x30, 0x06, 0x02, 0x01, 0x80, 0x02, 0x01, 0x01, 0x01])
    assert not is_valid_signature_encoding(bad)
    try:
        parse_signature_tolerant(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("the tolerant reader accepted a negative integer")
