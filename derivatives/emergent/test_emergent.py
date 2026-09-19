"""The two emergent rules, executed: the Berkeley DB lock rule's written stand-in (8bd028818) and
BIP 66's IsValidSignatureEncoding, each against the January 2009 side. Evidence: MODEL (one side of
the DER rule is also executed on the release build, recorded in the corpus). NOT money."""

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent / "model"))

from bdb_locks import (                                                   # noqa: E402
    FORK_BLOCK_TIME, MAX_UNIQUE_TXIDS, RULE_END_TIME, block_with_unique_ids,
    check_block_081_locks, check_block_v01_size, unique_txids_referenced,
)
from der_strictness import (                                              # noqa: E402
    corpus, encode_strict, is_valid_signature_encoding, parse_signature_tolerant,
    signature_from_script_sig,
)

INSIDE = 1365000000        # 3 April 2013
AFTER = 1370000000         # 31 May 2013


# ---- Berkeley DB: the January rule accepts what the 0.8.1 rule rejects --------------------------

def test_v01_accepts_a_block_with_4501_unique_txids():
    b = block_with_unique_ids(4501, INSIDE)
    assert unique_txids_referenced(b) == 4501
    ok, why = check_block_v01_size(b)
    assert ok, why


def test_081_rejects_the_same_block_inside_the_window():
    b = block_with_unique_ids(4501, INSIDE)
    assert FORK_BLOCK_TIME < b.ntime < RULE_END_TIME
    ok, why = check_block_081_locks(b)
    assert not ok and why == "15 May maxlocks violation"


def test_081_accepts_the_same_block_after_15_may_2013():
    b = block_with_unique_ids(4501, AFTER)
    assert check_block_081_locks(b) == (True, "ok")


def test_081_boundary_is_exactly_4500():
    assert unique_txids_referenced(block_with_unique_ids(4499, INSIDE)) == 4499
    assert check_block_081_locks(block_with_unique_ids(4499, INSIDE)) == (True, "ok")
    assert check_block_081_locks(block_with_unique_ids(4501, INSIDE))[0] is False
    assert MAX_UNIQUE_TXIDS == 4500


def test_the_count_is_distinct_ids_not_transactions():
    # the coinbase's own id counts; each spend adds its own id and one prevout
    b = block_with_unique_ids(11, INSIDE)
    assert len(b.vtx) == 6 and unique_txids_referenced(b) == 11


# ---- DER: BIP 66 over the corpus --------------------------------------------------------------------

def _sigs():
    out = []
    for v in corpus():
        sig = signature_from_script_sig(v["script_sig_hex"])
        if sig is not None:
            out.append((v, sig))
    assert out, "no pay-to-pubkey signatures found in the corpus"
    return out


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


def test_the_probes_differ_from_strict_only_in_encoding():
    # what the tolerant reader recovers from a probe, re-encoded the one strict way, passes BIP 66:
    # the three tolerances are about bytes, not about the numbers under them
    for v, sig in _sigs():
        if v.get("expected_binary") is None:
            r, s, flag = parse_signature_tolerant(sig)
            strict = encode_strict(r, s, flag)
            assert is_valid_signature_encoding(strict), v["note"]
            assert parse_signature_tolerant(strict) == (r, s, flag)
            assert strict != sig


def test_strict_signatures_round_trip_through_both_readers():
    for v, sig in _sigs():
        if is_valid_signature_encoding(sig):
            r, s, flag = parse_signature_tolerant(sig)
            assert encode_strict(r, s, flag) == sig, v["note"]


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
