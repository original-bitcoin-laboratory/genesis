"""Replay derivatives/vectors/*.json through the clean-room validator.

Two modes:
  JAN09-B : the rules docs/JAN09-B-SPECIFICATION.md states.
  JAN09   : the January 2009 release's rules, which the corpus's expected
            values are stated against.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jan09b as V

VEC = "/home/claude/genesis/derivatives/vectors"
PB = V.Params(V.JAN09B)
P1 = V.Params(V.JAN09)

results = {}   # suite -> mode -> list of (label, ok, detail)


def record(suite, mode, label, ok, detail=""):
    results.setdefault(suite, {}).setdefault(mode, []).append((label, ok, detail))


def load(name):
    with open(os.path.join(VEC, name)) as f:
        return json.load(f)


# ---------------------------------------------------------------- headers ---
def run_headers():
    d = load("headers.json")
    for v in d["vectors"]:
        f = v["fields"]
        hdr = (f["nVersion"].to_bytes(4, "little")
               + bytes.fromhex(f["hashPrevBlock"])[::-1]
               + bytes.fromhex(f["hashMerkleRoot"])[::-1]
               + f["nTime"].to_bytes(4, "little")
               + int(f["nBits"], 16).to_bytes(4, "little")
               + f["nNonce"].to_bytes(4, "little"))
        h = V.dsha256(hdr)
        target, _, _ = V.set_compact(int(f["nBits"], 16))
        pow_ok = int.from_bytes(h, "little") <= target
        got = (hdr.hex(), h[::-1].hex(), pow_ok)
        want = (v["header_hex"], v["hash"], v["pow_ok"])
        for mode in ("JAN09-B", "JAN09"):
            record("headers", mode, v["label"], got == want,
                   "" if got == want else "got=%r want=%r" % (got, want))


# ----------------------------------------------------------------- merkle ---
def run_merkle():
    d = load("merkle.json")
    for v in d["vectors"]:
        leaves = [bytes.fromhex(x) for x in v["leaves_hex"]]
        got = V.merkle_root(leaves).hex()
        ok = got == v["root_hex"]
        for mode in ("JAN09-B", "JAN09"):
            record("merkle", mode, v["label"], ok,
                   "" if ok else "got=%s want=%s" % (got, v["root_hex"]))


# --------------------------------------------------------------- retarget ---
def run_retarget():
    d = load("retarget.json")
    c = d["constants"]
    tts = c["nTargetTimespan"]
    n_interval = c["nInterval"]
    pow_nbits = int(c["bnProofOfWorkLimit_nbits"], 16)
    for v in d["vectors"]:
        w = v["window"]
        times = [w["t0"] + i * w["spacing"] for i in range(w["count"])]
        if w["last_override"] is not None:
            times[w["count"] - 1] = w["last_override"]
        actual = times[-1] - times[-n_interval]
        new = V.get_next_work_required(int(v["old_nbits"], 16), actual,
                                       tts, pow_nbits)
        ok = (actual == v["n_actual_timespan"]
              and "0x%08x" % new == v["new_nbits"])
        for mode in ("JAN09-B", "JAN09"):
            record("retarget", mode, v["label"], ok,
                   "" if ok else "actual=%d want=%d nbits=0x%08x want=%s"
                   % (actual, v["n_actual_timespan"], new, v["new_nbits"]))
    for k, cse in enumerate(d["nbits_codec"]):
        nb = int(cse["nbits"], 16)
        t, neg, over = V.set_compact(nb)
        rt = V.get_compact(t)
        ok = ("%064x" % t == cse["target_hex"]
              and "0x%08x" % rt == cse["roundtrip_nbits"]
              and neg == cse["negative"] and over == cse["overflow"]
              and str((1 << 256) // (t + 1)) == cse["expected_hashes"])
        for mode in ("JAN09-B", "JAN09"):
            record("retarget-codec", mode, cse["nbits"], ok,
                   "" if ok else "target=%064x rt=0x%08x" % (t, rt))


# ---------------------------------------------------------------- sighash ---
def run_sighash():
    d = load("sighash.json")
    for v in d["vectors"]:
        tx = V.Tx.from_hex(v["tx_hex"])
        code = bytes.fromhex(v["script_code_hex"])
        got = V.signature_hash(code, tx, v["n_in"], v["hash_type"]).hex()
        ok = got == v["digest_hex"]
        for mode in ("JAN09-B", "JAN09"):
            record("sighash", mode, v["label"], ok,
                   "" if ok else "got=%s want=%s" % (got, v["digest_hex"]))


# ------------------------------------------------------------- evalscript ---
def run_evalscript():
    d = load("evalscript.json")
    for v in d["vectors"]:
        script = bytes.fromhex(v["script_hex"])
        for mode, params in (("JAN09-B", PB), ("JAN09", P1)):
            stack = []
            try:
                ok = V.eval_script(script, stack, params, checker=None)
            except Exception as e:
                ok = False
                stack = []
            top = stack[-1].hex() if (ok and stack) else None
            valid = bool(ok and stack and V.cast_to_bool(stack[-1]))
            depth = len(stack) if ok else None
            got = (ok, valid, top, depth)
            want = (v["ok"], v["valid"], v["top_hex"], v["stack_depth"])
            record("evalscript", mode, v["label"], got == want,
                   "" if got == want else "got=%r want=%r" % (got, want))


# --------------------------------------------------------------- checksig ---
def run_checksig():
    d = load("checksig.json")
    for v in d["vectors"]:
        tx = V.Tx.from_hex(v["tx_hex"])
        ssig = bytes.fromhex(v["script_sig_hex"])
        spk = bytes.fromhex(v["script_pubkey_hex"])
        for mode, params, col in (("JAN09-B", PB, "expected_strict_der"),
                                  ("JAN09", P1, "expected_binary")):
            try:
                got = V.verify_signature(ssig, spk, tx, v["n_in"], params)
            except Exception as e:
                got = "ERROR:%s" % e
            want = v[col]
            if want is None:
                record("checksig", mode, v["label"], None,
                       "corpus has no expected value (%s=null); mine=%r" % (col, got))
            else:
                record("checksig", mode, v["label"], got == want,
                       "" if got == want else "got=%r want=%r (%s)" % (got, want, col))


# ----------------------------------------------------------------- blocks ---
def run_blocks():
    d = load("blocks.json")
    pow_nbits = int(d["pow_limit_nbits"], 16)
    gen = bytes.fromhex(d["genesis_hash"])[::-1]
    for mode, params in (("JAN09-B", PB), ("JAN09", P1)):
        chain = V.Chain(params, pow_limit_nbits=pow_nbits, genesis_hash=gen)
        for v in d["vectors"]:
            blk = V.Block.from_hex(v["block_hex"])
            try:
                verdict, stage, reason = chain.process_block(blk, now=v.get("now"))
            except Exception as e:
                verdict, stage, reason = "ERROR", "ERROR", repr(e)
            tip_h = chain.tip.height if chain.tip else None
            after_ok = (tip_h == v["after"]["tip_height"]
                        and len(chain.utxo) == v["after"]["utxo_count"])
            ok = (verdict == v["expect"]) and after_ok
            detail = ""
            if not ok:
                detail = ("verdict=%s want=%s stage=%s want=%s tip=%s/%s utxo=%d/%d"
                          % (verdict, v["expect"], stage, v["stage"], tip_h,
                             v["after"]["tip_height"], len(chain.utxo),
                             v["after"]["utxo_count"]))
            record("blocks", mode, v["label"], ok, detail)


def main():
    run_headers()
    run_merkle()
    run_retarget()
    run_sighash()
    run_evalscript()
    run_checksig()
    run_blocks()

    print("%-18s %-9s %6s %6s %6s %6s" % ("suite", "mode", "n", "agree", "differ", "n/a"))
    print("-" * 60)
    for suite in ("headers", "merkle", "retarget", "retarget-codec", "sighash",
                  "evalscript", "checksig", "blocks"):
        for mode in ("JAN09-B", "JAN09"):
            rs = results.get(suite, {}).get(mode, [])
            agree = sum(1 for _, ok, _ in rs if ok is True)
            differ = sum(1 for _, ok, _ in rs if ok is False)
            na = sum(1 for _, ok, _ in rs if ok is None)
            print("%-18s %-9s %6d %6d %6d %6d" % (suite, mode, len(rs), agree, differ, na))
    print()
    print("=== disagreements and unresolvable vectors ===")
    for suite, modes in results.items():
        for mode, rs in modes.items():
            for label, ok, detail in rs:
                if ok is not True:
                    tag = "DIFFER" if ok is False else "N/A   "
                    print("%s %-14s %-9s %-34s %s" % (tag, suite, mode, label, detail))


if __name__ == "__main__":
    main()
