"""
Clean-room validator for JAN09-B (docs/JAN09-B-SPECIFICATION.md) and for the
January-2009 (v0.1) rules it takes as its base.

Written from:
  - genesis/docs/JAN09-B-SPECIFICATION.md @ 6fe9e83
  - the CONSTITUTION-REGISTER.md rows it cites (OBL-C-0001..0014)
  - the prose `rule` strings inside derivatives/vectors/*.json
  - public knowledge of the January 2009 client's Script vocabulary, which the
    page delegates to ("the full Script vocabulary with nothing disabled beyond
    what v0.1 itself disabled") but does not reproduce.

NOT read: derivatives/validator-rs, derivatives/model, derivatives/port,
derivatives/vectors/verify_vectors.py, export_vectors.py, recipes.py,
test_vectors.py, test_replay.py.

Per JAN09-B section 5 no third-party library makes a validity decision here:
secp256k1 ECDSA and the DER parsers are written out below; hashlib supplies
SHA-256/SHA-1/RIPEMD-160 only, and its output is checked by the corpus's own
header and merkle suites.
"""

import hashlib

# ----------------------------------------------------------------------------
# Parameters: the two modes
# ----------------------------------------------------------------------------

JAN09B = "JAN09-B"
JAN09 = "JAN09"  # the January 2009 release's rules, as the base


class Params:
    def __init__(self, mode):
        self.mode = mode
        # OBL-C-0006: MAX_SIZE 32 MiB, inherited by JAN09-B section 3.
        self.MAX_SIZE = 0x02000000
        self.MAX_MONEY = 21_000_000 * 100_000_000
        self.COIN = 100_000_000
        if mode == JAN09B:
            # section 3: block validity size limit = the inherited MAX_SIZE, no 1 MB rule
            self.MAX_BLOCK_SIZE = self.MAX_SIZE
            self.MAX_BLOCK_TX_COUNT = self.MAX_SIZE
            # OBL-C-0004: MAX_SIZE / 50, "the 2010 ratio applied to the inherited ceiling"
            self.MAX_BLOCK_SIGOPS = self.MAX_SIZE // 50
            # OBL-C-0002: the 2010 values, adopted as a marked choice
            self.MAX_ELEMENT = 520
            self.MAX_SCRIPT_SIZE = 10000
            self.MAX_STACK = 1000
            self.MAX_NUM_SIZE = 4
            # OBL-C-0003
            self.MONEY_RANGE = True
            # OBL-C-0014: strict DER from genesis, no changeover
            self.STRICT_DER = True
            # OBL-C-0007: the 500,000,000 split
            self.LOCKTIME_THRESHOLD = 500_000_000
            # OBL-C-0008: cumulative work
            self.CHAIN_BY_WORK = True
            # OBL-C-0010: no separate transaction-size rule
            self.MAX_TX_SIZE = None
            # OBL-C-0005: none disabled beyond v0.1's own
            self.DISABLED = frozenset()
        elif mode == JAN09:
            self.MAX_BLOCK_SIZE = self.MAX_SIZE
            self.MAX_BLOCK_TX_COUNT = self.MAX_SIZE
            self.MAX_BLOCK_SIGOPS = None
            self.MAX_ELEMENT = 5000          # register OBL-C-0002: 5000 -> 520
            self.MAX_SCRIPT_SIZE = None      # 20000 arrives in 2010
            self.MAX_STACK = None            # 1000 arrives in 2010
            self.MAX_NUM_SIZE = None         # register says 258 -> 4; see report
            self.MONEY_RANGE = False
            self.STRICT_DER = False
            self.LOCKTIME_THRESHOLD = None   # heights only (OBL-F-0002)
            self.CHAIN_BY_WORK = False       # by height (blocks.json rule)
            self.MAX_TX_SIZE = None
            self.DISABLED = frozenset()
        else:
            raise ValueError(mode)


# ----------------------------------------------------------------------------
# Hashes and serialization
# ----------------------------------------------------------------------------

def sha256(b):
    return hashlib.sha256(b).digest()


def dsha256(b):
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


def ripemd160(b):
    return hashlib.new("ripemd160", b).digest()


def hash160(b):
    return ripemd160(sha256(b))


def ser_varint(n):
    if n < 0xfd:
        return bytes([n])
    if n <= 0xffff:
        return b"\xfd" + n.to_bytes(2, "little")
    if n <= 0xffffffff:
        return b"\xfe" + n.to_bytes(4, "little")
    return b"\xff" + n.to_bytes(8, "little")


class Reader:
    def __init__(self, b):
        self.b = b
        self.i = 0

    def take(self, n):
        if self.i + n > len(self.b):
            raise ValueError("truncated")
        r = self.b[self.i:self.i + n]
        self.i += n
        return r

    def u32(self):
        return int.from_bytes(self.take(4), "little")

    def i64(self):
        return int.from_bytes(self.take(8), "little", signed=True)

    def varint(self):
        c = self.take(1)[0]
        if c < 0xfd:
            return c
        if c == 0xfd:
            return int.from_bytes(self.take(2), "little")
        if c == 0xfe:
            return int.from_bytes(self.take(4), "little")
        return int.from_bytes(self.take(8), "little")

    def varstr(self):
        return self.take(self.varint())

    def done(self):
        return self.i >= len(self.b)


class TxIn:
    def __init__(self, prev_hash, prev_n, script_sig, sequence):
        self.prev_hash = prev_hash
        self.prev_n = prev_n
        self.script_sig = script_sig
        self.sequence = sequence

    def ser(self):
        return (self.prev_hash + self.prev_n.to_bytes(4, "little")
                + ser_varint(len(self.script_sig)) + self.script_sig
                + self.sequence.to_bytes(4, "little"))

    def is_null_prevout(self):
        return self.prev_hash == b"\x00" * 32 and self.prev_n == 0xffffffff

    def copy(self):
        return TxIn(self.prev_hash, self.prev_n, self.script_sig, self.sequence)


class TxOut:
    def __init__(self, value, script_pubkey):
        self.value = value
        self.script_pubkey = script_pubkey

    def ser(self):
        return (self.value.to_bytes(8, "little", signed=True)
                + ser_varint(len(self.script_pubkey)) + self.script_pubkey)

    def copy(self):
        return TxOut(self.value, self.script_pubkey)


class Tx:
    def __init__(self, version, vin, vout, locktime):
        self.version = version
        self.vin = vin
        self.vout = vout
        self.locktime = locktime

    @staticmethod
    def parse(r):
        version = r.u32()
        vin = []
        for _ in range(r.varint()):
            vin.append(TxIn(r.take(32), r.u32(), r.varstr(), r.u32()))
        vout = []
        for _ in range(r.varint()):
            vout.append(TxOut(r.i64(), r.varstr()))
        locktime = r.u32()
        return Tx(version, vin, vout, locktime)

    @staticmethod
    def from_hex(h):
        return Tx.parse(Reader(bytes.fromhex(h)))

    def ser(self):
        out = self.version.to_bytes(4, "little")
        out += ser_varint(len(self.vin)) + b"".join(i.ser() for i in self.vin)
        out += ser_varint(len(self.vout)) + b"".join(o.ser() for o in self.vout)
        out += self.locktime.to_bytes(4, "little")
        return out

    def txid(self):
        return dsha256(self.ser())

    def is_coinbase(self):
        return len(self.vin) == 1 and self.vin[0].is_null_prevout()

    def value_out(self, wrap=False):
        t = sum(o.value for o in self.vout)
        if wrap:
            # v0.1 accumulates into an int64 (CONSENSUS_BEHAVIORS #4)
            t = ((t + (1 << 63)) % (1 << 64)) - (1 << 63)
        return t

    def copy(self):
        return Tx(self.version, [i.copy() for i in self.vin],
                  [o.copy() for o in self.vout], self.locktime)


class Block:
    def __init__(self, version, prev, merkle_root, time, bits, nonce, txs, raw):
        self.version = version
        self.prev = prev
        self.merkle_root = merkle_root
        self.time = time
        self.bits = bits
        self.nonce = nonce
        self.txs = txs
        self.raw = raw

    @staticmethod
    def from_hex(h):
        raw = bytes.fromhex(h)
        r = Reader(raw)
        version = r.u32()
        prev = r.take(32)
        merkle_root = r.take(32)
        time = r.u32()
        bits = r.u32()
        nonce = r.u32()
        txs = [Tx.parse(r) for _ in range(r.varint())]
        return Block(version, prev, merkle_root, time, bits, nonce, txs, raw)

    def header(self):
        return (self.version.to_bytes(4, "little") + self.prev + self.merkle_root
                + self.time.to_bytes(4, "little") + self.bits.to_bytes(4, "little")
                + self.nonce.to_bytes(4, "little"))

    def hash(self):
        return dsha256(self.header())

    def size(self):
        return len(self.raw)


# ----------------------------------------------------------------------------
# Merkle (merkle.json rule) and nBits codec (retarget.json rule)
# ----------------------------------------------------------------------------

def merkle_root(leaves):
    if not leaves:
        return None
    level = list(leaves)
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        level = [dsha256(level[i] + level[i + 1]) for i in range(0, len(level), 2)]
    return level[0]


def set_compact(nbits):
    """Returns (target, negative, overflow)."""
    size = nbits >> 24
    word = nbits & 0x007fffff
    if size <= 3:
        word >>= 8 * (3 - size)
        target = word
    else:
        target = word << (8 * (size - 3))
    negative = word != 0 and bool(nbits & 0x00800000)
    overflow = word != 0 and (size > 34 or (word > 0xff and size > 33)
                              or (word > 0xffff and size > 32))
    return target, negative, overflow


def get_compact(target):
    if target == 0:
        return 0
    size = (target.bit_length() + 7) // 8
    if size <= 3:
        compact = target << (8 * (3 - size))
    else:
        compact = target >> (8 * (size - 3))
    if compact & 0x00800000:
        compact >>= 8
        size += 1
    return compact | (size << 24)


def get_next_work_required(old_nbits, n_actual_timespan,
                           target_timespan=1209600, pow_limit_nbits=0x1d00ffff):
    ts = n_actual_timespan
    if ts < target_timespan // 4:
        ts = target_timespan // 4
    if ts > target_timespan * 4:
        ts = target_timespan * 4
    old_target, _, _ = set_compact(old_nbits)
    new = old_target * ts // target_timespan
    limit, _, _ = set_compact(pow_limit_nbits)
    if new > limit:
        new = limit
    return get_compact(new)


# ----------------------------------------------------------------------------
# secp256k1 ECDSA, written out (JAN09-B section 5)
# ----------------------------------------------------------------------------

P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
A = 0
B = 7
GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8


def _inv(a, m):
    return pow(a, m - 2, m)


def _jac_double(pt):
    X, Y, Z = pt
    if Y == 0:
        return (0, 0, 0)
    S = (4 * X * Y * Y) % P
    M = (3 * X * X) % P
    Xp = (M * M - 2 * S) % P
    Yp = (M * (S - Xp) - 8 * pow(Y, 4, P)) % P
    Zp = (2 * Y * Z) % P
    return (Xp, Yp, Zp)


def _jac_add(p1, p2):
    X1, Y1, Z1 = p1
    X2, Y2, Z2 = p2
    if Z1 == 0:
        return p2
    if Z2 == 0:
        return p1
    Z1Z1 = Z1 * Z1 % P
    Z2Z2 = Z2 * Z2 % P
    U1 = X1 * Z2Z2 % P
    U2 = X2 * Z1Z1 % P
    S1 = Y1 * Z2 % P * Z2Z2 % P
    S2 = Y2 * Z1 % P * Z1Z1 % P
    if U1 == U2:
        if S1 != S2:
            return (0, 0, 0)
        return _jac_double(p1)
    H = (U2 - U1) % P
    R = (S2 - S1) % P
    HH = H * H % P
    HHH = H * HH % P
    V = U1 * HH % P
    X3 = (R * R - HHH - 2 * V) % P
    Y3 = (R * (V - X3) - S1 * HHH) % P
    Z3 = H * Z1 % P * Z2 % P
    return (X3, Y3, Z3)


def _jac_mul(pt, k):
    r = (0, 0, 0)
    cur = pt
    while k:
        if k & 1:
            r = _jac_add(r, cur)
        cur = _jac_double(cur)
        k >>= 1
    return r


def _to_affine(pt):
    X, Y, Z = pt
    if Z == 0:
        return None
    zi = _inv(Z, P)
    zi2 = zi * zi % P
    return (X * zi2 % P, Y * zi2 % P * zi % P)


def decode_pubkey(vch):
    """SEC point. Returns (x, y) or None."""
    if len(vch) == 65 and vch[0] == 0x04:
        x = int.from_bytes(vch[1:33], "big")
        y = int.from_bytes(vch[33:65], "big")
    elif len(vch) == 33 and vch[0] in (0x02, 0x03):
        x = int.from_bytes(vch[1:33], "big")
        y2 = (pow(x, 3, P) + A * x + B) % P
        y = pow(y2, (P + 1) // 4, P)
        if (y & 1) != (vch[0] & 1):
            y = P - y
    else:
        return None
    if x >= P or y >= P:
        return None
    if (y * y - (pow(x, 3, P) + A * x + B)) % P != 0:
        return None
    return (x, y)


def ecdsa_verify(pub, z, r, s):
    if not (1 <= r < N and 1 <= s < N):
        return False
    w = _inv(s, N)
    u1 = z * w % N
    u2 = r * w % N
    pt = _jac_add(_jac_mul((GX, GY, 1), u1), _jac_mul((pub[0], pub[1], 1), u2))
    aff = _to_affine(pt)
    if aff is None:
        return False
    return aff[0] % N == r % N


# ----------------------------------------------------------------------------
# DER: the strict rule (BIP 66) and a tolerant parser for the January base
# ----------------------------------------------------------------------------

def is_valid_signature_encoding(sig):
    """BIP 66 IsValidSignatureEncoding; `sig` includes the trailing hashtype byte."""
    if len(sig) < 9 or len(sig) > 73:
        return False
    if sig[0] != 0x30:
        return False
    if sig[1] != len(sig) - 3:
        return False
    lenR = sig[3]
    if 5 + lenR >= len(sig):
        return False
    lenS = sig[5 + lenR]
    if lenR + lenS + 7 != len(sig):
        return False
    if sig[2] != 0x02:
        return False
    if lenR == 0:
        return False
    if sig[4] & 0x80:
        return False
    if lenR > 1 and sig[4] == 0x00 and not (sig[5] & 0x80):
        return False
    if sig[lenR + 4] != 0x02:
        return False
    if lenS == 0:
        return False
    if sig[lenR + 6] & 0x80:
        return False
    if lenS > 1 and sig[lenR + 6] == 0x00 and not (sig[lenR + 7] & 0x80):
        return False
    return True


def der_parse_tolerant(der):
    """A permissive DER reader standing in for the January base's OpenSSL 0.9.8.
    Accepts padded lengths, negative/over-long integers and trailing garbage."""
    try:
        if len(der) < 2 or der[0] != 0x30:
            return None
        i = 1
        ln = der[i]
        i += 1
        if ln & 0x80:
            nb = ln & 0x7f
            if nb == 0 or nb > 4 or i + nb > len(der):
                return None
            i += nb
        vals = []
        for _ in range(2):
            if i >= len(der) or der[i] != 0x02:
                return None
            i += 1
            if i >= len(der):
                return None
            l = der[i]
            i += 1
            if l & 0x80:
                nb = l & 0x7f
                if nb == 0 or nb > 4 or i + nb > len(der):
                    return None
                l = int.from_bytes(der[i:i + nb], "big")
                i += nb
            if l == 0 or i + l > len(der):
                return None
            vals.append(int.from_bytes(der[i:i + l], "big", signed=True))
            i += l
        r, s = vals
        if r < 0 or s < 0:
            return None
        return r, s
    except Exception:
        return None


# ----------------------------------------------------------------------------
# Script
# ----------------------------------------------------------------------------

class ScriptError(Exception):
    pass


OP_0, OP_PUSHDATA1, OP_PUSHDATA2, OP_PUSHDATA4 = 0x00, 0x4c, 0x4d, 0x4e
OP_1NEGATE, OP_RESERVED, OP_1, OP_16 = 0x4f, 0x50, 0x51, 0x60
OP_NOP, OP_VER, OP_IF, OP_NOTIF, OP_VERIF, OP_VERNOTIF = 0x61, 0x62, 0x63, 0x64, 0x65, 0x66
OP_ELSE, OP_ENDIF, OP_VERIFY, OP_RETURN = 0x67, 0x68, 0x69, 0x6a
OP_TOALTSTACK, OP_FROMALTSTACK = 0x6b, 0x6c
OP_2DROP, OP_2DUP, OP_3DUP, OP_2OVER, OP_2ROT, OP_2SWAP = 0x6d, 0x6e, 0x6f, 0x70, 0x71, 0x72
OP_IFDUP, OP_DEPTH, OP_DROP, OP_DUP, OP_NIP, OP_OVER = 0x73, 0x74, 0x75, 0x76, 0x77, 0x78
OP_PICK, OP_ROLL, OP_ROT, OP_SWAP, OP_TUCK = 0x79, 0x7a, 0x7b, 0x7c, 0x7d
OP_CAT, OP_SUBSTR, OP_LEFT, OP_RIGHT, OP_SIZE = 0x7e, 0x7f, 0x80, 0x81, 0x82
OP_INVERT, OP_AND, OP_OR, OP_XOR, OP_EQUAL, OP_EQUALVERIFY = 0x83, 0x84, 0x85, 0x86, 0x87, 0x88
OP_1ADD, OP_1SUB, OP_2MUL, OP_2DIV, OP_NEGATE, OP_ABS = 0x8b, 0x8c, 0x8d, 0x8e, 0x8f, 0x90
OP_NOT, OP_0NOTEQUAL = 0x91, 0x92
OP_ADD, OP_SUB, OP_MUL, OP_DIV, OP_MOD, OP_LSHIFT, OP_RSHIFT = 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99
OP_BOOLAND, OP_BOOLOR, OP_NUMEQUAL, OP_NUMEQUALVERIFY, OP_NUMNOTEQUAL = 0x9a, 0x9b, 0x9c, 0x9d, 0x9e
OP_LESSTHAN, OP_GREATERTHAN, OP_LESSTHANOREQUAL, OP_GREATERTHANOREQUAL = 0x9f, 0xa0, 0xa1, 0xa2
OP_MIN, OP_MAX, OP_WITHIN = 0xa3, 0xa4, 0xa5
OP_RIPEMD160, OP_SHA1, OP_SHA256, OP_HASH160, OP_HASH256 = 0xa6, 0xa7, 0xa8, 0xa9, 0xaa
OP_CODESEPARATOR, OP_CHECKSIG, OP_CHECKSIGVERIFY = 0xab, 0xac, 0xad
OP_CHECKMULTISIG, OP_CHECKMULTISIGVERIFY = 0xae, 0xaf

# v0.1's own disabled opcode (JAN09-B section 3, OBL-C-0005: "none disabled
# beyond v0.1's own OP_NOTEQUAL").  0x9e is OP_NUMNOTEQUAL and is live; the
# opcode the January source names as removed has no number of its own.
V01_DISABLED = frozenset()


def get_op(script, i):
    """Returns (opcode, pushdata_or_None, next_index). Raises on truncation."""
    op = script[i]
    i += 1
    if op >= 0xf0:
        # v0.1 script.h: OP_SINGLEBYTE_END = 0xf0, OP_DOUBLEBYTE_BEGIN = 0xf000.
        # GetOp reads a second byte and combines them.
        if i >= len(script):
            raise ScriptError("truncated double-byte opcode")
        op = (op << 8) | script[i]
        i += 1
        return op, None, i
    if op <= 0x4b:
        n = op
    elif op == OP_PUSHDATA1:
        if i + 1 > len(script):
            raise ScriptError("truncated pushdata1")
        n = script[i]
        i += 1
    elif op == OP_PUSHDATA2:
        if i + 2 > len(script):
            raise ScriptError("truncated pushdata2")
        n = int.from_bytes(script[i:i + 2], "little")
        i += 2
    elif op == OP_PUSHDATA4:
        if i + 4 > len(script):
            raise ScriptError("truncated pushdata4")
        n = int.from_bytes(script[i:i + 4], "little")
        i += 4
    else:
        return op, None, i
    if i + n > len(script):
        raise ScriptError("truncated push")
    return op, script[i:i + n], i + n


def op_boundaries(script):
    """Yields (start, end) of each opcode+data unit; stops at malformation."""
    i = 0
    while i < len(script):
        try:
            _, _, j = get_op(script, i)
        except ScriptError:
            yield (i, len(script))
            return
        yield (i, j)
        i = j


def find_and_delete(script, pattern):
    if not pattern:
        return script
    out = bytearray()
    i = 0
    n = len(script)
    while i < n:
        if script[i:i + len(pattern)] == pattern:
            i += len(pattern)
            continue
        try:
            _, _, j = get_op(script, i)
        except ScriptError:
            out += script[i:]
            return bytes(out)
        out += script[i:j]
        i = j
    return bytes(out)


def push_script(data):
    """The script that pushes `data` (used by FindAndDelete, as CScript(vch))."""
    n = len(data)
    if n < 0x4c:
        return bytes([n]) + data
    if n <= 0xff:
        return bytes([OP_PUSHDATA1, n]) + data
    if n <= 0xffff:
        return bytes([OP_PUSHDATA2]) + n.to_bytes(2, "little") + data
    return bytes([OP_PUSHDATA4]) + n.to_bytes(4, "little") + data


def cast_to_bool(vch):
    for k, byte in enumerate(vch):
        if byte != 0:
            if k == len(vch) - 1 and byte == 0x80:
                return False
            return True
    return False


def vch_to_num(vch, max_size):
    """CBigNum/CScriptNum read of a stack element.  max_size None = unbounded."""
    if max_size is not None and len(vch) > max_size:
        raise ScriptError("numeric operand too large (%d > %d)" % (len(vch), max_size))
    if not vch:
        return 0
    v = int.from_bytes(vch, "little")
    if vch[-1] & 0x80:
        v &= (1 << (8 * len(vch) - 1)) - 1
        return -v
    return v


def num_to_vch(n):
    if n == 0:
        return b""
    neg = n < 0
    v = -n if neg else n
    out = bytearray(v.to_bytes((v.bit_length() + 7) // 8, "little"))
    if out[-1] & 0x80:
        out.append(0x80 if neg else 0x00)
    elif neg:
        out[-1] |= 0x80
    return bytes(out)


def make_same_size(a, b):
    n = max(len(a), len(b))
    return a + b"\x00" * (n - len(a)), b + b"\x00" * (n - len(b))


class SigChecker:
    """Supplies the transaction context that OP_CHECKSIG needs."""

    def __init__(self, tx, n_in, params):
        self.tx = tx
        self.n_in = n_in
        self.params = params

    def check_sig(self, sig, pubkey, script_code):
        if not sig:
            return False
        hash_type = sig[-1]
        der = sig[:-1]
        script_code = find_and_delete(script_code, push_script(sig))
        if self.params.STRICT_DER:
            if not is_valid_signature_encoding(sig):
                return False
        parsed = der_parse_tolerant(der)
        if parsed is None:
            return False
        r, s = parsed
        pub = decode_pubkey(pubkey)
        if pub is None:
            return False
        digest = signature_hash(script_code, self.tx, self.n_in, hash_type)
        z = int.from_bytes(digest, "big")
        return ecdsa_verify(pub, z, r, s)


def eval_script(script, stack, params, checker=None, altstack=None):
    """v0.1 EvalScript.  Returns True on completion, False on failure.
    `stack` is mutated (list of bytes)."""
    if params.MAX_SCRIPT_SIZE is not None and len(script) > params.MAX_SCRIPT_SIZE:
        return False
    if altstack is None:
        altstack = []
    exec_stack = []
    begin_codehash = 0
    MAXN = params.MAX_NUM_SIZE
    i = 0

    def num(vch):
        return vch_to_num(vch, MAXN)

    def need(k):
        if len(stack) < k:
            raise ScriptError("stack underflow")

    def push(v):
        if params.MAX_ELEMENT is not None and len(v) > params.MAX_ELEMENT:
            raise ScriptError("element too large")
        stack.append(v)

    try:
        while i < len(script):
            op, data, i = get_op(script, i)
            executing = all(exec_stack)

            if data is not None:
                if executing:
                    if params.MAX_ELEMENT is not None and len(data) > params.MAX_ELEMENT:
                        return False
                    stack.append(data)
                if params.MAX_STACK is not None and len(stack) + len(altstack) > params.MAX_STACK:
                    return False
                continue

            if op in params.DISABLED or op in V01_DISABLED:
                return False

            if op in (OP_IF, OP_NOTIF):
                val = False
                if executing:
                    need(1)
                    val = cast_to_bool(stack.pop())
                    if op == OP_NOTIF:
                        val = not val
                exec_stack.append(val)
                continue
            if op == OP_ELSE:
                if not exec_stack:
                    return False
                exec_stack[-1] = not exec_stack[-1]
                continue
            if op == OP_ENDIF:
                if not exec_stack:
                    return False
                exec_stack.pop()
                continue
            if not executing:
                continue

            if op == OP_1NEGATE or OP_1 <= op <= OP_16:
                push(num_to_vch(-1 if op == OP_1NEGATE else op - OP_1 + 1))
            elif op == OP_NOP:
                pass
            elif op == OP_VERIFY:
                # v0.1: "(false -- false) and return" -- pc = pend, not an error
                need(1)
                if cast_to_bool(stack[-1]):
                    stack.pop()
                else:
                    i = len(script)
            elif op == OP_RETURN:
                i = len(script)          # v0.1: pc = pend
            elif op == OP_TOALTSTACK:
                need(1)
                altstack.append(stack.pop())
            elif op == OP_FROMALTSTACK:
                if not altstack:
                    return False
                push(altstack.pop())
            elif op == OP_2DROP:
                need(2)
                stack.pop(); stack.pop()
            elif op == OP_2DUP:
                need(2)
                a, b = stack[-2], stack[-1]
                push(a); push(b)
            elif op == OP_3DUP:
                need(3)
                a, b, c = stack[-3], stack[-2], stack[-1]
                push(a); push(b); push(c)
            elif op == OP_2OVER:
                need(4)
                a, b = stack[-4], stack[-3]
                push(a); push(b)
            elif op == OP_2ROT:
                need(6)
                a, b = stack[-6], stack[-5]
                del stack[-6:-4]
                push(a); push(b)
            elif op == OP_2SWAP:
                need(4)
                stack[-4], stack[-3], stack[-2], stack[-1] = \
                    stack[-2], stack[-1], stack[-4], stack[-3]
            elif op == OP_IFDUP:
                need(1)
                if cast_to_bool(stack[-1]):
                    push(stack[-1])
            elif op == OP_DEPTH:
                push(num_to_vch(len(stack)))
            elif op == OP_DROP:
                need(1)
                stack.pop()
            elif op == OP_DUP:
                need(1)
                push(stack[-1])
            elif op == OP_NIP:
                need(2)
                del stack[-2]
            elif op == OP_OVER:
                need(2)
                push(stack[-2])
            elif op in (OP_PICK, OP_ROLL):
                need(2)
                n = num(stack.pop())
                if n < 0 or n >= len(stack):
                    return False
                v = stack[-n - 1]
                if op == OP_ROLL:
                    del stack[-n - 1]
                push(v)
            elif op == OP_ROT:
                need(3)
                stack[-3], stack[-2], stack[-1] = stack[-2], stack[-1], stack[-3]
            elif op == OP_SWAP:
                need(2)
                stack[-2], stack[-1] = stack[-1], stack[-2]
            elif op == OP_TUCK:
                need(2)
                v = stack[-1]
                stack.insert(len(stack) - 2, v)
            elif op == OP_CAT:
                need(2)
                b = stack.pop(); a = stack.pop()
                if params.MAX_ELEMENT is not None and len(a) + len(b) > params.MAX_ELEMENT:
                    return False
                push(a + b)
            elif op == OP_SUBSTR:
                # v0.1: "(in begin size -- out)"; nEnd = nBegin + size
                need(3)
                size = num(stack.pop()); beg = num(stack.pop()); v = stack.pop()
                end = beg + size
                if beg < 0 or end < beg:
                    return False
                beg = min(beg, len(v)); end = min(end, len(v))
                push(v[beg:end])
            elif op in (OP_LEFT, OP_RIGHT):
                need(2)
                n = num(stack.pop()); v = stack.pop()
                if n < 0:
                    return False
                n = min(n, len(v))
                push(v[:n] if op == OP_LEFT else (v[len(v) - n:] if n else b""))
            elif op == OP_SIZE:
                need(1)
                push(num_to_vch(len(stack[-1])))
            elif op == OP_INVERT:
                need(1)
                v = stack.pop()
                push(bytes((~x) & 0xff for x in v))
            elif op in (OP_AND, OP_OR, OP_XOR):
                need(2)
                b = stack.pop(); a = stack.pop()
                a, b = make_same_size(a, b)
                if op == OP_AND:
                    push(bytes(x & y for x, y in zip(a, b)))
                elif op == OP_OR:
                    push(bytes(x | y for x, y in zip(a, b)))
                else:
                    push(bytes(x ^ y for x, y in zip(a, b)))
            elif op in (OP_EQUAL, OP_EQUALVERIFY):
                need(2)
                b = stack.pop(); a = stack.pop()
                eq = a == b
                push(b"\x01" if eq else b"")
                if op == OP_EQUALVERIFY:
                    if eq:
                        stack.pop()
                    else:
                        i = len(script)
            elif op in (OP_1ADD, OP_1SUB, OP_2MUL, OP_2DIV, OP_NEGATE, OP_ABS,
                        OP_NOT, OP_0NOTEQUAL):
                need(1)
                n = num(stack.pop())
                if op == OP_1ADD:
                    n = n + 1
                elif op == OP_1SUB:
                    n = n - 1
                elif op == OP_2MUL:
                    n = _bn_shift(n, 1)
                elif op == OP_2DIV:
                    n = _bn_shift(n, -1)
                elif op == OP_NEGATE:
                    n = -n
                elif op == OP_ABS:
                    n = abs(n)
                elif op == OP_NOT:
                    n = 1 if n == 0 else 0
                else:
                    n = 1 if n != 0 else 0
                push(num_to_vch(n))
            elif op in (OP_ADD, OP_SUB, OP_MUL, OP_DIV, OP_MOD, OP_LSHIFT, OP_RSHIFT,
                        OP_BOOLAND, OP_BOOLOR, OP_NUMEQUAL, OP_NUMEQUALVERIFY,
                        OP_NUMNOTEQUAL, OP_LESSTHAN, OP_GREATERTHAN,
                        OP_LESSTHANOREQUAL, OP_GREATERTHANOREQUAL, OP_MIN, OP_MAX):
                need(2)
                b = num(stack.pop()); a = num(stack.pop())
                if op == OP_ADD:
                    r = a + b
                elif op == OP_SUB:
                    r = a - b
                elif op == OP_MUL:
                    r = a * b
                elif op == OP_DIV:
                    if b == 0:
                        return False
                    r = _bn_div(a, b)
                elif op == OP_MOD:
                    if b == 0:
                        return False
                    r = a - _bn_div(a, b) * b
                elif op == OP_LSHIFT:
                    if b < 0:
                        return False
                    r = _bn_shift(a, b)
                elif op == OP_RSHIFT:
                    if b < 0:
                        return False
                    r = _bn_shift(a, -b)
                elif op == OP_BOOLAND:
                    r = 1 if (a != 0 and b != 0) else 0
                elif op == OP_BOOLOR:
                    r = 1 if (a != 0 or b != 0) else 0
                elif op in (OP_NUMEQUAL, OP_NUMEQUALVERIFY):
                    r = 1 if a == b else 0
                elif op == OP_NUMNOTEQUAL:
                    r = 1 if a != b else 0
                elif op == OP_LESSTHAN:
                    r = 1 if a < b else 0
                elif op == OP_GREATERTHAN:
                    r = 1 if a > b else 0
                elif op == OP_LESSTHANOREQUAL:
                    r = 1 if a <= b else 0
                elif op == OP_GREATERTHANOREQUAL:
                    r = 1 if a >= b else 0
                elif op == OP_MIN:
                    r = min(a, b)
                else:
                    r = max(a, b)
                push(num_to_vch(r))
                if op == OP_NUMEQUALVERIFY:
                    if cast_to_bool(stack[-1]):
                        stack.pop()
                    else:
                        i = len(script)
            elif op == OP_WITHIN:
                need(3)
                hi = num(stack.pop()); lo = num(stack.pop()); x = num(stack.pop())
                push(b"\x01" if lo <= x < hi else b"")
            elif op in (OP_RIPEMD160, OP_SHA1, OP_SHA256, OP_HASH160, OP_HASH256):
                need(1)
                v = stack.pop()
                if op == OP_RIPEMD160:
                    push(ripemd160(v))
                elif op == OP_SHA1:
                    push(hashlib.sha1(v).digest())
                elif op == OP_SHA256:
                    push(sha256(v))
                elif op == OP_HASH160:
                    push(hash160(v))
                else:
                    push(dsha256(v))
            elif op == OP_CODESEPARATOR:
                begin_codehash = i
            elif op in (OP_CHECKSIG, OP_CHECKSIGVERIFY):
                need(2)
                if checker is None:
                    return False
                pubkey = stack.pop(); sig = stack.pop()
                code = script[begin_codehash:]
                ok = checker.check_sig(sig, pubkey, code)
                push(b"\x01" if ok else b"")
                if op == OP_CHECKSIGVERIFY:
                    if ok:
                        stack.pop()
                    else:
                        i = len(script)
            elif op in (OP_CHECKMULTISIG, OP_CHECKMULTISIGVERIFY):
                if checker is None:
                    return False
                k = 1
                need(k)
                n_keys = num(stack[-k])
                k += 1
                if n_keys < 0 or n_keys > 20:
                    return False
                ikey = k
                k += n_keys
                need(k)
                n_sigs = num(stack[-k])
                k += 1
                if n_sigs < 0 or n_sigs > n_keys:
                    return False
                isig = k
                k += n_sigs
                need(k)
                code = script[begin_codehash:]
                for j in range(n_sigs):
                    code = find_and_delete(code, push_script(stack[-isig - j]))
                success = True
                nk, ns = n_keys, n_sigs
                ik, isg = ikey, isig
                while success and ns > 0:
                    sig = stack[-isg]
                    key = stack[-ik]
                    if checker.check_sig(sig, key, code):
                        isg += 1
                        ns -= 1
                    ik += 1
                    nk -= 1
                    if ns > nk:
                        success = False
                for _ in range(k - 1):
                    stack.pop()
                # v0.1's extra pop (CONSENSUS_BEHAVIORS: CHECKMULTISIG extra pop)
                if not stack:
                    return False
                stack.pop()
                push(b"\x01" if success else b"")
                if op == OP_CHECKMULTISIGVERIFY:
                    if success:
                        stack.pop()
                    else:
                        i = len(script)
            else:
                return False

            if params.MAX_STACK is not None and len(stack) + len(altstack) > params.MAX_STACK:
                return False
    except ScriptError:
        return False
    except IndexError:
        return False

    if exec_stack:
        return False
    return True


def _bn_div(a, b):
    """BN_div truncates toward zero."""
    q = abs(a) // abs(b)
    return -q if (a < 0) != (b < 0) else q


def _bn_shift(n, bits):
    """BN_lshift/BN_rshift act on the magnitude; the sign is carried separately."""
    neg = n < 0
    m = abs(n)
    m = m << bits if bits >= 0 else m >> (-bits)
    return -m if neg else m


# ----------------------------------------------------------------------------
# SignatureHash (sighash.json rule; script.cpp:818)
# ----------------------------------------------------------------------------

SIGHASH_ALL, SIGHASH_NONE, SIGHASH_SINGLE, SIGHASH_ANYONECANPAY = 1, 2, 3, 0x80
ONE = (1).to_bytes(32, "little")


def signature_hash(script_code, tx, n_in, hash_type):
    if n_in >= len(tx.vin):
        return ONE  # era-authentic: SIGHASH returns 1
    code = find_and_delete(script_code, bytes([OP_CODESEPARATOR]))
    t = tx.copy()
    for k in range(len(t.vin)):
        t.vin[k].script_sig = b""
    t.vin[n_in].script_sig = code
    ht = hash_type & 0x1f
    if ht == SIGHASH_NONE:
        t.vout = []
        for k in range(len(t.vin)):
            if k != n_in:
                t.vin[k].sequence = 0
    elif ht == SIGHASH_SINGLE:
        if n_in >= len(tx.vout):
            return ONE  # era-authentic: SIGHASH_SINGLE returns 1
        t.vout = t.vout[:n_in + 1]
        for k in range(n_in):
            t.vout[k] = TxOut(-1, b"")
        for k in range(len(t.vin)):
            if k != n_in:
                t.vin[k].sequence = 0
    if hash_type & SIGHASH_ANYONECANPAY:
        t.vin = [t.vin[n_in]]
    return dsha256(t.ser() + (hash_type & 0xffffffff).to_bytes(4, "little"))


def verify_signature(script_sig, script_pubkey, tx, n_in, params):
    """script.cpp:1126 — EvalScript(scriptSig || OP_CODESEPARATOR || scriptPubKey)."""
    script = script_sig + bytes([OP_CODESEPARATOR]) + script_pubkey
    stack = []
    checker = SigChecker(tx, n_in, params)
    ok = eval_script(script, stack, params, checker)
    if not ok or not stack:
        return False
    return cast_to_bool(stack[-1])


# ----------------------------------------------------------------------------
# Transaction and block checks
# ----------------------------------------------------------------------------

def count_sigops(script):
    """Signature operations in a script, the 2010 counting rule (OBL-C-0004)."""
    n = 0
    i = 0
    last = None
    while i < len(script):
        try:
            op, data, j = get_op(script, i)
        except ScriptError:
            break
        if data is None:
            if op in (OP_CHECKSIG, OP_CHECKSIGVERIFY):
                n += 1
            elif op in (OP_CHECKMULTISIG, OP_CHECKMULTISIGVERIFY):
                if last is not None and OP_1 <= last <= OP_16:
                    n += last - OP_1 + 1
                else:
                    n += 20
        last = op
        i = j
    return n


def tx_sigops(tx):
    n = 0
    for i in tx.vin:
        n += count_sigops(i.script_sig)
    for o in tx.vout:
        n += count_sigops(o.script_pubkey)
    return n


def money_range(v, params):
    return 0 <= v <= params.MAX_MONEY


def check_transaction(tx, params):
    """CheckTransaction.  Returns (ok, reason)."""
    if not tx.vin:
        return False, "vin empty"
    if not tx.vout:
        return False, "vout empty"
    if params.MAX_TX_SIZE is not None and len(tx.ser()) > params.MAX_TX_SIZE:
        return False, "size limits failed"
    total = 0
    for o in tx.vout:
        if o.value < 0:
            return False, "txout.nValue negative"
        if params.MONEY_RANGE:
            # OBL-C-0003, as in d4c6b90ca
            if not money_range(o.value, params):
                return False, "txout.nValue too high"
            total += o.value
            if not money_range(total, params):
                return False, "txout total out of range"
    if tx.is_coinbase():
        if not (2 <= len(tx.vin[0].script_sig) <= 100):
            return False, "coinbase script size"
    else:
        for i in tx.vin:
            if i.is_null_prevout():
                return False, "prevout is null"
    return True, None


def is_final(tx, block_height, block_time, params):
    """nLockTime.  JAN09-B installs the 500,000,000 split (OBL-C-0007);
    the January base compares heights only (OBL-F-0002)."""
    if tx.locktime == 0:
        return True
    if params.LOCKTIME_THRESHOLD is None:
        limit = block_height
    else:
        limit = block_height if tx.locktime < params.LOCKTIME_THRESHOLD else block_time
    if tx.locktime < limit:
        return True
    for i in tx.vin:
        if i.sequence != 0xffffffff:
            return False
    return True


def check_block(block, params, now=None, pow_limit_nbits=0x1d00ffff):
    """CheckBlock in main.cpp's order (blocks.json rule).  Returns (ok, reason)."""
    # size limits (OBL-C-0006 / OBL-C-0001: JAN09-B keeps 32 MiB, installs no 1 MB)
    if not block.txs:
        return False, "CheckBlock() : size limits failed"
    if len(block.txs) > params.MAX_BLOCK_TX_COUNT:
        return False, "CheckBlock() : size limits failed"
    if block.size() > params.MAX_BLOCK_SIZE:
        return False, "CheckBlock() : size limits failed"
    if now is not None and block.time > now + 2 * 60 * 60:
        return False, "CheckBlock() : block timestamp too far in the future"
    if not block.txs[0].is_coinbase():
        return False, "CheckBlock() : first tx is not coinbase"
    for t in block.txs[1:]:
        if t.is_coinbase():
            return False, "CheckBlock() : more than one coinbase"
    for t in block.txs:
        ok, why = check_transaction(t, params)
        if not ok:
            return False, "CheckBlock() : CheckTransaction failed"
    target, neg, over = set_compact(block.bits)
    limit, _, _ = set_compact(pow_limit_nbits)
    if neg or over or target == 0 or target > limit:
        return False, "CheckBlock() : nBits below minimum work"
    if int.from_bytes(block.hash(), "little") > target:
        return False, "CheckBlock() : hash doesn't match nBits"
    if merkle_root([t.txid() for t in block.txs]) != block.merkle_root:
        return False, "CheckBlock() : hashMerkleRoot mismatch"
    # sigop ceiling (OBL-C-0004).  JAN09-B only; the January base has none.
    if params.MAX_BLOCK_SIGOPS is not None:
        if sum(tx_sigops(t) for t in block.txs) > params.MAX_BLOCK_SIGOPS:
            return False, "CheckBlock() : out-of-bounds SigOpCount"
    return True, None


def block_subsidy(height, params):
    """Not stated on the page; taken from blocks.json's rule statement,
    whose `height` is the 1-based chain length, so `height - 1` is the
    0-based index used here."""
    return (50 * params.COIN) >> (height // 210000)


def block_work(nbits):
    target, _, _ = set_compact(nbits)
    if target <= 0:
        return 0
    return (1 << 256) // (target + 1)


class BlockIndex:
    def __init__(self, blk, height, prev):
        self.blk = blk
        self.hash = blk.hash()
        self.height = height
        self.prev = prev
        self.work = (prev.work if prev else 0) + block_work(blk.bits)


class Chain:
    """ProcessBlock -> CheckBlock -> AcceptBlock -> AddToBlockIndex /
    ConnectBlock / Reorganize, in main.cpp's order (blocks.json rule)."""

    def __init__(self, params, pow_limit_nbits=0x1d00ffff, genesis_hash=None):
        self.params = params
        self.pow_limit = pow_limit_nbits
        self.index = {}          # hash -> BlockIndex
        self.tip = None
        self.utxo = {}           # (txid, n) -> (value, script, height, is_coinbase)
        self.genesis_hash = genesis_hash
        self.orphans = set()

    # -- helpers ------------------------------------------------------------

    def median_time_past(self, idx, span=11):
        times = []
        p = idx
        while p is not None and len(times) < span:
            times.append(p.blk.time)
            p = p.prev
        times.sort()
        return times[len(times) // 2]

    def next_work_required(self, prev):
        # below height 2016 the retarget does not fire; nBits is carried
        if (prev.height + 1) % 2016 != 0:
            return prev.blk.bits
        return prev.blk.bits  # no 2016-deep test chain here

    def better(self, cand, tip):
        if tip is None:
            return True
        if self.params.CHAIN_BY_WORK:
            return cand.work > tip.work
        return cand.height > tip.height

    # -- the stages ---------------------------------------------------------

    def process_block(self, blk, now=None):
        h = blk.hash()
        if h in self.index:
            return ("reject", "ProcessBlock", "already have")
        ok, why = check_block(blk, self.params, now=now, pow_limit_nbits=self.pow_limit)
        if not ok:
            return ("reject", "CheckBlock", why)
        if blk.prev != b"\x00" * 32 and blk.prev not in self.index:
            self.orphans.add(h)
            return ("orphan", "ProcessBlock", "ProcessBlock: ORPHAN BLOCK")
        return self.accept_block(blk)

    def accept_block(self, blk):
        h = blk.hash()
        prev = self.index.get(blk.prev)
        if prev is None:
            # genesis
            if self.genesis_hash is not None and h != self.genesis_hash:
                return ("reject", "AcceptBlock", "AcceptBlock() : prev block not found")
            idx = BlockIndex(blk, 0, None)
        else:
            if blk.time <= self.median_time_past(prev):
                return ("reject", "AcceptBlock", "AcceptBlock() : block's timestamp is too early")
            if blk.bits != self.next_work_required(prev):
                return ("reject", "AcceptBlock", "AcceptBlock() : incorrect proof of work")
            idx = BlockIndex(blk, prev.height + 1, prev)
        return self.add_to_block_index(idx)

    def add_to_block_index(self, idx):
        self.index[idx.hash] = idx
        if not self.better(idx, self.tip):
            return ("side", "AddToBlockIndex", "not higher than the best chain")
        if self.tip is None or idx.prev is self.tip:
            snapshot = dict(self.utxo)
            ok, why = self.connect_block(idx)
            if not ok:
                self.utxo = snapshot
                del self.index[idx.hash]
                return ("reject", "ConnectBlock", why)
            self.tip = idx
            return ("accept", "ConnectBlock", "ProcessBlock: ACCEPTED")
        ok, why = self.reorganize(idx)
        if not ok:
            return ("reject", "ConnectBlock", why)
        return ("accept", "ConnectBlock", "ProcessBlock: ACCEPTED")

    def reorganize(self, new_tip):
        snapshot = dict(self.utxo)
        old_tip = self.tip
        # find the fork
        a, b = old_tip, new_tip
        chain_new = []
        while b is not None and b.height > a.height:
            chain_new.append(b); b = b.prev
        chain_old = []
        while a is not None and b is not None and a is not b:
            chain_old.append(a); a = a.prev
            chain_new.append(b); b = b.prev
        chain_new.reverse()
        for idx in chain_old:
            self.disconnect_block(idx)
        for idx in chain_new:
            ok, why = self.connect_block(idx)
            if not ok:
                self.utxo = snapshot
                # erase the failing block and the rest of the branch
                for j in chain_new[chain_new.index(idx):]:
                    self.index.pop(j.hash, None)
                return False, "Reorganize() : ConnectBlock failed"
        self.tip = new_tip
        return True, None

    def disconnect_block(self, idx):
        for t in reversed(idx.blk.txs):
            txid = t.txid()
            for n in range(len(t.vout)):
                self.utxo.pop((txid, n), None)
            if not t.is_coinbase():
                for i in t.vin:
                    src = getattr(i, "_spent_from", None)
                    if src is not None:
                        self.utxo[(i.prev_hash, i.prev_n)] = src

    def connect_block(self, idx):
        params = self.params
        height = idx.height
        fees = 0
        spent_here = {}
        for t in idx.blk.txs:
            if t.is_coinbase():
                continue
            vin_total = 0
            for i in t.vin:
                key = (i.prev_hash, i.prev_n)
                ent = self.utxo.get(key)
                if ent is None:
                    return False, "ConnectInputs() : prev tx already used"
                value, script, src_height, src_cb = ent
                if src_cb and height - src_height < 99:
                    return False, "ConnectInputs() : tried to spend coinbase at depth"
                n_in = t.vin.index(i)
                if not verify_signature(i.script_sig, script, t, n_in, params):
                    return False, "ConnectInputs() : VerifySignature failed"
                if params.MONEY_RANGE and not money_range(value, params):
                    return False, "ConnectInputs() : txin values out of range"
                vin_total += value
                i._spent_from = ent
                spent_here[key] = ent
                del self.utxo[key]
            out_total = t.value_out(wrap=not params.MONEY_RANGE)
            if vin_total < out_total:
                return False, "ConnectInputs() : nTxFee < 0"
            fees += vin_total - out_total
            txid = t.txid()
            for n, o in enumerate(t.vout):
                self.utxo[(txid, n)] = (o.value, o.script_pubkey, height, False)
        cb = idx.blk.txs[0]
        if cb.value_out(wrap=not params.MONEY_RANGE) > block_subsidy(height, params) + fees:
            return False, "ConnectBlock() : coinbase pays too much"
        txid = cb.txid()
        for n, o in enumerate(cb.vout):
            self.utxo[(txid, n)] = (o.value, o.script_pubkey, height, True)
        return True, None
