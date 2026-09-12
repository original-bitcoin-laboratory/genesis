#!/usr/bin/env python3
"""Sign or verify a challenge with a secp256k1 key, the way the chain's author key answers one.

Standard library only. This is the tool the signature files under docs/ refer to
(for example PQ-SUCCESSION-CERTIFICATE.txt.secp256k1): the message that is signed is
the double SHA-256 of the 64-character ASCII hex digest of the challenged file -- the hex
STRING, not the raw digest bytes -- and the signature is RFC 6979 deterministic ECDSA
with low-s normalisation, so signing the same challenge twice yields the same (r, s).

Verify (what a stranger runs; needs no key):

    sha256sum PQ-SUCCESSION-CERTIFICATE.txt          # -> <hash>
    python verify/prove.py verify <hash> <r> <s> <pubkey-hex>

    or, reading the r, s and public key straight out of the signature file:
    python verify/prove.py check docs/PQ-SUCCESSION-CERTIFICATE.txt

Sign (only the key holder can; the key file holds the 32-byte secret as hex):

    python verify/prove.py sign <hash> --key /path/to/secret.hex

Exit status 0 means the signature verifies; 1 means it does not.
"""
import hashlib, hmac, re, sys, pathlib

P  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
G  = (Gx, Gy)

def _inv(a, m):
    return pow(a, -1, m)

def _add(p, q):
    if p is None: return q
    if q is None: return p
    (x1, y1), (x2, y2) = p, q
    if x1 == x2 and (y1 + y2) % P == 0: return None
    lam = (3 * x1 * x1) * _inv(2 * y1, P) % P if p == q else (y2 - y1) * _inv(x2 - x1, P) % P
    x3 = (lam * lam - x1 - x2) % P
    return (x3, (lam * (x1 - x3) - y1) % P)

def _mul(k, p):
    r = None
    while k:
        if k & 1: r = _add(r, p)
        p = _add(p, p); k >>= 1
    return r

def _msg_int(challenge_hex: str) -> int:
    """The signed message is double SHA-256 (SHA-256 applied twice, as Bitcoin hashes) over the
    ASCII hex string of the challenge -- the 64 characters, not the 32 bytes they denote."""
    first = hashlib.sha256(challenge_hex.encode("ascii")).digest()
    return int.from_bytes(hashlib.sha256(first).digest(), "big")

def _rfc6979_k(d: int, e: int) -> int:
    x = d.to_bytes(32, "big"); h1 = e.to_bytes(32, "big")
    v = b"\x01" * 32; k = b"\x00" * 32
    k = hmac.new(k, v + b"\x00" + x + h1, hashlib.sha256).digest(); v = hmac.new(k, v, hashlib.sha256).digest()
    k = hmac.new(k, v + b"\x01" + x + h1, hashlib.sha256).digest(); v = hmac.new(k, v, hashlib.sha256).digest()
    while True:
        v = hmac.new(k, v, hashlib.sha256).digest()
        cand = int.from_bytes(v, "big")
        if 1 <= cand < N: return cand
        k = hmac.new(k, v + b"\x00", hashlib.sha256).digest(); v = hmac.new(k, v, hashlib.sha256).digest()

def sign(challenge_hex: str, d: int):
    e = _msg_int(challenge_hex)
    while True:
        k = _rfc6979_k(d, e)
        R = _mul(k, G); r = R[0] % N
        s = _inv(k, N) * (e + r * d) % N
        if r and s:
            if s > N // 2: s = N - s          # low-s
            return r, s
        e = (e + 1) % N                       # practically unreachable

def verify(challenge_hex: str, r: int, s: int, pub_hex: str) -> bool:
    pub = bytes.fromhex(pub_hex)
    if len(pub) != 65 or pub[0] != 4: raise ValueError("expected an uncompressed 65-byte public key")
    Q = (int.from_bytes(pub[1:33], "big"), int.from_bytes(pub[33:], "big"))
    if not (1 <= r < N and 1 <= s < N): return False
    e = _msg_int(challenge_hex); w = _inv(s, N)
    X = _add(_mul(e * w % N, G), _mul(r * w % N, Q))
    return X is not None and X[0] % N == r

def _from_sigfile(path: pathlib.Path):
    """Read r, s, the public key and the signed digest out of a *.secp256k1 file."""
    t = path.read_text(encoding="utf-8")
    msg = re.search(r"message signed\s+([0-9a-f]{64})", t)
    r = re.search(r"^\s*r\s+([0-9a-f]{64})\s*$", t, re.M)
    s = re.search(r"^\s*s\s+([0-9a-f]{64})\s*$", t, re.M)
    pub = re.search(r"public key\s+([0-9a-f]+)\s*\n\s*([0-9a-f]+)", t)
    if not (msg and r and s and pub): raise ValueError(f"could not parse {path}")
    pubhex = pub.group(1) + pub.group(2)
    if len(pubhex) != 130: raise ValueError(f"public key in {path} is {len(pubhex)} hex chars, expected 130")
    return msg.group(1), int(r.group(1), 16), int(s.group(1), 16), pubhex

def main(argv):
    if len(argv) >= 5 and argv[0] == "verify":
        ok = verify(argv[1], int(argv[2], 16), int(argv[3], 16), argv[4])
        print("VERIFIES" if ok else "DOES NOT VERIFY"); return 0 if ok else 1
    if len(argv) == 2 and argv[0] == "check":
        doc = pathlib.Path(argv[1]); sig = doc.with_name(doc.name + ".secp256k1")
        digest = hashlib.sha256(doc.read_bytes()).hexdigest()
        msg, r, s, pub = _from_sigfile(sig)
        if msg != digest:
            print(f"the file hashes to {digest} but the signature file names {msg}"); return 1
        ok = verify(digest, r, s, pub)
        print(f"{doc.name}: sha256 {digest}\n  signature {'VERIFIES' if ok else 'DOES NOT VERIFY'} against key {pub[:16]}…"); return 0 if ok else 1
    if len(argv) >= 4 and argv[0] == "sign" and argv[2] == "--key":
        d = int(pathlib.Path(argv[3]).read_text().strip(), 16)
        r, s = sign(argv[1], d)
        print(f"r  {r:064x}\ns  {s:064x}"); return 0
    print(__doc__); return 2

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
