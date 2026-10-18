#!/usr/bin/env python3
"""In-process signature timings: one process, many operations, through OpenSSL's EVP interface.

The whole-process instrument (verify/pq_signature_cost.py) times a complete `openssl` process per
operation, so its figures include a process-spawn cost of about 12-17 ms and it cannot resolve an
operation faster than that. This instrument calls libcrypto directly through ctypes, so the spawn cost
is paid once for the run and each timing covers one EVP_PKEY_sign or EVP_PKEY_verify call.

Timed interval: only the EVP_PKEY_sign or EVP_PKEY_verify call. Context creation, the
sign/verify_message_init call, buffer allocation and the size query are outside it.

The library is the one the whole-process instrument uses where possible (the libcrypto beside the
`openssl` on PATH is tried first) and is recorded by version, path and SHA-256, with the CLI binary,
`openssl version -a` and the CPU, so that the two instruments' builds can be compared.

The timings are wall-clock (`perf_counter_ns`) and include one ctypes call. That call's cost is
measured on the same library by timing `OpenSSL_version_num`, a function that does no cryptography,
and reported beside the medians. This is not a cycle-accurate benchmark of the SUPERCOP kind.

    python bench_inprocess.py --list
    python bench_inprocess.py --n 100 --out inprocess-timings.json
"""
from __future__ import annotations

import argparse
import ctypes
import glob
import hashlib
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import time
from ctypes import POINTER, byref, c_char_p, c_int, c_size_t, c_ubyte, c_void_p

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

D, OK, W, AR = chr(0x26D4), "ok  ", chr(0x26A0), chr(0x21D2)
NL = chr(10)

# The schemes the paper reports, by the name OpenSSL knows them under.
SCHEMES = ["ML-DSA-44", "ML-DSA-65", "ML-DSA-87",
           "SLH-DSA-SHA2-128s", "SLH-DSA-SHA2-128f", "SLH-DSA-SHA2-192s"]


def find_libcrypto(explicit=None):
    """Find an OpenSSL libcrypto with the one-shot signature API. Each candidate's own version string
    decides, because the first `libcrypto` found on a machine can be another library (on the machine
    measured, LibreSSL), which lacks these algorithms."""
    cands = []
    if explicit:
        cands.append(explicit)
    exe = __import__("shutil").which("openssl")
    if exe:
        cands += sorted(glob.glob(os.path.join(os.path.dirname(exe), "libcrypto*.dll")))
    for pat in (r"C:\Program Files\Git\mingw64\bin\libcrypto*.dll",
                r"C:\msys64\mingw64\bin\libcrypto*.dll",
                "/usr/lib/x86_64-linux-gnu/libcrypto.so.3", "/usr/lib64/libcrypto.so.3",
                "/usr/local/lib/libcrypto.so.3", "/opt/homebrew/lib/libcrypto.3.dylib"):
        cands += sorted(glob.glob(pat))
    seen, out = set(), []
    for c in cands:
        if c in seen:
            continue
        seen.add(c)
        try:
            lib = ctypes.CDLL(c)
            lib.OpenSSL_version.restype = c_char_p
            ver = lib.OpenSSL_version(0).decode("utf-8", "replace")
        except Exception:                                                 # noqa: BLE001
            continue
        if "OpenSSL" not in ver:
            out.append((c, ver, "not OpenSSL"))
            continue
        if not hasattr(lib, "EVP_PKEY_sign_message_init"):
            out.append((c, ver, "no one-shot signature API (needs 3.5 or later)"))
            continue
        return lib, c, ver, out
    return None, None, None, out


def _bind(lib):
    lib.EVP_PKEY_CTX_new_from_name.restype = c_void_p
    lib.EVP_PKEY_CTX_new_from_name.argtypes = [c_void_p, c_char_p, c_char_p]
    lib.EVP_PKEY_CTX_new_from_pkey.restype = c_void_p
    lib.EVP_PKEY_CTX_new_from_pkey.argtypes = [c_void_p, c_void_p, c_char_p]
    lib.EVP_PKEY_keygen_init.argtypes = [c_void_p]
    lib.EVP_PKEY_generate.argtypes = [c_void_p, POINTER(c_void_p)]
    lib.EVP_SIGNATURE_fetch.restype = c_void_p
    lib.EVP_SIGNATURE_fetch.argtypes = [c_void_p, c_char_p, c_char_p]
    lib.EVP_PKEY_sign_message_init.argtypes = [c_void_p, c_void_p, c_void_p]
    lib.EVP_PKEY_verify_message_init.argtypes = [c_void_p, c_void_p, c_void_p]
    lib.EVP_PKEY_sign.argtypes = [c_void_p, POINTER(c_ubyte), POINTER(c_size_t),
                                  POINTER(c_ubyte), c_size_t]
    lib.EVP_PKEY_verify.argtypes = [c_void_p, POINTER(c_ubyte), c_size_t,
                                    POINTER(c_ubyte), c_size_t]
    lib.EVP_PKEY_free.argtypes = [c_void_p]
    lib.EVP_PKEY_CTX_free.argtypes = [c_void_p]
    lib.EVP_SIGNATURE_free.argtypes = [c_void_p]
    lib.ERR_get_error.restype = ctypes.c_ulong
    lib.ERR_error_string_n.argtypes = [ctypes.c_ulong, c_char_p, c_size_t]


def _err(lib):
    buf = ctypes.create_string_buffer(256)
    e = lib.ERR_get_error()
    if not e:
        return "no error on the stack"
    lib.ERR_error_string_n(e, buf, 256)
    return buf.value.decode("utf-8", "replace")


def keygen(lib, name):
    ctx = lib.EVP_PKEY_CTX_new_from_name(None, name.encode(), None)
    if not ctx:
        raise RuntimeError("no context for %s: %s" % (name, _err(lib)))
    try:
        if lib.EVP_PKEY_keygen_init(ctx) != 1:
            raise RuntimeError("keygen_init %s: %s" % (name, _err(lib)))
        pkey = c_void_p()
        if lib.EVP_PKEY_generate(ctx, byref(pkey)) != 1:
            raise RuntimeError("generate %s: %s" % (name, _err(lib)))
        return pkey
    finally:
        lib.EVP_PKEY_CTX_free(ctx)


def time_one(lib, name, pkey, msg, n):
    """Returns (sign_ns list, verify_ns list, siglen). One context per operation, as a caller has."""
    algo = lib.EVP_SIGNATURE_fetch(None, name.encode(), None)
    if not algo:
        raise RuntimeError("no signature object for %s: %s" % (name, _err(lib)))
    m = (c_ubyte * len(msg)).from_buffer_copy(msg)
    sign_ns, verify_ns = [], []
    sig_buf, siglen = None, 0
    try:
        for _ in range(n):
            sctx = lib.EVP_PKEY_CTX_new_from_pkey(None, pkey, None)
            if not sctx or lib.EVP_PKEY_sign_message_init(sctx, algo, None) != 1:
                raise RuntimeError("sign_message_init %s: %s" % (name, _err(lib)))
            need = c_size_t(0)
            if lib.EVP_PKEY_sign(sctx, None, byref(need), m, len(msg)) != 1:
                raise RuntimeError("sign size %s: %s" % (name, _err(lib)))
            buf = (c_ubyte * need.value)()
            out = c_size_t(need.value)
            t0 = time.perf_counter_ns()
            rc = lib.EVP_PKEY_sign(sctx, buf, byref(out), m, len(msg))
            t1 = time.perf_counter_ns()
            lib.EVP_PKEY_CTX_free(sctx)
            if rc != 1:
                raise RuntimeError("sign %s: %s" % (name, _err(lib)))
            sign_ns.append(t1 - t0)
            sig_buf, siglen = buf, out.value

            vctx = lib.EVP_PKEY_CTX_new_from_pkey(None, pkey, None)
            if not vctx or lib.EVP_PKEY_verify_message_init(vctx, algo, None) != 1:
                raise RuntimeError("verify_message_init %s: %s" % (name, _err(lib)))
            t0 = time.perf_counter_ns()
            rc = lib.EVP_PKEY_verify(vctx, sig_buf, siglen, m, len(msg))
            t1 = time.perf_counter_ns()
            lib.EVP_PKEY_CTX_free(vctx)
            if rc != 1:
                raise RuntimeError("verify %s returned %d: %s" % (name, rc, _err(lib)))
            verify_ns.append(t1 - t0)
    finally:
        lib.EVP_SIGNATURE_free(algo)
    return sign_ns, verify_ns, siglen


def negative_control(lib, name, pkey, msg):
    """Negative control: a signature with one flipped byte must fail to verify. Without it, a verify
    call that succeeded unconditionally would be timed as a fast verification."""
    algo = lib.EVP_SIGNATURE_fetch(None, name.encode(), None)
    m = (c_ubyte * len(msg)).from_buffer_copy(msg)
    try:
        sctx = lib.EVP_PKEY_CTX_new_from_pkey(None, pkey, None)
        lib.EVP_PKEY_sign_message_init(sctx, algo, None)
        need = c_size_t(0)
        lib.EVP_PKEY_sign(sctx, None, byref(need), m, len(msg))
        buf = (c_ubyte * need.value)()
        out = c_size_t(need.value)
        lib.EVP_PKEY_sign(sctx, buf, byref(out), m, len(msg))
        lib.EVP_PKEY_CTX_free(sctx)
        buf[0] ^= 0xFF                                   # one flipped byte in the signature
        vctx = lib.EVP_PKEY_CTX_new_from_pkey(None, pkey, None)
        lib.EVP_PKEY_verify_message_init(vctx, algo, None)
        rc = lib.EVP_PKEY_verify(vctx, buf, out.value, m, len(msg))
        lib.EVP_PKEY_CTX_free(vctx)
        lib.ERR_get_error()                              # drain the expected failure
        return rc != 1
    finally:
        lib.EVP_SIGNATURE_free(algo)


def boundary_overhead(lib, n):
    """The cost of one ctypes call into the same library when the callee does no cryptography:
    `OpenSSL_version_num` returns a constant. (Until 18 October 2026 this timed hashlib.sha256 instead,
    which is not a ctypes call into libcrypto; an internal review caught it.)"""
    lib.OpenSSL_version_num.restype = ctypes.c_ulong
    lib.OpenSSL_version_num.argtypes = []
    out = []
    for _ in range(n):
        t0 = time.perf_counter_ns()
        lib.OpenSSL_version_num()
        t1 = time.perf_counter_ns()
        out.append(t1 - t0)
    return out


def _sha256(path):
    try:
        return hashlib.sha256(open(path, "rb").read()).hexdigest()
    except OSError:
        return None


def _cpu():
    name = platform.processor()
    if platform.system() == "Windows":
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-Command",
                                "(Get-CimInstance Win32_Processor).Name"], capture_output=True, text=True)
            name = r.stdout.strip() or name
        except OSError:
            pass
    return name


def _q(v, k):
    """The k-th quartile (1, 2, 3) of v, in microseconds."""
    return round(statistics.quantiles(v, n=4)[k - 1] / 1000, 1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split(NL + NL)[0])
    ap.add_argument("--n", type=int, default=100, help="operations per scheme")
    ap.add_argument("--msglen", type=int, default=32, help="message length in bytes")
    ap.add_argument("--lib", default=None, help="path to libcrypto, if the search picks wrongly")
    ap.add_argument("--out", default=None, help="write the measurement as JSON")
    ap.add_argument("--list", action="store_true", help="report the library and the schemes only")
    a = ap.parse_args(argv)

    lib, path, ver, rejected = find_libcrypto(a.lib)
    print("=" * 78)
    print("  IN-PROCESS SIGNATURE TIMINGS -- one process, many operations")
    print("=" * 78)
    for p, v, why in rejected:
        print("  %s skipped %s (%s): %s" % (W, os.path.basename(p), v.split()[0], why))
    if lib is None:
        print("  %s no libcrypto with the one-shot signature API was found. OpenSSL 3.5 or later is"
              % D)
        print("     required for ML-DSA and SLH-DSA through EVP. Pass --lib PATH.")
        return 1
    _bind(lib)
    print("  %s %s" % (OK, ver))
    print("       %s" % path)
    print("  %s %s %s, python %s"
          % (OK, platform.system(), platform.machine(), platform.python_version()))

    msg = os.urandom(a.msglen)
    rows, missing = [], []
    for name in SCHEMES:
        n_this = a.n                                    # the same count for every scheme
        try:
            pkey = keygen(lib, name)
        except RuntimeError as e:
            missing.append((name, str(e)[:70]))
            continue
        try:
            if not negative_control(lib, name, pkey, msg):
                print("  %s %s: a FLIPPED SIGNATURE BYTE STILL VERIFIED. Every timing for this "
                      "scheme is discarded." % (D, name))
                missing.append((name, "negative control did not fail"))
                continue
            s_ns, v_ns, siglen = time_one(lib, name, pkey, msg, n_this)
        finally:
            lib.EVP_PKEY_free(pkey)
        rows.append({"scheme": name, "n": n_this, "sig_bytes": siglen,
                     "sign_us_median": round(statistics.median(s_ns) / 1000, 1),
                     "sign_us_q1": _q(s_ns, 1), "sign_us_q3": _q(s_ns, 3),
                     "verify_us_median": round(statistics.median(v_ns) / 1000, 1),
                     "verify_us_q1": _q(v_ns, 1), "verify_us_q3": _q(v_ns, 3)})
    oh = boundary_overhead(lib, 2000)
    oh_med = round(statistics.median(oh) / 1000, 3)

    print()
    print("  %-20s %5s %8s %10s %19s %10s %17s"
          % ("scheme", "n", "sig B", "sign us", "IQR", "verify us", "IQR"))
    print("  " + "-" * 94)
    for r in rows:
        print("  %-20s %5s %8s %10s %19s %10s %17s"
              % (r["scheme"], r["n"], format(r["sig_bytes"], ","), r["sign_us_median"],
                 "%s-%s" % (r["sign_us_q1"], r["sign_us_q3"]), r["verify_us_median"],
                 "%s-%s" % (r["verify_us_q1"], r["verify_us_q3"])))
    for name, why in missing:
        print("  %s %-20s not measured: %s" % (W, name, why))
    print()
    print("  ctypes call cost into the same library (OpenSSL_version_num, no cryptography): %s us median."
          % oh_med)
    print("  Every figure above includes one such call.")
    print("  %s a flipped signature byte was checked to FAIL for every scheme reported" % OK)

    if a.out:
        exe = shutil.which("openssl")
        rec = {"_readme": "In-process EVP timings: one process, many operations. Wall-clock around the "
                          "EVP_PKEY_sign / EVP_PKEY_verify call only; medians with first and third "
                          "quartiles in microseconds. The ctypes call cost is measured on the same library.",
               "library": ver, "library_path": path, "library_sha256": _sha256(path),
               "openssl_cli_path": exe, "openssl_cli_sha256": _sha256(exe) if exe else None,
               "openssl_version_a": subprocess.run(["openssl", "version", "-a"], capture_output=True,
                                                   text=True).stdout.strip() if exe else None,
               "cpu": _cpu(),
               # system and architecture only: the OS build number identifies a machine and
               # decides nothing about a timing
               "platform": platform.system() + " " + platform.machine(),
               "python": platform.python_version(),
               "n_requested": a.n, "msg_bytes": a.msglen,
               "ctypes_call_us_median": oh_med,
               "negative_control": "a flipped signature byte must fail; checked per scheme",
               "schemes": rows, "not_measured": [{"scheme": n, "why": w} for n, w in missing]}
        with open(a.out, "w", encoding="utf-8", newline="\n") as f:
            json.dump(rec, f, indent=1)
        print("  %s wrote %s" % (OK, a.out))
    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
