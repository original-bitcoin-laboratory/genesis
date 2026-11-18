"""The status probe must not abort its run, or misreport an anchor, for a reason that is not a
measurement.

⛔ WHY THIS TEST EXISTS. Of the 100 scheduled `status` runs from 25 Oct to 18 Nov 2026, six failed
(31 Oct twice, 10, 11, 16 and 18 Nov), and a failed run skips the publish step. Three causes:

  1. KeyError 'height' (11 and 18 Nov). An online chain whose walk did not complete has no
     `height` by design, and the summary line read it anyway, after status.json was written.
  2. EAI_NODATA for seed.bitcoin-lab.org (31 Oct twice, 16 Nov). One empty lookup ended the run;
     the runs before and after resolved the name.
  3. WireError "connection closed" (10 Nov). A peer that closed mid-walk made wire.read_message
     raise WireError, which nothing caught, so asyncio.gather() aborted the probe of every chain.

None of them should have aborted the run. And the fix for 3 must not overcorrect: an anchor that
completed the handshake and then dropped DID answer, so it is reachable with its height
unmeasured -- never reported offline, and never given a number.
"""
import asyncio
import json
import pathlib
import socket
import sys
import time

import pytest

_HERE = pathlib.Path(__file__).resolve().parent
for _p in ("model", "p2p", "nov08x"):
    sys.path.insert(0, str(_HERE.parent / _p))
sys.path.insert(0, str(_HERE))

import status_probe as sp                                   # noqa: E402
from chains import CHAINS                                   # noqa: E402
from p2p import MSG_BLOCK, inv_payload, version_payload    # noqa: E402
from wire import frame                                      # noqa: E402


# ---------------------------------------------------------------- 1. the summary line

def test_summary_line_handles_unmeasured_height():
    status = {
        "jan09x": {"online": True, "height": 135200},
        "nov08x": {"online": True, "height_unmeasured": True},     # online, walk incomplete
        "bitcoin": {"online": False},
    }
    assert sp.summary_line(status) == "jan09x=h135200, nov08x=unmeasured, bitcoin=offline"


def test_summary_line_does_not_invent_a_height():
    assert sp.summary_line({"x": {"online": True, "height": 0}}) == "x=h0"   # 0 is a measurement
    assert sp.summary_line({"x": {"online": True}}) == "x=unmeasured"


def _unmeasured_run(monkeypatch):
    async def fake_run(chains, anchors, recent_n, timeout):
        return {"jan09x": {"chain": "jan09x", "online": True, "height_unmeasured": True,
                           "anchors": [{"ip": anchors[0], "reachable": True, "walk_complete": False}]}}
    monkeypatch.setattr(sp, "_run", fake_run)


def test_main_completes_and_publishes_an_unmeasured_chain(tmp_path, monkeypatch, capsys):
    # on the code before the fix this raised KeyError after writing the file
    _unmeasured_run(monkeypatch)
    out = tmp_path / "status.json"
    sp.main(["--out", str(out), "--chain", "jan09x:18009", "--anchor", "203.0.113.7"])
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "height" not in data["chains"]["jan09x"]
    assert "jan09x=unmeasured" in capsys.readouterr().out


# ---------------------------------------------------------------- 2. the anchor host lookup

def _flaky(failures, answer=("203.0.113.7", "198.51.100.2")):
    calls = {"n": 0}

    def getaddrinfo(host, port, family):
        calls["n"] += 1
        if calls["n"] <= failures:
            raise socket.gaierror(-5, "No address associated with hostname")
        return [(family, 1, 6, "", (ip, 0)) for ip in answer]
    return getaddrinfo, calls


def test_resolve_retries_a_transient_failure():
    gai, calls = _flaky(failures=2)
    slept = []
    assert sp.resolve_anchor_host("seed.example", getaddrinfo=gai, sleep=slept.append) == \
        ["198.51.100.2", "203.0.113.7"]
    assert calls["n"] == 3 and slept == [5, 15]


def test_resolve_still_fails_when_the_name_stays_unresolvable():
    gai, calls = _flaky(failures=99)
    slept = []
    with pytest.raises(socket.gaierror):
        sp.resolve_anchor_host("seed.example", getaddrinfo=gai, sleep=slept.append)
    assert calls["n"] == sp.DNS_ATTEMPTS and slept == list(sp.DNS_DELAYS)


def test_main_retries_the_lookup_then_publishes(tmp_path, monkeypatch):
    # on the code before the fix the first empty answer ended the run
    gai, _ = _flaky(failures=2)
    monkeypatch.setattr(sp.socket, "getaddrinfo", gai)
    monkeypatch.setattr(time, "sleep", lambda s: None)
    _unmeasured_run(monkeypatch)
    out = tmp_path / "status.json"
    sp.main(["--out", str(out), "--chain", "jan09x:18009", "--anchor-host", "seed.example"])
    assert out.exists()


def test_main_writes_nothing_when_the_name_stays_unresolvable(tmp_path, monkeypatch):
    gai, _ = _flaky(failures=99)
    monkeypatch.setattr(sp.socket, "getaddrinfo", gai)
    monkeypatch.setattr(time, "sleep", lambda s: None)
    out = tmp_path / "status.json"
    with pytest.raises(SystemExit):
        sp.main(["--out", str(out), "--chain", "jan09x:18009", "--anchor-host", "seed.example"])
    assert not out.exists() and not out.with_suffix(".json.tmp").exists()


# ---------------------------------------------------------------- 3. a peer that closes

class _Reader:
    """Serves `data`, then behaves as a closed socket."""

    def __init__(self, data=b""):
        self.data = data

    async def readexactly(self, n):
        if len(self.data) < n:
            got, self.data = self.data, b""
            raise asyncio.IncompleteReadError(got, n)
        chunk, self.data = self.data[:n], self.data[n:]
        return chunk


class _Writer:
    def write(self, data):
        pass

    async def drain(self):
        pass

    def close(self):
        pass


def _serve(monkeypatch, data):
    async def fake_open_connection(host, port):
        return _Reader(data), _Writer()
    monkeypatch.setattr(sp.asyncio, "open_connection", fake_open_connection)


def test_close_before_the_handshake_is_unreachable(monkeypatch):
    _serve(monkeypatch, b"")
    assert asyncio.run(sp._probe_anchor("203.0.113.7", 18009, b"\xf0\x0b\xa7\x09", b"\x00" * 32,
                                        15, 1.0)) is None


def _version_then_one_page(cfg):
    ck = getattr(cfg, "wire_checksum", True)
    return (frame("version", version_payload(), cfg.magic, checksum=ck) +
            frame("inv", inv_payload([(MSG_BLOCK, b"\x11" * 32)]), cfg.magic, checksum=ck))


def test_close_mid_walk_is_reachable_and_unmeasured(monkeypatch):
    # the 10 Nov 2026 case: handshake done, one inv page served, then the peer closes
    cfg = CHAINS["jan09x"]
    _serve(monkeypatch, _version_then_one_page(cfg))
    entry = asyncio.run(sp.probe_chain("jan09x", 18009, ["203.0.113.7"], 15, 1.0))
    assert entry["online"] is True
    assert entry["anchors"] == [{"ip": "203.0.113.7", "reachable": True, "walk_complete": False}]
    assert entry.get("height_unmeasured") is True
    assert "height" not in entry                             # an interrupted walk gives no number
