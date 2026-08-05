"""Extract the whitepaper from the Bitcoin block chain and hash it.

The canonical PDF was embedded in mainnet transaction
  54e48e5f5c656b26c3bca14a8c95aa583d07ebe84dde3b7dd4a78f4e4186e713
as 948 bare-multisig outputs whose "public keys" are really PDF bytes. Reassembling them gives back
the file byte for byte.

Why this matters to this lab's grading: it is the ONLY copy of any whitepaper version carrying a
CHAIN-class anchor. Proof-of-work cannot be backdated, so this fixes the canonical text to the block
that confirmed it -- 2013, not 2008. It says nothing about October 2008, and it is not offered as if
it did. It does mean the file we ship cannot have been altered since that block.

Reproducible from any node with txindex (`bitcoin-cli getrawtransaction <txid> 1`) or, as here, from
a public API so it can be checked without one.
"""
import urllib.request, json, sys, hashlib, re

sys.stdout.reconfigure(encoding="utf-8")
TXID = "54e48e5f5c656b26c3bca14a8c95aa583d07ebe84dde3b7dd4a78f4e4186e713"
UA = {"User-Agent": "obl-archive/1.0 (provenance check)"}
OUT = sys.argv[1] if len(sys.argv) > 1 else "chain-bitcoin.pdf"


def get(u, t=120):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=t).read()


tx = json.loads(get(f"https://blockstream.info/api/tx/{TXID}"))
print(f"  tx      {TXID}")
print(f"  block   {tx['status']['block_height']}   {tx['status'].get('block_hash','')[:32]}…")
import datetime
print(f"  time    {datetime.datetime.utcfromtimestamp(tx['status']['block_time'])} UTC")
print(f"  outputs {len(tx['vout'])}")

chunks = []
for o in tx["vout"]:
    asm = o.get("scriptpubkey_asm", "")
    if "OP_CHECKMULTISIG" not in asm:
        continue                      # vout[946..947] are ordinary P2PKH change, not data
    # Bare multisig: the "public keys" carry file bytes. Keep them WHOLE -- the 0x04 prefixes are
    # part of the stream, not framing; stripping them corrupts the file. 945 outputs hold three
    # 65-byte keys each; vout[945] is a 1-of-1 holding the 33-byte tail.
    chunks += re.findall(r"OP_PUSHBYTES_(?:65|33) ([0-9a-f]+)", asm)

hexdata = "".join(chunks)
# 8-byte header, then the file, then zero padding to fill the last push.
payload = hexdata[16:16 + 184292 * 2]
pdf = bytes.fromhex(payload)
print(f"  data pushes {len(chunks)}, {len(hexdata)//2:,} bytes; file = {len(pdf):,} after the header")
print(f"  starts {pdf[:8]!r}   ends {pdf[-16:]!r}")

open(OUT, "wb").write(pdf)

h = hashlib.sha256(pdf).hexdigest()
print(f"\n  sha256  {h}")
CANON = "b1674191a88ec5cdd733e4240a81803105dc412d6c6708d53ab94fc248f4f553"
print(f"  canonical b1674191…f4f553")
print(f"  MATCH: {h == CANON}")
sys.exit(0 if h == CANON else 1)
