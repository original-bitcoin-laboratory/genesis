"""A minimal DNS message codec (query parse + A/AAAA response build) — stdlib only. NOT money.

Just enough of RFC 1035 to run an **authoritative A-record responder** for one zone: parse an
incoming query (transaction id, requested name, type) and build a response that echoes the question
and appends A (IPv4) answer records. This is exactly what a Bitcoin-style DNS seed does — a fresh
node resolves a seed hostname and gets back a batch of peer IPs to bootstrap from.

No compression beyond the standard 0xC00C pointer back to the question name. Evidence: NEW-EXP.
"""

from __future__ import annotations

import socket
import struct

TYPE_A = 1
TYPE_AAAA = 28
CLASS_IN = 1
_RDLEN = {TYPE_A: 4, TYPE_AAAA: 16}
_QR_AA = 0x8400          # response, authoritative, no error
_RCODE_NAME_ERROR = 0x8403
_RCODE_NOT_IMPL = 0x8404


def parse_query(data: bytes):
    """Return (txid, qname, qtype) for a single-question query, or raise ValueError."""
    if len(data) < 12:
        raise ValueError("short DNS header")
    txid, _flags, qd, _an, _ns, _ar = struct.unpack(">HHHHHH", data[:12])
    if qd < 1:
        raise ValueError("no question")
    i, labels = 12, []
    while True:
        if i >= len(data):
            raise ValueError("truncated qname")
        ln = data[i]; i += 1
        if ln == 0:
            break
        if ln & 0xC0:                                       # a pointer in a question is unexpected here
            raise ValueError("compressed qname in question")
        labels.append(data[i:i + ln].decode("ascii", "replace")); i += ln
    qtype, _qclass = struct.unpack(">HH", data[i:i + 4])
    return txid, ".".join(labels), qtype


def _question_bytes(qname: str, qtype: int) -> bytes:
    out = b""
    for label in qname.split("."):
        b = label.encode("ascii", "ignore")[:63]
        out += bytes([len(b)]) + b
    return out + b"\x00" + struct.pack(">HH", qtype, CLASS_IN)


def build_response(txid: int, qname: str, ips, ttl: int = 60, qtype: int = TYPE_A) -> bytes:
    """An authoritative A (IPv4) or AAAA (IPv6) response for `qname` with the given addresses.

    An empty `ips` is a valid answer: NOERROR with zero records means "the name exists, but it has
    no record of this type" -- which is exactly right when the seed knows no peer of that family,
    and is what lets a dual-stack resolver fall back to the other family instead of giving up."""
    q = _question_bytes(qname, qtype)
    header = struct.pack(">HHHHHH", txid, _QR_AA, 1, len(ips), 0, 0)
    rdlen = _RDLEN[qtype]
    fam = socket.AF_INET6 if qtype == TYPE_AAAA else socket.AF_INET
    body = q
    for ip in ips:
        body += b"\xc0\x0c"                                 # NAME -> pointer to the question at offset 12
        body += struct.pack(">HHIH", qtype, CLASS_IN, ttl, rdlen)
        body += socket.inet_pton(fam, ip)
    return header + body


def build_error(txid: int, qname: str, qtype: int, rcode: int = _RCODE_NAME_ERROR) -> bytes:
    """An empty (no-answer) response — used for names/types we are not authoritative for."""
    return struct.pack(">HHHHHH", txid, rcode, 1, 0, 0, 0) + _question_bytes(qname, qtype)


def parse_records(response: bytes, qtype: int = TYPE_A):
    """Test/utility helper: pull the A or AAAA addresses out of a response we built."""
    _txid, _flags, qd, an, _ns, _ar = struct.unpack(">HHHHHH", response[:12])
    i = 12
    for _ in range(qd):                                     # skip the question
        while response[i] != 0:
            i += 1 + response[i]
        i += 1 + 4
    out, want, fam = [], _RDLEN[qtype], socket.AF_INET6 if qtype == TYPE_AAAA else socket.AF_INET
    for _ in range(an):
        i += 2                                              # NAME pointer
        rtype, _cls, _ttl, rdlen = struct.unpack(">HHIH", response[i:i + 10]); i += 10
        if rtype == qtype and rdlen == want:
            out.append(socket.inet_ntop(fam, response[i:i + rdlen]))
        i += rdlen
    return out


def parse_a_records(response: bytes):
    """Test/utility helper: pull the A-record IPv4 addresses out of a response we built."""
    txid, _flags, qd, an, _ns, _ar = struct.unpack(">HHHHHH", response[:12])
    i = 12
    for _ in range(qd):                                     # skip the question
        while response[i] != 0:
            i += 1 + response[i]
        i += 1 + 4
    ips = []
    for _ in range(an):
        i += 2                                              # NAME pointer
        rtype, _cls, _ttl, rdlen = struct.unpack(">HHIH", response[i:i + 10]); i += 10
        if rtype == TYPE_A and rdlen == 4:
            ips.append(socket.inet_ntoa(response[i:i + 4]))
        i += rdlen
    return ips
