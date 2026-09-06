#!/usr/bin/env python3
"""verify_slhdsa.py — SLH-DSA-SHA2-128s signature verification in pure Python.

⛔ WHY THIS EXISTS. This laboratory publishes two kinds of signature over its releases and
protocol documents, and they do not have the same lifetime.

    elliptic-curve       secp256k1 and Ed25519. Checkable today with ordinary tools, and
                         NOT survivable: given a public key, a cryptographically relevant
                         quantum computer recovers the private one

    SLH-DSA-SHA2-128s    FIPS 205. Rests on SHA-256 alone, so it stands where SHA-256
                         stands. This is the signature meant to still mean something after
                         the other kind stops meaning anything

The published way to check the second was:

    openssl pkeyutl -verify -pubin -inkey <pk>.pem -rawin -in <file> -sigfile <file>.slhdsa

which needs **OpenSSL 3.5 or later** — a specific version of one program, standing behind the
one signature whose entire purpose is to remain checkable when the surrounding software has
changed beyond recognition.

⇒ That is backwards, and it is the only reason this file exists. SLH-DSA-SHA2-128s rests on
  SHA-256 and nothing else, so its verifier can rest on `hashlib` and nothing else: no OpenSSL,
  no build step, no package, no network. Verified working from a bare directory containing this
  file, a public key, a signed file and its signature.

WHAT IT IS AND IS NOT

  * VERIFY ONLY. There is no signing path here. It holds no secret, needs none, and refuses a
    private key outright rather than reading one.
  * It implements FIPS 205 for one parameter set, SLH-DSA-SHA2-128s. A key for any other set is
    refused by its algorithm identifier rather than attempted — running these constants against
    another set would produce a confident wrong answer.
  * It makes no claim about any signature it is not given, and takes no position on anything
    outside the bytes handed to it. It answers one question: does this signature verify under
    this key over these bytes.

⚠️ WHAT THE VALIDATION DOES **NOT** COVER, stated because a validation claim without its bound is
   worth less than no claim at all:

     NOT CHECKED against NIST ACVP / FIPS 205 official test vectors. They were not available
     offline when this was written. What it IS checked against is (a) 17 signatures this project
     made with an independent signer, (b) 17 cross-key rejections, (c) 8 mutations, and (d) 39
     verdicts identical to OpenSSL 3.5.4 on accepts AND rejects.

     ⇒ The residual risk is a misreading of FIPS 205 that OpenSSL shares. That is a real
       possibility and not a large one -- the two implementations were written by different
       people in different languages -- but it is the gap, and it closes properly only against
       the official vectors. If they ever become reachable, run them.

   ⚠️ It also proves nothing about WHEN. A signature answers who; the `.ots` proof beside it is
      what answers when, and only the anchor survives a break of the signing scheme.

    python verify_slhdsa.py <pubkey.pem> <file> <file.slhdsa>
    python verify_slhdsa.py --selftest [--corpus DIR]

Exit 0 iff the signature verifies (or, with --selftest, iff every case behaved).
"""
import argparse
import base64
import hashlib
import pathlib
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

OK, BAD, STOP = "ok  ", "FAIL", chr(0x26D4)

# ---------------------------------------------------------------- SLH-DSA-SHA2-128s, FIPS 205
# Table 2. Only this parameter set: a wrong set must be refused, never guessed at.
N = 16          # security parameter, bytes
H = 63          # total hypertree height
D = 7           # hypertree layers
H_ = H // D     # 9, height of one XMSS tree
A = 12          # FORS tree height
K = 14          # FORS trees
LG_W = 4
W = 1 << LG_W   # 16
M_DIGEST = 30   # bytes of H_msg output

# ⛔ THESE ARE THE PARAMETER SET'S VALUES, NOT A GENERAL FORMULA. A first draft computed len2 as
# `(LEN1 * (W - 1)).bit_length() // LG_W + 1`, which gives 3 here and is WRONG IN GENERAL --
# for len1*(w-1) = 15 it returns 2 where FIPS 205's floor(log_w(x)) + 1 gives 1. It was right for
# this set by arithmetic accident. Since this file supports exactly one parameter set, the values
# are stated and asserted rather than derived by a formula that only happens to work.
LEN1 = 32       # ceil(8n / lg_w)                = ceil(128/4)
LEN2 = 3        # floor(log_w(len1*(w-1))) + 1   = floor(log16(480)) + 1
LEN = LEN1 + LEN2                                                  # 35
assert LEN1 == (8 * N + LG_W - 1) // LG_W
assert (W - 1) * LEN1 < W ** LEN2, "len2 too small to hold the checksum"

PK_BYTES = 2 * N                                                   # 32
SIG_BYTES = (1 + K * (1 + A) + H + D * LEN) * N                    # 7856

# The OID that says which parameter set a key is for. A key for a different set must be REFUSED,
# not verified with these constants -- the maths would run and the answer would be meaningless.
OID_SLH_DSA_SHA2_128S = bytes.fromhex("0609608648016503040314")    # 2.16.840.1.101.3.4.3.20
OID_NAMES = {
    "0609608648016503040314": "SLH-DSA-SHA2-128s",
    "0609608648016503040313": "SLH-DSA-SHA2-128f",
    "0609608648016503040315": "SLH-DSA-SHA2-192s",
    "0609608648016503040317": "SLH-DSA-SHA2-256s",
    "060960864801650304031a": "SLH-DSA-SHAKE-128s",
}

WOTS_HASH, WOTS_PK, TREE, FORS_TREE, FORS_ROOTS = 0, 1, 2, 3, 4


# ------------------------------------------------------------------------------- addresses
class Adrs:
    """The 32-byte address, and its 22-byte compressed form used by the SHA2 instantiation.

    FIPS 205 §11.2: ADRS^c = ADRS[3] || ADRS[8:16] || ADRS[19] || ADRS[20:32].
    ⚠ It is a COMPRESSION, not a truncation: the layer byte and the type byte are the low byte
      of their 4-byte fields, and the tree address keeps its low 8 of 12 bytes.
    """

    __slots__ = ("a",)

    def __init__(self, a=None):
        self.a = bytearray(32) if a is None else bytearray(a)

    def clone(self):
        return Adrs(self.a)

    def compressed(self):
        return bytes(self.a[3:4] + self.a[8:16] + self.a[19:20] + self.a[20:32])

    def set_layer(self, x):
        self.a[0:4] = x.to_bytes(4, "big")

    def set_tree(self, x):
        self.a[4:16] = x.to_bytes(12, "big")

    def set_type_and_clear(self, y):
        self.a[16:20] = y.to_bytes(4, "big")
        self.a[20:32] = bytes(12)

    def set_keypair(self, x):
        self.a[20:24] = x.to_bytes(4, "big")

    def get_keypair(self):
        return int.from_bytes(self.a[20:24], "big")

    def set_chain(self, x):
        self.a[24:28] = x.to_bytes(4, "big")

    def set_hash(self, x):
        self.a[28:32] = x.to_bytes(4, "big")

    def set_tree_height(self, x):
        self.a[24:28] = x.to_bytes(4, "big")

    def set_tree_index(self, x):
        self.a[28:32] = x.to_bytes(4, "big")

    def get_tree_index(self):
        return int.from_bytes(self.a[28:32], "big")


# ------------------------------------------------------------------------- hash functions
# SHA2, security category 1 (n=16). F, H and T_l share one construction:
#   Trunc_n( SHA-256( PK.seed || toByte(0, 64-n) || ADRS^c || M ) )
# The 48 zero bytes pad PK.seed out to one full SHA-256 block, which is the whole point of the
# construction and is not optional.
_PAD = bytes(64 - N)


def _thash(pk_seed, adrs, m):
    return hashlib.sha256(pk_seed + _PAD + adrs.compressed() + m).digest()[:N]


def h_msg(r, pk_seed, pk_root, msg):
    """MGF1-SHA-256( R || PK.seed || SHA-256(R || PK.seed || PK.root || M), m )."""
    seed = r + pk_seed + hashlib.sha256(r + pk_seed + pk_root + msg).digest()
    out, counter = b"", 0
    while len(out) < M_DIGEST:
        out += hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
        counter += 1
    return out[:M_DIGEST]


def base_2b(x, b, out_len):
    """out_len integers of b bits each, taken from x most-significant-bit first.

    ⚠ Refuses a short input rather than raising IndexError deep inside a hash loop. Malformed
      input must reach the caller as a verification failure, not as a traceback.
    """
    if len(x) * 8 < b * out_len:
        raise ValueError("base_2b needs %d bits, got %d" % (b * out_len, len(x) * 8))
    out, bits, total, in_i = [], 0, 0, 0
    for _ in range(out_len):
        while bits < b:
            total = (total << 8) + x[in_i]
            in_i += 1
            bits += 8
        bits -= b
        out.append((total >> bits) & ((1 << b) - 1))
    return out


# --------------------------------------------------------------------------------- WOTS+
def chain(x, start, steps, pk_seed, adrs):
    tmp = x
    for j in range(start, start + steps):
        adrs.set_hash(j)
        tmp = _thash(pk_seed, adrs, tmp)
    return tmp


def wots_pk_from_sig(sig, msg, pk_seed, adrs):
    csum = 0
    m = base_2b(msg, LG_W, LEN1)
    for v in m:
        csum += W - 1 - v
    csum <<= (8 - ((LEN2 * LG_W) % 8)) % 8
    m += base_2b(csum.to_bytes((LEN2 * LG_W + 7) // 8, "big"), LG_W, LEN2)

    tmp = []
    for i in range(LEN):
        adrs.set_chain(i)
        tmp.append(chain(sig[i * N:(i + 1) * N], m[i], W - 1 - m[i], pk_seed, adrs))

    pk_adrs = adrs.clone()
    pk_adrs.set_type_and_clear(WOTS_PK)
    pk_adrs.set_keypair(adrs.get_keypair())
    return _thash(pk_seed, pk_adrs, b"".join(tmp))


# ---------------------------------------------------------------------------------- XMSS
def xmss_pk_from_sig(idx, sig_xmss, msg, pk_seed, adrs):
    auth = sig_xmss[LEN * N:]
    adrs.set_type_and_clear(WOTS_HASH)
    adrs.set_keypair(idx)
    node = wots_pk_from_sig(sig_xmss[:LEN * N], msg, pk_seed, adrs)

    adrs.set_type_and_clear(TREE)
    adrs.set_tree_index(idx)
    for k in range(H_):
        adrs.set_tree_height(k + 1)
        a_k = auth[k * N:(k + 1) * N]
        if (idx >> k) % 2 == 0:
            adrs.set_tree_index(adrs.get_tree_index() // 2)
            node = _thash(pk_seed, adrs, node + a_k)
        else:
            adrs.set_tree_index((adrs.get_tree_index() - 1) // 2)
            node = _thash(pk_seed, adrs, a_k + node)
    return node


def ht_verify(msg, sig_ht, pk_seed, idx_tree, idx_leaf, pk_root):
    adrs = Adrs()
    adrs.set_layer(0)
    adrs.set_tree(idx_tree)
    xmss_sig_len = (LEN + H_) * N
    node = xmss_pk_from_sig(idx_leaf, sig_ht[:xmss_sig_len], msg, pk_seed, adrs)
    for j in range(1, D):
        idx_leaf = idx_tree % (1 << H_)
        idx_tree >>= H_
        adrs.set_layer(j)
        adrs.set_tree(idx_tree)
        sig = sig_ht[j * xmss_sig_len:(j + 1) * xmss_sig_len]
        node = xmss_pk_from_sig(idx_leaf, sig, node, pk_seed, adrs)
    return node == pk_root


# ---------------------------------------------------------------------------------- FORS
def fors_pk_from_sig(sig_fors, md, pk_seed, adrs):
    indices = base_2b(md, A, K)
    roots = []
    step = (A + 1) * N
    for i in range(K):
        blk = sig_fors[i * step:(i + 1) * step]
        node = blk[:N]
        auth = blk[N:]
        adrs.set_tree_height(0)
        adrs.set_tree_index(i * (1 << A) + indices[i])
        node = _thash(pk_seed, adrs, node)
        for j in range(A):
            a_j = auth[j * N:(j + 1) * N]
            adrs.set_tree_height(j + 1)
            if (indices[i] >> j) % 2 == 0:
                adrs.set_tree_index(adrs.get_tree_index() // 2)
                node = _thash(pk_seed, adrs, node + a_j)
            else:
                adrs.set_tree_index((adrs.get_tree_index() - 1) // 2)
                node = _thash(pk_seed, adrs, a_j + node)
        roots.append(node)

    pk_adrs = adrs.clone()
    pk_adrs.set_type_and_clear(FORS_ROOTS)
    pk_adrs.set_keypair(adrs.get_keypair())
    return _thash(pk_seed, pk_adrs, b"".join(roots))


# ------------------------------------------------------------------------------- verify
def verify_internal(pk, msg, sig):
    """FIPS 205 Algorithm 20, slh_verify_internal. `msg` is already the M' the signer used.

    ⚠ Any malformed input is a verification FAILURE, never an exception escaping to the caller.
      A verifier that crashes on hostile bytes hands its caller a decision it did not make.
    """
    if len(pk) != PK_BYTES or len(sig) != SIG_BYTES:
        return False
    try:
        return _verify_internal(pk, msg, sig)
    except (ValueError, IndexError, OverflowError):
        return False


def _verify_internal(pk, msg, sig):
    pk_seed, pk_root = pk[:N], pk[N:]

    r = sig[:N]
    fors_len = K * (1 + A) * N
    sig_fors = sig[N:N + fors_len]
    sig_ht = sig[N + fors_len:]

    digest = h_msg(r, pk_seed, pk_root, msg)
    ka8 = (K * A + 7) // 8                       # 21
    tree_bytes = (H - H_ + 7) // 8               # 7
    leaf_bytes = (H_ + 7) // 8                   # 2

    md = digest[:ka8]
    idx_tree = int.from_bytes(digest[ka8:ka8 + tree_bytes], "big") % (1 << (H - H_))
    idx_leaf = int.from_bytes(digest[ka8 + tree_bytes:ka8 + tree_bytes + leaf_bytes],
                              "big") % (1 << H_)

    adrs = Adrs()
    adrs.set_tree(idx_tree)
    adrs.set_type_and_clear(FORS_TREE)
    adrs.set_keypair(idx_leaf)
    pk_fors = fors_pk_from_sig(sig_fors, md, pk_seed, adrs)

    return ht_verify(pk_fors, sig_ht, pk_seed, idx_tree, idx_leaf, pk_root)


def verify(pk, message, sig, ctx=b""):
    """FIPS 205 Algorithm 24, slh_verify: the pure form, with a context string.

    ⚠ The domain separator is NOT decoration. `M' = toByte(0,1) || toByte(|ctx|,1) || ctx || M`
      is what a FIPS 205 "pure" signer signs, and `openssl pkeyutl -rawin` produces exactly that
      with an empty context. Verifying the bare message instead would reject every real
      signature -- and, worse, a verifier that fell back to the bare message on failure would
      accept signatures made over a different domain.
    """
    if len(ctx) > 255:
        raise ValueError("context string longer than 255 bytes")
    m_prime = bytes([0, len(ctx)]) + ctx + message
    return verify_internal(pk, m_prime, sig)


# --------------------------------------------------------------------------- key loading
class NotThisParameterSet(Exception):
    """The key is well-formed but for a different SLH-DSA parameter set."""


def load_pubkey(path):
    """Raw 32-byte key from a PEM SubjectPublicKeyInfo, refusing any other parameter set.

    ⛔ REFUSES PRIVATE KEY MATERIAL BY STRUCTURE, NOT BY FILENAME. A first draft's self-test
    picked candidate keys with `"-sk" not in name`, which is a naming convention standing in for
    a property -- exactly the substring-for-a-token mistake this project keeps finding. A secret
    lives in the same directory as its public half, and one differently-named file would have
    been read into memory. The PEM label is what actually says which one it is.
    """
    p = pathlib.Path(path)
    raw = p.read_bytes()
    if b"PRIVATE KEY" in raw[:200]:
        raise SystemExit(
            "%s %s is a PRIVATE key. This tool verifies; it never needs a secret, and it will "
            "not read one." % (STOP, p.name))

    if b"-----BEGIN" in raw:
        b64 = b"".join(l.strip() for l in raw.splitlines() if not l.startswith(b"-----"))
        der = base64.b64decode(b64)
    else:
        der = raw
    if len(der) == PK_BYTES:          # already a raw key
        return der

    # Parse the structure rather than searching for bytes: SEQUENCE { SEQUENCE { OID .. }, BIT }.
    # A substring hit anywhere in the file is not the same claim as "the algorithm identifier of
    # this key is that OID".
    try:
        if der[0] != 0x30:
            raise ValueError("not a SEQUENCE")
        body = der[2:] if der[1] < 0x80 else der[2 + (der[1] & 0x7F):]
        if body[0] != 0x30:
            raise ValueError("no AlgorithmIdentifier")
        alg = body[2:2 + body[1]]
        if alg[0] != 0x06:
            raise ValueError("no OID in the AlgorithmIdentifier")
        oid = alg[:2 + alg[1]]
    except (IndexError, ValueError) as e:
        raise SystemExit("%s %s is not a SubjectPublicKeyInfo (%s)" % (STOP, p.name, e))

    if oid != OID_SLH_DSA_SHA2_128S:
        name = OID_NAMES.get(oid.hex())
        raise NotThisParameterSet(
            "%s is %s, not SLH-DSA-SHA2-128s. This file implements one parameter set; running "
            "it against another would produce a confident wrong answer."
            % (p.name, name or ("OID " + oid.hex())))

    rest = body[2 + body[1]:]
    if not rest or rest[0] != 0x03:
        raise SystemExit("%s cannot find the public key bit string in %s" % (STOP, p.name))
    key = rest[3:3 + rest[1] - 1]     # skip length byte and the unused-bits octet
    if len(key) != PK_BYTES:
        raise SystemExit("%s public key is %d bytes; SLH-DSA-SHA2-128s keys are %d"
                         % (STOP, len(key), PK_BYTES))
    return key


# ------------------------------------------------------------------------------ selftest
def _find_cases(corpus):
    """Every (pubkey, message, signature) triple this project has already published.

    Public keys are selected by reading the PEM label, never by filename: `load_pubkey` refuses
    private material outright, and a key for another parameter set is skipped by exception.
    """
    root = pathlib.Path(corpus)
    keys, skipped = [], []
    for p in sorted(root.rglob("*.pem")):
        if b"PRIVATE KEY" in p.read_bytes()[:200]:
            continue
        try:
            load_pubkey(p)
        except NotThisParameterSet as e:
            skipped.append(str(e).split(" is ")[0] + " (other parameter set)")
            continue
        except SystemExit:
            continue
        keys.append(p)

    cases = []
    for sig in sorted(root.rglob("*.slhdsa")):
        if ".ots" in sig.suffixes or "_superseded" in str(sig):
            continue
        signed = sig.with_suffix("")
        if signed.is_file():
            cases.append((signed, sig))
    return keys, cases, skipped


def selftest(corpus):
    print("=" * 78)
    print("  SLH-DSA-SHA2-128s verifier, checked against this project's own signatures")
    print("=" * 78)
    print("  n=%d h=%d d=%d h'=%d a=%d k=%d len=%d  pk=%dB sig=%dB"
          % (N, H, D, H_, A, K, LEN, PK_BYTES, SIG_BYTES))
    print("  corpus %s\n" % corpus)

    keys, cases, skipped = _find_cases(corpus)
    if not keys or not cases:
        # ⚠ THE FIRST THING A NEW READER HITS, IF THE SCRIPT AND THE ARTIFACTS ARE NOT IN THE SAME
        #   DIRECTORY -- which is the normal layout, not an unusual one. An empty corpus is not a
        #   failed check and must not read like one: say what was looked at and what to pass.
        print("%s nothing to check against: %d public key(s) and %d signature(s) in"
              % (STOP, len(keys), len(cases)))
        print("     %s" % corpus)
        print()
        print("  This is not a failed verification. --selftest needs a directory holding public")
        print("  keys (*.pem) beside the files they signed (<file> and <file>.slhdsa).")
        print("  Point it at one:")
        print()
        print("      python %s --selftest --corpus <dir>"
              % pathlib.Path(__file__).name)
        return 1
    print("  %d public key(s), %d signed file(s)" % (len(keys), len(cases)))
    for s in skipped:
        print("  skipped %s" % s)
    print()

    # ⇒ EVERY KEY IS TRIED AGAINST EVERY SIGNATURE, and exactly one must verify. Stopping at the
    #   first match would have made the cross-key rejections invisible: with two keys and 17
    #   files, 16 of them are ALSO evidence that the other key is refused, and that is the
    #   cheapest strong control available here. A verifier that accepted anything would show two
    #   matches per file, and the count below would say so.
    verified, unmatched, fails, cross = [], [], 0, 0
    for signed, sigpath in cases:
        sig = sigpath.read_bytes()
        msg = signed.read_bytes()
        if len(sig) != SIG_BYTES:
            print("  %s  %s is %d bytes, not %d" % (BAD, sigpath.name, len(sig), SIG_BYTES))
            fails += 1
            continue
        hits = [kp for kp in keys if verify(load_pubkey(kp), msg, sig)]
        cross += len(keys) - len(hits)
        if len(hits) == 1:
            verified.append((signed, sigpath, hits[0], sig, msg))
            print("  %s  %-52s under %s" % (OK, signed.name, hits[0].name))
        elif not hits:
            unmatched.append((signed, sigpath))
            print("  %s  %-52s no key verifies it" % (BAD, signed.name))
            fails += 1
        else:
            print("  %s  %-52s verifies under %d keys at once" % (BAD, signed.name, len(hits)))
            fails += 1
    print("\n  %d cross-key rejection(s): a real signature refused by a real key that did not "
          "make it" % cross)

    # ⇒ A VERIFIER THAT ACCEPTS EVERYTHING ALSO ACCEPTS EVERY REAL SIGNATURE. Accepting the
    #   genuine ones is necessary and nowhere near sufficient, so each one is mutated and must
    #   then be REFUSED. Without this the suite above would pass for `return True`.
    print("\n  --- negative controls: each mutation must be REFUSED ---")
    if not verified:
        print("  %s nothing verified, so there is nothing to mutate. The controls below cannot "
              "run and this suite proves nothing." % STOP)
        return 1

    signed, sigpath, kp, sig, msg = verified[0]
    pk = load_pubkey(kp)
    muts = [
        ("one bit flipped in the signature",
         pk, msg, sig[:100] + bytes([sig[100] ^ 0x01]) + sig[101:]),
        ("one bit flipped in the message",
         pk, msg[:1] + bytes([msg[0] ^ 0x01]) + msg[1:], sig),
        ("one bit flipped in the public key",
         pk[:1] + bytes([pk[0] ^ 0x01]) + pk[1:], msg, sig),
        ("the randomiser R replaced",
         pk, msg, bytes(N) + sig[N:]),
        ("the last hypertree layer's signature zeroed",
         pk, msg, sig[:-(LEN + H_) * N] + bytes((LEN + H_) * N)),
        ("a truncated signature", pk, msg, sig[:-1]),
        ("an empty message", pk, b"", sig),
    ]
    for label, mpk, mmsg, msig in muts:
        if verify(mpk, mmsg, msig):
            print("  %s  ACCEPTED: %s" % (BAD, label))
            fails += 1
        else:
            print("  %s  refused: %s" % (OK, label))

    # ⚠ And the domain separator must be load-bearing, or this file is verifying a different
    #   scheme that happens to agree on the real cases.
    if verify_internal(pk, msg, sig):
        print("  %s  ACCEPTED: the bare message, without the FIPS 205 context prefix" % BAD)
        fails += 1
    else:
        print("  %s  refused: the bare message, without the FIPS 205 context prefix" % OK)

    print("\n" + "=" * 78)
    print("  %d verified, %d unmatched, %d failure(s)" % (len(verified), len(unmatched), fails))
    if not fails:
        print("  Every published signature verifies and every mutation is refused.")
    print("=" * 78)
    return 1 if fails else 0


def crosscheck(corpus):
    """Differential test: this file and OpenSSL must agree on EVERY verdict, accept and reject.

    ⇒ THE POINT OF THIS TOOL IS NOT TO NEED OPENSSL. But while an independent implementation is
      still available, it is the strongest evidence obtainable that the maths here is right: two
      implementations written by different people from the same specification, agreeing on
      accepts AND on rejects. Agreement on accepts alone would be satisfied by both being
      permissive.

    ⚠ This is a validation run, not a dependency. When OpenSSL is absent -- which is the future
      this file exists for -- it reports that and changes nothing about `--selftest`.
    """
    import shutil
    import subprocess
    import tempfile

    exe = shutil.which("openssl")
    if not exe:
        print("%s openssl is not on PATH, so no independent implementation is available to "
              "cross-check against. That is not a failure -- it is the condition this file was "
              "written for." % chr(0x26A0))
        return 0
    ver = subprocess.run([exe, "version"], capture_output=True, text=True).stdout.strip()
    print("=" * 78)
    print("  DIFFERENTIAL TEST — this file vs %s" % ver)
    print("=" * 78 + "\n")

    def openssl_ok(pk_pem, msg_bytes, sig_bytes):
        with tempfile.TemporaryDirectory() as td:
            d = pathlib.Path(td)
            (d / "m").write_bytes(msg_bytes)
            (d / "s").write_bytes(sig_bytes)
            r = subprocess.run([exe, "pkeyutl", "-verify", "-pubin", "-inkey", str(pk_pem),
                                "-rawin", "-in", str(d / "m"), "-sigfile", str(d / "s")],
                               capture_output=True, text=True)
            return r.returncode == 0 and "Verified Successfully" in r.stdout

    keys, cases, _ = _find_cases(corpus)
    agree = disagree = 0

    for signed, sigpath in cases:
        msg, sig = signed.read_bytes(), sigpath.read_bytes()
        for kp in keys:
            mine = verify(load_pubkey(kp), msg, sig)
            theirs = openssl_ok(kp, msg, sig)
            if mine == theirs:
                agree += 1
            else:
                disagree += 1
                print("  %s  DISAGREE %s under %s: this=%s openssl=%s"
                      % (BAD, signed.name, kp.name, mine, theirs))
    print("  %d verdict(s) on real signatures, %d disagreement(s)" % (agree, disagree))

    # Mutations, where both must say NO. Agreement on rejects is the half that a permissive
    # implementation fails.
    if cases and keys:
        signed, sigpath = cases[0]
        msg, sig = signed.read_bytes(), sigpath.read_bytes()
        kp = next((k for k in keys if verify(load_pubkey(k), msg, sig)), keys[0])
        muts = [("flip a signature bit", msg, sig[:9] + bytes([sig[9] ^ 1]) + sig[10:]),
                ("flip a message bit", bytes([msg[0] ^ 1]) + msg[1:], sig),
                ("zero the FORS block", msg, sig[:N] + bytes(K * (1 + A) * N) + sig[N + K * (1 + A) * N:]),
                ("swap two signature halves", msg, sig[len(sig) // 2:] + sig[:len(sig) // 2]),
                ("append a byte to the message", msg + b"\x00", sig)]
        print()
        for label, mmsg, msig in muts:
            mine = verify(load_pubkey(kp), mmsg, msig)
            theirs = openssl_ok(kp, mmsg, msig)
            if mine == theirs is False:
                agree += 1
                print("  %s  both refuse: %s" % (OK, label))
            else:
                disagree += 1
                print("  %s  %s -> this=%s openssl=%s" % (BAD, label, mine, theirs))

    print("\n" + "=" * 78)
    print("  %d agreement(s), %d disagreement(s)" % (agree, disagree))
    if not disagree:
        print("  Two independent implementations, identical verdicts throughout.")
    print("=" * 78)
    return 1 if disagree else 0


def _default_corpus():
    """Where --selftest looks for signatures: beside this file, unless told otherwise.

    ⛔ THE DEFAULT USED TO BE A FIXED RELATIVE PATH, WHICH IS A CLAIM ABOUT WHERE THIS FILE SITS.
    Copied to a second location it resolved to a directory that does not exist, and `--selftest`
    failed there for a reason that had nothing to do with any signature. A tool written to still
    work decades from now must not assume its own address.

    ⇒ It defaults to its own directory and searches nothing. Point `--corpus` at a tree of
      signed files to check a wider set; the answer for each is the same either way.
    """
    return str(pathlib.Path(__file__).resolve().parent)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pubkey", nargs="?")
    ap.add_argument("file", nargs="?")
    ap.add_argument("signature", nargs="?")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--crosscheck", action="store_true",
                    help="differential test against OpenSSL, if one is installed")
    ap.add_argument("--corpus", default=_default_corpus())
    ap.add_argument("--ctx", default="", help="FIPS 205 context string (default empty)")
    a = ap.parse_args()

    if a.crosscheck:
        return crosscheck(a.corpus)
    if a.selftest:
        return selftest(a.corpus)
    if not (a.pubkey and a.file and a.signature):
        ap.print_help()
        return 2

    # ⛔ A MISSING FILE PRODUCED A TRACEBACK WHERE A VERDICT BELONGS, and it was found by running
    # this tool's own documented command in the folder the documentation says to run it in. An
    # unhandled exception is not a "no": a caller reading only the exit code cannot tell a
    # refused signature from a mistyped path.
    missing = [p for p in (a.pubkey, a.file, a.signature) if not pathlib.Path(p).is_file()]
    if missing:
        for p in missing:
            print("%s not found: %s" % (STOP, p))
        print("  Nothing was verified. This is a missing file, NOT a failed signature.")
        return 2

    pk = load_pubkey(a.pubkey)
    msg = pathlib.Path(a.file).read_bytes()
    sig = pathlib.Path(a.signature).read_bytes()
    if len(sig) != SIG_BYTES:
        print("%s signature is %d bytes; SLH-DSA-SHA2-128s signatures are %d"
              % (STOP, len(sig), SIG_BYTES))
        return 1
    good = verify(pk, msg, sig, a.ctx.encode())
    print("%s  %s" % ("VERIFIED" if good else "FAILED", pathlib.Path(a.file).name))
    if good:
        print("  signed under SLH-DSA-SHA2-128s by the key in %s" % a.pubkey)
        print("  This says WHO signed these bytes. It says nothing about WHEN --")
        print("  that is what the .ots proof beside the signature is for.")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
