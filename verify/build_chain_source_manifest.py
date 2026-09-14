"""Build a deterministic manifest of the SOURCE THAT PRODUCED THIS CHAIN'S GENESIS BLOCK.

WHY THIS EXISTS
---------------
The laboratory measures whether four identities are cryptographically bound -- the whitepaper
author line (W), the source copyright line (L), the chain keys (K) and the OpenPGP key (P). For
Satoshi's 2008-09 record every pair is unbound: zero of six.

Run on ourselves, five of six were bound as of 12 August 2026. The exception was L <-> K, which
sat at "by construction": the source carrying the copyright line is the source that mined our
genesis, but nobody had SIGNED anything to that effect -- exactly the status Satoshi's L <-> K has,
and exactly the kind of administrative-not-cryptographic link this laboratory refuses to count
when somebody else offers it.

This manifest is the object that closes it. The genesis key signs the manifest's SHA-256, so the
key that mined block 0 has signed the source that built block 0.

SCHEMA 2 (14 September 2026) -- WHAT CHANGED, AND WHY
-----------------------------------------------------
Schema 1 pinned 45 files by their bytes: the 43-file client tree, the substitution patch, and
PROVENANCE.txt. On 12 September a language pass corrected PROVENANCE.txt -- prose only, no
constant moved -- and the signed manifest stopped matching the tree. The signature was still valid
over the manifest; the manifest no longer described the source.

Two things were wrong with the scope, in opposite directions:

  * PROVENANCE.txt is a note that describes the chain to a reader. The compiler does not read it.
    Pinning its bytes meant a chain-key signature broke whenever the prose improved -- the trap
    docs/PRESERVATION.md already names for the DNS record: "a binding that breaks whenever the thing
    it binds is improved is the wrong binding." Worse, a mismatch became AMBIGUOUS: a verifier could
    not tell a consensus byte from a typo.
  * net.py -- which holds the chain's magic, port, coinbase headline, genesis hash, time, nonce,
    bits, public key and the genesis block itself -- was pinned by nothing.

Schema 2 pins by TWO different rules, chosen by what a change would MEAN:

  PINNED BY BYTES    src/**                 the composed client tree that was compiled into the
                                            binary that mined block 0. A byte change here is a
                                            different program.
                     bitcoin-v0.1.0.patch   the nine substitutions that separate this chain from
                                            Satoshi's. make_chain.py produces this file; pinning
                                            the patch pins the composer's effect.

  PINNED BY VALUE    chain_identity         the identity constants, READ OUT OF net.py and emitted
                                            as values. A verifier re-reads net.py AND the patch and
                                            requires all three to agree. A prose edit to net.py
                                            does not break the signature; a changed constant does.
                                            (This is the "gate the claim, not the shape" rule this
                                            workshop keeps paying to relearn.)

  EXCLUDED, BY CLASS *.md, *.txt at the root  prose for a reader; the build never reads it
                     make_chain.py          the composer; its effect is the patch, which is pinned
                     make_release.sh, deploy/, dist/   packaging, downstream of the source
                     build*/, obj/, __pycache__/       outputs, not reproducible across toolchains
                     .gitignore             repository tooling

  FAIL CLOSED        any root-level entry that matches none of those classes ABORTS the build.
                     A list of names measures a subset and reports on the whole (this workshop's
                     _sync_backup.py made that mistake and says so in its header); a rule with a
                     refusal does not.

Schema 1 remains buildable with --schema 1 so the superseded manifest can be regenerated and its
signed hash reproduced. Nothing is withdrawn: the schema-1 manifest, its signature and its
OpenTimestamps proofs stay in manifests/ under a SUPERSEDED- prefix.

DETERMINISM
-----------
Files are sorted by path, hashed as raw bytes, and emitted with sorted JSON keys and a fixed
separator. Running this twice on an unchanged tree produces byte-identical output, so the signature
over it remains valid until the source -- or an identity constant -- actually changes.

    python build_chain_source_manifest.py                      # schema 2 -> manifests/CHAIN_SOURCE_MANIFEST.v2-UNSIGNED.json
    python build_chain_source_manifest.py --out PATH           # schema 2 -> PATH
    python build_chain_source_manifest.py --schema 1 --out PATH
    python build_chain_source_manifest.py --check              # build in memory, print the hash, write nothing
"""
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.dirname(HERE)
ROOT = os.path.normpath(os.path.join(GEN, "derivatives", "bitcoin"))
MANIFESTS = os.path.join(GEN, "manifests")
DEFAULT_OUT = os.path.join(MANIFESTS, "CHAIN_SOURCE_MANIFEST.v2-UNSIGNED.json")

GENESIS = "00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a"
AGENT_PUB = ("04c0414cfdcc009830708543b06e43a03570dc1ffa45ddf98657045e594a815eba7"
             "94ca0602e8527d7ba3197e53c0c2f226892212aa99b827e8e2fd95fcea2f834")
COPYRIGHT = b"Copyright (c) 2009 Satoshi Nakamoto"

# The schema-1 manifest this supersedes. Its hash is the one the chain key signed on 12 Aug 2026;
# it is recorded INSIDE the schema-2 document so the succession is part of what gets signed.
SUPERSEDED_V1_SHA256 = "62ba1cee54f26cf5a17070be6a7389818e75e2069d043a4f4828724606855beb"

# ---- the rule, as data ---------------------------------------------------------------------
# Root-level entries are classified by these tables. Anything that matches none is an ERROR.
PIN_DIRS = {"src": "the composed client tree, compiled into the binary that mined block 0"}
PIN_FILES = {"bitcoin-v0.1.0.patch": "the nine substitutions; make_chain.py produces this file"}
VALUE_FILES = {"net.py": "chain identity is READ from here and pinned as values, not bytes"}
EXCLUDE_FILES = {
    "make_chain.py": "the composer; its effect is the patch, which is pinned",
    "make_release.sh": "release packaging, downstream of the source",
    ".gitignore": "repository tooling",
}
EXCLUDE_FILE_EXT = {".md": "prose for a reader", ".txt": "prose for a reader"}
EXCLUDE_DIRS = {"dist": "packaging output", "deploy": "deployment packaging",
                "obj": "build output", "__pycache__": "python bytecode"}
EXCLUDE_DIR_PREFIX = {"build": "build output tree, not reproducible across toolchains"}


class RuleError(Exception):
    pass


def classify_root():
    """Every root entry -> (class, reason). Unclassified -> RuleError. This is the projection."""
    out = {}
    for name in sorted(os.listdir(ROOT)):
        p = os.path.join(ROOT, name)
        if os.path.isdir(p):
            if name in PIN_DIRS:
                out[name] = ("pin-bytes", PIN_DIRS[name])
            elif name in EXCLUDE_DIRS:
                out[name] = ("excluded", EXCLUDE_DIRS[name])
            elif any(name.startswith(pre) for pre in EXCLUDE_DIR_PREFIX):
                out[name] = ("excluded", next(v for k, v in EXCLUDE_DIR_PREFIX.items() if name.startswith(k)))
            else:
                raise RuleError(f"unclassified directory at root: {name}/")
        else:
            ext = os.path.splitext(name)[1]
            if name in PIN_FILES:
                out[name] = ("pin-bytes", PIN_FILES[name])
            elif name in VALUE_FILES:
                out[name] = ("pin-value", VALUE_FILES[name])
            elif name in EXCLUDE_FILES:
                out[name] = ("excluded", EXCLUDE_FILES[name])
            elif ext in EXCLUDE_FILE_EXT:
                out[name] = ("excluded", EXCLUDE_FILE_EXT[ext])
            else:
                raise RuleError(f"unclassified file at root: {name}")
    return out


def _walk(sub):
    src = os.path.join(ROOT, sub)
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames[:] = sorted(d for d in dirnames if d not in ("obj", "__pycache__"))
        for fn in sorted(filenames):
            yield os.path.relpath(os.path.join(dirpath, fn), ROOT).replace(os.sep, "/")


def collect(schema=2):
    """Relative paths pinned BY BYTES for the given schema."""
    if schema == 1:
        entries = list(_walk("src"))
        for extra in ("PROVENANCE.txt", "bitcoin-v0.1.0.patch"):
            if os.path.exists(os.path.join(ROOT, extra)):
                entries.append(extra)
        return sorted(set(entries))
    classes = classify_root()                                  # raises on anything unclassified
    entries = []
    for name, (cls, _why) in classes.items():
        if cls != "pin-bytes":
            continue
        if os.path.isdir(os.path.join(ROOT, name)):
            entries.extend(_walk(name))
        else:
            entries.append(name)
    return sorted(set(entries))


# ---- chain identity, read as VALUES ---------------------------------------------------------
def _strip_comments(s):
    return re.sub(r"#[^\n]*", "", s)


def identity_from_net():
    """Read the identity constants out of net.py. Comments are stripped FIRST -- an earlier
    one-off extractor stopped at a ')' inside a comment and reported a false mismatch."""
    s = open(os.path.join(ROOT, "net.py"), encoding="utf-8").read()
    def one(pat, flags=0):
        m = re.search(pat, s, flags)
        if not m:
            raise RuleError(f"net.py: pattern not found: {pat}")
        return m.group(1)
    magic = "".join(re.findall(r"\\x([0-9a-f]{2})", one(r'BITCOIN_MAGIC = b"((?:\\x[0-9a-f]{2}){4})"')))
    port = int(one(r"BITCOIN_PORT = (\d+)"))
    message = one(r'BITCOIN_GENESIS_MESSAGE = b"([^"]*)"')
    ghash = one(r'BITCOIN_GENESIS_HASH = "([0-9a-f]{64})"')
    gtime = int(one(r"BITCOIN_GENESIS_TIME = (\d+)"))
    gnonce = int(one(r"BITCOIN_GENESIS_NONCE = (\d+)"))
    gbits = int(one(r"BITCOIN_GENESIS_BITS = (0x[0-9A-Fa-f]+)"), 16)
    pub = "".join(re.findall(r'"([0-9a-f]+)"', one(r"BITCOIN_PUBKEY = \((.*?)\)", re.S)))
    # the literal closes on its LAST hex line -- `..."00000000")` -- not on a line of its own, and
    # comments inside it contain ')' too. Anchor the end on the closing quote of the last hex run.
    raw_blk = one(r'GENESIS_RAW = bytes\.fromhex\((.*?"\s*)\)', re.S)
    raw = bytes.fromhex("".join(re.findall(r'"([0-9a-fA-F]+)"', _strip_comments(raw_blk))))
    # self-consistency of net.py's own literal, before anything is emitted
    computed = hashlib.sha256(hashlib.sha256(raw[:80]).digest()).digest()[::-1].hex()
    if computed != ghash:
        raise RuleError(f"net.py GENESIS_RAW hashes to {computed}, not BITCOIN_GENESIS_HASH {ghash}")
    if message.encode() not in raw:
        raise RuleError("net.py GENESIS_RAW does not contain BITCOIN_GENESIS_MESSAGE")
    if int.from_bytes(raw[68:72], "little") != gtime or int.from_bytes(raw[76:80], "little") != gnonce:
        raise RuleError("net.py GENESIS_RAW header disagrees with BITCOIN_GENESIS_TIME/NONCE")
    return {
        "magic": magic,
        "port": port,
        "coinbase_message": message,
        "genesis_hash": ghash,
        "genesis_time": gtime,
        "genesis_nonce": gnonce,
        "genesis_bits": f"{gbits:08x}",
        "genesis_pubkey": pub,
        "merkle_root": raw[36:68][::-1].hex(),
        "genesis_raw_sha256": hashlib.sha256(raw).hexdigest(),
        "genesis_raw_bytes": len(raw),
    }


def identity_from_patch():
    """The same constants, read from the '+' lines of the substitution patch. Only added lines:
    the '-' lines carry Satoshi's 2009 values and reading them is how a false mismatch is made."""
    t = open(os.path.join(ROOT, "bitcoin-v0.1.0.patch"), encoding="utf-8").read()
    plus = "\n".join(l[1:] for l in t.splitlines() if l.startswith("+") and not l.startswith("+++"))
    def one(pat):
        m = re.search(pat, plus)
        if not m:
            raise RuleError(f"patch: pattern not found in + lines: {pat}")
        return m.group(1)
    magic = "".join(re.findall(r"0x([0-9a-fA-F]{2})", one(r"pchMessageStart\[4\] = \{([^}]*)\}"))).lower()
    # the script literal is CBigNum("0x...") -- the public key in reversed byte order
    pk_rev = one(r'CBigNum\("0x([0-9A-Fa-f]+)"\)').lower()
    return {
        "magic": magic,
        "port": int(one(r"DEFAULT_PORT = htons\((\d+)\)")),
        "coinbase_message": one(r'pszTimestamp = "([^"]*)"'),
        "genesis_hash": one(r'hashGenesisBlock\("0x([0-9a-f]{64})"\)'),
        "genesis_time": int(one(r"block\.nTime\s*=\s*(\d+)")),
        "genesis_nonce": int(one(r"block\.nNonce\s*=\s*(\d+)")),
        "merkle_root": one(r'hashMerkleRoot == uint256\("0x([0-9a-f]{64})"\)'),
        "genesis_pubkey": bytes.fromhex(pk_rev)[::-1].hex(),
    }


def cross_check(net, patch):
    """Every key the patch also states must agree with net.py. Returns the list of keys checked."""
    checked = []
    for k, v in patch.items():
        if net.get(k) != v:
            raise RuleError(f"identity disagreement on {k!r}: net.py={net.get(k)!r} patch={v!r}")
        checked.append(k)
    if net["genesis_hash"] != GENESIS:
        raise RuleError("net.py genesis is not the genesis this manifest is about")
    if net["genesis_pubkey"] != AGENT_PUB:
        raise RuleError("net.py genesis pubkey is not the agent key this manifest names")
    return sorted(checked)


# ---- the document ----------------------------------------------------------------------------
def build(schema=2):
    files, carry = [], 0
    for rel in collect(schema):
        raw = open(os.path.join(ROOT, rel), "rb").read()
        if COPYRIGHT in raw:
            carry += 1
        files.append({"path": rel, "size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})

    if schema == 1:
        doc = {
            "schema": 1,
            "what": ("the source that produced this chain's genesis block, and the copyright line it "
                     "carries"),
            "genesis": GENESIS,
            "agent_public_key": AGENT_PUB,
            "root": "derivatives/bitcoin",
            "file_count": len(files),
            "files_carrying_satoshi_copyright": carry,
            "excluded": ["build outputs", "dist/", "build-*/", "obj/", "__pycache__/"],
            "files": files,
        }
    else:
        net = identity_from_net()
        patch = identity_from_patch()
        checked = cross_check(net, patch)
        classes = classify_root()
        doc = {
            "schema": 2,
            "what": ("the source that produced this chain's genesis block -- the client tree and the "
                     "substitution patch pinned by their bytes, and the chain's identity constants "
                     "pinned by their values"),
            "genesis": GENESIS,
            "agent_public_key": AGENT_PUB,
            "root": "derivatives/bitcoin",
            "rule": {
                "pinned_by_bytes": {k: v for k, v in list(PIN_DIRS.items()) + list(PIN_FILES.items())},
                "pinned_by_value": VALUE_FILES,
                "excluded": {
                    **{k: v for k, v in EXCLUDE_FILES.items()},
                    **{"*" + k: v for k, v in EXCLUDE_FILE_EXT.items()},
                    **{k + "/": v for k, v in EXCLUDE_DIRS.items()},
                    **{k + "*/": v for k, v in EXCLUDE_DIR_PREFIX.items()},
                },
                "fail_closed": "a root-level entry matching none of these classes aborts the build",
                "root_as_classified": {k: v[0] for k, v in classes.items()},
            },
            "chain_identity": net,
            "identity_cross_checked_against_patch": checked,
            "file_count": len(files),
            "files_carrying_satoshi_copyright": carry,
            "files": files,
            "supersedes": {
                "schema": 1,
                "manifest_sha256": SUPERSEDED_V1_SHA256,
                "signed": "2026-08-12",
                "why": ("schema 1 pinned PROVENANCE.txt, prose the build never reads, and omitted "
                        "net.py, which holds the chain's identity. A prose correction on 2026-09-12 "
                        "left the signed manifest describing a tree that no longer existed. Schema 2 "
                        "pins source by bytes and identity by value, so the signature breaks only "
                        "when the program or the chain changes."),
            },
        }
    blob = json.dumps(doc, indent=1, sort_keys=True, separators=(",", ": ")).encode() + b"\n"
    return doc, blob


def main(argv):
    schema = 2
    out = DEFAULT_OUT
    check = False
    i = 0
    while i < len(argv):
        if argv[i] == "--schema":
            schema = int(argv[i + 1]); i += 2
        elif argv[i] == "--out":
            out = argv[i + 1]; i += 2
        elif argv[i] == "--check":
            check = True; i += 1
        else:
            print(__doc__); return 2
    try:
        doc, blob = build(schema)
    except RuleError as e:
        print(f"REFUSED: {e}")
        return 1
    h = hashlib.sha256(blob).hexdigest()
    print("schema                              %d" % schema)
    print("files pinned by bytes               %d" % doc["file_count"])
    print("carrying Satoshi's copyright line   %d" % doc["files_carrying_satoshi_copyright"])
    if schema == 2:
        ci = doc["chain_identity"]
        print("identity pinned by value            magic %s  port %d  genesis %s..." % (ci["magic"], ci["port"], ci["genesis_hash"][:16]))
        print("cross-checked against the patch     %s" % ", ".join(doc["identity_cross_checked_against_patch"]))
    print("manifest bytes                      %d" % len(blob))
    print("manifest sha256                     %s" % h)
    if check:
        print("(--check: nothing written)")
        return 0
    os.makedirs(os.path.dirname(out), exist_ok=True)
    prior = open(out, "rb").read() if os.path.exists(out) else None
    with open(out, "wb") as fd:
        fd.write(blob)
    print("written                             %s" % os.path.relpath(out, GEN).replace(os.sep, "/"))
    if prior is not None:
        print("unchanged since last build          %s" % (prior == blob))
    if schema == 2:
        print()
        print("To bind L <-> K on this schema, sign that sha256 with the genesis key:")
        print('    python verify/prove.py sign "%s" --key /path/to/secret.hex' % h)
        print("then follow manifests/CHAIN_SOURCE_MANIFEST-v2-SIGNING.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
