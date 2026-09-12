#!/usr/bin/env python3
"""Replay the JSON corpus from the rules alone — hashlib and integer arithmetic, nothing from the lab.

    python verify_vectors.py            # retarget, merkle, headers from first principles; evalscript via the model
    python verify_vectors.py --no-model # skip the evalscript suite (needs ../model); everything else is pure

This file is the "from the spec" verifier: it deliberately does NOT import retarget.py or p2p.py.
If it agrees with the corpus, the prose rules in README.md are sufficient to reimplement those
three surfaces. The evalscript suite needs a Script interpreter, so it is replayed through the
lab's model and reported separately. Exit code 0 iff every vector passes. NOT money.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent


def dsha256(b: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


def load(name: str) -> dict:
    return json.loads((HERE / name).read_text(encoding="ascii"))


# ---- nBits codec, written from the rule text -------------------------------------------------

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
        new = old * span // timespan
        new = min(new, pow_limit)
        got = f"0x{get_compact(new):08x}"
        if got != v["new_nbits"]:
            fails.append(f"retarget {v['label']}: {got} != {v['new_nbits']}")
    for c in d["nbits_codec"]:
        n += 1
        t, neg, ovf = set_compact(int(c["nbits"], 16))
        exp_hashes = str((1 << 256) // (t + 1))
        if (f"{t:064x}", neg, ovf, f"0x{get_compact(t):08x}", exp_hashes) != (
                c["target_hex"], c["negative"], c["overflow"], c["roundtrip_nbits"], c["expected_hashes"]):
            fails.append(f"nbits codec {c['nbits']}: mismatch")
    return n, fails


def check_merkle() -> tuple[int, list[str]]:
    d = load("merkle.json")
    fails, n = [], 0
    for v in d["vectors"]:
        n += 1
        h = [bytes.fromhex(x) for x in v["leaves_hex"]]
        while len(h) > 1:
            if len(h) & 1:
                h.append(h[-1])
            h = [dsha256(h[i] + h[i + 1]) for i in range(0, len(h), 2)]
        if h[0].hex() != v["root_hex"]:
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
        h = dsha256(hdr)
        if h[::-1].hex() != v["hash"]:
            fails.append(f"headers {v['label']}: hash mismatch")
        target, _, _ = set_compact(int(f["nBits"], 16))
        if (int.from_bytes(h, "little") <= target) != v["pow_ok"]:
            fails.append(f"headers {v['label']}: pow_ok mismatch")
    return n, fails


def check_evalscript() -> tuple[int, list[str]]:
    sys.path.insert(0, str(HERE.parent / "model"))
    import cscript                                  # noqa: E402
    from evalscript_model import cast_to_bool, run  # noqa: E402
    d = load("evalscript.json")
    fails, n = [], 0
    for v in d["vectors"]:
        n += 1
        ok, stack = run(cscript.parse(bytes.fromhex(v["script_hex"])), None)
        valid = bool(ok and stack and cast_to_bool(stack[-1]))
        top = stack[-1].hex() if (ok and stack) else None
        depth = len(stack) if ok else None
        if (bool(ok), valid, top, depth) != (v["ok"], v["valid"], v["top_hex"], v["stack_depth"]):
            fails.append(f"evalscript {v['label']}: got ok={ok} valid={valid} top={top}")
    return n, fails


def main(argv: list[str]) -> int:
    fails = check_manifest()
    total = 0
    suites = [("retarget", check_retarget), ("merkle", check_merkle), ("headers", check_headers)]
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
