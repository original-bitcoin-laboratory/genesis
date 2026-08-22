#!/usr/bin/env python3
"""Verify a mining-round capture from BITCOIN-NODE-1, from the raw bytes only.

    python3 verify_capture.py <capture-dir> [--prev <previous blk0001.dat>]

WHY THIS EXISTS AS A SCRIPT
---------------------------
Every round so far has been verified by hand and reported the same way. Doing it by hand is how a
number gets read out of `debug.log` by accident -- and the log is a narrative, cumulative across
sessions, counting blocks RECEIVED as well as blocks mined. `ProcessBlock: ACCEPTED` has already
been mistaken for a round's block count once. **The chain is the record; the log is a story about
it.** So everything below is derived from `blk0001.dat` and from file digests, and the log is
parsed only for things that are genuinely log-shaped: exceptions, reorganisations, error lines.

WHAT IT CHECKS
--------------
  1. every block parses under THIS chain's magic f0 0b a7 26, and nothing else appears
  2. the blocks link into one chain from the fixed genesis, with no breaks
  3. proof-of-work: every header hash is below its own nBits target
  4. every merkle root recomputes from that block's transactions
  5. the previous capture's blk0001.dat is a byte-exact PREFIX of this one (append-only)
  6. coinbase payees, and whether the agent's genesis key was paid
  7. the executed-binary bindings agree pre and post, and the on-disk exe re-hashes to them
  8. the log's own claims are reported as log claims, never promoted to evidence

Exit 0 only if every structural check passes.
"""
import argparse
import hashlib
import io
import json
import pathlib
import re
import struct
import sys
import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

MAGIC = bytes([0xF0, 0x0B, 0xA7, 0x26])          # this chain, and only this chain
GENESIS = "00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a"
AGENT_KEY_PREFIX = "04c0414cfdcc0098"


def dsha(b):
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


def rh(b):
    return b[::-1].hex()


def varint(buf, i):
    n = buf[i]
    if n < 0xFD:
        return n, i + 1
    if n == 0xFD:
        return struct.unpack_from("<H", buf, i + 1)[0], i + 3
    if n == 0xFE:
        return struct.unpack_from("<I", buf, i + 1)[0], i + 5
    return struct.unpack_from("<Q", buf, i + 1)[0], i + 9


def parse_tx(buf, i):
    start = i
    i += 4                                            # version
    nin, i = varint(buf, i)
    ins = []
    for _ in range(nin):
        prev = buf[i:i + 36]; i += 36
        sl, i = varint(buf, i)
        script = buf[i:i + sl]; i += sl
        i += 4                                        # sequence
        ins.append((prev, script))
    nout, i = varint(buf, i)
    outs = []
    for _ in range(nout):
        val = struct.unpack_from("<q", buf, i)[0]; i += 8
        sl, i = varint(buf, i)
        spk = buf[i:i + sl]; i += sl
        outs.append((val, spk))
    i += 4                                            # locktime
    return {"ins": ins, "outs": outs, "raw": buf[start:i]}, i


def parse_file(p):
    """Return the list of blocks in FILE ORDER, each with its header fields and txs."""
    buf = p.read_bytes()
    i, blocks, stray = 0, [], 0
    while i + 8 <= len(buf):
        if buf[i:i + 4] != MAGIC:
            stray += 1
            i += 1
            continue
        size = struct.unpack_from("<I", buf, i + 4)[0]
        body = buf[i + 8:i + 8 + size]
        if len(body) < 80:
            break
        hdr = body[:80]
        ver, prev, root, t, bits, nonce = struct.unpack("<I32s32sIII", hdr)
        j = 80
        ntx, j = varint(body, j)
        txs = []
        for _ in range(ntx):
            tx, j = parse_tx(body, j)
            txs.append(tx)
        blocks.append({
            "hash": rh(dsha(hdr)), "prev": rh(prev), "root": rh(root),
            "time": t, "bits": bits, "nonce": nonce, "txs": txs,
            "offset": i, "size": size,
        })
        i += 8 + size
    return blocks, stray, len(buf)


def merkle(txs):
    lvl = [dsha(t["raw"]) for t in txs]
    if not lvl:
        return None
    while len(lvl) > 1:
        if len(lvl) % 2:
            lvl.append(lvl[-1])
        lvl = [dsha(lvl[k] + lvl[k + 1]) for k in range(0, len(lvl), 2)]
    return rh(lvl[0])


def target_from_bits(bits):
    exp = bits >> 24
    mant = bits & 0xFFFFFF
    return mant * (1 << (8 * (exp - 3)))


def utc(ts):
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("capture")
    ap.add_argument("--prev", default=None, help="previous round's blk0001.dat, for the prefix proof")
    a = ap.parse_args()
    root = pathlib.Path(a.capture)
    ok, bad = [], []

    def chk(label, cond, got=""):
        (ok if cond else bad).append(("  ok   " if cond else "  FAIL ") + label +
                                     (("  -> " + str(got)) if (got and not cond) else ""))

    # ── locate the chain file ───────────────────────────────────────────────────────────────────
    cands = sorted(root.rglob("blk0001.dat"))
    if not cands:
        print("  ** no blk0001.dat under", root)
        return 2
    blk = [c for c in cands if c.parent.name == "datadir"] or cands
    blk = blk[0]
    print("\n  chain file:", blk.relative_to(root).as_posix())

    blocks, stray, nbytes = parse_file(blk)
    print("  parsed    : %d blocks, %d bytes, %d stray byte(s) outside a framed block\n"
          % (len(blocks), nbytes, stray))
    chk("no stray bytes outside framed blocks", stray == 0, stray)
    chk("every block carries this chain's magic f00ba726", len(blocks) > 0)

    # ── 1. link them into one chain from the fixed genesis ──────────────────────────────────────
    by_prev = {}
    for b in blocks:
        by_prev.setdefault(b["prev"], []).append(b)
    known = {b["hash"]: b for b in blocks}
    gen = [b for b in blocks if b["hash"] == GENESIS]
    chk("the fixed genesis is present and is this chain's", len(gen) == 1,
        "found %d" % len(gen))
    chain, cur = [], GENESIS
    if gen:
        chain = [known[GENESIS]]
        while True:
            nxt = by_prev.get(cur, [])
            if not nxt:
                break
            # the active chain is the longest; at a fork take the branch that goes furthest
            if len(nxt) > 1:
                def depth(h, seen=0):
                    d, c = 0, h["hash"]
                    while by_prev.get(c):
                        c = by_prev[c][0]["hash"]; d += 1
                    return d
                nxt = sorted(nxt, key=depth, reverse=True)
            chain.append(nxt[0])
            cur = nxt[0]["hash"]
    heights = len(chain) - 1
    orphans = len(blocks) - len(chain)
    print("  ACTIVE CHAIN")
    print("    blocks on the active chain %d   heights 0-%d" % (len(chain), heights))
    print("    blocks in file not on it   %d   (forks/orphans retained by the client)" % orphans)
    if chain:
        print("    height 0   %s" % chain[0]["hash"])
        print("    tip        %s" % chain[-1]["hash"])
        print("    tip time   %d = %s" % (chain[-1]["time"], utc(chain[-1]["time"])))
    chk("linkage from genesis to tip is unbroken", len(chain) > 1)

    # ── 2. proof of work and merkle roots, every block ──────────────────────────────────────────
    pow_bad = [b["hash"] for b in blocks if int(b["hash"], 16) > target_from_bits(b["bits"])]
    chk("every block's hash is below its own nBits target", not pow_bad,
        "%d failed" % len(pow_bad))
    mr_bad = [b["hash"] for b in blocks if merkle(b["txs"]) != b["root"]]
    chk("every merkle root recomputes from that block's transactions", not mr_bad,
        "%d failed" % len(mr_bad))
    bits = {hex(b["bits"]) for b in blocks}
    print("    nBits seen %s" % ", ".join(sorted(bits)))
    chk("difficulty is unchanged across the capture", len(bits) == 1, sorted(bits))
    nonmono = sum(1 for k in range(1, len(chain)) if chain[k]["time"] < chain[k - 1]["time"])
    print("    non-monotonic timestamps on the active chain: %d" % nonmono)

    # ── 2b. cadence, a property of the VM and NOT a protocol measurement ────────────────────────
    if len(chain) > 2:
        span = chain[-1]["time"] - chain[0]["time"]
        print("    cadence overall  %d blocks over %.1f h = %.1f min/block"
              % (len(chain) - 1, span / 3600.0, span / 60.0 / (len(chain) - 1)))

    # ── 3. the append-only proof ────────────────────────────────────────────────────────────────
    if a.prev:
        pp = pathlib.Path(a.prev)
        if pp.exists():
            prev = pp.read_bytes()
            cur_b = blk.read_bytes()
            pref = hashlib.sha256(cur_b[:len(prev)]).hexdigest()
            whole = hashlib.sha256(prev).hexdigest()
            print("\n  APPEND-ONLY PROOF")
            print("    previous capture  %10d B  sha256 %s" % (len(prev), whole))
            print("    this capture      %10d B" % len(cur_b))
            print("    appended          %10d B" % (len(cur_b) - len(prev)))
            print("    sha256(this[:%d]) %s" % (len(prev), pref))
            chk("the previous capture is a byte-exact PREFIX of this one", pref == whole)
        else:
            bad.append("  FAIL --prev given but not found: %s" % pp)

    # ── 4. coinbase payees ──────────────────────────────────────────────────────────────────────
    payees, agent_heights = [], []
    for h, b in enumerate(chain):
        cb = b["txs"][0]
        for val, spk in cb["outs"]:
            if len(spk) >= 66 and spk[0] == 65 and spk[1] == 4:
                k = spk[1:66].hex()
                payees.append(k)
                if k.startswith(AGENT_KEY_PREFIX):
                    agent_heights.append(h)
    from collections import Counter
    c = Counter(payees)
    print("\n  COINBASE PAYEES")
    print("    coinbase outputs with a 65-byte key   %d" % len(payees))
    print("    distinct payees                       %d" % len(c))
    print("    payees appearing more than once       %d" % sum(1 for v in c.values() if v > 1))
    print("    heights paying the AGENT genesis key  %s" % (agent_heights or "none"))

    # ── 4b. which blocks are NOT on the active chain, and who mined what ────────────────────────
    on = {b["hash"] for b in chain}
    off = [b for b in blocks if b["hash"] not in on]
    if off:
        h_of = {b["hash"]: i for i, b in enumerate(chain)}
        print("\nBLOCKS OFF THE ACTIVE CHAIN")
        for b in off:
            parent_h = h_of.get(b["prev"])
            print("    %s" % b["hash"])
            print("      parent %s%s" % (b["prev"],
                  ("  = height %d" % parent_h) if parent_h is not None else "  (unknown)"))
            print("      would have been height %s, time %s"
                  % (parent_h + 1 if parent_h is not None else "?", utc(b["time"])))
        print("    ⇒ retained by the client; they are not the chain. A losing branch is evidence")
        print("      that the rule chose, not evidence of a defect.")

    # coinbase scriptSig carries whatever the miner put there -- a way to tell the miners apart
    print("\nCOINBASE scriptSig MARKERS (who mined what)")
    marks = Counter()
    ext_heights = []
    for h, b in enumerate(chain):
        sig = b["txs"][0]["ins"][0][1]
        printable = bytes(c for c in sig if 32 <= c < 127)
        tag = printable.decode("ascii", "ignore")
        if len(tag) >= 4:
            marks[tag[:28]] += 1
            ext_heights.append((h, tag[:28]))
    for k, v in marks.most_common(8):
        print("    %4d  %r" % (v, k))
    if ext_heights:
        hs = [h for h, _ in ext_heights]
        print("    heights carrying a text marker: %s" % (hs if len(hs) <= 24 else
              "%d blocks, %d..%d" % (len(hs), min(hs), max(hs))))

    # ── 5. the executed-binary bindings ─────────────────────────────────────────────────────────
    print("\n  EXECUTED BINARY BINDING")
    js = sorted(root.rglob("EXECUTED_BINARY_BINDING_*.json"))
    recs = {}
    for j in js:
        try:
            # ⛔ utf-8-SIG. capture_binding.ps1 is PowerShell and writes a UTF-8 BOM, so a plain
            #    utf-8 read raises and the binding reads as ABSENT. The first run of this script
            #    reported "both bindings present: FAIL" on a capture whose bindings were perfect.
            #    A tool that cannot open a file has said nothing about the file.
            recs[j.name] = json.loads(j.read_text(encoding="utf-8-sig", errors="ignore"))
        except Exception as e:
            bad.append("  FAIL unreadable binding %s: %s" % (j.name, e))
    pre = next((v for k, v in recs.items() if "_pre" in k), None)
    post = next((v for k, v in recs.items() if "_post" in k), None)
    chk("both pre- and post-run bindings are present", bool(pre and post))
    if pre and post:
        def g(d, *names):
            for n in names:
                if n in d:
                    return d[n]
            for v in d.values():
                if isinstance(v, dict):
                    r = g(v, *names)
                    if r is not None:
                        return r
            return None
        pid_a, pid_b = g(pre, "pid", "ProcessId"), g(post, "pid", "ProcessId")
        # the binding records sha256 as a MAP of filename -> digest, not a single string. Comparing
        # the map to the on-disk digest failed a capture whose bitcoin.exe matched perfectly.
        def exe_sha(d):
            v = g(d, "sha256", "Sha256")
            if isinstance(v, dict):
                return v.get("bitcoin.exe")
            return v
        sha_a, sha_b = exe_sha(pre), exe_sha(post)
        print("    pid   pre=%s  post=%s" % (pid_a, pid_b))
        print("    bitcoin.exe sha256 pre =%s" % sha_a)
        print("    bitcoin.exe sha256 post=%s" % sha_b)
        chk("the SAME running process is bound at both ends", pid_a is not None and pid_a == pid_b,
            "%s vs %s" % (pid_a, pid_b))
        chk("the bound binary digest is identical pre and post",
            sha_a is not None and sha_a == sha_b)
        exes = sorted(root.rglob("bitcoin.exe"))
        if exes and sha_a:
            d = hashlib.sha256(exes[0].read_bytes()).hexdigest()
            print("    on-disk bitcoin.exe sha256 %s" % d)
            chk("the on-disk bitcoin.exe re-hashes to the bound digest",
                d.lower() == str(sha_a).lower(), d)
        diff = sorted(k for k in set(pre) | set(post)
                      if json.dumps(pre.get(k), sort_keys=True) != json.dumps(post.get(k), sort_keys=True))
        print("    fields differing pre->post: %s" % (", ".join(diff) or "none"))

    # ── 6. the log, reported AS A LOG ───────────────────────────────────────────────────────────
    print("\n  DEBUG LOG (claims of the log, not evidence about the chain)")
    logs = sorted(root.rglob("debug.log"))
    if logs:
        txt = logs[0].read_text(encoding="utf-8", errors="ignore")
        lines = txt.splitlines()
        acc = sum(1 for l in lines if "ProcessBlock: ACCEPTED" in l)
        exc = sum(1 for l in lines if "EXCEPTION" in l or "Exception" in l)
        reo = sum(1 for l in lines if "REORGANIZE" in l)
        inv = sum(1 for l in lines if "InvalidChainFound" in l)
        errs = [l for l in lines if "ERROR" in l or "error" in l]
        print("    lines                      %d" % len(lines))
        print("    ProcessBlock: ACCEPTED     %d   <- CUMULATIVE, and counts blocks RECEIVED too" % acc)
        print("    exceptions                 %d" % exc)
        print("    REORGANIZE                 %d" % reo)
        print("    InvalidChainFound          %d" % inv)
        print("    error lines                %d" % len(errs))
        kinds = Counter()
        for l in errs:
            if "send error" in l:
                kinds["send error (peer dropped socket)"] += 1
            elif "GetMyExternalIP" in l:
                kinds["GetMyExternalIP (dead 2009 host)"] += 1
            elif "irc" in l.lower() or "freenode" in l.lower():
                kinds["IRC bootstrap (dead 2009 host)"] += 1
            else:
                kinds[re.sub(r"^\S+ \S+ ", "", l).strip()[:58]] += 1
        for k, v in kinds.most_common(10):
            print("      %4d  %s" % (v, k))
        chk("no exceptions in the log", exc == 0, exc)
        chk("no InvalidChainFound in the log", inv == 0, inv)
    else:
        bad.append("  FAIL no debug.log in the capture")

    # ── 7. inventory ────────────────────────────────────────────────────────────────────────────
    files = [p for p in root.rglob("*") if p.is_file()]
    shots = [p for p in files if p.suffix.lower() == ".png"]
    print("\n  INVENTORY")
    print("    files %d   bytes %s   screenshots %d"
          % (len(files), format(sum(p.stat().st_size for p in files), ","), len(shots)))
    if shots:
        ns = sorted(re.sub(r"[^0-9]", "", p.stem)[:12] for p in shots)
        print("    screenshots span %s -> %s" % (ns[0], ns[-1]))

    print("\n" + "\n".join(ok + bad))
    print("\n  %d checks passed, %d FAILED\n" % (len(ok), len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
