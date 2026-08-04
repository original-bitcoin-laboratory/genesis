#!/usr/bin/env python3
"""Make a node discoverable to the released v0.1.0 client, the way v0.1.0 discovers nodes.

The January 2009 client has no switch for a peer address. Reading `mapArgs` in ui.cpp, the only
options it honours are /datadir /proxy /debug /dropmessages /loadblockindextest /printblockindex
/gen /randsendtest -- there is no -connect and no -addnode. It learns addresses from exactly three
places (net.cpp AddAddress callers):

    db.cpp:419    addresses persisted in addr.dat from a previous run
    irc.cpp:225   names harvested from an IRC channel
    main.cpp:1759 `addr` messages from a peer it is already connected to

All three are downstream of the second. A client with an empty datadir and no peers can only
bootstrap over IRC, so a seed that is not in the channel does not exist as far as that client is
concerned -- it will sit at height 0 for ever with the node it wanted a few hops away in DNS.

This publishes that presence. It joins the channel with its nickname set to the seed's address in
the client's own encoding, which is all the client needs: ThreadIRCSeed parses names out of the
WHO reply (`352`, field 7) and out of JOIN lines (`vWords[0]`, up to the `!`), and any name
beginning with 'u' is run through DecodeAddress and added to mapAddresses.

The encoding, from irc.cpp:

    #pragma pack(1) struct ircaddr { int ip; short port; };   // exactly 6 bytes, no padding
    EncodeAddress() -> "u" + EncodeBase58Check(those 6 bytes)

CAddress stores `ip` from inet_addr and `port` from htons, both already network byte order, so the
six bytes are the four IP octets in order followed by the port big-endian. EncodeBase58Check is the
standard construction: append the first 4 bytes of double-SHA256, then base58.

NOT money. This publishes the seed's IP address into a public channel -- which is the point, and is
information already in DNS and on the website. Note that every client that joins publishes its own
the same way; that is a property of the protocol being reproduced, and it is documented in the
release notes rather than papered over.

    python3 -m netnode.ircseed --addr 168.144.27.117:18026 --print-nick
    python3 -m netnode.ircseed --addr 168.144.27.117:18026 --channel '#bitcoin26'
"""
from __future__ import annotations

import argparse
import hashlib
import socket
import struct
import sys
import time

B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _b58encode(b: bytes) -> str:
    n = int.from_bytes(b, "big")
    out = ""
    while n > 0:
        n, r = divmod(n, 58)
        out = B58[r] + out
    # base58.h emits one '1' per leading zero byte
    return "1" * (len(b) - len(b.lstrip(b"\x00"))) + out


def _b58decode(s: str) -> bytes:
    n = 0
    for ch in s:
        n = n * 58 + B58.index(ch)
    body = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return b"\x00" * (len(s) - len(s.lstrip("1"))) + body


def _sha256d(b: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


def encode_address(ip: str, port: int) -> str:
    """The client's EncodeAddress(): 'u' + base58check(4-byte ip || 2-byte port, both big-endian)."""
    payload = socket.inet_aton(ip) + struct.pack(">H", port)
    assert len(payload) == 6, "ircaddr is #pragma pack(1) and must stay 6 bytes"
    return "u" + _b58encode(payload + _sha256d(payload)[:4])


def decode_address(nick: str) -> tuple[str, int]:
    """The client's DecodeAddress(), for the round-trip self-check."""
    if not nick.startswith("u"):
        raise ValueError("a v0.1.0 address nickname begins with 'u'")
    raw = _b58decode(nick[1:])
    body, check = raw[:-4], raw[-4:]
    if _sha256d(body)[:4] != check:
        raise ValueError("base58check failed")
    if len(body) != 6:
        raise ValueError(f"expected 6 bytes, got {len(body)}")
    return socket.inet_ntoa(body[:4]), struct.unpack(">H", body[4:])[0]


def selfcheck(ip: str, port: int) -> str:
    nick = encode_address(ip, port)
    back = decode_address(nick)
    if back != (ip, port):
        raise SystemExit(f"!! encode/decode disagree: {back} != {(ip, port)}")
    # The client copies the WHO reply's field 7 with strcpy into a fixed buffer and notes that the
    # field "is limited to 16 characters". A longer name would be truncated and fail to decode.
    if len(nick) > 16:
        raise SystemExit(f"!! nickname {nick!r} is {len(nick)} chars; WHO field 7 caps at 16")
    return nick


def run(host: str, port: int, channel: str, nick: str, once: bool = False) -> None:
    backoff = 10
    while True:
        try:
            print(f"-- connecting {host}:{port} as {nick}", flush=True)
            s = socket.create_connection((host, port), timeout=60)
            f = s.makefile("rwb", buffering=0)

            def send(line: str) -> None:
                f.write((line + "\r\n").encode("utf-8", "replace"))

            # The client sends both, and harvests from both, so both must carry the address.
            send(f"NICK {nick}")
            send(f"USER {nick} 8 * : {nick}")

            joined = False
            while True:
                raw = f.readline()
                if not raw:
                    raise ConnectionError("server closed the connection")
                line = raw.decode("utf-8", "replace").rstrip("\r\n")

                if line.startswith("PING"):
                    send("PONG" + line[4:])
                    continue

                parts = line.split()
                code = parts[1] if len(parts) > 1 else ""

                if code == "004" and not joined:      # registration complete
                    send(f"JOIN {channel}")
                    joined = True
                    print(f"-- joined {channel}", flush=True)
                    backoff = 10
                    if once:
                        print("-- --once given; presence established, exiting", flush=True)
                        s.close()
                        return
                elif code in ("433", "436"):          # nick in use / collision
                    # Another node is already advertising this exact address, which is harmless
                    # but means our presence adds nothing. Say so rather than looping silently.
                    print(f"!! {nick} already in the channel -- this address is already published",
                          flush=True)
                    s.close()
                    return
                elif code in ("465", "464"):
                    print(f"!! refused by server: {line}", flush=True)
                    s.close()
                    return
        except KeyboardInterrupt:
            print("-- stopped", flush=True)
            return
        except Exception as e:                        # noqa: BLE001 - a seed must survive anything
            print(f"!! {type(e).__name__}: {e}; reconnecting in {backoff}s", flush=True)
            time.sleep(backoff)
            backoff = min(backoff + 30, 300)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--addr", required=True, metavar="IP:PORT",
                   help="the seed address to publish, e.g. 168.144.27.117:18026")
    p.add_argument("--server", default="chat.freenode.net",
                   help="IRC host the client resolves (irc.cpp gethostbyname); default %(default)s")
    p.add_argument("--server-port", type=int, default=6667)
    p.add_argument("--channel", default="#bitcoin26",
                   help="channel the client joins; default %(default)s")
    p.add_argument("--print-nick", action="store_true",
                   help="print the encoded nickname and exit, without connecting")
    p.add_argument("--once", action="store_true",
                   help="exit once presence is established (for testing)")
    a = p.parse_args(argv)

    ip, _, port_s = a.addr.partition(":")
    if not port_s:
        p.error("--addr must be IP:PORT")
    port = int(port_s)

    nick = selfcheck(ip, port)
    print(f"   address  {ip}:{port}")
    print(f"   nickname {nick}  ({len(nick)} chars, decodes back clean)")
    if a.print_nick:
        return 0

    run(a.server, a.server_port, a.channel, nick, once=a.once)
    return 0


if __name__ == "__main__":
    sys.exit(main())
