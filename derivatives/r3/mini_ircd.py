"""Minimal IRC daemon for the R3 isolated two-node network (derivative tool).

Bitcoin v0.1 discovers peers only via IRC (irc.cpp): it connects to
chat.freenode.net:6667, waits for a "Found your hostname" notice and a 004
numeric, then JOIN #bitcoin / WHO #bitcoin, and extracts each peer's address from
the NICK carried in WHO 352 replies (field index 7) and JOIN messages. Each node's
nick is EncodeAddress(local) — which begins with 'u' only if the local IP
IsRoutable(): v0.1 treats everything except 10.x and 192.168.x as routable
(net.h:265), so put the isolated net on e.g. 172.20.0.0/24.

This server implements just enough IRC for that handshake — no external ircd
needed. Point both VMs' hosts file: `chat.freenode.net -> <this server's IP>`.
Run:  python mini_ircd.py [--host 0.0.0.0] [--port 6667]
Evidence level: DERIVATIVE (test infrastructure; not original code).
"""

from __future__ import annotations

import argparse
import asyncio

SERVER = "obl-ircd"
CHANNEL = "#bitcoin"


class Client:
    def __init__(self, reader, writer):
        self.reader, self.writer = reader, writer
        self.nick = None
        self.user = "u"
        self.host = writer.get_extra_info("peername", ("?", 0))[0]

    def send(self, line: str):
        self.writer.write((line + "\r\n").encode("latin-1", "replace"))


class MiniIRCd:
    def __init__(self):
        self.channel: set[Client] = set()

    async def handle(self, reader, writer):
        c = Client(reader, writer)
        c.send(f":{SERVER} NOTICE AUTH :*** Found your hostname")   # irc.cpp RecvUntil
        try:
            while True:
                raw = await reader.readline()
                if not raw:
                    break
                line = raw.decode("latin-1", "replace").strip("\r\n")
                if not line:
                    continue
                await self.on_line(c, line)
                await writer.drain()
        except (ConnectionError, asyncio.IncompleteReadError):
            pass
        finally:
            self.channel.discard(c)
            for m in self.channel:
                m.send(f":{c.nick}!{c.user}@{SERVER} PART {CHANNEL}")
            writer.close()

    async def on_line(self, c: Client, line: str):
        w = line.split(" ")
        cmd = w[0].upper()
        if cmd == "NICK":
            c.nick = w[1] if len(w) > 1 else c.nick
        elif cmd == "USER":
            c.user = w[1] if len(w) > 1 else "u"
            # registration -> send 001..004 (irc.cpp waits for " 004 ")
            n = c.nick or "*"
            c.send(f":{SERVER} 001 {n} :Welcome to the OBL isolated IRC network {n}")
            c.send(f":{SERVER} 002 {n} :Your host is {SERVER}")
            c.send(f":{SERVER} 003 {n} :This server is for the Original Bitcoin Laboratory")
            c.send(f":{SERVER} 004 {n} {SERVER} obl-0.1 o o")
        elif cmd == "PING":
            c.send(f":{SERVER} PONG {SERVER} :{w[1] if len(w) > 1 else ''}")
        elif cmd == "JOIN":
            self.channel.add(c)
            for m in self.channel:                                  # echo JOIN to all members
                m.send(f":{c.nick}!{c.user}@{SERVER} JOIN :{CHANNEL}")
            c.send(f":{SERVER} 353 {c.nick} = {CHANNEL} :" + " ".join(m.nick for m in self.channel))
            c.send(f":{SERVER} 366 {c.nick} {CHANNEL} :End of NAMES")
        elif cmd == "WHO":
            for m in self.channel:                                  # 352: nick is field index 7
                c.send(f":{SERVER} 352 {c.nick} {CHANNEL} {m.user} {m.host} {SERVER} {m.nick} H :0 obl")
            c.send(f":{SERVER} 315 {c.nick} {CHANNEL} :End of WHO")
        elif cmd == "QUIT":
            raise ConnectionError


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=6667)
    args = ap.parse_args()
    ircd = MiniIRCd()
    server = await asyncio.start_server(ircd.handle, args.host, args.port)
    addrs = ", ".join(str(s.getsockname()) for s in server.sockets)
    print(f"mini_ircd listening on {addrs} (channel {CHANNEL})")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
