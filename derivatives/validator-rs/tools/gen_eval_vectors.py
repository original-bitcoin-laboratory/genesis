"""Regenerate the Rust EvalScript golden vectors from the verified Python model.

    python validator-rs/tools/gen_eval_vectors.py

Writes validator-rs/tests/data/eval_data.rs: a broad opcode-coverage suite (arithmetic incl. big
numbers, stack/alt-stack, splice, bitwise, comparisons, hashes, flow control, VERIFY/RETURN,
structural errors) — each a script assembled to bytes, run through model/evalscript_model, with the
resulting (ok, valid). NOT money.
"""
import hashlib
import pathlib
import sys

D = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(D / "model"))

import cscript
from evalscript_model import bn_to_vch, cast_to_bool, run

n = bn_to_vch  # push an integer


def ripemd160(b):
    return hashlib.new("ripemd160", b).digest()


SHA256_ABC = hashlib.sha256(b"abc").digest()
SHA1_EMPTY = hashlib.sha1(b"").digest()
RIPEMD_ABC = ripemd160(b"abc")
HASH160_ABC = ripemd160(hashlib.sha256(b"abc").digest())
HASH256_ABC = hashlib.sha256(hashlib.sha256(b"abc").digest()).digest()

CASES = [
    # label, tokens
    ("push_true", ["OP_5"]),
    ("push_false0", ["OP_0"]),
    ("push_neg1", ["OP_1NEGATE"]),
    ("push_zerobyte_false", [b"\x00"]),
    ("add", ["OP_2", "OP_3", "OP_ADD", "OP_5", "OP_EQUAL"]),
    ("sub", ["OP_5", "OP_3", "OP_SUB", "OP_2", "OP_EQUAL"]),
    ("mul", ["OP_3", "OP_4", "OP_MUL", n(12), "OP_EQUAL"]),
    ("div", [n(20), "OP_6", "OP_DIV", "OP_3", "OP_EQUAL"]),
    ("mod", [n(20), "OP_6", "OP_MOD", "OP_2", "OP_EQUAL"]),
    ("abs_neg", [n(-7), "OP_ABS", "OP_7", "OP_EQUAL"]),
    ("negate", ["OP_7", "OP_NEGATE", n(-7), "OP_EQUAL"]),
    ("1add", ["OP_5", "OP_1ADD", "OP_6", "OP_EQUAL"]),
    ("1sub", ["OP_5", "OP_1SUB", "OP_4", "OP_EQUAL"]),
    ("2mul", ["OP_6", "OP_2MUL", n(12), "OP_EQUAL"]),
    ("2div", ["OP_7", "OP_2DIV", "OP_3", "OP_EQUAL"]),
    ("0notequal", ["OP_5", "OP_0NOTEQUAL"]),
    ("bignum_lshift", ["OP_1", n(64), "OP_LSHIFT", n(2 ** 64), "OP_EQUAL"]),
    ("bignum_add", [n(2 ** 70), "OP_5", "OP_ADD", n(2 ** 70 + 5), "OP_EQUAL"]),
    ("div_by_zero_err", ["OP_5", "OP_0", "OP_DIV"]),
    ("lessthan", ["OP_3", "OP_5", "OP_LESSTHAN"]),
    ("numequal", ["OP_5", "OP_5", "OP_NUMEQUAL"]),
    ("numnotequal", ["OP_5", "OP_6", "OP_NUMNOTEQUAL"]),
    ("gte", ["OP_5", "OP_5", "OP_GREATERTHANOREQUAL"]),
    ("min", ["OP_3", "OP_9", "OP_MIN", "OP_3", "OP_EQUAL"]),
    ("max", ["OP_3", "OP_9", "OP_MAX", "OP_9", "OP_EQUAL"]),
    ("booland", ["OP_1", "OP_2", "OP_BOOLAND"]),
    ("within_true", [n(2), n(1), n(5), "OP_WITHIN"]),
    ("within_false", [n(5), n(1), n(5), "OP_WITHIN"]),
    ("drop", ["OP_1", "OP_2", "OP_DROP", "OP_1", "OP_EQUAL"]),
    ("dup", ["OP_1", "OP_DUP", "OP_EQUAL"]),
    ("swap", ["OP_1", "OP_2", "OP_SWAP", "OP_1", "OP_EQUAL"]),
    ("rot", ["OP_1", "OP_2", "OP_3", "OP_ROT", "OP_1", "OP_EQUAL"]),
    ("nip", ["OP_1", "OP_2", "OP_NIP", "OP_2", "OP_EQUAL"]),
    ("over", ["OP_1", "OP_2", "OP_OVER", "OP_1", "OP_EQUAL"]),
    ("tuck", ["OP_1", "OP_2", "OP_TUCK", "OP_2", "OP_EQUAL"]),
    ("2dup", ["OP_1", "OP_2", "OP_2DUP", "OP_2", "OP_EQUAL"]),
    ("2swap", ["OP_1", "OP_2", "OP_3", "OP_4", "OP_2SWAP", "OP_2", "OP_EQUAL"]),
    ("2rot", ["OP_1", "OP_2", "OP_3", "OP_4", "OP_5", "OP_6", "OP_2ROT", "OP_2", "OP_EQUAL"]),
    ("3dup", ["OP_1", "OP_2", "OP_3", "OP_3DUP", "OP_3", "OP_EQUAL"]),
    ("2over", ["OP_1", "OP_2", "OP_3", "OP_4", "OP_2OVER", "OP_2", "OP_EQUAL"]),
    ("depth", ["OP_2", "OP_3", "OP_DEPTH", n(2), "OP_EQUAL"]),
    ("ifdup_true", ["OP_5", "OP_IFDUP", "OP_5", "OP_EQUAL"]),
    ("altstack", ["OP_7", "OP_TOALTSTACK", "OP_1", "OP_FROMALTSTACK", "OP_7", "OP_EQUAL"]),
    ("pick", ["OP_1", "OP_2", "OP_3", n(2), "OP_PICK", "OP_1", "OP_EQUAL"]),
    ("roll", ["OP_1", "OP_2", "OP_3", n(2), "OP_ROLL", "OP_1", "OP_EQUAL"]),
    ("pick_neg_err", ["OP_1", n(-1), "OP_PICK"]),
    ("cat", [b"\xaa", b"\xbb", "OP_CAT", b"\xaa\xbb", "OP_EQUAL"]),
    ("substr", [b"\x11\x22\x33", "OP_0", n(2), "OP_SUBSTR", b"\x11\x22", "OP_EQUAL"]),
    ("left", [b"\x11\x22\x33", n(2), "OP_LEFT", b"\x11\x22", "OP_EQUAL"]),
    ("right", [b"\x11\x22\x33", n(2), "OP_RIGHT", b"\x22\x33", "OP_EQUAL"]),
    ("size", [b"\xaa\xbb\xcc", "OP_SIZE", "OP_3", "OP_EQUAL"]),
    ("invert", [b"\xff", "OP_INVERT", b"\x00", "OP_EQUAL"]),
    ("and", [b"\xff", b"\x0f", "OP_AND", b"\x0f", "OP_EQUAL"]),
    ("or", [b"\xf0", b"\x0f", "OP_OR", b"\xff", "OP_EQUAL"]),
    ("xor", [b"\xff", b"\xff", "OP_XOR", b"\x00", "OP_EQUAL"]),
    ("sha256", [b"abc", "OP_SHA256", SHA256_ABC, "OP_EQUAL"]),
    ("sha1", [b"", "OP_SHA1", SHA1_EMPTY, "OP_EQUAL"]),
    ("ripemd160", [b"abc", "OP_RIPEMD160", RIPEMD_ABC, "OP_EQUAL"]),
    ("hash160", [b"abc", "OP_HASH160", HASH160_ABC, "OP_EQUAL"]),
    ("hash256", [b"abc", "OP_HASH256", HASH256_ABC, "OP_EQUAL"]),
    ("if_true", ["OP_1", "OP_IF", "OP_2", "OP_ELSE", "OP_3", "OP_ENDIF", "OP_2", "OP_EQUAL"]),
    ("if_false", ["OP_0", "OP_IF", "OP_2", "OP_ELSE", "OP_3", "OP_ENDIF", "OP_3", "OP_EQUAL"]),
    ("notif", ["OP_1", "OP_NOTIF", "OP_2", "OP_ELSE", "OP_3", "OP_ENDIF", "OP_3", "OP_EQUAL"]),
    ("nested_if", ["OP_1", "OP_IF", "OP_1", "OP_IF", "OP_5", "OP_ENDIF", "OP_ENDIF", "OP_5", "OP_EQUAL"]),
    ("verify_true", ["OP_1", "OP_VERIFY", "OP_7", "OP_7", "OP_EQUAL"]),
    ("verify_false", ["OP_0", "OP_VERIFY"]),
    ("equalverify_true", ["OP_5", "OP_5", "OP_EQUALVERIFY", "OP_1"]),
    ("equalverify_false", ["OP_5", "OP_6", "OP_EQUALVERIFY", "OP_1"]),
    ("return_stops", ["OP_1", "OP_RETURN", "OP_0"]),
    ("underflow_add_err", ["OP_ADD"]),
    ("underflow_drop_err", ["OP_DROP"]),
    ("stray_endif_err", ["OP_ENDIF"]),
    ("codeseparator_nop", ["OP_1", "OP_CODESEPARATOR", "OP_1", "OP_EQUAL"]),
]

out = ["// generated by gen_eval_vectors.py from the verified Python EvalScript model — do not edit", ""]
out.append("// (label, script_hex, expected_ok, expected_valid)")
out.append("pub const EVAL: &[(&str, &str, bool, bool)] = &[")
for label, tokens in CASES:
    raw = cscript.assemble(tokens)
    ok, stack = run(cscript.parse(raw), None)
    valid = ok and len(stack) > 0 and cast_to_bool(stack[-1])
    out.append(f'    ("{label}", "{raw.hex()}", {"true" if ok else "false"}, {"true" if valid else "false"}),')
out.append("];")
out.append("")

dst = D / "validator-rs" / "tests" / "data" / "eval_data.rs"
dst.write_text("\n".join(out), encoding="utf-8")
print("wrote", dst, f"({len(CASES)} cases)")
