"""OpenSSL's DER parsing as a consensus rule, and the rule written to replace it -- MODEL, one side executed.

The second rule nobody wrote (constitution row OBL-C-0014, docs/CONSENSUS-ATLAS.md section 9): the
January 2009 client hands every signature to OpenSSL, so what OpenSSL's parser accepted was what the
chain accepted. BIP 66 (2015) wrote the acceptance rule down as IsValidSignatureEncoding, and it was
enforced from 4 July 2015.

What this module executes:

  * IsValidSignatureEncoding, ported line for line from BIP 66's reference implementation;
  * a BER-tolerant reader that models the three tolerances the laboratory's corpus probes -- a
    long-form outer length, a redundant leading 0x00 on an integer, and a byte between the DER and
    the sighash flag -- and returns the (r, s) pair a tolerant parser would recover;

and runs both over the corpus's checksig vectors (../vectors/checksig.json): every signature the
corpus marks strict passes BIP 66; each of the three probes fails BIP 66, and the (r, s) the tolerant
reader recovers from it verifies under the vector's own key over the vector's own signature hash
(test_emergent.py, with the laboratory's SignatureHash model and an ECDSA verifier), which is what
"differs from a strict signature only in encoding" means here. (An earlier docstring said each probe
is read "to the same (r, s) as its strict twin"; the corpus holds no such twin, and an adversarial
review of 20 September 2026 said so. The corrected statement is the one above.)

The tolerant reader is a model of the tolerance, not OpenSSL 0.9.8: whether the 2009 binary accepts
each probe is recorded in the corpus as `expected_binary: null` until that binary is replayed. The
laboratory's release build (OpenSSL 1.0.2u) rejects all three (finding OBL-F-0010). The acceptance
side of the rule, that OpenSSL 0.9.8 accepted these encodings, has no artifact at any grade; the
constitution row stays open on it. NOT money.
"""
from __future__ import annotations

import json
import pathlib

_HERE = pathlib.Path(__file__).resolve().parent
CHECKSIG_JSON = _HERE.parent / "vectors" / "checksig.json"


# -- BIP 66, verbatim in structure -----------------------------------------------------------------
def is_valid_signature_encoding(sig: bytes) -> bool:
    """IsValidSignatureEncoding(sig) from BIP 66. `sig` includes the trailing sighash byte."""
    # Minimum and maximum size constraints.
    if len(sig) < 9:
        return False
    if len(sig) > 73:
        return False
    # A signature is of type 0x30 (compound).
    if sig[0] != 0x30:
        return False
    # Make sure the length covers the entire signature.
    if sig[1] != len(sig) - 3:
        return False
    # Extract the length of the R element.
    len_r = sig[3]
    # Make sure the length of the S element is still inside the signature.
    if 5 + len_r >= len(sig):
        return False
    # Extract the length of the S element.
    len_s = sig[5 + len_r]
    # Verify that the length of the signature matches the sum of the length of the elements.
    if len_r + len_s + 7 != len(sig):
        return False
    # Check whether the R element is an integer.
    if sig[2] != 0x02:
        return False
    # Zero-length integers are not allowed for R.
    if len_r == 0:
        return False
    # Negative numbers are not allowed for R.
    if sig[4] & 0x80:
        return False
    # Null bytes at the start of R are not allowed, unless R would otherwise be interpreted as negative.
    if len_r > 1 and sig[4] == 0x00 and not (sig[5] & 0x80):
        return False
    # Check whether the S element is an integer.
    if sig[len_r + 4] != 0x02:
        return False
    # Zero-length integers are not allowed for S.
    if len_s == 0:
        return False
    # Negative numbers are not allowed for S.
    if sig[len_r + 6] & 0x80:
        return False
    # Null bytes at the start of S are not allowed, unless S would otherwise be interpreted as negative.
    if len_s > 1 and sig[len_r + 6] == 0x00 and not (sig[len_r + 7] & 0x80):
        return False
    return True


# -- a BER-tolerant reader: the three tolerances the corpus probes -----------------------------------
def _read_length(b: bytes, i: int) -> tuple[int, int]:
    """BER length at b[i]: short form, or long form 0x81 LL. Returns (length, next index)."""
    if b[i] < 0x80:
        return b[i], i + 1
    n = b[i] & 0x7F
    if n == 0 or i + 1 + n > len(b):
        raise ValueError("bad length")
    return int.from_bytes(b[i + 1:i + 1 + n], "big"), i + 1 + n


def parse_signature_tolerant(sig: bytes) -> tuple[int, int, int]:
    """Read (r, s, sighash) accepting long-form lengths, non-minimal integers and bytes between the
    sequence and the sighash flag. Rejects what no parser accepts: a wrong tag, an integer that runs
    past its container, or a negative integer (r and s are unsigned in ECDSA)."""
    if len(sig) < 2 or sig[0] != 0x30:
        raise ValueError("not a sequence")
    seq_len, i = _read_length(sig, 1)
    end = i + seq_len
    if end > len(sig) - 1:
        raise ValueError("sequence runs past the signature")
    vals = []
    for _ in range(2):
        if sig[i] != 0x02:
            raise ValueError("not an integer")
        n, i = _read_length(sig, i + 1)
        if n == 0 or i + n > end:
            raise ValueError("integer runs past the sequence")
        body = sig[i:i + n]
        if body[0] & 0x80:
            raise ValueError("negative integer")
        vals.append(int.from_bytes(body, "big"))      # a redundant 0x00 pad reads to the same value
        i += n
    # anything between the sequence's end and the final byte is tolerated; the last byte is the flag
    return vals[0], vals[1], sig[-1]


def encode_strict(r: int, s: int, flag: int) -> bytes:
    """The one strict DER encoding of (r, s) plus the sighash byte: minimal unsigned integers."""
    def integer(v: int) -> bytes:
        body = v.to_bytes((v.bit_length() + 7) // 8 or 1, "big")
        if body[0] & 0x80:
            body = b"\x00" + body
        return bytes([0x02, len(body)]) + body
    seq = integer(r) + integer(s)
    return bytes([0x30, len(seq)]) + seq + bytes([flag])


# -- the corpus ----------------------------------------------------------------------------------------
def signature_from_script_sig(script_sig_hex: str) -> bytes | None:
    """A pay-to-pubkey scriptSig is one push of the signature; return its bytes, or None."""
    b = bytes.fromhex(script_sig_hex)
    if not b:
        return None
    n = b[0]
    if 1 <= n <= 75 and len(b) == 1 + n:
        return b[1:]
    return None


def corpus() -> list[dict]:
    d = json.loads(CHECKSIG_JSON.read_text(encoding="utf-8"))
    return [v for v in d["vectors"] if v.get("kind") == "p2pk"]


def report() -> None:
    print("DER STRICTNESS -- BIP 66 IsValidSignatureEncoding over the corpus (MODEL)")
    strict_ok = probes = 0
    for v in corpus():
        sig = signature_from_script_sig(v["script_sig_hex"])
        if sig is None:
            continue
        strict = is_valid_signature_encoding(sig)
        try:
            r, s, flag = parse_signature_tolerant(sig)
            tolerant = f"reads r={hex(r)[:10]}.. s={hex(s)[:10]}.. flag={flag}"
        except ValueError as e:
            tolerant = f"rejects ({e})"
        mark = "probe" if v.get("expected_binary") is None else "     "
        print(f"  {mark} strict={str(strict):5}  tolerant {tolerant:44}  {v['note'][:60]}")
        if v.get("expected_strict_der") is True and strict:
            strict_ok += 1
        if v.get("expected_binary") is None:
            probes += 1
    print(f"  => {strict_ok} strict signatures pass BIP 66; {probes} probes fail it and are read by a tolerant parser;")
    print("     the 2009 binary's verdict on the probes stays open until it is replayed. NOT money.")


if __name__ == "__main__":
    report()
