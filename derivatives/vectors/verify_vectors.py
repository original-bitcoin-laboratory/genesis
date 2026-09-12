#!/usr/bin/env python3
"""Replay the JSON corpus from the rules alone — hashlib, hmac and integer arithmetic, nothing from the lab.

    python verify_vectors.py            # every suite; evalscript is replayed through ../model
    python verify_vectors.py --no-model # skip the evalscript suite (needs ../model); everything else is pure

This file is the "from the spec" verifier: it deliberately does NOT import anything under
`../model`, `../retarget`, `../p2p`, `../ledger` or `../netnode`. The secp256k1 arithmetic, the DER
parser, SignatureHash, the small EvalScript needed for P2PK / multisig spends, and the 2009 block
validator below are all written from the rule text carried in the JSON files. If they agree with
the corpus, the prose is sufficient to reimplement those surfaces. The full-vocabulary EvalScript
suite needs a complete Script interpreter, so it is replayed through the lab's model and reported
separately. Exit code 0 iff every vector passes. NOT money.

The same validator (`Chain2009`) drives `replay/fake2009.py`, the local stand-in for the frozen
2009 binary, so the replay harness is exercised end-to-end before it is pointed at the VM.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent

COIN = 100_000_000
COINBASE_MATURITY = 100          # main.h:20
MAX_SIZE = 0x02000000            # main.h:17
N_MEDIAN_TIME_SPAN = 11          # main.h nMedianTimeSpan
POW_LIMIT_2009_NBITS = 0x1D00FFFF


# =============================================================================================
# hashes, integers, compact sizes
# =============================================================================================

def sha256(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


def dsha256(b: bytes) -> bytes:
    return sha256(sha256(b))


def hash160(b: bytes) -> bytes:
    return hashlib.new("ripemd160", sha256(b)).digest()


def le(n: int, length: int) -> bytes:
    return n.to_bytes(length, "little")


def le_signed(n: int, length: int) -> bytes:
    return n.to_bytes(length, "little", signed=True)


def read_varint(b: bytes, i: int) -> tuple[int, int]:
    b0 = b[i]
    if b0 < 0xFD:
        return b0, i + 1
    if b0 == 0xFD:
        return int.from_bytes(b[i + 1:i + 3], "little"), i + 3
    if b0 == 0xFE:
        return int.from_bytes(b[i + 1:i + 5], "little"), i + 5
    return int.from_bytes(b[i + 1:i + 9], "little"), i + 9


def varint(n: int) -> bytes:
    if n < 0xFD:
        return bytes([n])
    if n <= 0xFFFF:
        return b"\xfd" + le(n, 2)
    if n <= 0xFFFFFFFF:
        return b"\xfe" + le(n, 4)
    return b"\xff" + le(n, 8)


# =============================================================================================
# transactions and blocks (main.h CTransaction / CBlock serialization)
# =============================================================================================

def parse_tx(b: bytes, i: int = 0) -> tuple[dict, int]:
    version = int.from_bytes(b[i:i + 4], "little", signed=True); i += 4
    n, i = read_varint(b, i)
    vin = []
    for _ in range(n):
        prevhash = b[i:i + 32]; i += 32
        pn = int.from_bytes(b[i:i + 4], "little"); i += 4
        sl, i = read_varint(b, i)
        script = b[i:i + sl]; i += sl
        seq = int.from_bytes(b[i:i + 4], "little"); i += 4
        vin.append({"prevhash": prevhash, "n": pn, "script": script, "seq": seq})
    n, i = read_varint(b, i)
    vout = []
    for _ in range(n):
        value = int.from_bytes(b[i:i + 8], "little", signed=True); i += 8
        sl, i = read_varint(b, i)
        script = b[i:i + sl]; i += sl
        vout.append({"value": value, "script": script})
    locktime = int.from_bytes(b[i:i + 4], "little"); i += 4
    return {"version": version, "vin": vin, "vout": vout, "locktime": locktime}, i


def ser_tx(tx: dict) -> bytes:
    s = le_signed(tx["version"], 4) + varint(len(tx["vin"]))
    for vi in tx["vin"]:
        s += vi["prevhash"] + le(vi["n"], 4) + varint(len(vi["script"])) + vi["script"] + le(vi["seq"], 4)
    s += varint(len(tx["vout"]))
    for vo in tx["vout"]:
        s += le_signed(vo["value"], 8) + varint(len(vo["script"])) + vo["script"]
    return s + le(tx["locktime"], 4)


def txid(tx: dict) -> bytes:
    return dsha256(ser_tx(tx))


def is_coinbase(tx: dict) -> bool:
    return len(tx["vin"]) == 1 and tx["vin"][0]["prevhash"] == b"\x00" * 32 and tx["vin"][0]["n"] == 0xFFFFFFFF


def value_out(tx: dict) -> int:
    return sum(o["value"] for o in tx["vout"])


def parse_block(b: bytes) -> dict:
    hdr = b[:80]
    f = {"nVersion": int.from_bytes(hdr[0:4], "little", signed=True), "hashPrevBlock": hdr[4:36],
         "hashMerkleRoot": hdr[36:68], "nTime": int.from_bytes(hdr[68:72], "little"),
         "nBits": int.from_bytes(hdr[72:76], "little"), "nNonce": int.from_bytes(hdr[76:80], "little")}
    n, i = read_varint(b, 80)
    txs = []
    for _ in range(n):
        tx, i = parse_tx(b, i)
        txs.append(tx)
    return {"header": hdr, "fields": f, "txs": txs, "raw": b, "hash": dsha256(hdr)}


def merkle_root(leaves: list[bytes]) -> bytes:
    h = list(leaves)
    while len(h) > 1:
        if len(h) & 1:
            h.append(h[-1])                       # main.h:878 — odd level pairs the last node with itself
        h = [dsha256(h[i] + h[i + 1]) for i in range(0, len(h), 2)]
    return h[0] if h else b"\x00" * 32


def set_compact(c: int) -> tuple[int, bool, bool]:
    size = c >> 24
    word = c & 0x007FFFFF
    val = word >> (8 * (3 - size)) if size <= 3 else word << (8 * (size - 3))
    negative = word != 0 and (c & 0x00800000) != 0
    overflow = word != 0 and (size > 34 or (word > 0xFF and size > 33) or (word > 0xFFFF and size > 32))
    return val, negative, overflow


def get_compact(value: int) -> int:
    size = (value.bit_length() + 7) // 8
    compact = (value << (8 * (3 - size))) if size <= 3 else (value >> (8 * (size - 3)))
    if compact & 0x00800000:
        compact >>= 8
        size += 1
    return compact | (size << 24)


def pow_ok(header: bytes, nbits: int) -> bool:
    target, _, _ = set_compact(nbits)
    return int.from_bytes(dsha256(header), "little") <= target


# =============================================================================================
# secp256k1 and ECDSA, from the curve constants (SEC 2) and the textbook verify equation
# =============================================================================================

P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
G = (GX, GY)


def ec_add(p, q):
    if p is None:
        return q
    if q is None:
        return p
    if p[0] == q[0]:
        if (p[1] + q[1]) % P == 0:
            return None
        lam = (3 * p[0] * p[0]) * pow(2 * p[1], -1, P) % P
    else:
        lam = (q[1] - p[1]) * pow(q[0] - p[0], -1, P) % P
    x = (lam * lam - p[0] - q[0]) % P
    return (x, (lam * (p[0] - x) - p[1]) % P)


def ec_mul(k: int, p):
    r = None
    while k:
        if k & 1:
            r = ec_add(r, p)
        p = ec_add(p, p)
        k >>= 1
    return r


def on_curve(pt) -> bool:
    return pt is not None and (pt[1] * pt[1] - pt[0] ** 3 - 7) % P == 0


def pubkey_point(sec: bytes):
    """SEC1 point decoding: 65-byte uncompressed (04|x|y) or 33-byte compressed (02/03|x)."""
    if len(sec) == 65 and sec[0] == 4:
        pt = (int.from_bytes(sec[1:33], "big"), int.from_bytes(sec[33:65], "big"))
        return pt if on_curve(pt) else None
    if len(sec) == 33 and sec[0] in (2, 3):
        x = int.from_bytes(sec[1:], "big")
        if x >= P:
            return None
        y = pow((x ** 3 + 7) % P, (P + 1) // 4, P)
        if (y * y - x ** 3 - 7) % P != 0:
            return None
        if (y & 1) != (sec[0] & 1):
            y = P - y
        return (x, y)
    return None


def sec_uncompressed(pt) -> bytes:
    return b"\x04" + pt[0].to_bytes(32, "big") + pt[1].to_bytes(32, "big")


def sec_compressed(pt) -> bytes:
    return bytes([2 + (pt[1] & 1)]) + pt[0].to_bytes(32, "big")


def ecdsa_verify(pub, z: int, r: int, s: int) -> bool:
    """Textbook ECDSA verify. Accepts any s in [1, N-1] — the OpenSSL semantics v0.1 inherits (high-S
    is valid); a low-S rule is a later, descendant-specific restriction."""
    if pub is None or not (1 <= r < N) or not (1 <= s < N):
        return False
    w = pow(s, -1, N)
    pt = ec_add(ec_mul(z * w % N, G), ec_mul(r * w % N, pub))
    return pt is not None and pt[0] % N == r


def der_parse_strict(sig: bytes):
    """Strict DER (the BIP66 form every modern verifier accepts): 30 L 02 Lr r 02 Ls s, short-form
    lengths, minimal positive integers, nothing trailing. Returns (r, s) or None."""
    n = len(sig)
    if n < 8 or n > 72 or sig[0] != 0x30 or sig[1] != n - 2 or sig[1] >= 0x80 or sig[2] != 0x02:
        return None
    lr = sig[3]
    if lr == 0 or lr >= 0x80 or 5 + lr >= n:
        return None
    r = sig[4:4 + lr]
    if sig[4 + lr] != 0x02:
        return None
    ls = sig[5 + lr]
    if ls == 0 or ls >= 0x80 or 6 + lr + ls != n:
        return None
    s = sig[6 + lr:]
    for v in (r, s):
        if v[0] & 0x80:
            return None
        if len(v) > 1 and v[0] == 0 and not (v[1] & 0x80):
            return None
    return int.from_bytes(r, "big"), int.from_bytes(s, "big")


def der_encode(r: int, s: int) -> bytes:
    def enc(v: int) -> bytes:
        b = v.to_bytes((v.bit_length() + 7) // 8 or 1, "big")
        if b[0] & 0x80:
            b = b"\x00" + b
        return b"\x02" + bytes([len(b)]) + b
    body = enc(r) + enc(s)
    return b"\x30" + bytes([len(body)]) + body


# =============================================================================================
# SignatureHash (script.cpp:818) and the small EvalScript needed for P2PK / multisig spends
# =============================================================================================

SIGHASH_ALL, SIGHASH_NONE, SIGHASH_SINGLE, SIGHASH_ANYONECANPAY = 1, 2, 3, 0x80
OP_0, OP_PUSHDATA1, OP_PUSHDATA2, OP_PUSHDATA4, OP_1NEGATE, OP_1, OP_16 = 0x00, 0x4C, 0x4D, 0x4E, 0x4F, 0x51, 0x60
OP_NOP, OP_VERIFY, OP_DUP, OP_EQUAL, OP_EQUALVERIFY, OP_HASH160 = 0x61, 0x69, 0x76, 0x87, 0x88, 0xA9
OP_CODESEPARATOR, OP_CHECKSIG, OP_CHECKSIGVERIFY, OP_CHECKMULTISIG, OP_CHECKMULTISIGVERIFY = 0xAB, 0xAC, 0xAD, 0xAE, 0xAF


def push(data: bytes) -> bytes:
    n = len(data)
    if n < OP_PUSHDATA1:
        return bytes([n]) + data
    if n <= 0xFF:
        return bytes([OP_PUSHDATA1, n]) + data
    return bytes([OP_PUSHDATA2, n & 0xFF, n >> 8]) + data


def get_op(script: bytes, pc: int):
    """CScript::GetOp: returns (opcode, data-or-None, next_pc), or None past the end / on truncation."""
    if pc >= len(script):
        return None
    op = script[pc]; pc += 1
    if op <= OP_PUSHDATA4:
        if op < OP_PUSHDATA1:
            n = op
        elif op == OP_PUSHDATA1:
            if pc >= len(script):
                return None
            n = script[pc]; pc += 1
        elif op == OP_PUSHDATA2:
            if pc + 2 > len(script):
                return None
            n = int.from_bytes(script[pc:pc + 2], "little"); pc += 2
        else:
            if pc + 4 > len(script):
                return None
            n = int.from_bytes(script[pc:pc + 4], "little"); pc += 4
        if pc + n > len(script):
            return None
        return op, script[pc:pc + n], pc + n
    return op, None, pc


def find_and_delete(script: bytes, pattern: bytes) -> bytes:
    """CScript::FindAndDelete: at every opcode boundary, delete the pattern as long as it matches there."""
    out = bytearray()
    pc = 0
    while True:
        while script[pc:pc + len(pattern)] == pattern and pattern:
            pc += len(pattern)
        r = get_op(script, pc)
        if r is None:
            out += script[pc:]
            return bytes(out)
        _op, _data, nxt = r
        out += script[pc:nxt]
        pc = nxt


def signature_hash(script_code: bytes, tx: dict, n_in: int, hash_type: int) -> bytes:
    """script.cpp:818. Note the two `return 1` cases and that the subscript has OP_CODESEPARATOR removed."""
    if n_in >= len(tx["vin"]):
        return (1).to_bytes(32, "little")
    script_code = find_and_delete(script_code, bytes([OP_CODESEPARATOR]))
    t = {"version": tx["version"], "locktime": tx["locktime"],
         "vin": [dict(v) for v in tx["vin"]], "vout": [dict(o) for o in tx["vout"]]}
    for v in t["vin"]:
        v["script"] = b""
    t["vin"][n_in]["script"] = script_code
    ht = hash_type & 0x1F
    if ht == SIGHASH_NONE:
        t["vout"] = []
        for k, v in enumerate(t["vin"]):
            if k != n_in:
                v["seq"] = 0
    elif ht == SIGHASH_SINGLE:
        if n_in >= len(t["vout"]):
            return (1).to_bytes(32, "little")
        t["vout"] = t["vout"][:n_in + 1]
        for k in range(n_in):
            t["vout"][k] = {"value": -1, "script": b""}        # CTxOut::SetNull: nValue = -1, empty script
        for k, v in enumerate(t["vin"]):
            if k != n_in:
                v["seq"] = 0
    if hash_type & SIGHASH_ANYONECANPAY:
        t["vin"] = [t["vin"][n_in]]
    return dsha256(ser_tx(t) + le(hash_type, 4))


def cast_to_bool(v: bytes) -> bool:
    """CastToBool: CBigNum(vch) != 0 — false for empty, all-zero, and negative zero (…00 80)."""
    for i, b in enumerate(v):
        if b != 0:
            return not (i == len(v) - 1 and b == 0x80)
    return False


def script_num(n: int) -> bytes:
    """CBigNum::getvch for small integers (sign-magnitude, little-endian)."""
    if n == 0:
        return b""
    neg, n = n < 0, abs(n)
    b = n.to_bytes((n.bit_length() + 7) // 8, "little")
    if b[-1] & 0x80:
        b += b"\x80" if neg else b"\x00"
    elif neg:
        b = b[:-1] + bytes([b[-1] | 0x80])
    return b


def script_int(v: bytes) -> int:
    if not v:
        return 0
    n = int.from_bytes(v[:-1] + bytes([v[-1] & 0x7F]), "little")
    return -n if v[-1] & 0x80 else n


class Unsupported(Exception):
    """The from-spec interpreter covers only what checksig.json / blocks.json use; anything else fails
    loudly rather than silently, so a passing run never rests on an opcode it did not implement."""


def check_sig(sig: bytes, pubkey: bytes, script_code: bytes, tx: dict, n_in: int) -> bool:
    """script.cpp:881 CheckSig with nHashType == 0 (as VerifySignature calls it): the hash type is the
    signature's last byte, whatever it is; the DER body is what precedes it."""
    if not sig:
        return False
    hash_type, der = sig[-1], sig[:-1]
    rs = der_parse_strict(der)
    if rs is None:
        return False
    z = int.from_bytes(signature_hash(script_code, tx, n_in, hash_type), "big")
    return ecdsa_verify(pubkey_point(pubkey), z, rs[0], rs[1])


def eval_script(script: bytes, tx: dict | None, n_in: int) -> tuple[bool, list]:
    """The subset of script.cpp EvalScript that P2PK, P2PKH and CHECKMULTISIG spends exercise."""
    stack: list[bytes] = []
    pc, begin_code_hash = 0, 0
    while pc < len(script):
        r = get_op(script, pc)
        if r is None:
            return False, stack
        op, data, pc = r
        if op <= OP_PUSHDATA4:
            stack.append(data)
        elif op == OP_1NEGATE:
            stack.append(script_num(-1))
        elif OP_1 <= op <= OP_16:
            stack.append(script_num(op - OP_1 + 1))
        elif op == OP_NOP:
            pass
        elif op == OP_VERIFY:
            if not stack:
                return False, stack
            if cast_to_bool(stack[-1]):
                stack.pop()
            else:
                return False, stack
        elif op == OP_DUP:
            if not stack:
                return False, stack
            stack.append(stack[-1])
        elif op == OP_HASH160:
            if not stack:
                return False, stack
            stack.append(hash160(stack.pop()))
        elif op in (OP_EQUAL, OP_EQUALVERIFY):
            if len(stack) < 2:
                return False, stack
            eq = stack[-1] == stack[-2]
            del stack[-2:]
            stack.append(b"\x01" if eq else b"")
            if op == OP_EQUALVERIFY:
                if eq:
                    stack.pop()
                else:
                    return False, stack
        elif op == OP_CODESEPARATOR:
            begin_code_hash = pc
        elif op in (OP_CHECKSIG, OP_CHECKSIGVERIFY):
            if len(stack) < 2:
                return False, stack
            sig, pub = stack[-2], stack[-1]
            code = find_and_delete(script[begin_code_hash:], push(sig))   # "drop the signature"
            ok = check_sig(sig, pub, code, tx, n_in) if tx is not None else False
            del stack[-2:]
            stack.append(b"\x01" if ok else b"")
            if op == OP_CHECKSIGVERIFY:
                if ok:
                    stack.pop()
                else:
                    return False, stack
        elif op in (OP_CHECKMULTISIG, OP_CHECKMULTISIGVERIFY):
            i = 1
            if len(stack) < i:
                return False, stack
            nkeys = script_int(stack[-i])
            if nkeys < 0 or nkeys > 20:
                return False, stack
            i += 1
            ikey = i
            i += nkeys
            if len(stack) < i:
                return False, stack
            nsigs = script_int(stack[-i])
            if nsigs < 0 or nsigs > nkeys:
                return False, stack
            i += 1
            isig = i
            i += nsigs
            if len(stack) < i:
                return False, stack
            code = script[begin_code_hash:]
            for k in range(nsigs):
                code = find_and_delete(code, push(stack[-(isig + k)]))
            ok = True
            while ok and nsigs > 0:
                sig, pub = stack[-isig], stack[-ikey]
                if tx is not None and check_sig(sig, pub, code, tx, n_in):
                    isig += 1
                    nsigs -= 1
                ikey += 1
                nkeys -= 1
                if nsigs > nkeys:
                    ok = False
            del stack[-i:]                          # pops one element more than it consumed (the off-by-one)
            stack.append(b"\x01" if ok else b"")
            if op == OP_CHECKMULTISIGVERIFY:
                if ok:
                    stack.pop()
                else:
                    return False, stack
        else:
            raise Unsupported(f"opcode 0x{op:02x} is outside the from-spec subset")
    return True, stack


def verify_spend(script_sig: bytes, script_pubkey: bytes, tx: dict, n_in: int) -> bool:
    """script.cpp:1126 VerifySignature: EvalScript(scriptSig + OP_CODESEPARATOR + scriptPubKey), true iff
    execution completes and CastToBool(top)."""
    ok, stack = eval_script(script_sig + bytes([OP_CODESEPARATOR]) + script_pubkey, tx, n_in)
    return bool(ok and stack and cast_to_bool(stack[-1]))


# =============================================================================================
# The 2009 block / transaction acceptance rules, in main.cpp's order, with main.cpp's error strings
# =============================================================================================

class Chain2009:
    """CheckBlock -> (orphan?) -> AcceptBlock -> AddToBlockIndex -> SetBestChain/ConnectBlock, and
    AcceptTransaction for loose transactions, over an in-memory index, UTXO set and relay pool.

    `pow_limit_nbits` is bnProofOfWorkLimit: 0x1d00ffff on the 2009 chain; the exported corpus uses
    an easy limit so its blocks can be mined at export time (a NEW-EXP parameter, stated in the JSON).
    Blocks are connected only when they extend the current tip; equal-work side blocks stay in the
    index unconnected, exactly as v0.1 leaves a ConnectBlock failure in mapBlockIndex with zero work.
    """

    def __init__(self, pow_limit_nbits: int, genesis_hash: bytes):
        self.pow_limit, _, _ = set_compact(pow_limit_nbits)
        self.genesis_hash = genesis_hash
        self.index: dict[bytes, dict] = {}        # hash -> {height, prev, time, bits, main}
        self.main: list[bytes] = []               # main-chain hashes in order
        self.utxo: dict[tuple, dict] = {}         # (txid, n) -> {value, script, height, coinbase}
        self.txindex: dict[bytes, int] = {}       # txid -> height, for every tx ever connected
        self.spent: dict[tuple, bytes] = {}       # outpoint -> spending txid (for "already used")
        self.mempool: dict[bytes, dict] = {}      # txid -> tx
        self.mempool_spends: dict[tuple, bytes] = {}
        self.log: list[str] = []
        # VerifySignature hook: None = the from-spec subset interpreter above; replay/fake2009.py plugs the
        # lab's full-vocabulary model in so it can grade every evalscript spend locally.
        self.spend_verifier = None

    # ---- helpers ------------------------------------------------------------------------------
    @property
    def tip(self) -> bytes | None:
        return self.main[-1] if self.main else None

    @property
    def height(self) -> int:
        return len(self.main) - 1

    def median_time_past(self, h: bytes) -> int:
        times = []
        cur = h
        while cur is not None and len(times) < N_MEDIAN_TIME_SPAN:
            e = self.index[cur]
            times.append(e["time"])
            cur = e["prev"]
        times.sort()
        return times[len(times) // 2]

    def next_work_required(self, prev: bytes | None) -> int:
        if prev is None:
            return get_compact(self.pow_limit)
        e = self.index[prev]
        if (e["height"] + 1) % 2016 != 0:
            return e["bits"]                       # only every 2016 blocks; the corpus stays below that
        raise Unsupported("retarget boundary reached; retarget.json covers that arithmetic")

    def subsidy(self, best_height: int) -> int:
        return (50 * COIN) >> (max(best_height, 0) // 210000)   # GetBlockValue uses nBestHeight (main.cpp:675)

    def _err(self, msg: str) -> str:
        self.log.append("ERROR: " + msg)
        return msg

    # ---- CTransaction::CheckTransaction (main.h:442) -------------------------------------------
    def check_transaction(self, tx: dict) -> str | None:
        if not tx["vin"] or not tx["vout"]:
            return "CTransaction::CheckTransaction() : vin or vout empty"
        for o in tx["vout"]:
            if o["value"] < 0:
                return "CTransaction::CheckTransaction() : txout.nValue negative"
        if is_coinbase(tx):
            if not (2 <= len(tx["vin"][0]["script"]) <= 100):
                return "CTransaction::CheckTransaction() : coinbase script size"
        else:
            for vi in tx["vin"]:
                if vi["prevhash"] == b"\x00" * 32 and vi["n"] == 0xFFFFFFFF:
                    return "CTransaction::CheckTransaction() : prevout is null"
        return None

    # ---- CTransaction::ConnectInputs (main.cpp:772), fBlock or loose ---------------------------
    def connect_inputs(self, tx: dict, block_height: int | None, pending: dict, pending_spent: dict,
                       loose: bool) -> tuple[str | None, int]:
        """Returns (error, fee). `pending` holds outputs created earlier in the same block (fBlock) or by
        mempool transactions (loose); `pending_spent` the outpoints they spent."""
        if is_coinbase(tx):
            return None, 0
        best_height = self.height
        value_in = 0
        for i, vi in enumerate(tx["vin"]):
            key = (vi["prevhash"], vi["n"])
            coin = self.utxo.get(key) or pending.get(key)
            if coin is None:
                if key in self.spent or key in pending_spent:
                    return "ConnectInputs() : prev tx already used", 0     # main.cpp:840, spent outpoint
                if vi["prevhash"] in self.txindex:
                    return "ConnectInputs() : prevout.n out of range", 0
                if loose:
                    return "ConnectInputs() : mapTransactions prev not found", 0   # -> orphan tx
                return "ConnectInputs() : prev tx index entry not found", 0
            if coin["coinbase"] and best_height - coin["height"] < COINBASE_MATURITY - 1:
                return "ConnectInputs() : tried to spend coinbase at depth", 0
            if not (self.spend_verifier or verify_spend)(vi["script"], coin["script"], tx, i):
                return "ConnectInputs() : VerifySignature failed", 0
            if key in pending_spent:
                return "ConnectInputs() : prev tx already used", 0
            pending_spent[key] = txid(tx)
            value_in += coin["value"]
        fee = value_in - value_out(tx)
        if fee < 0:
            return "ConnectInputs() : nTxFee < 0", 0
        return None, fee

    # ---- CTransaction::AcceptTransaction (main.cpp:406) ----------------------------------------
    def accept_tx(self, raw: bytes) -> tuple[bool, str]:
        tx, _ = parse_tx(raw)
        h = txid(tx)
        if is_coinbase(tx):
            return False, self._err("AcceptTransaction() : coinbase as individual tx")
        e = self.check_transaction(tx)
        if e:
            self._err(e)
            return False, self._err("AcceptTransaction() : CheckTransaction failed")
        if h in self.mempool or h in self.txindex:
            return False, "already have"
        for vi in tx["vin"]:
            if (vi["prevhash"], vi["n"]) in self.mempool_spends:
                return False, "conflicts with a pool transaction"           # replacement not modelled
        pending = {(t, n): {"value": o["value"], "script": o["script"], "height": None, "coinbase": False}
                   for t, mt in self.mempool.items() for n, o in enumerate(mt["vout"])}
        spent = dict(self.mempool_spends)
        err, _fee = self.connect_inputs(tx, None, pending, spent, loose=True)
        if err:
            self._err(err)
            return False, self._err("AcceptTransaction() : ConnectInputs failed")
        self.mempool[h] = tx
        for vi in tx["vin"]:
            self.mempool_spends[(vi["prevhash"], vi["n"])] = h
        self.log.append(f"AcceptTransaction(): accepted {h[::-1].hex()[:6]}")
        return True, "accepted"

    # ---- CBlock::CheckBlock (main.cpp:1154) ----------------------------------------------------
    def check_block(self, blk: dict) -> str | None:
        txs, f = blk["txs"], blk["fields"]
        if not txs or len(txs) > MAX_SIZE or len(blk["raw"]) > MAX_SIZE:
            return "CheckBlock() : size limits failed"
        # nTime > GetAdjustedTime() + 2h is a wall-clock rule and is not replayed from data
        if not is_coinbase(txs[0]):
            return "CheckBlock() : first tx is not coinbase"
        for tx in txs[1:]:
            if is_coinbase(tx):
                return "CheckBlock() : more than one coinbase"
        for tx in txs:
            e = self.check_transaction(tx)
            if e:
                self._err(e)
                return "CheckBlock() : CheckTransaction failed"
        target, _neg, _ovf = set_compact(f["nBits"])
        if target > self.pow_limit:
            return "CheckBlock() : nBits below minimum work"
        if int.from_bytes(blk["hash"], "little") > target:
            return "CheckBlock() : hash doesn't match nBits"
        if f["hashMerkleRoot"] != merkle_root([txid(t) for t in txs]):
            return "CheckBlock() : hashMerkleRoot mismatch"
        return None

    # ---- ProcessBlock / AcceptBlock / ConnectBlock -----------------------------------------------
    def process_block(self, raw: bytes) -> dict:
        blk = parse_block(raw)
        h, f = blk["hash"], blk["fields"]
        res = {"hash": h, "verdict": "reject", "stage": None, "reason": None}
        if h in self.index:
            res.update(verdict="duplicate", reason="ProcessBlock() : already have block")
            return res
        e = self.check_block(blk)
        if e:
            self._err(e)
            self._err("ProcessBlock() : CheckBlock FAILED")
            res.update(stage="CheckBlock", reason=e)
            return res
        is_genesis = h == self.genesis_hash and not self.index
        if not is_genesis and f["hashPrevBlock"] not in self.index:
            self.log.append(f"ProcessBlock: ORPHAN BLOCK, prev={f['hashPrevBlock'][::-1].hex()[:14]}")
            res.update(verdict="orphan", stage="ProcessBlock", reason="ProcessBlock: ORPHAN BLOCK")
            return res
        # AcceptBlock (main.cpp:1192)
        prev = None if is_genesis else f["hashPrevBlock"]
        if prev is not None:
            if f["nTime"] <= self.median_time_past(prev):
                e = self._err("AcceptBlock() : block's timestamp is too early")
                self._err("ProcessBlock() : AcceptBlock FAILED")
                res.update(stage="AcceptBlock", reason=e)
                return res
            if f["nBits"] != self.next_work_required(prev):
                e = self._err("AcceptBlock() : incorrect proof of work")
                self._err("ProcessBlock() : AcceptBlock FAILED")
                res.update(stage="AcceptBlock", reason=e)
                return res
        height = 0 if prev is None else self.index[prev]["height"] + 1
        self.index[h] = {"height": height, "prev": prev, "time": f["nTime"], "bits": f["nBits"], "main": False}
        # AddToBlockIndex -> SetBestChain only for more work; with uniform nBits that means "extends the tip"
        if prev is not None and prev != self.tip:
            res.update(verdict="side", stage="AddToBlockIndex", reason="not more work than the best chain")
            self.log.append("ProcessBlock: ACCEPTED")
            return res
        e = self.connect_block(blk, height)
        if e:
            self._err("SetBestChain() : ConnectBlock failed")
            self._err("ProcessBlock() : AcceptBlock FAILED")
            res.update(stage="ConnectBlock", reason=e)
            return res
        self.index[h]["main"] = True
        self.main.append(h)
        self.log.append(f"SetBestChain: new best={h[::-1].hex()[:16]}  height={height}")
        self.log.append("ProcessBlock: ACCEPTED")
        res.update(verdict="accept", stage="ConnectBlock", reason="ProcessBlock: ACCEPTED")
        return res

    def connect_block(self, blk: dict, height: int) -> str | None:
        """ConnectBlock (main.cpp:934): every tx through ConnectInputs in order (fBlock), then the
        coinbase claim against GetBlockValue(nFees), which is computed at nBestHeight (the tip before
        this block). Atomic: nothing is applied unless the whole block connects."""
        txs = blk["txs"]
        pending: dict[tuple, dict] = {}
        pending_spent: dict[tuple, bytes] = {}
        fees = 0
        for tx in txs:
            err, fee = self.connect_inputs(tx, height, pending, pending_spent, loose=False)
            if err:
                self._err(err)
                return err
            fees += fee
            t = txid(tx)
            for n, o in enumerate(tx["vout"]):
                pending[(t, n)] = {"value": o["value"], "script": o["script"], "height": height,
                                   "coinbase": is_coinbase(tx)}
        if value_out(txs[0]) > self.subsidy(self.height) + fees:
            return "SetBestChain() : ConnectBlock failed"         # main.cpp:953 returns false silently
        for key, spender in pending_spent.items():
            self.utxo.pop(key, None)
            pending.pop(key, None)
            self.spent[key] = spender
        for key, coin in pending.items():
            self.utxo[key] = coin
        for tx in txs:
            t = txid(tx)
            self.txindex[t] = height
            self.mempool.pop(t, None)
            for vi in tx["vin"]:
                self.mempool_spends.pop((vi["prevhash"], vi["n"]), None)
        return None


# =============================================================================================
# suite checks
# =============================================================================================

def load(name: str) -> dict:
    return json.loads((HERE / name).read_text(encoding="ascii"))


def check_manifest() -> list[str]:
    fails = []
    for line in (HERE / "MANIFEST.sha256").read_text(encoding="ascii").splitlines():
        digest, name = line.split("  ", 1)
        if hashlib.sha256((HERE / name).read_bytes()).hexdigest() != digest:
            fails.append(f"manifest: {name} hash mismatch")
    return fails


def check_retarget() -> tuple[int, list[str]]:
    d = load("retarget.json")
    k = d["constants"]
    n_interval, timespan = k["nInterval"], k["nTargetTimespan"]
    pow_limit, _, _ = set_compact(int(k["bnProofOfWorkLimit_nbits"], 16))
    fails, n = [], 0
    for v in d["vectors"]:
        n += 1
        w = v["window"]
        times = [w["t0"] + i * w["spacing"] for i in range(w["count"])]
        if w["last_override"] is not None:
            times[-1] = w["last_override"]
        old, _, _ = set_compact(int(v["old_nbits"], 16))
        span = times[-1] - times[-n_interval]
        if span != v["n_actual_timespan"]:
            fails.append(f"retarget {v['label']}: span {span} != {v['n_actual_timespan']}")
        span = max(timespan // 4, min(timespan * 4, span))
        new = min(old * span // timespan, pow_limit)
        got = f"0x{get_compact(new):08x}"
        if got != v["new_nbits"]:
            fails.append(f"retarget {v['label']}: {got} != {v['new_nbits']}")
    for c in d["nbits_codec"]:
        n += 1
        t, neg, ovf = set_compact(int(c["nbits"], 16))
        if (f"{t:064x}", neg, ovf, f"0x{get_compact(t):08x}", str((1 << 256) // (t + 1))) != (
                c["target_hex"], c["negative"], c["overflow"], c["roundtrip_nbits"], c["expected_hashes"]):
            fails.append(f"nbits codec {c['nbits']}: mismatch")
    return n, fails


def check_merkle() -> tuple[int, list[str]]:
    d = load("merkle.json")
    fails, n = [], 0
    for v in d["vectors"]:
        n += 1
        if merkle_root([bytes.fromhex(x) for x in v["leaves_hex"]]).hex() != v["root_hex"]:
            fails.append(f"merkle {v['label']}: root mismatch")
    return n, fails


def check_headers() -> tuple[int, list[str]]:
    d = load("headers.json")
    fails, n = [], 0
    for v in d["vectors"]:
        n += 1
        f = v["fields"]
        hdr = (f["nVersion"].to_bytes(4, "little") + bytes.fromhex(f["hashPrevBlock"])[::-1]
               + bytes.fromhex(f["hashMerkleRoot"])[::-1] + f["nTime"].to_bytes(4, "little")
               + int(f["nBits"], 16).to_bytes(4, "little") + f["nNonce"].to_bytes(4, "little"))
        if hdr.hex() != v["header_hex"] or len(hdr) != 80:
            fails.append(f"headers {v['label']}: serialization mismatch")
        if dsha256(hdr)[::-1].hex() != v["hash"]:
            fails.append(f"headers {v['label']}: hash mismatch")
        if pow_ok(hdr, int(f["nBits"], 16)) != v["pow_ok"]:
            fails.append(f"headers {v['label']}: pow_ok mismatch")
    return n, fails


def check_sighash() -> tuple[int, list[str]]:
    d = load("sighash.json")
    fails, n = [], 0
    for v in d["vectors"]:
        n += 1
        tx, _ = parse_tx(bytes.fromhex(v["tx_hex"]))
        got = signature_hash(bytes.fromhex(v["script_code_hex"]), tx, v["n_in"], v["hash_type"]).hex()
        if got != v["digest_hex"]:
            fails.append(f"sighash {v['label']}: {got} != {v['digest_hex']}")
    return n, fails


def check_checksig() -> tuple[int, list[str]]:
    d = load("checksig.json")
    fails, n = [], 0
    for v in d["vectors"]:
        n += 1
        tx, _ = parse_tx(bytes.fromhex(v["tx_hex"]))
        try:
            got = verify_spend(bytes.fromhex(v["script_sig_hex"]), bytes.fromhex(v["script_pubkey_hex"]),
                               tx, v["n_in"])
        except Unsupported as e:
            fails.append(f"checksig {v['label']}: {e}")
            continue
        if got != v["expected_strict_der"]:
            fails.append(f"checksig {v['label']}: from-spec {got} != expected_strict_der {v['expected_strict_der']}")
    return n, fails


def check_blocks() -> tuple[int, list[str]]:
    d = load("blocks.json")
    chain = Chain2009(int(d["pow_limit_nbits"], 16), bytes.fromhex(d["genesis_hash"])[::-1])
    fails, n = [], 0
    for v in d["vectors"]:
        n += 1
        try:
            r = chain.process_block(bytes.fromhex(v["block_hex"]))
        except Unsupported as e:
            fails.append(f"blocks {v['label']}: {e}")
            continue
        exp = (v["expect"], v["stage"], v["reason"])
        got = (r["verdict"], r["stage"], r["reason"])
        if got != exp:
            fails.append(f"blocks {v['label']}: got {got} expected {exp}")
        after = {"tip_height": chain.height, "utxo_count": len(chain.utxo)}
        if after != v["after"]:
            fails.append(f"blocks {v['label']}: state {after} != {v['after']}")
    return n, fails


def check_evalscript() -> tuple[int, list[str]]:
    sys.path.insert(0, str(HERE.parent / "model"))
    import cscript                                  # noqa: E402
    from evalscript_model import cast_to_bool as ctb, run  # noqa: E402
    d = load("evalscript.json")
    fails, n = [], 0
    for v in d["vectors"]:
        n += 1
        ok, stack = run(cscript.parse(bytes.fromhex(v["script_hex"])), None)
        valid = bool(ok and stack and ctb(stack[-1]))
        top = stack[-1].hex() if (ok and stack) else None
        depth = len(stack) if ok else None
        if (bool(ok), valid, top, depth) != (v["ok"], v["valid"], v["top_hex"], v["stack_depth"]):
            fails.append(f"evalscript {v['label']}: got ok={ok} valid={valid} top={top}")
    return n, fails


def main(argv: list[str]) -> int:
    fails = check_manifest()
    total = 0
    suites = [("retarget", check_retarget), ("merkle", check_merkle), ("headers", check_headers),
              ("sighash", check_sighash), ("checksig", check_checksig), ("blocks", check_blocks)]
    if "--no-model" not in argv:
        suites.append(("evalscript (via ../model)", check_evalscript))
    for name, fn in suites:
        n, f = fn()
        total += n
        fails += f
        print(f"{name:28s} {n:4d} vectors  {'OK' if not f else str(len(f)) + ' FAIL'}")
    for f in fails:
        print("  ", f)
    print(f"total {total} vectors, {len(fails)} failures")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
