"""Report a Windows release binary's architecture and which C runtime time functions it imports, to
answer one question: does its clock wrap in 2038?

    python verify/pe_time_width.py path/to/bitcoin.exe

A 32-bit `time_t` (imports `_time32`, `_localtime32`, `_gmtime32`) counts seconds in a signed 32-bit
integer and wraps at 2038-01-19 03:14:07 UTC; `_time64` and friends do not. The release `bitcoin.exe`
(sha256 c3f15fc5…, see derivatives/bitcoin/RELEASE-0.1.5.txt) imports the 32-bit set, as a 2009 MinGW
build of the same source did. The block header's own nTime field is an unsigned 32-bit value and runs
to 2106; the 2038 limit is the client's reading of the wall clock. Exit 0 always; this reports.
"""
import hashlib
import struct
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "bitcoin.exe"
b = open(path, "rb").read()
pe = struct.unpack_from("<I", b, 0x3C)[0]
machine = struct.unpack_from("<H", b, pe + 4)[0]
print(f"  file      {path}  sha256 {hashlib.sha256(b).hexdigest()}")
print(f"  machine   { {0x14C: 'i386 (32-bit)', 0x8664: 'x86-64 (64-bit)'}.get(machine, hex(machine))}")
names = [b"_time32", b"_localtime32", b"_gmtime32", b"_mktime32",
         b"_time64", b"_localtime64", b"_gmtime64", b"_mktime64"]
found = {n.decode(): b.count(n + b"\x00") for n in names}
for n, k in found.items():
    print(f"  {n:<13} {'imported' if k else '-'}")
w32 = any(found[n] for n in ("_time32", "_localtime32", "_gmtime32", "_mktime32"))
w64 = any(found[n] for n in ("_time64", "_localtime64", "_gmtime64", "_mktime64"))
verdict = ("32-bit time: the clock wraps at 2038-01-19 03:14:07 UTC" if w32 and not w64 else
           "64-bit time" if w64 and not w32 else "mixed or none found: inspect the import table")
print(f"  verdict   {verdict}")
