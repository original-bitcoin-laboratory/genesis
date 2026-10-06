"""Extract the 2026 on-chain copy of the whitepaper, hash it, and show it is the canonical file plus
one inserted line.

Mainnet transaction
  00000000000ad99639585eb5fb0dc0bb093575719ecd78cfede972637b65de07   (block 949973, 18 May 2026)
carries the PDF as a single OP_RETURN push (vout 1, OP_PUSHDATA4, 184,303 bytes). The file is the
canonical whitepaper with ONE PDF comment line inserted before %%EOF. PDF readers ignore comment
lines, so it renders as the canonical paper; the line works as a nonce that gives the file's own
SHA-256 twelve leading zero hex digits. Removing it gives back the canonical file byte for byte.

What this adds to the lab's grading: a second, independent chain anchor of the canonical text --
later than block 230009 (2013), so it adds nothing to dating; it does show the same bytes,
independently re-anchored. The transaction does not say who made it.

Reproducible from any node with txindex (`bitcoin-cli getrawtransaction <txid> 1`) or, as here,
from a public API so it can be checked without one.
"""
import datetime
import hashlib
import json
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
TXID = "00000000000ad99639585eb5fb0dc0bb093575719ecd78cfede972637b65de07"
CANONICAL = "b1674191a88ec5cdd733e4240a81803105dc412d6c6708d53ab94fc248f4f553"
GENESIS_P2PK = ("4104678afdb0fe5548271967f1a67130b7105cd6a828e03909a67962e0ea1f61deb649f6bc3f4cef38c4f35"
                "504e51ec112de5c384df7ba0b8d578a4c702b6bf11d5fac")
UA = {"User-Agent": "obl-archive/1.0 (provenance check)"}
OUT = sys.argv[1] if len(sys.argv) > 1 else "chain-bitcoin-2026.pdf"


def get(u, t=120):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=t).read()


tx = json.loads(get(f"https://blockstream.info/api/tx/{TXID}"))
print(f"  tx      {TXID}")
print(f"  block   {tx['status']['block_height']}   "
      f"{datetime.datetime.fromtimestamp(tx['status']['block_time'], datetime.timezone.utc):%Y-%m-%d %H:%M:%S} UTC")
note = bytes.fromhex(tx["vout"][0]["scriptpubkey"])
print(f"  vout 0  OP_RETURN note: {note[2:].decode('utf-8', 'replace')!r}")

s = bytes.fromhex(tx["vout"][1]["scriptpubkey"])
assert s[0] == 0x6A and s[1] == 0x4E, "vout 1 is not OP_RETURN OP_PUSHDATA4"
n = int.from_bytes(s[2:6], "little")
pdf = s[6:6 + n]
assert len(pdf) == n and len(s) == 6 + n, "push length does not match the script"
open(OUT, "wb").write(pdf)
h = hashlib.sha256(pdf).hexdigest()
print(f"  carved  {len(pdf):,} bytes -> {OUT}")
print(f"  sha256  {h}")

eof = pdf.rfind(b"\n%%EOF")
line_start = pdf.rfind(b"\n", 0, eof) + 1
inserted = pdf[line_start:eof + 1]
print(f"  inserted line before %%EOF: {inserted!r} ({len(inserted)} bytes, a PDF comment: "
      f"{inserted.startswith(b'%')})")
restored = pdf[:line_start] + pdf[eof + 1:]
r = hashlib.sha256(restored).hexdigest()
print(f"  without that line: {len(restored):,} bytes, sha256 {r}")
print(f"  == canonical whitepaper (b1674191...):  {r == CANONICAL}")
print(f"  vout 2 pays the genesis block's public key (P2PK): "
      f"{tx['vout'][2]['scriptpubkey'] == GENESIS_P2PK}")
sys.exit(0 if r == CANONICAL else 1)
