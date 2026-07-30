"""Smoke test: two clients perform v0.1's IRC handshake against mini_ircd and each
discovers the other's nick (which carries the peer address). No bitcoin.exe needed.
Evidence level: DERIVATIVE (test infrastructure)."""

import asyncio

from mini_ircd import MiniIRCd


async def _read_until(reader, needle: str) -> None:
    while True:
        line = (await reader.readline()).decode("latin-1", "replace")
        if not line or needle in line:
            return


async def _register(host, port, nick, term="\r"):
    # term defaults to a bare '\r' — the terminator the real v0.1 client uses
    # (irc.cpp: Send "...\r"). mini_ircd must accept it as well as CRLF/LF.
    reader, writer = await asyncio.open_connection(host, port)
    await _read_until(reader, "Found your hostname")
    writer.write(f"NICK {nick}{term}".encode())
    writer.write(f"USER {nick} 8 * :{nick}{term}".encode())
    await writer.drain()
    await _read_until(reader, " 004 ")
    writer.write(f"JOIN #bitcoin{term}".encode())
    await writer.drain()
    return reader, writer


async def _who_nicks(reader, writer):
    writer.write(b"WHO #bitcoin\r\n")
    await writer.drain()
    nicks = []
    while True:
        line = (await reader.readline()).decode("latin-1", "replace").strip()
        w = line.split(" ")
        if len(w) > 1 and w[1] == "352" and len(w) >= 8:
            nicks.append(w[7])                     # field 7 = nick, per irc.cpp:206
        if len(w) > 1 and w[1] == "315":
            return nicks


async def _scenario(term="\r"):
    ircd = MiniIRCd()
    server = await asyncio.start_server(ircd.handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    async with server:
        ra, wa = await _register("127.0.0.1", port, "uAAAA1111", term)
        rb, wb = await _register("127.0.0.1", port, "uBBBB2222", term)
        await asyncio.sleep(0.05)
        a_who = await _who_nicks(ra, wa)
        b_who = await _who_nicks(rb, wb)
        wa.close(); wb.close()
    return a_who, b_who


def test_two_nodes_discover_each_other():
    # the real v0.1 protocol: bare-'\r'-terminated lines (the case that broke the live R3 run)
    a_who, b_who = asyncio.run(_scenario(term="\r"))
    assert "uBBBB2222" in a_who and "uAAAA1111" in a_who    # A's WHO lists both peers
    assert "uAAAA1111" in b_who and "uBBBB2222" in b_who    # B's WHO lists both peers


def test_two_nodes_discover_with_crlf():
    # ordinary CRLF must still work (test/other clients)
    a_who, b_who = asyncio.run(_scenario(term="\r\n"))
    assert "uBBBB2222" in a_who and "uAAAA1111" in b_who


if __name__ == "__main__":
    print(asyncio.run(_scenario()))
