"""A persisted, diversity-aware peer database for the X-chain node — a compact addrman. NOT money.

Bitcoin's eclipse-resistance comes from its address manager: addresses are bucketed by network group
so no single subnet can fill the table (or your outbound slots), and peers you have actually connected
to ('tried') are preferred over merely-gossiped ones ('new'). This is a small, faithful-in-spirit
version:

  - addresses are grouped by **/16** (IPv4) and **capped per group** — one subnet can't dominate the
    table (the core anti-eclipse property);
  - **'tried'** (we connected) vs **'new'** (only gossiped) — tried peers are preferred when we pick
    who to dial or gossip;
  - the table **persists** to `<datadir>/peers.json`, so a restarted node re-meshes from its own
    memory without needing a fresh seed.

Everything is bounded (total + per-group). This is discovery hygiene on a valueless research network,
not a hardened production addrman. **Not money.**
"""

from __future__ import annotations

import json
import pathlib
import random
import time

Addr = tuple


def group_of(host: str) -> str:
    """The network group used for diversity: the /16 for a dotted IPv4, else the host string."""
    parts = host.split(".")
    if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
        return f"{parts[0]}.{parts[1]}"
    return host


class PeerDB:
    def __init__(self, max_addrs: int = 1024, max_per_group: int = 32,
                 rng: random.Random | None = None):
        self.max_addrs = max_addrs
        self.max_per_group = max_per_group
        self.tried: dict[Addr, float] = {}     # addr -> last-seen (we have connected)
        self.new: dict[Addr, float] = {}       # addr -> last-seen (only gossiped)
        self.rng = rng or random.Random()

    def __len__(self) -> int:
        return len(self.tried) + len(self.new)

    def addrs(self) -> set:
        return set(self.tried) | set(self.new)

    def _group_count(self, group: str) -> int:
        return sum(1 for a in self.addrs() if group_of(a[0]) == group)

    def add(self, addr, now: float | None = None) -> bool:
        """Record a gossiped peer. Bounded by the total cap AND a per-/16 cap (anti-eclipse):
        an attacker who owns one subnet cannot fill the table. Returns True iff newly added."""
        addr = (addr[0], int(addr[1]))
        now = time.time() if now is None else now
        if addr in self.tried:
            self.tried[addr] = now
            return False
        if addr in self.new:
            self.new[addr] = now
            return False
        if len(self) >= self.max_addrs:
            return False
        if self._group_count(group_of(addr[0])) >= self.max_per_group:
            return False
        self.new[addr] = now
        return True

    def mark_good(self, addr, now: float | None = None) -> None:
        """Promote a peer we successfully connected to into the 'tried' set."""
        addr = (addr[0], int(addr[1]))
        now = time.time() if now is None else now
        self.new.pop(addr, None)
        if addr in self.tried or len(self) < self.max_addrs:
            self.tried[addr] = now

    def sample(self, k: int, exclude=(), per_group: int | None = None) -> list:
        """Up to `k` addresses, preferring 'tried', shuffled, optionally capped `per_group` so no
        single /16 dominates the returned set."""
        exclude = set(exclude)
        picked: list = []
        seen: dict[str, int] = {}
        for tier in (self.tried, self.new):
            items = [a for a in tier if a not in exclude]
            self.rng.shuffle(items)
            for a in items:
                if len(picked) >= k:
                    return picked
                g = group_of(a[0])
                if per_group is not None and seen.get(g, 0) >= per_group:
                    continue
                picked.append(a)
                seen[g] = seen.get(g, 0) + 1
        return picked

    # -- persistence -----------------------------------------------------------
    def save(self, path) -> None:
        data = {"not_money": True,
                "tried": [[h, p, t] for (h, p), t in self.tried.items()],
                "new": [[h, p, t] for (h, p), t in self.new.items()]}
        tmp = pathlib.Path(str(path) + ".tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        tmp.replace(path)                          # atomic-ish replace (no torn file on crash)

    def load(self, path) -> None:
        p = pathlib.Path(path)
        if not p.exists():
            return
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return                                  # a corrupt peer file is non-fatal — start fresh
        for h, port, t in data.get("tried", []):
            if len(self) < self.max_addrs:
                self.tried[(h, int(port))] = float(t)
        for h, port, t in data.get("new", []):
            self.add((h, int(port)), now=float(t))
