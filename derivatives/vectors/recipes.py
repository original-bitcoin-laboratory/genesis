"""Recipes shared by the export (easy test chain) and the binary replay (live 2009 chain in the VM).

A recipe is a *construction*, not a byte string: the same signature variant or block case is rebuilt
on whatever chain it is pointed at, with that chain's previous hash, height, median time and
funding outputs. That is what lets the corpus (built at export time at an easy difficulty) and the
replay (mined at difficulty 1 against the frozen binary) test the same thing. NOT money.

Everything here is written on top of verify_vectors' from-spec primitives, so the recipes carry no
lab code either.
"""
from __future__ import annotations

import hashlib
import hmac

from verify_vectors import (COIN, G, N, OP_1, OP_CHECKMULTISIG, OP_CHECKSIG, SIGHASH_ALL, SIGHASH_ANYONECANPAY,
                            SIGHASH_NONE, SIGHASH_SINGLE, der_encode, dsha256, ec_mul, get_compact, le,
                            merkle_root, parse_tx, push, sec_compressed, sec_uncompressed, ser_tx, set_compact,
                            signature_hash, txid, varint)

OP_TRUE_SCRIPT = bytes([OP_1])           # 0x51: anyone can spend; the scriptSig is empty
ZERO32 = b"\x00" * 32


# ---------------------------------------------------------------------------------------------
# keys and deterministic signing
# ---------------------------------------------------------------------------------------------

def key_from_label(label: str) -> dict:
    """A test key derived from a label: reproducible, and worthless by construction (published)."""
    priv = int.from_bytes(hashlib.sha256(b"obl-vectors:" + label.encode()).digest(), "big") % N
    pt = ec_mul(priv, G)
    return {"label": label, "priv": priv, "point": pt, "sec": sec_uncompressed(pt), "sec_c": sec_compressed(pt)}


def sign_det(priv: int, z: int) -> tuple[int, int]:
    """Deterministic ECDSA: k = HMAC-SHA256(priv, z || counter), retried until r and s are non-zero.
    (Not RFC 6979 — any valid k gives a valid signature; determinism is all the corpus needs.)"""
    pb, zb = priv.to_bytes(32, "big"), z.to_bytes(32, "big")
    for ctr in range(256):
        k = int.from_bytes(hmac.new(pb, zb + bytes([ctr]), hashlib.sha256).digest(), "big") % N
        if k == 0:
            continue
        r = ec_mul(k, G)[0] % N
        if r == 0:
            continue
        s = pow(k, -1, N) * (z + r * priv) % N
        if s == 0:
            continue
        return r, s
    raise RuntimeError("no k")


def low_s(r: int, s: int) -> tuple[int, int]:
    return r, (N - s if s > N // 2 else s)


def high_s(r: int, s: int) -> tuple[int, int]:
    return r, (s if s > N // 2 else N - s)


# ---------------------------------------------------------------------------------------------
# transaction builders
# ---------------------------------------------------------------------------------------------

def make_tx(vin: list, vout: list, version: int = 1, locktime: int = 0) -> dict:
    return {"version": version, "locktime": locktime,
            "vin": [{"prevhash": p, "n": n, "script": s, "seq": seq} for (p, n, s, seq) in vin],
            "vout": [{"value": v, "script": s} for (v, s) in vout]}


def make_coinbase(height: int, outputs: list[tuple[int, bytes]], tag: bytes = b"obl-vectors") -> dict:
    """A v0.1 coinbase: null prevout, a 2..100-byte scriptSig (height bytes + tag), any outputs."""
    script = bytes([height & 0xFF, (height >> 8) & 0xFF]) + tag
    assert 2 <= len(script) <= 100
    return make_tx([(ZERO32, 0xFFFFFFFF, script, 0xFFFFFFFF)], outputs)


def spend(prev_txid: bytes, n: int, value: int, script_out: bytes, script_sig: bytes = b"") -> dict:
    return make_tx([(prev_txid, n, script_sig, 0xFFFFFFFF)], [(value, script_out)])


def p2pk(sec: bytes) -> bytes:
    return push(sec) + bytes([OP_CHECKSIG])


def sign_p2pk(key: dict, tx: dict, n_in: int, script_pubkey: bytes, hash_type: int = SIGHASH_ALL,
              s_form=low_s) -> tuple[bytes, int]:
    """Returns (DER, z) for the P2PK spend: the scriptCode is the scriptPubKey."""
    z = int.from_bytes(signature_hash(script_pubkey, tx, n_in, hash_type), "big")
    r, s = s_form(*sign_det(key["priv"], z))
    return der_encode(r, s), z


# ---------------------------------------------------------------------------------------------
# signature variants for checksig.json and the replay
#
# expected_strict_der: what a strict-DER verifier that accepts high-S (the from-spec rule) says.
# expected_binary: None = to be recorded from the frozen 2009 binary (OpenSSL 0.9.8) by the replay.
#                  A stated value is one that no DER leniency can change (semantic, not syntactic).
# ---------------------------------------------------------------------------------------------

def _der_long_form_length(der: bytes) -> bytes:
    """Same DER, but the outer SEQUENCE length written in long form (0x81 LL): valid BER, not DER."""
    return b"\x30\x81" + bytes([der[1]]) + der[2:]


def _der_pad_r(der: bytes) -> bytes:
    """Same (r, s), but r carries an unnecessary leading 0x00: valid BER integer, non-minimal DER."""
    lr = der[3]
    r = der[4:4 + lr]
    rest = der[4 + lr:]
    r2 = b"\x00" + r
    body = b"\x02" + bytes([len(r2)]) + r2 + rest
    return b"\x30" + bytes([len(body)]) + body


def _der_negative_r(der: bytes) -> bytes:
    """Strip r's sign pad so its high bit is set: the integer parses as NEGATIVE, so ECDSA rejects it
    semantically (r must be in [1, n-1]) — no parser leniency can make it valid."""
    lr = der[3]
    r = der[4:4 + lr]
    if not (r[0] == 0 and r[1] & 0x80):
        return None                                 # r had no pad byte; variant not applicable to this k
    r2 = r[1:]
    rest = der[4 + lr:]
    body = b"\x02" + bytes([len(r2)]) + r2 + rest
    return b"\x30" + bytes([len(body)]) + body


def build_sig_variants(key: dict, wrong_key: dict, key_b: dict) -> list[dict]:
    """Each entry: label, note, script_pubkey, scriptsig(tx, n_in) -> bytes, expected_strict_der,
    expected_binary (None = pending), and 'kind'."""
    spk = p2pk(key["sec"])
    spk_c = p2pk(key["sec_c"])
    multisig_1of2 = bytes([OP_1]) + push(key["sec"]) + push(key_b["sec"]) + bytes([OP_1 + 1, OP_CHECKMULTISIG])
    multisig_2of2 = bytes([OP_1 + 1]) + push(key["sec"]) + push(key_b["sec"]) + bytes([OP_1 + 1, OP_CHECKMULTISIG])

    def sig(k, spk_, ht, s_form=low_s, mutate=None):
        def f(tx, n_in):
            der, _z = sign_p2pk(k, tx, n_in, spk_, ht, s_form)
            if mutate:
                der = mutate(der)
                if der is None:
                    return None
            return push(der + bytes([ht]))
        return f

    def sig_hashtype_mismatch(tx, n_in):
        der, _ = sign_p2pk(key, tx, n_in, spk, SIGHASH_ALL)
        return push(der + bytes([SIGHASH_NONE]))     # signed the ALL digest, claims NONE

    def sig_empty(tx, n_in):
        return push(b"")

    def sig_trailing(tx, n_in):
        der, _ = sign_p2pk(key, tx, n_in, spk, SIGHASH_ALL)
        return push(der + b"\x00" + bytes([SIGHASH_ALL]))

    def ms(keys, ht=SIGHASH_ALL):
        def f(tx, n_in):
            out = bytes([0x00])                       # the dummy element the off-by-one pop consumes
            for k in keys:
                der, _ = sign_p2pk(k, tx, n_in, multisig_2of2 if len(keys) == 2 else multisig_1of2, ht)
                out += push(der + bytes([ht]))
            return out
        return f

    V = []

    def add(label, spk_, fn, strict, binary, note, kind="p2pk"):
        V.append({"label": label, "script_pubkey": spk_, "scriptsig": fn, "expected_strict_der": strict,
                  "expected_binary": binary, "note": note, "kind": kind})

    add("canonical_low_s", spk, sig(key, spk, SIGHASH_ALL), True, True,
        "a correct signature in canonical DER with low S; SIGHASH_ALL")
    add("high_s", spk, sig(key, spk, SIGHASH_ALL, high_s), True, True,
        "same signature with s -> n-s: mathematically valid; OpenSSL accepts (the malleability descendants later closed)")
    add("wrong_key", spk, sig(wrong_key, spk, SIGHASH_ALL), False, False,
        "signed by a different key")
    add("hashtype_byte_mismatch", spk, sig_hashtype_mismatch, False, False,
        "digest signed as SIGHASH_ALL, trailing byte says SIGHASH_NONE: CheckSig recomputes the NONE digest, fails")
    add("hashtype_zero", spk, sig(key, spk, 0), True, True,
        "hash type byte 0x00: v0.1 CheckSig takes the byte as-is and SignatureHash treats 0 like ALL, so it verifies")
    add("sighash_none", spk, sig(key, spk, SIGHASH_NONE), True, True, "SIGHASH_NONE: outputs are not committed")
    add("sighash_single", spk, sig(key, spk, SIGHASH_SINGLE), True, True, "SIGHASH_SINGLE with n_in < vout.size()")
    add("sighash_all_anyonecanpay", spk, sig(key, spk, SIGHASH_ALL | SIGHASH_ANYONECANPAY), True, True,
        "ANYONECANPAY: only this input is committed")
    add("empty_signature", spk, sig_empty, False, False, "empty vchSig: CheckSig returns false before parsing")
    add("compressed_pubkey", spk_c, sig(key, spk_c, SIGHASH_ALL), True, True,
        "the same key in 33-byte compressed SEC form; o2i_ECPublicKey accepts it")
    add("der_trailing_byte", spk, sig_trailing, False, None,
        "one 0x00 byte between the DER and the hash type: strict verifiers reject; OpenSSL 0.9.8's d2i is not known to")
    add("der_long_form_length", spk, sig(key, spk, SIGHASH_ALL, low_s, _der_long_form_length), False, None,
        "outer length in BER long form (81 LL): strict DER rejects; BER-tolerant parsers accept")
    add("der_r_extra_leading_zero", spk, sig(key, spk, SIGHASH_ALL, low_s, _der_pad_r), False, None,
        "r with a redundant 0x00 pad: non-minimal integer, strict DER rejects; BER-tolerant parsers accept")
    add("der_negative_r", spk, sig(key, spk, SIGHASH_ALL, low_s, _der_negative_r), False, False,
        "r's sign pad removed so it parses as negative: rejected on the arithmetic, whatever the parser")
    add("multisig_1of2", multisig_1of2, ms([key]), True, True,
        "OP_1 <A> <B> OP_2 OP_CHECKMULTISIG spent with OP_0 <sigA>: the leading dummy is what the off-by-one pop eats",
        kind="multisig")
    add("multisig_2of2_in_order", multisig_2of2, ms([key, key_b]), True, True,
        "signatures in key order; each key is tried once, in order", kind="multisig")
    add("multisig_2of2_reversed", multisig_2of2, ms([key_b, key]), False, False,
        "signatures out of key order: key A is skipped past, so the second signature has no key left", kind="multisig")
    return V


# ---------------------------------------------------------------------------------------------
# block cases for blocks.json and the replay
# ---------------------------------------------------------------------------------------------

def header(version: int, prev: bytes, merkle: bytes, ntime: int, nbits: int, nonce: int) -> bytes:
    return le(version, 4) + prev + merkle + le(ntime, 4) + le(nbits, 4) + le(nonce, 4)


def assemble_block(prev: bytes, txs: list[dict], ntime: int, nbits: int, mine, merkle_override: bytes | None = None,
                   nonce_override: int | None = None) -> bytes:
    mr = merkle_override if merkle_override is not None else merkle_root([txid(t) for t in txs])
    prefix = le(1, 4) + prev + mr + le(ntime, 4) + le(nbits, 4)
    nonce = nonce_override if nonce_override is not None else mine(prefix, nbits)
    if nonce is None:
        raise RuntimeError("miner returned no nonce")
    return prefix + le(nonce, 4) + varint(len(txs)) + b"".join(ser_tx(t) for t in txs)


def easy_mine(prefix76: bytes, nbits: int) -> int:
    target, _, _ = set_compact(nbits)
    for nonce in range(1 << 32):
        if int.from_bytes(dsha256(prefix76 + le(nonce, 4)), "little") <= target:
            return nonce
    raise RuntimeError("no nonce")


def easier_than(pow_limit_nbits: int) -> int:
    """An nBits whose target exceeds the proof-of-work limit (CheckBlock: 'nBits below minimum work')."""
    limit, _, _ = set_compact(pow_limit_nbits)
    return get_compact(limit * 2)


def harder_than(nbits: int) -> int:
    """The next-harder nBits: same exponent, mantissa - 1."""
    return nbits - 1


BLOCK_CASE_ORDER = [
    "v_spend_with_fee", "v_chain_in_block", "v_coinbase_underclaim",
    "double_spend", "inflation", "immature", "bad_sig", "bad_merkle", "bad_pow", "two_coinbases",
    "first_tx_not_coinbase", "timestamp_too_early", "negative_output", "coinbase_script_too_short",
    "prevout_null_in_noncoinbase", "coinbase_overclaim", "wrong_nbits", "nbits_below_minimum", "orphan",
]


def build_block_case(name: str, ctx: dict) -> dict:
    """ctx: prev (bytes, internal order), height (of the block being built), mtp (of prev), ntime (to use
    for a normal block), nbits, pow_limit_nbits, subsidy (int for this height), key, wrong_key,
    funding: list of P2PK outputs [{txid, n, value}] paying `key`, last_cb: {txid, value} of a recent
    (immature) coinbase, mine(prefix76, nbits) -> nonce.
    Returns {raw, expect, stage, reason, needs_pow, consumes: [funding indexes]}."""
    prev, h, nbits, sub = ctx["prev"], ctx["height"], ctx["nbits"], ctx["subsidy"]
    key, wkey, fund, mine, t = ctx["key"], ctx["wrong_key"], ctx["funding"], ctx["mine"], ctx["ntime"]
    spk = p2pk(key["sec"])

    def signed_spend(k, fi, value_out, script_out=OP_TRUE_SCRIPT, ht=SIGHASH_ALL):
        f = fund[fi]
        tx = spend(f["txid"], f["n"], value_out, script_out)
        der, _ = sign_p2pk(k, tx, 0, spk, ht)
        tx["vin"][0]["script"] = push(der + bytes([ht]))
        return tx

    def blk(txs, **kw):
        return assemble_block(prev, txs, kw.pop("ntime", t), kw.pop("nbits", nbits), mine, **kw)

    def ok(raw, **extra):
        return {"raw": raw, "expect": "accept", "stage": "ConnectBlock", "reason": "ProcessBlock: ACCEPTED",
                "needs_pow": True, **extra}

    def rej(raw, stage, reason, needs_pow=True, **extra):
        return {"raw": raw, "expect": "reject", "stage": stage, "reason": reason, "needs_pow": needs_pow, **extra}

    if name == "v_spend_with_fee":
        fee = 1000
        s = signed_spend(key, 0, fund[0]["value"] - fee)
        return ok(blk([make_coinbase(h, [(sub + fee, OP_TRUE_SCRIPT)]), s]), consumes=[0],
                  note="a signed P2PK spend paying a fee; the coinbase claims subsidy + fee exactly")
    if name == "v_chain_in_block":
        a = signed_spend(key, 1, fund[1]["value"])
        b = spend(txid(a), 0, fund[1]["value"], OP_TRUE_SCRIPT)          # spends a's OP_TRUE output, empty scriptSig
        return ok(blk([make_coinbase(h, [(sub, OP_TRUE_SCRIPT)]), a, b]), consumes=[1],
                  note="a transaction spending an output created earlier in the same block")
    if name == "v_coinbase_underclaim":
        return ok(blk([make_coinbase(h, [(sub - 1, OP_TRUE_SCRIPT)])]),
                  note="the coinbase may claim less than the subsidy (the rule is <=)")
    if name == "double_spend":
        s1 = signed_spend(key, 2, fund[2]["value"] - 1)
        s2 = signed_spend(key, 2, fund[2]["value"] - 2)
        return rej(blk([make_coinbase(h, [(sub, OP_TRUE_SCRIPT)]), s1, s2]), "ConnectBlock",
                   "ConnectInputs() : prev tx already used")
    if name == "inflation":
        s = signed_spend(key, 3, fund[3]["value"] * 5)
        return rej(blk([make_coinbase(h, [(sub, OP_TRUE_SCRIPT)]), s]), "ConnectBlock", "ConnectInputs() : nTxFee < 0")
    if name == "immature":
        cb = ctx["last_cb"]
        s = spend(cb["txid"], 0, cb["value"], OP_TRUE_SCRIPT)                # last coinbase pays OP_TRUE
        return rej(blk([make_coinbase(h, [(sub, OP_TRUE_SCRIPT)]), s]), "ConnectBlock",
                   "ConnectInputs() : tried to spend coinbase at depth")
    if name == "bad_sig":
        s = signed_spend(wkey, 4, fund[4]["value"])
        return rej(blk([make_coinbase(h, [(sub, OP_TRUE_SCRIPT)]), s]), "ConnectBlock",
                   "ConnectInputs() : VerifySignature failed")
    if name == "bad_merkle":
        cb = make_coinbase(h, [(sub, OP_TRUE_SCRIPT)])
        wrong = bytes(b ^ 0xFF for b in merkle_root([txid(cb)]))
        return rej(blk([cb], merkle_override=wrong), "CheckBlock", "CheckBlock() : hashMerkleRoot mismatch")
    if name == "bad_pow":
        cb = make_coinbase(h, [(sub, OP_TRUE_SCRIPT)])
        target, _, _ = set_compact(nbits)
        for nonce in range(1 << 32):
            raw = blk([cb], nonce_override=nonce)
            if int.from_bytes(dsha256(raw[:80]), "little") > target:
                return rej(raw, "CheckBlock", "CheckBlock() : hash doesn't match nBits", needs_pow=False)
    if name == "two_coinbases":
        return rej(blk([make_coinbase(h, [(sub, OP_TRUE_SCRIPT)]), make_coinbase(h, [(1, OP_TRUE_SCRIPT)], b"second")],
                       nonce_override=0), "CheckBlock", "CheckBlock() : more than one coinbase", needs_pow=False)
    if name == "first_tx_not_coinbase":
        s = signed_spend(key, 5, fund[5]["value"])
        return rej(blk([s, make_coinbase(h, [(sub, OP_TRUE_SCRIPT)])], nonce_override=0), "CheckBlock",
                   "CheckBlock() : first tx is not coinbase", needs_pow=False)
    if name == "timestamp_too_early":
        return rej(blk([make_coinbase(h, [(sub, OP_TRUE_SCRIPT)])], ntime=ctx["mtp"]), "AcceptBlock",
                   "AcceptBlock() : block's timestamp is too early")
    if name == "negative_output":
        return rej(blk([make_coinbase(h, [(-1, OP_TRUE_SCRIPT)])], nonce_override=0), "CheckBlock",
                   "CheckBlock() : CheckTransaction failed", needs_pow=False,
                   inner="CTransaction::CheckTransaction() : txout.nValue negative")
    if name == "coinbase_script_too_short":
        cb = make_tx([(ZERO32, 0xFFFFFFFF, b"\x01", 0xFFFFFFFF)], [(sub, OP_TRUE_SCRIPT)])
        return rej(blk([cb], nonce_override=0), "CheckBlock", "CheckBlock() : CheckTransaction failed",
                   needs_pow=False, inner="CTransaction::CheckTransaction() : coinbase script size")
    if name == "prevout_null_in_noncoinbase":
        f = fund[5]
        bad = make_tx([(f["txid"], f["n"], b"", 0xFFFFFFFF), (ZERO32, 0xFFFFFFFF, b"", 0xFFFFFFFF)],
                      [(1, OP_TRUE_SCRIPT)])
        return rej(blk([make_coinbase(h, [(sub, OP_TRUE_SCRIPT)]), bad], nonce_override=0), "CheckBlock",
                   "CheckBlock() : CheckTransaction failed", needs_pow=False,
                   inner="CTransaction::CheckTransaction() : prevout is null")
    if name == "coinbase_overclaim":
        return rej(blk([make_coinbase(h, [(sub + 1, OP_TRUE_SCRIPT)])]), "ConnectBlock",
                   "SetBestChain() : ConnectBlock failed",
                   note="main.cpp:953 returns false without its own error line; only SetBestChain's shows")
    if name == "wrong_nbits":
        hb = harder_than(nbits)
        return rej(blk([make_coinbase(h, [(sub, OP_TRUE_SCRIPT)])], nbits=hb), "AcceptBlock",
                   "AcceptBlock() : incorrect proof of work",
                   note="mined at the next-harder target so CheckBlock passes and AcceptBlock's nBits comparison is what fails")
    if name == "nbits_below_minimum":
        eb = easier_than(ctx["pow_limit_nbits"])
        return rej(blk([make_coinbase(h, [(sub, OP_TRUE_SCRIPT)])], nbits=eb), "CheckBlock",
                   "CheckBlock() : nBits below minimum work")
    if name == "orphan":
        nowhere = hashlib.sha256(b"nowhere").digest()
        raw = assemble_block(nowhere, [make_coinbase(h, [(sub, OP_TRUE_SCRIPT)])], t, nbits, mine)
        return {"raw": raw, "expect": "orphan", "stage": "ProcessBlock", "reason": "ProcessBlock: ORPHAN BLOCK",
                "needs_pow": True}
    raise KeyError(name)


def parse_raw_tx(hexstr: str) -> dict:
    tx, _ = parse_tx(bytes.fromhex(hexstr))
    return tx
