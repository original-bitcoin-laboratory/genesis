"""Byte-level CScript vectors (assemble / parse / find_and_delete). The opcode
byte values come from our generated inventory/OPCODES.json; the hardcoded bytes
here double as a check that those values match the known v0.1 encoding.
Evidence level: MODEL.
"""

import cscript


def test_push_encoding():
    assert cscript.assemble([b"\x01\x02"]) == b"\x02\x01\x02"                 # [len][data]
    assert cscript.assemble([b"\xaa" * 75]) == bytes([75]) + b"\xaa" * 75
    assert cscript.assemble([b"\xaa" * 76]) == bytes([0x4C, 76]) + b"\xaa" * 76  # OP_PUSHDATA1
    assert cscript.assemble([b"\x00" * 256])[:3] == bytes([0x4D, 0x00, 0x01])    # OP_PUSHDATA2 (LE)


def test_opcode_bytes_match_known_v01_values():
    assert cscript.assemble(["OP_0"]) == b"\x00"
    assert cscript.assemble(["OP_1"]) == b"\x51"
    assert cscript.assemble(["OP_16"]) == b"\x60"
    assert cscript.assemble(["OP_DUP", "OP_HASH160"]) == bytes([0x76, 0xA9])
    assert cscript.assemble(["OP_EQUALVERIFY", "OP_CHECKSIG"]) == bytes([0x88, 0xAC])
    assert cscript.assemble(["OP_CHECKMULTISIG"]) == b"\xae"
    assert cscript.assemble(["OP_CODESEPARATOR"]) == b"\xab"


def test_roundtrip_parse():
    pub = b"\x04" + b"\x11" * 64
    assert cscript.parse(cscript.assemble([pub, "OP_CHECKSIG"])) == [pub, "OP_CHECKSIG"]
    p2pkh = ["OP_DUP", "OP_HASH160", b"\x33" * 20, "OP_EQUALVERIFY", "OP_CHECKSIG"]
    assert cscript.parse(cscript.assemble(p2pkh)) == p2pkh


def test_find_and_delete_removes_sig_push():
    sig = b"\x30" + b"\x44" * 10
    pub = b"\x04" + b"\x11" * 64
    script = cscript.assemble([sig, pub, "OP_CHECKSIG"])
    got = cscript.find_and_delete(script, cscript.assemble([sig]))
    assert got == cscript.assemble([pub, "OP_CHECKSIG"])
