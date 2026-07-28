#!/usr/bin/env python3
"""Red-team probe: fire malformed / adversarial wire frames at a running X-chain node and confirm it
survives — it stays responsive and still completes a fresh handshake after the barrage. A hostile or
buggy peer must be able to drop only *itself*, never hang or crash an honest node.

This is the manual counterpart to the automated regressions
(`test_netnode.py::test_node_survives_a_malformed_message_flood_and_still_serves`,
`p2p/test_p2p.py`, and the Rust `dos.rs`); see `docs/AUDIT.md`. NOT money.

Usage:
    # one shell — start a node:
    python -m netnode --chain jan09x --datadir ./data --listen 127.0.0.1:18009
    # another shell — probe it:
    python adversarial_probe.py --chain jan09x --connect 127.0.0.1:18009

Exit code 0 = node survived (still handshakes after the barrage); 1 = it did not; 2 = no node found.
"""
import argparse
import pathlib
import socket
import sys
import time

_HERE = pathlib.Path(__file__).resolve().parent
for _p in (_HERE.parent / "model", _HERE.parent / "p2p", _HERE):
    sys.path.insert(0, str(_p))

from wire import frame            # noqa: E402
from p2p import version_payload   # noqa: E402
from chains import CHAINS         # noqa: E402


def attacks(magic):
    """Malformed frames, including the 'huge claimed count' vectors that once hung the event loop."""
    return [
        ("empty_inv",               frame("inv", b"", magic)),
        ("inv_claims_65535_empty",  frame("inv", b"\xfd\xff\xff", magic)),
        ("inv_claims_2**64",        frame("inv", b"\xff" + b"\xff" * 8, magic)),
        ("getblocks_claims_2**64",  frame("getblocks", b"\x00\x00\x00\x00\xff" + b"\xff" * 8, magic)),
        ("getblocks_truncated",     frame("getblocks", b"\x05", magic)),
        ("tx_claims_2**64_inputs",  frame("tx", b"\x01\x00\x00\x00\xff" + b"\x00" * 8, magic)),
        ("tx_4_random_bytes",       frame("tx", bytes([1, 2, 3, 4]), magic)),
        ("block_hdr_plus_junk_ntx", frame("block", b"\x00" * 80 + b"\xfd\xff\xff", magic)),
        ("garbage_addr",            frame("addr", b"\xff\x01\x02\x03", magic)),
        ("random_inv_500b",         frame("inv", bytes(x % 256 for x in range(500)), magic)),
        ("unknown_command",         frame("frobnicate", b"\x00" * 20, magic)),
    ]


def handshakes(host, port, magic, timeout=5.0):
    """Open a fresh connection, send `version`, and confirm the node frames a reply back to us."""
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.settimeout(timeout)
        s.sendall(frame("version", version_payload(), magic))
        hdr = s.recv(24)
        s.close()
        return len(hdr) >= 4 and hdr[:4] == magic
    except OSError:
        return False


def main():
    ap = argparse.ArgumentParser(description="fire malformed frames at a node; confirm it survives")
    ap.add_argument("--chain", choices=list(CHAINS), default="jan09x")
    ap.add_argument("--connect", default="127.0.0.1:18009", help="HOST:PORT of the node to probe")
    args = ap.parse_args()
    host, port_s = args.connect.rsplit(":", 1)
    port = int(port_s)
    magic = CHAINS[args.chain].magic

    if not handshakes(host, port, magic):
        print(f"[skip] no {args.chain} node answering at {host}:{port}")
        return 2

    print(f"probing {args.chain} node at {host}:{port} — firing {len(attacks(magic))} malformed frames")
    for name, fr in attacks(magic):
        try:
            s = socket.create_connection((host, port), timeout=5)
            s.sendall(frame("version", version_payload(), magic))   # look like a peer, then misbehave
            s.sendall(fr)
            time.sleep(0.1)
            s.close()
            print(f"  fired: {name}")
        except OSError as e:
            print(f"  {name}: client-side send error {e!r}")

    time.sleep(0.3)
    alive = handshakes(host, port, magic)
    print(f"\nnode still handshakes after the barrage: {alive}")
    print("PASS - node survived the barrage" if alive else "FAIL - node did not respond")
    return 0 if alive else 1


if __name__ == "__main__":
    raise SystemExit(main())
