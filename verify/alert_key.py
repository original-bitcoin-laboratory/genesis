"""Check that the alert private key published on 3 July 2018 derives the public key the alert system
was introduced with in SVN r142 (`401926283`, 25 Aug 2010).

Both inputs are fetched from public sources:
  - the 2018 disclosure post in the bitcoin.org repository (mainnet public and private key);
  - the r142 commit's diff from the bitcoin/bitcoin repository (the key hard-coded in CAlert).
The published private key is an OpenSSL ECPrivateKey (DER); its 32-byte scalar d is multiplied by the
secp256k1 generator G here, in pure Python. Exit 0 iff d*G equals the r142 key and the published
public key, and the negative control (d+1)*G does not.

What this shows: the 2018 secret is the private half of the 2010 alert key. What it does not show:
who held the key at any date before publication.
"""
import json
import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

POST = ("https://raw.githubusercontent.com/bitcoin-dot-org/Bitcoin.org/master/"
        "_posts/2018-07-03-alert-key-and-vulnerabilities-disclosure.md")
COMMIT = "https://api.github.com/repos/bitcoin/bitcoin/commits/401926283a200994ecd7df8eae8ced8e0b067c46"
UA = {"User-Agent": "obl-archive/1.0 (provenance check)"}
P = 2**256 - 2**32 - 977
G = (0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
     0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)


def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read()


def add(a, b):
    if a is None:
        return b
    if b is None:
        return a
    if a[0] == b[0] and (a[1] + b[1]) % P == 0:
        return None
    if a == b:
        lam = 3 * a[0] * a[0] * pow(2 * a[1], -1, P) % P
    else:
        lam = (b[1] - a[1]) * pow(b[0] - a[0], -1, P) % P
    x = (lam * lam - a[0] - b[0]) % P
    return (x, (lam * (a[0] - x) - a[1]) % P)


def mul(k, pt):
    r = None
    while k:
        if k & 1:
            r = add(r, pt)
        pt = add(pt, pt)
        k >>= 1
    return r


def pub(d):
    q = mul(d, G)
    return "04" + format(q[0], "064x") + format(q[1], "064x")


post = get(POST).decode("utf-8")
der = bytes.fromhex(re.search(r"mainnet private key:\s+([0-9a-f]+)", post).group(1))
assert der[:7] == bytes.fromhex("30820113020101") and der[7:9] == bytes.fromhex("0420"), \
    "unexpected ECPrivateKey prefix"
d = int.from_bytes(der[9:41], "big")
published = re.search(r"mainnet public key:\s+([0-9a-f]+)", post).group(1)

c = json.loads(get(COMMIT))
patch = "".join(f.get("patch", "") for f in c["files"])
r142 = re.search(r'SetPubKey\(ParseHex\("([0-9a-f]+)"\)\)', patch).group(1)

derived = pub(d)
control = pub(d + 1)
print(f"  r142 commit            {c['sha'][:12]}  {c['commit']['author']['date']}")
print(f"  key in r142 diff       {r142[:24]}…")
print(f"  key published 2018     {published[:24]}…")
print(f"  d*G                    {derived[:24]}…   equal to both: {derived == r142 == published}")
print(f"  control (d+1)*G        differs: {control != r142}")
sys.exit(0 if derived == r142 == published and control != r142 else 1)
