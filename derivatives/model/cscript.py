"""Byte-level CScript for the MODEL: assemble token scripts to v0.1 bytes, parse
them back via GetOp, and FindAndDelete — so OP_CHECKSIG's scriptCode is derived
from the real serialized subscript (script.cpp), not a configured constant.

Opcode byte values are loaded from our own generated `inventory/OPCODES.json`
(itself produced from the extracted script.h), keeping the byte encoding anchored
to the canonical source. Evidence level: MODEL.

Push encoding follows script.h CScript::operator<<(vector<unsigned char>):
  len < 76        -> [len][data]
  len <= 0xff     -> [OP_PUSHDATA1][len][data]
  else            -> [OP_PUSHDATA2][len:2 LE][data]
GetOp follows script.h CScript::GetOp.
"""

from __future__ import annotations

import json
from pathlib import Path

_OPC = json.loads(
    (Path(__file__).resolve().parents[2] / "inventory" / "OPCODES.json").read_text())
NAME_TO_OP = {o["name"]: o["value"] for o in _OPC["opcodes"]}
# value -> canonical name (skip aliases so 0x00->OP_0, 0x51->OP_1)
OP_TO_NAME: dict[int, str] = {}
for o in _OPC["opcodes"]:
    if o["alias_of"] is None and o["value"] not in OP_TO_NAME:
        OP_TO_NAME[o["value"]] = o["name"]

OP_PUSHDATA1 = NAME_TO_OP["OP_PUSHDATA1"]   # 76
OP_PUSHDATA2 = NAME_TO_OP["OP_PUSHDATA2"]   # 77
OP_PUSHDATA4 = NAME_TO_OP["OP_PUSHDATA4"]   # 78


def _push_data(data: bytes) -> bytes:
    n = len(data)
    if n < OP_PUSHDATA1:
        return bytes([n]) + data
    if n <= 0xFF:
        return bytes([OP_PUSHDATA1, n]) + data
    return bytes([OP_PUSHDATA2, n & 0xFF, (n >> 8) & 0xFF]) + data


def assemble(tokens: list) -> bytes:
    """Tokens: bytes (data push) or an OP_ name string (single-byte opcode)."""
    out = bytearray()
    for t in tokens:
        if isinstance(t, (bytes, bytearray)):
            out += _push_data(bytes(t))
        elif t in NAME_TO_OP:
            v = NAME_TO_OP[t]
            if v > 0xFF:
                raise ValueError(f"multi-byte opcode not assembled: {t}")
            out.append(v)
        else:
            raise ValueError(f"unknown token: {t!r}")
    return bytes(out)


def _iter_ops(script: bytes):
    """Yield (start, end, opcode_byte, pushdata_or_None) per GetOp."""
    pc = 0
    n = len(script)
    while pc < n:
        start = pc
        op = script[pc]; pc += 1
        data = None
        if op <= OP_PUSHDATA4:
            if op < OP_PUSHDATA1:
                size = op
            elif op == OP_PUSHDATA1:
                if pc + 1 > n:
                    return
                size = script[pc]; pc += 1
            elif op == OP_PUSHDATA2:
                if pc + 2 > n:
                    return
                size = script[pc] | (script[pc + 1] << 8); pc += 2
            else:  # OP_PUSHDATA4
                if pc + 4 > n:
                    return
                size = int.from_bytes(script[pc:pc + 4], "little"); pc += 4
            if pc + size > n:
                return
            data = script[pc:pc + size]; pc += size
        yield start, pc, op, data


def parse(script: bytes) -> list:
    """Inverse of assemble: bytes -> tokens (pushdata bytes / OP_ names)."""
    tokens = []
    for _s, _e, op, data in _iter_ops(script):
        if data is not None:
            tokens.append(data)
        else:
            tokens.append(OP_TO_NAME.get(op, f"OP_UNKNOWN_{op:02x}"))
    return tokens


def find_and_delete(script: bytes, needle: bytes) -> bytes:
    """CScript::FindAndDelete — remove each opcode chunk equal to `needle`."""
    if not needle:
        return script
    out = bytearray()
    for s, e, _op, _data in _iter_ops(script):
        chunk = script[s:e]
        if chunk != needle:
            out += chunk
    return bytes(out)
