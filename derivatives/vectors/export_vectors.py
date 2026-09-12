#!/usr/bin/env python3
"""Export the lab's conformance vectors as a language-neutral JSON corpus.

    python export_vectors.py            # regenerate ./*.json and MANIFEST.sha256
    python export_vectors.py --check    # regenerate into memory and fail if the committed files differ

Every vector is computed by the lab's verified Python MODEL (`../model`, `../retarget`, `../p2p`),
which is differentially tested against the C++/OpenSSL port (`../port`), the Rust validator
(`../validator-rs`) and, for the genesis headers, the unmodified 2009 binary (`../../r3-findings`).
The JSON carries no Python: a reader in any language can replay it from the rules stated in
README.md. Evidence level: MODEL. NOT money.

Output is deterministic (sorted keys, LF line endings) so the files diff cleanly.
"""
from __future__ import annotations

import ast
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
DERIV = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(DERIV / "model"))
sys.path.insert(0, str(DERIV / "retarget"))

import cscript                                   # noqa: E402
from evalscript_model import cast_to_bool, num, run   # noqa: E402
import retarget                                  # noqa: E402
import verify_vectors as spec                    # noqa: E402  (the from-spec primitives; cross-checked, never trusted alone)
import recipes                                   # noqa: E402
from tx_sighash import Tx, TxIn, TxOut, signature_hash as model_sighash   # noqa: E402
from spend import verify_spend as model_verify_spend                        # noqa: E402

SCHEMA = 1


def _lab_tx(tx: dict) -> Tx:
    """A from-spec tx dict as the lab model's Tx object."""
    return Tx(tx["version"], [TxIn(v["prevhash"], v["n"], v["script"], v["seq"]) for v in tx["vin"]],
              [TxOut(o["value"], o["script"]) for o in tx["vout"]], tx["locktime"])


def dsha256(b: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


def le(n: int, length: int) -> bytes:
    return n.to_bytes(length, "little")


# ---------------------------------------------------------------------------------------------
# 1. EvalScript — the same case lists the Rust and C++ differentials use, run through the model
# ---------------------------------------------------------------------------------------------

def _rust_generator_cases() -> list[tuple[str, list]]:
    """Load CASES from validator-rs/tools/gen_eval_vectors.py WITHOUT running its file-writing tail.

    The generator writes eval_data.rs at import time, so it is not importable; its CASES literal is
    extracted with `ast` and evaluated in a namespace holding the same helpers it uses.
    """
    src = (DERIV / "validator-rs" / "tools" / "gen_eval_vectors.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    node = next(n for n in tree.body
                if isinstance(n, ast.Assign) and n.targets[0].id == "CASES")   # type: ignore[attr-defined]

    def ripemd160(b: bytes) -> bytes:
        return hashlib.new("ripemd160", b).digest()

    ns = {
        "n": num,
        "SHA256_ABC": hashlib.sha256(b"abc").digest(),
        "SHA1_EMPTY": hashlib.sha1(b"").digest(),
        "RIPEMD_ABC": ripemd160(b"abc"),
        "HASH160_ABC": ripemd160(hashlib.sha256(b"abc").digest()),
        "HASH256_ABC": dsha256(b"abc"),
    }
    return eval(compile(ast.Expression(node.value), "<gen_eval_vectors.CASES>", "eval"), ns)


def _port_dsl_cases() -> list[tuple[str, list]]:
    """The C++ port differential's vectors.txt: `n:<int>` pushes an integer, `x:<hex>` pushes bytes."""
    out = []
    for i, line in enumerate((DERIV / "port" / "vectors.txt").read_text(encoding="utf-8").splitlines()):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        toks: list = []
        for tok in line.split():
            if tok.startswith("n:"):
                toks.append(num(int(tok[2:])))
            elif tok.startswith("x:"):
                toks.append(bytes.fromhex(tok[2:]))
            else:
                toks.append(tok)
        out.append((f"port_{i + 1:02d}", toks))
    return out


def _run_script(tokens: list) -> dict:
    raw = cscript.assemble(tokens)
    ok, stack = run(cscript.parse(raw), None)
    valid = bool(ok and len(stack) > 0 and cast_to_bool(stack[-1]))
    top = stack[-1].hex() if (ok and stack) else None
    return {"script_hex": raw.hex(), "ok": bool(ok), "valid": valid,
            "top_hex": top, "stack_depth": len(stack) if ok else None}


def export_evalscript() -> dict:
    vectors = []
    for label, toks in _rust_generator_cases():
        vectors.append({"label": label, "source": "validator-rs/tools/gen_eval_vectors.py", **_run_script(toks)})
    for label, toks in _port_dsl_cases():
        vectors.append({"label": label, "source": "port/vectors.txt", **_run_script(toks)})
    return {
        "schema": SCHEMA,
        "suite": "evalscript",
        "rule": ("v0.1 EvalScript (script.cpp) run on the scriptSig-free form: `ok` is whether "
                 "execution completed without error; `valid` is ok AND a non-empty stack AND "
                 "CastToBool(top); `top_hex` is the top stack element after execution (null if not ok "
                 "or empty); no CHECKSIG in this suite, so no transaction context is needed."),
        "oracle": "model/evalscript_model.py (== port/port.cpp on OpenSSL BN == validator-rs)",
        "vectors": vectors,
    }


# ---------------------------------------------------------------------------------------------
# 2. Retarget — GetNextWorkRequired (main.cpp:685-728) and the nBits codec
# ---------------------------------------------------------------------------------------------

def _window(spacing: int, t0: int = 1_700_000_000) -> list[int]:
    """nInterval timestamps at a constant INTEGER spacing (no rounding, so any language agrees)."""
    return [t0 + i * spacing for i in range(retarget.N_INTERVAL)]


def export_retarget() -> dict:
    d1 = retarget.POW_LIMIT
    d4 = d1 // 4                      # a difficulty-4 target
    cases = []

    def add(label, times, old_target, note):
        new = retarget.get_next_work_required(times, old_target)
        cases.append({"label": label, "note": note,
                      "window": {"t0": times[0], "spacing": times[1] - times[0], "count": len(times),
                                 "last_override": None},
                      "old_nbits": f"0x{retarget.get_compact(old_target):08x}",
                      "new_nbits": f"0x{retarget.get_compact(new):08x}",
                      "n_actual_timespan": times[-1] - times[-retarget.N_INTERVAL]})

    add("exact_600s_is_not_fixed_point", _window(600), d4,
        "2015 measured intervals vs a 2016-interval budget: 600 s blocks read as slightly fast, target shrinks")
    add("d1_600s_goes_slightly_harder", _window(600), d1,
        "at difficulty 1 the same 600 s window computes a slightly harder target (0x1d00ffde); the pow-limit "
        "cap only bounds easing, so exact ten-minute blocks leave the floor")
    add("d1_3900s_stays_d1", _window(3900), d1,
        "65-minute blocks (the 2026 chain's observed rate): timespan > target, adjustment DOWN, clamped at the floor")
    add("d1_1200s_stays_d1", _window(1200), d1,
        "any chain slower than 600 s per block at difficulty 1 stays at 0x1d00ffff after every retarget")
    add("d4_150s_quadruple_clamp", _window(150), d4,
        "4x too fast: timespan clamped to nTargetTimespan/4, target divides by 4 exactly")
    add("d4_2400s_fencepost_misses_the_clamp", _window(2400), d4,
        "nominally 4x too slow, but 2015 measured intervals give 4,836,000 s, just under the 4x clamp of "
        "4,838,400 s, so the target eases by 2015/2016 * 4, not 4")
    add("d8_2500s_quarter_clamp", _window(2500), d1 // 8,
        "4x+ too slow: timespan clamped to 4*nTargetTimespan, target multiplies by 4 exactly (d8 -> d2)")
    add("d4_60s_still_only_4x", _window(60), d4,
        "10x too fast still clamps to 4x")

    # timewarp: honest 600 s spacing, but the boundary (last) timestamp is forged far into the future
    tw = _window(600)
    tw[-1] = tw[-2] + 4 * retarget.N_TARGET_TIMESPAN
    new = retarget.get_next_work_required(tw, d4)
    cases.append({"label": "timewarp_forged_boundary_forces_4x_drop",
                  "note": ("boundary-only measurement (main.cpp:706): one forged last timestamp forces the "
                           "maximal 4x easing; nothing binds period boundaries together"),
                  "window": {"t0": tw[0], "spacing": 600, "count": len(tw),
                             "last_override": tw[-1]},
                  "old_nbits": f"0x{retarget.get_compact(d4):08x}",
                  "new_nbits": f"0x{retarget.get_compact(new):08x}",
                  "n_actual_timespan": tw[-1] - tw[-retarget.N_INTERVAL]})

    codec = []
    for nbits in (0x1d00ffff, 0x1c00ffff, 0x1b0404cb, 0x1d00ffff - 1, 0x0300ffff, 0x1c7fffff):
        target, neg, ovf = retarget.set_compact(nbits)
        codec.append({"nbits": f"0x{nbits:08x}", "target_hex": f"{target:064x}",
                      "negative": neg, "overflow": ovf,
                      "roundtrip_nbits": f"0x{retarget.get_compact(target):08x}",
                      "expected_hashes": str(retarget.expected_hashes(target))})

    return {
        "schema": SCHEMA,
        "suite": "retarget",
        "constants": {"nTargetTimespan": retarget.N_TARGET_TIMESPAN, "nTargetSpacing": retarget.N_TARGET_SPACING,
                      "nInterval": retarget.N_INTERVAL, "bnProofOfWorkLimit_nbits": "0x1d00ffff",
                      "intervals_measured": retarget.intervals_measured()},
        "rule": ("times[i] = t0 + i*spacing for i in [0, count), then times[count-1] = last_override if not "
                 "null. nActualTimespan = times[-1] - times[-nInterval]; clamp to [nTargetTimespan/4, "
                 "nTargetTimespan*4]; new = old_target * nActualTimespan / nTargetTimespan (integer "
                 "division); if new > pow_limit then new = pow_limit; report GetCompact(new)."),
        "oracle": "retarget/retarget.py (line-for-line port of main.cpp:685-728)",
        "vectors": cases,
        "nbits_codec": codec,
    }


# ---------------------------------------------------------------------------------------------
# 3. Merkle — BuildMerkleTree (main.h:868-882): odd levels pair the last node with itself
# ---------------------------------------------------------------------------------------------

def merkle_root_of_hashes(leaves: list[bytes]) -> bytes:
    h = list(leaves)
    while len(h) > 1:
        if len(h) & 1:
            h.append(h[-1])                       # main.h:878  i2 = min(i+1, nSize-1)
        h = [dsha256(h[i] + h[i + 1]) for i in range(0, len(h), 2)]
    return h[0] if h else b"\x00" * 32


def export_merkle() -> dict:
    # cross-check the leaf-level port against the p2p MODEL's merkle_root over real transactions
    sys.path.insert(0, str(DERIV / "p2p"))
    import p2p                                    # noqa: E402
    from tx_sighash import Tx, TxIn, TxOut, serialize   # noqa: E402
    vtx = [Tx(1, [TxIn(b"\x00" * 32, 0xFFFFFFFF, bytes([i + 1]))], [TxOut(50 * 10**8, b"\x51")], 0)
           for i in range(5)]
    for k in range(1, 6):
        assert p2p.merkle_root(vtx[:k]) == merkle_root_of_hashes([dsha256(serialize(t)) for t in vtx[:k]])

    def leaf(i: int) -> bytes:
        return hashlib.sha256(f"leaf-{i}".encode()).digest()

    vectors = []
    for n in (1, 2, 3, 4, 5, 6, 7, 8):
        leaves = [leaf(i) for i in range(n)]
        vectors.append({"label": f"n{n}", "leaves_hex": [x.hex() for x in leaves],
                        "root_hex": merkle_root_of_hashes(leaves).hex()})
    a, b, c = leaf(0), leaf(1), leaf(2)
    vectors.append({"label": "cve_2012_2459_abc_equals_abcc",
                    "leaves_hex": [a.hex(), b.hex(), c.hex(), c.hex()],
                    "root_hex": merkle_root_of_hashes([a, b, c, c]).hex(),
                    "note": "same root as n3: [A,B,C] and [A,B,C,C] are indistinguishable by root"})
    assert vectors[-1]["root_hex"] == vectors[2]["root_hex"]
    return {
        "schema": SCHEMA,
        "suite": "merkle",
        "rule": ("leaves are 32-byte hashes in list order (byte order as given, i.e. internal/LE uint256 "
                 "order). While more than one node remains: if the count is odd, append a copy of the "
                 "last node; then replace the list with dsha256(node[2i] || node[2i+1]). The single "
                 "remaining node is the root. dsha256 = SHA-256(SHA-256(x))."),
        "oracle": "p2p/p2p.py merkle_root (== validator-rs/src/lib.rs, == node/node_port.cpp)",
        "vectors": vectors,
    }


# ---------------------------------------------------------------------------------------------
# 4. Headers — 80-byte serialization, hash, and the proof-of-work check
# ---------------------------------------------------------------------------------------------

def header_bytes(version, prev_le, merkle_le, ntime, nbits, nonce) -> bytes:
    return le(version, 4) + prev_le + merkle_le + le(ntime, 4) + le(nbits, 4) + le(nonce, 4)


def export_headers() -> dict:
    genesis = [
        ("satoshi_2009_genesis", "The Times 03/Jan/2009 Chancellor on brink of second bailout for banks",
         "4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b", 1231006505, 0x1d00ffff, 2083236893,
         "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f"),
        ("bitcoin_2026_genesis", "The Times 03/Aug/2026 Toll of schooling 'straitjacket'",
         "aaa5bdfd6c4075a646db9975aab8515781c67fdd73b02df1773a4e1e21a38085", 1785781375, 0x1d00ffff, 33394338,
         "00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a"),
    ]
    vectors = []
    for label, coinbase, merkle_disp, ntime, nbits, nonce, expect_disp in genesis:
        merkle_le = bytes.fromhex(merkle_disp)[::-1]
        hdr = header_bytes(1, b"\x00" * 32, merkle_le, ntime, nbits, nonce)
        h = dsha256(hdr)
        target, _, _ = retarget.set_compact(nbits)
        assert h[::-1].hex() == expect_disp, label
        assert int.from_bytes(h, "little") <= target
        vectors.append({"label": label, "coinbase_text": coinbase,
                        "fields": {"nVersion": 1, "hashPrevBlock": "00" * 32, "hashMerkleRoot": merkle_disp,
                                   "nTime": ntime, "nBits": f"0x{nbits:08x}", "nNonce": nonce},
                        "header_hex": hdr.hex(), "hash": expect_disp, "pow_ok": True})
        # negative control: the neighbouring nonce must NOT satisfy the target
        bad = header_bytes(1, b"\x00" * 32, merkle_le, ntime, nbits, nonce + 1)
        hb = dsha256(bad)
        assert int.from_bytes(hb, "little") > target
        vectors.append({"label": label + "_nonce_plus_1", "coinbase_text": coinbase,
                        "fields": {"nVersion": 1, "hashPrevBlock": "00" * 32, "hashMerkleRoot": merkle_disp,
                                   "nTime": ntime, "nBits": f"0x{nbits:08x}", "nNonce": nonce + 1},
                        "header_hex": bad.hex(), "hash": hb[::-1].hex(), "pow_ok": False})
    return {
        "schema": SCHEMA,
        "suite": "headers",
        "rule": ("header = LE32(nVersion) || hashPrevBlock (internal byte order) || hashMerkleRoot "
                 "(internal byte order) || LE32(nTime) || LE32(nBits) || LE32(nNonce), 80 bytes. "
                 "hash = dsha256(header); `hash` is shown in display order (reversed bytes). "
                 "pow_ok = hash as a little-endian 256-bit integer <= SetCompact(nBits). "
                 "hashMerkleRoot is shown in display order; reverse it to get the bytes in the header."),
        "oracle": ("the executed 2009 binary reproduces satoshi_2009_genesis (r3-findings/run1, JAN09-EXECUTED); "
                   "derivatives/bitcoin/net.py re-derives bitcoin_2026_genesis; both re-derived here from hashlib alone"),
        "vectors": vectors,
    }


# ---------------------------------------------------------------------------------------------
# 5. SignatureHash — script.cpp:818, every hash type, both inputs, and the two `return 1` cases
# ---------------------------------------------------------------------------------------------

def export_sighash() -> dict:
    ka, kb = recipes.key_from_label("sighash-a"), recipes.key_from_label("sighash-b")
    tx = recipes.make_tx([(hashlib.sha256(b"prev0").digest(), 0, b"", 0xFFFFFFFF),
                          (hashlib.sha256(b"prev1").digest(), 1, b"", 0xFFFFFFFE)],
                         [(50 * spec.COIN, recipes.p2pk(ka["sec"])), (10 * spec.COIN, recipes.OP_TRUE_SCRIPT)])
    code = recipes.p2pk(kb["sec"])
    names = {1: "ALL", 2: "NONE", 3: "SINGLE", 0x81: "ALL|ANYONECANPAY", 0x82: "NONE|ANYONECANPAY",
             0x83: "SINGLE|ANYONECANPAY"}
    cases = []
    for n_in in (0, 1):
        for ht in (1, 2, 3, 0x81, 0x82, 0x83):
            cases.append((f"in{n_in}_{names[ht].lower().replace('|', '_')}", tx, code, n_in, ht, None))
    one_out = recipes.make_tx([(v["prevhash"], v["n"], v["script"], v["seq"]) for v in tx["vin"]],
                              [(tx["vout"][0]["value"], tx["vout"][0]["script"])])
    cases.append(("in1_single_out_of_range_returns_1", one_out, code, 1, 3,
                  "SIGHASH_SINGLE with nOut >= vout.size(): SignatureHash returns the integer 1 (script.cpp:851)"))
    cases.append(("in2_out_of_range_returns_1", tx, code, 2, 1,
                  "nIn >= vin.size(): SignatureHash returns the integer 1 (script.cpp:824)"))
    code_sep = spec.push(kb["sec"]) + bytes([spec.OP_CODESEPARATOR, spec.OP_CHECKSIG])
    cases.append(("codeseparator_removed_from_scriptcode", tx, code_sep, 0, 1,
                  "OP_CODESEPARATOR inside the scriptCode is deleted before hashing, so this equals in0_all"))
    vectors = []
    for label, t, c, n_in, ht, note in cases:
        got = spec.signature_hash(c, t, n_in, ht)
        ref = model_sighash(c, _lab_tx(t), n_in, ht)
        assert got == ref, label                          # from-spec == the lab model (== the C++ port)
        v = {"label": label, "tx_hex": spec.ser_tx(t).hex(), "script_code_hex": c.hex(), "n_in": n_in,
             "hash_type": ht, "digest_hex": got.hex()}
        if note:
            v["note"] = note
        vectors.append(v)
    assert vectors[-1]["digest_hex"] == vectors[0]["digest_hex"]
    return {
        "schema": SCHEMA,
        "suite": "sighash",
        "rule": ("SignatureHash(scriptCode, tx, nIn, nHashType) (script.cpp:818): if nIn >= vin.size() return 1 "
                 "(as a 32-byte little-endian integer). Copy tx; delete every OP_CODESEPARATOR byte from "
                 "scriptCode at opcode boundaries; set every input's scriptSig empty, then vin[nIn].scriptSig = "
                 "scriptCode. If (nHashType & 0x1f) == SIGHASH_NONE (2): vout = [], and nSequence = 0 for every "
                 "input except nIn. If == SIGHASH_SINGLE (3): if nIn >= vout.size() return 1; keep vout[0..nIn], "
                 "set vout[k] for k < nIn to (nValue = -1, empty script), nSequence = 0 for inputs != nIn. If "
                 "nHashType & 0x80 (ANYONECANPAY): vin = [vin[nIn]]. digest = dsha256(serialize(tx) || "
                 "LE32(nHashType)). ECDSA signs/verifies digest as a big-endian integer."),
        "oracle": "model/tx_sighash.py == port/sighash.cpp (OpenSSL, run_sighash.sh); re-derived here from the rule",
        "vectors": vectors,
    }


# ---------------------------------------------------------------------------------------------
# 6. CheckSig / VerifySignature — P2PK and CHECKMULTISIG spends, with the DER-leniency probes
# ---------------------------------------------------------------------------------------------

def export_checksig() -> dict:
    key, wrong, kb = (recipes.key_from_label(x) for x in ("checksig-a", "checksig-wrong", "checksig-b"))
    variants = recipes.build_sig_variants(key, wrong, kb)
    vectors = []
    for v in variants:
        tx = recipes.spend(hashlib.sha256(b"funding:" + v["label"].encode()).digest(), 0, 1000, recipes.OP_TRUE_SCRIPT)
        ss = v["scriptsig"](tx, 0)
        if ss is None:
            continue
        tx["vin"][0]["script"] = ss
        strict = spec.verify_spend(ss, v["script_pubkey"], tx, 0)
        assert strict == v["expected_strict_der"], v["label"]          # the authored expectation vs the from-spec verifier
        model = bool(model_verify_spend(cscript.parse(ss), cscript.parse(v["script_pubkey"]), _lab_tx(tx), 0))
        vectors.append({"label": v["label"], "kind": v["kind"], "note": v["note"],
                        "script_sig_hex": ss.hex(), "script_pubkey_hex": v["script_pubkey"].hex(),
                        "tx_hex": spec.ser_tx(tx).hex(), "n_in": 0,
                        "expected_strict_der": v["expected_strict_der"], "expected_model": model,
                        "expected_binary": v["expected_binary"]})
    return {
        "schema": SCHEMA,
        "suite": "checksig",
        "rule": ("VerifySignature (script.cpp:1126): EvalScript(scriptSig || OP_CODESEPARATOR || scriptPubKey) with "
                 "the spending tx and nIn; valid iff execution completes and CastToBool(top). OP_CHECKSIG "
                 "(script.cpp:881 CheckSig, nHashType 0): sig empty -> false; hashType = last byte; DER = the rest; "
                 "scriptCode = script from the last executed OP_CODESEPARATOR, with the pushed signature deleted "
                 "(FindAndDelete); verify ECDSA over SignatureHash(scriptCode, tx, nIn, hashType) as a big-endian "
                 "integer; any s in [1, n-1] is accepted. OP_CHECKMULTISIG: pop nKeys, keys, nSigs, sigs, then ONE "
                 "EXTRA element; each signature is matched against the keys in order without backtracking. "
                 "The three expected_* columns: expected_strict_der = this rule with a strict DER parser; "
                 "expected_model = the lab's Python model (OpenSSL 3 via `cryptography`); expected_binary = the "
                 "frozen 2009 bitcoin.exe (OpenSSL 0.9.8), null until recorded by replay/."),
        "oracle": "model/spend.py + tx_sighash.SigChecker (== port/checksig_e2e.cpp); the binary column is the VM's",
        "test_keys": {k["label"]: {"priv_hex": f"{k['priv']:064x}", "pub_sec_hex": k["sec"].hex()}
                      for k in (key, wrong, kb)},
        "vectors": vectors,
    }


# ---------------------------------------------------------------------------------------------
# 7. Block validity — the 2009 acceptance rules on a small chain, with main.cpp's error strings
# ---------------------------------------------------------------------------------------------

EASY_NBITS = 0x207FFFFF
T0 = 1_700_000_000


def export_blocks() -> dict:
    key, wrong = recipes.key_from_label("blocks-a"), recipes.key_from_label("blocks-wrong")

    def ntime(h: int) -> int:
        return T0 + 600 * h

    vectors = []
    gen_cb = recipes.make_coinbase(0, [(50 * spec.COIN, recipes.OP_TRUE_SCRIPT)], b"obl-vectors genesis")
    genesis = recipes.assemble_block(recipes.ZERO32, [gen_cb], ntime(0), EASY_NBITS, recipes.easy_mine)
    gh = spec.dsha256(genesis[:80])
    chain = spec.Chain2009(EASY_NBITS, gh)

    def submit(label: str, raw: bytes, expect: str, stage: str, reason: str, **extra):
        r = chain.process_block(raw)
        got = (r["verdict"], r["stage"], r["reason"])
        assert got == (expect, stage, reason), (label, got)
        v = {"label": label, "block_hex": raw.hex(), "expect": expect, "stage": stage, "reason": reason,
             "after": {"tip_height": chain.height, "utxo_count": len(chain.utxo)}, **extra}
        vectors.append(v)

    submit("genesis", genesis, "accept", "ConnectBlock", "ProcessBlock: ACCEPTED",
           note="the test chain's genesis; the validator takes it on its hash, as v0.1 takes hashGenesisBlock")
    fund_cb = recipes.make_coinbase(1, [(8 * spec.COIN, recipes.p2pk(key["sec"]))] * 6)
    submit("funding", recipes.assemble_block(chain.tip, [fund_cb], ntime(1), EASY_NBITS, recipes.easy_mine),
           "accept", "ConnectBlock", "ProcessBlock: ACCEPTED",
           note="six P2PK outputs to the test key; spendable once 100 blocks deep")
    funding = [{"txid": spec.txid(fund_cb), "n": i, "value": 8 * spec.COIN} for i in range(6)]
    last_cb = None
    for h in range(2, 102):
        cb = recipes.make_coinbase(h, [(50 * spec.COIN, recipes.OP_TRUE_SCRIPT)])
        submit(f"mature_{h:03d}", recipes.assemble_block(chain.tip, [cb], ntime(h), EASY_NBITS, recipes.easy_mine),
               "accept", "ConnectBlock", "ProcessBlock: ACCEPTED")
        last_cb = {"txid": spec.txid(cb), "value": 50 * spec.COIN}
    for name in recipes.BLOCK_CASE_ORDER:
        h = chain.height + 1
        ctx = {"prev": chain.tip, "height": h, "mtp": chain.median_time_past(chain.tip), "ntime": ntime(h),
               "nbits": EASY_NBITS, "pow_limit_nbits": EASY_NBITS, "subsidy": chain.subsidy(chain.height),
               "key": key, "wrong_key": wrong, "funding": funding, "last_cb": last_cb, "mine": recipes.easy_mine}
        case = recipes.build_block_case(name, ctx)
        extra = {k: case[k] for k in ("note", "inner") if k in case}
        submit(name, case["raw"], case["expect"], case["stage"], case["reason"], needs_pow=case["needs_pow"], **extra)
    return {
        "schema": SCHEMA,
        "suite": "blocks",
        "pow_limit_nbits": f"0x{EASY_NBITS:08x}",
        "genesis_hash": gh[::-1].hex(),
        "test_keys": {k["label"]: {"priv_hex": f"{k['priv']:064x}", "pub_sec_hex": k["sec"].hex()} for k in (key, wrong)},
        "rule": ("Process the vectors in order against one state. ProcessBlock (main.cpp:1236): duplicate -> "
                 "'already have'. CheckBlock (main.cpp:1154), in this order: size limits; [nTime <= now+2h, a "
                 "wall-clock rule not replayed]; vtx[0] must be coinbase (one input, null prevout = 32 zero bytes + "
                 "n 0xffffffff); no other coinbase; every tx passes CheckTransaction (vin/vout non-empty, no "
                 "negative nValue, coinbase scriptSig 2..100 bytes, non-coinbase inputs have non-null prevout); "
                 "SetCompact(nBits) <= pow limit; hash <= SetCompact(nBits); hashMerkleRoot == BuildMerkleTree. "
                 "Then: prev not in index -> ORPHAN (held, not rejected). AcceptBlock (main.cpp:1192): nTime > "
                 "median of the last 11 block times ending at prev; nBits == GetNextWorkRequired(prev) (== prev.nBits "
                 "below height 2016). The block enters the index. It becomes the best chain only if it extends the "
                 "tip; then ConnectBlock (main.cpp:934): each tx via ConnectInputs in order — every input's prevout "
                 "exists and is unspent (outputs of earlier txs in the same block count); a coinbase input is "
                 "spendable only if (height-1) - coinbase_height >= 99; VerifySignature; sum(in) >= sum(out); then "
                 "vtx[0].GetValueOut() <= (50 COIN >> ((height-1) // 210000)) + fees. A ConnectBlock failure leaves "
                 "the block in the index with zero work and the tip unchanged. The exported chain uses pow limit "
                 f"0x{EASY_NBITS:08x} so it can be mined at export time (a NEW-EXP parameter): the 2009 binary would "
                 "reject every one of these headers at 'nBits below minimum work'; replay/ rebuilds the same cases "
                 "at 0x1d00ffff on the live chain. Scripts used: OP_TRUE (0x51) and P2PK."),
        "oracle": ("verify_vectors.Chain2009, written from main.cpp; agrees with ledger/, netnode/chainstate.py and "
                   "validator-rs on the shared cases; the binary column comes from replay/"),
        "vectors": vectors,
    }


SUITES = {
    "evalscript.json": export_evalscript,
    "retarget.json": export_retarget,
    "merkle.json": export_merkle,
    "headers.json": export_headers,
    "sighash.json": export_sighash,
    "checksig.json": export_checksig,
    "blocks.json": export_blocks,
}


def render(obj) -> bytes:
    return (json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode("ascii")


def build() -> dict[str, bytes]:
    files = {name: render(fn()) for name, fn in SUITES.items()}
    lines = [f"{hashlib.sha256(files[k]).hexdigest()}  {k}" for k in sorted(files)]
    files["MANIFEST.sha256"] = ("\n".join(lines) + "\n").encode("ascii")
    return files


def main(argv: list[str]) -> int:
    files = build()
    if "--check" in argv:
        bad = [k for k, v in files.items() if not (HERE / k).exists() or (HERE / k).read_bytes() != v]
        for k in bad:
            print("DIFFERS or MISSING:", k)
        print("check:", "OK" if not bad else f"{len(bad)} file(s) differ")
        return 1 if bad else 0
    for k, v in files.items():
        (HERE / k).write_bytes(v)
        print("wrote", k, len(v), "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
