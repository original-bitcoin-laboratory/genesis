#!/usr/bin/env python3
"""What does post-quantum signing actually cost a 2009-shaped chain? Measured, not modelled.

WHY THIS EXISTS
---------------
Every "post-quantum Bitcoin" proposal is priced in adjectives. The question that decides whether any
of them is buildable is arithmetic: a signature goes in every transaction input, so its size is
multiplied by the whole history of the chain. This script measures that instead of asserting it.

WHAT IS MEASURED VS WHAT IS COMPUTED
------------------------------------
  MEASURED   signature sizes, from real keys signing real messages, sampled (ECDSA/DER is VARIABLE)
  MEASURED   key sizes, from real generated keys
  MEASURED   sign and verify wall-clock, median of N operations
  COMPUTED   transaction and block sizes, from Bitcoin v0.1's serialization rules -- and the model
             is VALIDATED against a real v0.1 chain file before any of it is used: the bundled sample
             (verify/data/v01-relayed-spend-blk0001.dat, SHA-256 7563b699...) is the unmodified 2009
             binary's own 124-block chain from a published evidence set of that binary's runs, and it
             holds a relayed spend of a pay-to-pubkey output whose exact size the model must reproduce

The baseline is secp256k1 ECDSA because that is what v0.1 calls: `EC_KEY_new_by_curve_name
(NID_secp256k1)` and `ECDSA_sign` in key.h. The transaction model reuses v0.1's serialisation rules;
the timings measure a modern OpenSSL, not the archived client.

  python verify/pq_signature_cost.py            # full run
  python verify/pq_signature_cost.py --quick    # fewer samples, for a smoke test

NOT MONEY. This measures byte costs. It advocates nothing and predicts nothing.
"""
import json, os, statistics, struct, subprocess, sys, tempfile, time

QUICK = "--quick" in sys.argv
SAMPLES = 25 if QUICK else 200
TIMING_N = 20 if QUICK else 100

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.normpath(os.path.join(HERE, ".."))


def find_chain():
    """Locate a v0.1-format blk0001.dat to validate the serialization model against.

    The model is the only COMPUTED part of this measurement, so validating it matters. Anyone
    running a node on this chain has the file; anyone who does not can still run everything else,
    and the script says plainly which figures rest on an unvalidated parser rather than pretending
    the step happened.

        python verify/pq_signature_cost.py --chain /path/to/blk0001.dat
    """
    if "--chain" in sys.argv:
        return sys.argv[sys.argv.index("--chain") + 1]
    # Newest round first: a longer chain validates the parser against more real records.
    # Older rounds stay as fallbacks so this still works for anyone holding only those.
    for cand in (
        os.path.join(HERE, "data", "v01-relayed-spend-blk0001.dat"),
        os.path.join(HERE, "blk0001.dat"),
        os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Bitcoin", "blk0001.dat"),
        os.path.join(os.path.expanduser("~"), ".bitcoin", "blk0001.dat"),
    ):
        if os.path.exists(cand):
            return cand
    return None


CHAIN = find_chain()

# Schemes to measure. secp256k1 is v0.1's own curve; the rest are the NIST PQ standards.
SCHEMES = [
    ("secp256k1-ECDSA", "ec", "secp256k1"),
    ("ML-DSA-44",       "pq", None),
    ("ML-DSA-65",       "pq", None),
    ("ML-DSA-87",       "pq", None),
    ("SLH-DSA-SHA2-128s", "pq", None),
    ("SLH-DSA-SHA2-128f", "pq", None),
    ("SLH-DSA-SHA2-192s", "pq", None),
]


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, check=False, **kw)


def genkey(name, kind, curve, path):
    if kind == "ec":
        r = run(["openssl", "genpkey", "-algorithm", "EC",
                 "-pkeyopt", f"ec_paramgen_curve:{curve}", "-out", path])
    else:
        r = run(["openssl", "genpkey", "-algorithm", name, "-out", path])
    return r.returncode == 0, r.stderr.decode()[:120]


def raw_pubkey_len(name, kind, priv, d):
    """Bytes that would go ON CHAIN -- the RAW key, not OpenSSL's DER wrapper.

    A SubjectPublicKeyInfo is SEQUENCE { AlgorithmIdentifier, BIT STRING }. Only the BIT STRING
    payload is the key; the ASN.1 around it is a file format and would never be on a chain.
    Reporting the DER size instead adds a constant 22 B (lattice) or 18 B (hash-based) and
    OVERSTATES the post-quantum cost -- an error in the direction that flatters our own argument,
    which is the direction that most needs catching.

    For secp256k1 the on-chain form is the 65-byte uncompressed point v0.1 pushes."""
    if kind == "ec":
        return 65
    pub = os.path.join(d, "pub.der")
    r = run(["openssl", "pkey", "-in", priv, "-pubout", "-outform", "DER", "-out", pub])
    if r.returncode != 0:
        raise SystemExit("%s: could not export the public key, so its raw size is unknown; refusing to "
                         "continue" % name)
    b = open(pub, "rb").read()
    # walk to the outermost BIT STRING (tag 0x03) and return its payload minus the unused-bits byte
    i = 0
    while i < len(b):
        tag = b[i]; i += 1
        ln = b[i]; i += 1
        if ln & 0x80:                       # long form
            nb = ln & 0x7f
            ln = int.from_bytes(b[i:i+nb], "big"); i += nb
        if tag == 0x30:                     # SEQUENCE -- descend
            continue
        if tag == 0x03:                     # BIT STRING -- payload less the unused-bits octet
            return ln - 1
        i += ln                             # skip any other element
    # No BIT STRING: the key's raw size is unknown. Fail rather than return the DER size, which would
    # pass into every transaction and capacity figure as a plausible-looking key length.
    raise SystemExit("%s: no BIT STRING in the exported public key, so its raw size is unknown; "
                     "refusing to continue" % name)


def measure(name, kind, curve):
    with tempfile.TemporaryDirectory() as d:
        priv = os.path.join(d, "k.pem")
        ok, err = genkey(name, kind, curve, priv)
        if not ok:
            return {"scheme": name, "available": False, "error": err}

        msg = os.path.join(d, "m.bin")
        open(msg, "wb").write(b"post-quantum cost measurement, 2026")

        # Sample ACROSS KEYS, not just across messages. A DER length distribution is a property
        # of the (key, message) pairs; one key sampled many times understates the spread. The first
        # run of this script used a single key and reported 3 distinct lengths where there are 4.
        sizes = []
        keys = [priv]
        if kind == "ec":
            for k in range(1, 8):
                extra = os.path.join(d, f"k{k}.pem")
                if genkey(name, kind, curve, extra)[0]:
                    keys.append(extra)
        for i in range(SAMPLES):
            priv_i = keys[i % len(keys)]
            open(msg, "wb").write(b"pq cost %d" % i)
            sig = os.path.join(d, "m.sig")
            if kind == "ec":
                r = run(["openssl", "dgst", "-sha256", "-sign", priv_i, "-out", sig, msg])
            else:
                r = run(["openssl", "pkeyutl", "-sign", "-inkey", priv_i, "-rawin",
                         "-in", msg, "-out", sig])
            if r.returncode != 0:
                return {"scheme": name, "available": False, "error": r.stderr.decode()[:120]}
            sizes.append(os.path.getsize(sig))

        # timing: median of TIMING_N sign and verify operations
        open(msg, "wb").write(os.urandom(32))      # 32 bytes, as the in-process instrument signs
        sig = os.path.join(d, "t.sig")
        st = []
        for _ in range(TIMING_N):
            t0 = time.perf_counter()
            if kind == "ec":
                r = run(["openssl", "dgst", "-sha256", "-sign", priv, "-out", sig, msg])
            else:
                r = run(["openssl", "pkeyutl", "-sign", "-inkey", priv, "-rawin", "-in", msg, "-out", sig])
            st.append(time.perf_counter() - t0)
            if r.returncode != 0:                   # a failed operation is not a timing
                raise RuntimeError("timed sign failed for %s: %s" % (name, r.stderr.decode()[:120]))
        pub = os.path.join(d, "pub.pem")
        run(["openssl", "pkey", "-in", priv, "-pubout", "-out", pub])
        vt = []
        for _ in range(TIMING_N):
            t0 = time.perf_counter()
            if kind == "ec":
                r = run(["openssl", "dgst", "-sha256", "-verify", pub, "-signature", sig, msg])
            else:
                r = run(["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", pub, "-rawin",
                         "-in", msg, "-sigfile", sig])
            vt.append(time.perf_counter() - t0)
            if r.returncode != 0:
                raise RuntimeError("timed verify failed for %s: %s" % (name, r.stderr.decode()[:120]))

        return {
            "scheme": name, "available": True,
            "sig_min": min(sizes), "sig_max": max(sizes),
            "sig_median": int(statistics.median(sizes)),
            "sig_distinct": len(set(sizes)), "samples": len(sizes),
            "sk_file": os.path.getsize(priv),
            "pk_onchain": raw_pubkey_len(name, kind, priv, d),
            # subprocess overhead dominates; report it and say so rather than pretend precision
            "sign_ms": round(statistics.median(st) * 1000, 2),
            "verify_ms": round(statistics.median(vt) * 1000, 2),
        }


# ---- validate the serialization model against real chain data ---------------------------------
def varint(b, i):
    n = b[i]
    if n < 0xfd: return n, i + 1
    if n == 0xfd: return struct.unpack("<H", b[i+1:i+3])[0], i + 3
    if n == 0xfe: return struct.unpack("<I", b[i+1:i+5])[0], i + 5
    return struct.unpack("<Q", b[i+1:i+9])[0], i + 9


MAGICS = (bytes.fromhex("f9beb4d9"), bytes.fromhex("f00ba726"))   # the 2009 network's, then a lab chain's


def parse_chain(path):
    """Walk every block of a v0.1 blk0001.dat. Coinbases (each block's first transaction) and spends
    are recorded separately; for a spend, the scriptSig and output-script lengths are kept so that the
    model can be asked to reproduce its exact size. A block whose transactions do not end exactly at
    its recorded length is a parse failure and is counted as one."""
    if not path or not os.path.exists(path):
        return None
    d = open(path, "rb").read()
    i, blocks, bad, coinbases, spends = 0, 0, 0, [], []
    while i < len(d) - 8:
        if d[i:i+4] not in MAGICS:
            i += 1; continue
        sz = struct.unpack("<I", d[i+4:i+8])[0]; raw = d[i+8:i+8+sz]
        j = 80; ntx, j = varint(raw, j)
        for k in range(ntx):
            st = j; j += 4
            nin, j = varint(raw, j)
            sigs = []
            for _ in range(nin):
                j += 36; sl, j = varint(raw, j); sigs.append(raw[j:j+sl]); j += sl + 4
            nout, j = varint(raw, j)
            outs = []
            for _ in range(nout):
                j += 8; sl, j = varint(raw, j); outs.append(sl); j += sl
            j += 4
            if k == 0:
                coinbases.append(j - st)
            else:
                spends.append({"bytes": j - st, "nin": nin, "nout": nout, "out_script_bytes": outs,
                               "scriptsig_bytes": [len(s) for s in sigs],
                               "sig_bytes": [s[0] - 1 for s in sigs]})   # one push of sig||hashtype
        if j != sz:
            bad += 1
        blocks += 1; i += 8 + sz
    return {"blocks": blocks, "blocks_not_ending_exactly": bad, "coinbase_bytes": coinbases,
            "spends": spends, "txs": len(coinbases) + len(spends)}


def spawn_overhead_ms():
    """Measure what an openssl process costs to start, so the timing column can be read honestly
    instead of caveated vaguely. `openssl version` does no cryptography."""
    ts = []
    for _ in range(20):
        t0 = time.perf_counter(); run(["openssl", "version"]); ts.append(time.perf_counter() - t0)
    return round(statistics.median(ts) * 1000, 2)


COINBASE_BYTES = 134   # the 2009 binary's own coinbase in the bundled sample (123 of its 124; one is 204 B).
                       # Until 18 October 2026 this was 135, a mean from a later sample; no per-block count
                       # differs between the two. Fixed here so both scripts count the same block.


def push_len(n):
    """The bytes a push of `n` data bytes costs before the data, as v0.1's CScript::operator<< writes
    it (script.h): one opcode byte below OP_PUSHDATA1 (0x4c = 76), OP_PUSHDATA1 + 1 to 255 bytes,
    OP_PUSHDATA2 + 2 to 65,535 bytes, OP_PUSHDATA4 + 4 above. An ECDSA signature with its hash-type
    byte (70-73 B) and a 65-byte key take the one-byte form; every post-quantum signature and every
    lattice key take OP_PUSHDATA2. (Until 20 September 2026 this model charged one byte for every
    push, which left each post-quantum row two to four bytes short; the base row is unchanged.)"""
    return 1 if n < 0x4c else 2 if n <= 0xff else 3 if n <= 0xffff else 5


def varint_len(n):
    return 1 if n < 0xfd else 3 if n <= 0xffff else 5


HEADER_BYTES = 80      # the block header; v0.1's MAX_SIZE test (main.cpp:1160) and the 2010 MAX_BLOCK_SIZE
                       # test both measure the WHOLE serialised block: header, transaction count, transactions


def spends_per_block(block_bytes, tx_bytes):
    """How many spends of `tx_bytes` fit a block of `block_bytes` after the header, the transaction-count
    varint and one coinbase. Until 18 October 2026 both scripts computed (block - coinbase) // tx, which
    left the 80-byte header and the count out. Four counts fell by one (4,999 -> 4,998 at 1 MB for
    secp256k1; 16,047 -> 16,046; 5,987 -> 5,986 twice)."""
    n = (block_bytes - HEADER_BYTES - COINBASE_BYTES) // tx_bytes
    while n > 0 and HEADER_BYTES + varint_len(n + 1) + COINBASE_BYTES + n * tx_bytes > block_bytes:
        n -= 1
    return n


def model_spend(sig_len, out_script_len, n_out=1):
    """A one-input v0.1 spend of a pay-to-pubkey output (scriptSig = one push of sig||hashtype) into
    `n_out` outputs whose scripts are `out_script_len` bytes. Validated against a real spend."""
    ss = push_len(sig_len + 1) + sig_len + 1
    inp = 36 + varint_len(ss) + ss + 4
    out = 8 + varint_len(out_script_len) + out_script_len
    return 4 + 1 + inp + 1 + out * n_out + 4


def model_p2pk_spend(sig_len, pk_len, n_out=1):
    """A v0.1 pay-to-pubkey spend, 1 input, 1 output, sizes from the real serialization:
       tx      = version(4) + varint(nin) + input + varint(nout) + output + locktime(4)
       input   = prevout(36) + varint(scriptlen) + scriptSig + sequence(4)
       scriptSig for P2PK = PUSH(sig||hashtype)   -> push_len(sig_len + 1) + sig_len + 1
       output  = value(8) + varint(scriptlen) + scriptPubKey
       scriptPubKey P2PK  = PUSH(pubkey) + OP_CHECKSIG -> push_len(pk_len) + pk_len + 1
    """
    ss = push_len(sig_len + 1) + sig_len + 1
    spk = push_len(pk_len) + pk_len + 1
    inp = 36 + varint_len(ss) + ss + 4
    out = 8 + varint_len(spk) + spk
    return 4 + 1 + inp + 1 + out * n_out + 4


def main():
    print("=" * 78)
    print(" POST-QUANTUM COST ON A 2009-SHAPED CHAIN — measured")
    print("=" * 78)
    v = run(["openssl", "version"]).stdout.decode().strip()
    print(f"  {v}")
    print(f"  samples per scheme: {SAMPLES}   timing ops: {TIMING_N}\n")

    chain = parse_chain(CHAIN)
    # A file that exists but yields NO blocks has not validated anything. The first version of this
    # script picked up a 293-byte stub from the host's default Bitcoin directory, parsed zero blocks
    # out of it, and printed that under the heading "MODEL VALIDATION" -- a failed control reported
    # as a passing one. If the walker finds nothing, the validation is VOID and says so.
    if chain and chain["blocks"] == 0:
        print(f"  MODEL VALIDATION VOID - found a file but parsed NO blocks from it:")
        print(f"    {CHAIN}")
        print(f"    Wrong chain (magic mismatch) or not a v0.1 blk0001.dat. A file that yields")
        print(f"    nothing has validated nothing. Pass the right one with --chain <path>.")
        print()
        chain = None
    elif chain:
        s = chain["coinbase_bytes"]
        print(f"  MODEL VALIDATION against a real v0.1 chain file:")
        print(f"    {CHAIN}")
        print(f"    parsed {chain['blocks']} blocks, {chain['txs']} transactions; "
              f"{chain['blocks_not_ending_exactly']} block(s) not ending exactly at their recorded length")
        print(f"    coinbase sizes: min {min(s)} max {max(s)}")
        chain["spend_checks"] = []
        for sp in chain["spends"]:
            if sp["nin"] != 1:
                continue
            want = model_spend(sp["sig_bytes"][0], sp["out_script_bytes"][0], sp["nout"]) \
                if len(set(sp["out_script_bytes"])) == 1 else None
            chain["spend_checks"].append({"real": sp["bytes"], "model": want})
            print(f"    spend: {sp['bytes']} B real, {want} B by the model "
                  f"(signature {sp['sig_bytes'][0]} B, {sp['nout']} output(s) of {sp['out_script_bytes'][0]} B)")
        if chain["blocks_not_ending_exactly"] or any(c["real"] != c["model"] for c in chain["spend_checks"]):
            print("    VALIDATION FAILED: the walker or the model disagrees with the file. Nothing below")
            print("    may be read as validated.")
            return 1
        print(f"    -> the walker reads every block to its exact length and the model reproduces")
        print(f"       every spend's size, so the computed columns rest on checked framing\n")
    else:
        print("  MODEL VALIDATION SKIPPED - no v0.1 blk0001.dat found.")
        print("    The measured columns (signature sizes, key sizes, timings) are unaffected.")
        print("    The COMPUTED columns rest on an unvalidated serialization walker in this run.")
        print("    Point it at a chain file to validate:  --chain /path/to/blk0001.dat")
        print("    The bundled sample is verify/data/v01-relayed-spend-blk0001.dat.\n")

    results = [measure(n, k, c) for n, k, c in SCHEMES]

    print(f"  {'scheme':<20}{'sig B':>12}{'distinct':>9}{'pk B':>8}{'sign ms':>9}{'verify ms':>10}")
    print("  " + "-" * 70)
    base = None
    for r in results:
        if not r["available"]:
            print(f"  {r['scheme']:<20}  UNAVAILABLE — {r['error']}"); continue
        rng = f"{r['sig_min']}" if r['sig_min'] == r['sig_max'] else f"{r['sig_min']}-{r['sig_max']}"
        print(f"  {r['scheme']:<20}{rng:>12}{r['sig_distinct']:>9}{str(r['pk_onchain']):>8}"
              f"{r['sign_ms']:>9}{r['verify_ms']:>10}")
        if r["scheme"].startswith("secp256k1"):
            base = r
    ov = spawn_overhead_ms()
    print()
    print("  process-spawn floor, MEASURED: %s ms (openssl version, no cryptography at all)." % ov)
    print("  Each timing above is a whole process, floor included. A median at or below the floor")
    print("  is not a negative cryptographic cost: it is a cost this method cannot resolve. Read")
    print("  the columns as 'sign/verify is within N ms of a bare process start', not as N ms of")
    print("  cryptography; a library benchmark (no process per operation) is the sharper instrument.")
    print(f"  {'scheme':<20}{'sign - floor':>14}{'verify - floor':>16}")
    for r in results:
        if not r["available"]: continue
        s = r["sign_ms"] - ov; vv = r["verify_ms"] - ov
        fs = f"{s:.1f} ms" if s > 0 else "<= floor"
        fv = f"{vv:.1f} ms" if vv > 0 else "<= floor"
        print(f"  {r['scheme']:<20}{fs:>14}{fv:>16}")

    if not base:
        return 1
    print("\n" + "=" * 78)
    print(" WHAT IT COSTS A CHAIN — a v0.1 P2PK spend, 1 input, 1 and 2 outputs")
    print("=" * 78)
    BLOCK = 1_000_000            # the 2010 rule (MAX_BLOCK_SIZE)
    BLOCK_V01 = 0x02000000       # the January 2009 ceiling (MAX_SIZE, 32 MiB), the rule v0.1 itself enforces
    b_tx = model_p2pk_spend(base["sig_median"], base["pk_onchain"])
    b_per = spends_per_block(BLOCK, b_tx)
    print(f"  {'scheme':<20}{'1-in':>8}{'1-in':>8}{'x base':>8}{'tx/1MB':>10}{'tx/32MiB':>10}{'blk MB for':>12}{'chain GB/yr':>13}")
    print(f"  {'':<20}{'1-out':>8}{'2-out':>8}{'':>8}{'block':>10}{'block':>10}{'same rate':>12}{'same rate':>13}")
    print("  " + "-" * 90)
    for r in results:
        if not r["available"]: continue
        tx = model_p2pk_spend(r["sig_median"], r["pk_onchain"])
        per = spends_per_block(BLOCK, tx)               # header, count, one coinbase, then spends
        per_v01 = spends_per_block(BLOCK_V01, tx)
        # The honest comparison holds THROUGHPUT constant, not block size. Holding block size
        # constant makes chain growth identical for every scheme by construction -- it measures
        # the block limit, not the signature. Ask instead: to carry the SAME transactions per
        # block, how large must a block be, and how fast does the chain then grow?
        need_mb = b_per * tx / 1e6
        gb_yr = b_per * tx * 52560 / 1e9      # 2009 pacing: 6 blocks/h, 52,560 blocks/year
        tx2 = model_p2pk_spend(r["sig_median"], r["pk_onchain"], n_out=2)
        print(f"  {r['scheme']:<20}{tx:>8}{tx2:>8}{tx/b_tx:>7.1f}x{per:>10,}{per_v01:>10,}{need_mb:>12.1f}{gb_yr:>13.1f}")
    print(f"\n  baseline: secp256k1 tx = {b_tx} B, {b_per:,} per 1 MB block after the header and a {COINBASE_BYTES} B coinbase, "
          f"{b_per*b_tx*52560/1e9:.1f} GB/yr")
    print("  'chain GB/yr' counts the spends only; coinbases and headers add the same amount to every row.")
    print("  'same rate' = the block size and annual growth needed to carry the SAME number of")
    print("  transactions per block as secp256k1 at 1 MB. Holding BLOCK SIZE fixed instead would make")
    print("  growth identical for every scheme, which measures the block cap and not the signature.")
    print("  'tx/32MiB' is the same count under the January 2009 ceiling, the rule v0.1 enforces.")

    out = os.path.join(HERE, "pq-cost-measurement.json")
    import hashlib, platform, shutil
    exe = shutil.which("openssl")
    env = {"openssl_cli_path": exe,
           "openssl_cli_sha256": hashlib.sha256(open(exe, "rb").read()).hexdigest() if exe else None,
           "openssl_version_a": run(["openssl", "version", "-a"]).stdout.decode().strip(),
           "cpu": platform.processor(), "system": platform.system() + " " + platform.machine(),
           "python": platform.python_version()}
    json.dump({"openssl": v, "environment": env, "samples": SAMPLES, "timing_n": TIMING_N,
               "timing_message_bytes": 32,
               "chain_validation": ({"file": os.path.basename(CHAIN),
                                     "sha256": hashlib.sha256(open(CHAIN, "rb").read()).hexdigest(),
                                     "blocks": chain["blocks"], "txs": chain["txs"],
                                     "blocks_not_ending_exactly": chain["blocks_not_ending_exactly"],
                                     "coinbase_bytes_min": min(chain["coinbase_bytes"]),
                                     "coinbase_bytes_max": max(chain["coinbase_bytes"]),
                                     "spend_checks": chain.get("spend_checks", [])} if chain else None),
               "schemes": results,
               "tx_bytes": {r["scheme"]: model_p2pk_spend(r["sig_median"], r["pk_onchain"])
                            for r in results if r["available"]}},
              open(out, "w"), indent=2)
    print(f"\n  wrote {os.path.basename(out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
