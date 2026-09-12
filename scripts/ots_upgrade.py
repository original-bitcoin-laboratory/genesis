#!/usr/bin/env python3
"""Upgrade pending OpenTimestamps proofs, and say whether each is Bitcoin-anchored, by parsing them.

Why not `ots upgrade`? On some machines the `ots` command line tool cannot even start (it imports
a wallet library that needs an OpenSSL DLL an upgrade never touches), and a tool that crashes
prints no "BitcoinBlockHeaderAttestation" -- so anything that judged a proof by the tool's output
would call every proof pending. This script talks to the calendars through the pure-python
`opentimestamps` package (pip install opentimestamps-client) and decides pending-vs-anchored by
reading the proof, never by output text or file size.

    python scripts/ots_upgrade.py docs/                  # every .ots under docs/, upgrade what is ready
    python scripts/ots_upgrade.py --dry-run docs/ a.ots  # report only, touch nothing

A proof is rewritten only when a calendar returns a Bitcoin attestation. "Not found yet" is the
normal answer for a fresh stamp: the calendar has not put it in a Bitcoin transaction. Wait and
re-run; that is time, not a defect.
"""
import os, ssl, sys, urllib.request
from opentimestamps.core.timestamp import DetachedTimestampFile
from opentimestamps.core.notary import PendingAttestation, BitcoinBlockHeaderAttestation
from opentimestamps.core.serialize import BytesSerializationContext, BytesDeserializationContext
from opentimestamps.calendar import RemoteCalendar

# Some system CA stores cannot verify the calendars; certifi's bundle can. Without this, a
# certificate error looks exactly like "not ready yet", which is the wrong diagnosis.
try:
    import certifi
    _CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _CTX = ssl.create_default_context()
urllib.request.install_opener(urllib.request.build_opener(urllib.request.HTTPSHandler(context=_CTX)))

def load(path):
    with open(path, "rb") as fd:
        return DetachedTimestampFile.deserialize(BytesDeserializationContext(fd.read()))

def save(path, detached):
    ctx = BytesSerializationContext(); detached.serialize(ctx)
    with open(path, "wb") as fd:
        fd.write(ctx.getbytes())

def heights(ts):
    """Bitcoin block heights this proof attests to. Empty set == pending."""
    return {att.height for _m, att in ts.all_attestations() if isinstance(att, BitcoinBlockHeaderAttestation)}

def upgrade(ts):
    changed = False
    for sub in ts.ops.values():
        if upgrade(sub): changed = True
    if any(isinstance(a, BitcoinBlockHeaderAttestation) for a in ts.attestations):
        return changed
    for att in list(ts.attestations):
        if not isinstance(att, PendingAttestation): continue
        uri = att.uri.decode() if isinstance(att.uri, bytes) else att.uri
        try:
            got = RemoteCalendar(uri).get_timestamp(ts.msg)
        except Exception as exc:
            print(f"      {uri:<44} {type(exc).__name__}", flush=True); continue
        if got is not None:
            ts.merge(got); changed = True
    return changed

def main(argv):
    dry = "--dry-run" in argv
    targets = [a for a in argv if a != "--dry-run"] or ["."]
    proofs = []
    for t in targets:
        if os.path.isdir(t):
            for root, dirs, files in os.walk(t):
                dirs[:] = [d for d in dirs if d != ".git"]
                proofs += [os.path.join(root, f) for f in files if f.endswith(".ots")]
        elif t.endswith(".ots"):
            proofs.append(t)
    proofs.sort()
    pending, anchored, broken = [], [], []
    for p in proofs:
        try:
            (anchored if heights(load(p).timestamp) else pending).append(p)
        except Exception as exc:
            broken.append((p, type(exc).__name__))
    print(f"proofs {len(proofs)}: anchored {len(anchored)}, pending {len(pending)}, unparseable {len(broken)}")
    for p, why in broken: print(f"  UNPARSEABLE {p} ({why})")
    done = 0
    for p in pending:
        print(f"  {p}", flush=True)
        if dry: continue
        d = load(p)
        if upgrade(d.timestamp) and heights(d.timestamp):
            save(p, d); print(f"      -> ANCHORED block {sorted(heights(d.timestamp))}"); done += 1
        else:
            print("      -> still pending")
    if not dry and pending: print(f"upgraded {done}, still pending {len(pending) - done}")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
