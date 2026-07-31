"""Lab rule profiles — make "which rules is this run using" explicit and verifiable.

A *profile* pairs a consensus rule set (the monetary / PoW / coinbase parameters,
faithful to a source edition) with a *script-vocabulary posture*:

  - faithful-v0.1    : v0.1's EvalScript as written, with OP_NOTEQUAL disabled
                       (the one functional opcode commented out at script.cpp:486).
  - nothing-disabled : the isolated experimental networks (JAN09-X / NOV08-X), which
                       re-open OP_NOTEQUAL. Safe ONLY because they carry no value.

The declaration lives in `profiles.json`. This module loads it, resolves each posture to
the actual engine that implements it, and `verify()` checks the declaration against both
the reproducible opcode inventory (`inventory/OPCODES.json`) and live engine behavior — so
a profile cannot silently drift away from what the code really does. Evidence level: MODEL.
NOT money.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_DERIV = _HERE.parent
_ROOT = _DERIV.parent
for _p in ("model", "jan09x", "nov08x"):
    sys.path.insert(0, str(_DERIV / _p))

from evalscript_model import cast_to_bool          # noqa: E402
from evalscript_model import run as _run_faithful  # noqa: E402
from script_full import run_full as _run_full      # noqa: E402
from consensus import Rules                         # noqa: E402

_REGISTRY = json.loads((_HERE / "profiles.json").read_text(encoding="utf-8"))
_POSTURES = _REGISTRY["script_postures"]

# script-vocabulary posture -> the engine that implements it
_RUNNERS = {
    "faithful-v0.1": _run_faithful,      # OP_NOTEQUAL absent -> structural failure
    "nothing-disabled": _run_full,       # OP_NOTEQUAL re-opened as OP_EQUAL then OP_NOT
}


class Profile:
    def __init__(self, doc: dict):
        self.name = doc["name"]
        self.chain = doc["chain"]
        self.consensus_rules = doc["consensus_rules"]
        self.script_posture = doc["script_posture"]
        self.klass = doc["class"]
        self.description = doc["description"]
        self._posture = _POSTURES[self.script_posture]

    @property
    def disabled_opcodes(self) -> list[str]:
        return list(self._posture["disabled_opcodes"])

    @property
    def reopened_opcodes(self) -> list[str]:
        return list(self._posture["reopened_opcodes"])

    def runner(self):
        """The script engine that implements this profile's vocabulary posture."""
        return _RUNNERS[self.script_posture]

    def rules(self) -> Rules:
        """The consensus (monetary / PoW / coinbase) rule set."""
        return Rules.load(self.consensus_rules)

    def profile_hash(self) -> str:
        """A stable SHA-256 over this profile's identity — its declared fields plus the resolved
        script posture. Lets a run record *exactly which* profile governed a result, so the paper's
        'this finding used profile X' is a checkable object, not a claim."""
        ident = {
            "name": self.name,
            "chain": self.chain,
            "consensus_rules": self.consensus_rules,
            "script_posture": self.script_posture,
            "class": self.klass,
            "disabled_opcodes": sorted(self.disabled_opcodes),
            "reopened_opcodes": sorted(self.reopened_opcodes),
        }
        blob = json.dumps(ident, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()

    def __repr__(self):
        return f"Profile({self.name}: {self.chain}/{self.script_posture})"


def all_profiles() -> list[Profile]:
    return [Profile(d) for d in _REGISTRY["profiles"]]


def load(name: str) -> Profile:
    for d in _REGISTRY["profiles"]:
        if d["name"] == name:
            return Profile(d)
    raise KeyError(f"no such profile: {name!r} (have {[d['name'] for d in _REGISTRY['profiles']]})")


def _inventory_disabled() -> list[str]:
    """The opcodes the reproducible inventory records as commented out in EvalScript."""
    doc = json.loads((_ROOT / "inventory" / "OPCODES.json").read_text(encoding="utf-8"))
    # schema 2 records each disabled case as {name, file, line, source_sha256}; tolerate the older
    # bare-string form too.
    return sorted(e["name"] if isinstance(e, dict) else e
                  for e in doc.get("disabled_commented_out", []))


# The one opcode v0.1 disabled, as runnable probes: `x x OP_NOTEQUAL`.
_PROBE_EQ = ["OP_1", "OP_1", "OP_NOTEQUAL"]      # 1 != 1 -> false
_PROBE_NE = ["OP_1", "OP_2", "OP_NOTEQUAL"]      # 1 != 2 -> true


def verify() -> list[str]:
    """Check every profile against the reproducible inventory and the live engine.
    Returns a list of problems (empty == every declaration matches reality)."""
    problems: list[str] = []
    inv_disabled = _inventory_disabled()

    for p in all_profiles():
        runner = p.runner()
        ok_eq, st_eq = runner(list(_PROBE_EQ))
        ok_ne, st_ne = runner(list(_PROBE_NE))

        if p.script_posture == "faithful-v0.1":
            # OP_NOTEQUAL must be disabled: the engine fails structurally on it.
            if ok_eq or ok_ne:
                problems.append(f"{p.name}: faithful posture executed OP_NOTEQUAL (should be disabled)")
            if p.disabled_opcodes != inv_disabled:
                problems.append(
                    f"{p.name}: declared disabled {p.disabled_opcodes} != inventory {inv_disabled}")
        else:  # nothing-disabled
            # OP_NOTEQUAL must be re-opened and compute byte inequality.
            if not (ok_eq and ok_ne):
                problems.append(f"{p.name}: nothing-disabled posture failed to run OP_NOTEQUAL")
            elif cast_to_bool(st_eq[-1]) or not cast_to_bool(st_ne[-1]):
                problems.append(f"{p.name}: OP_NOTEQUAL semantics wrong (1!=1 must be false, 1!=2 true)")
            if p.reopened_opcodes != inv_disabled:
                problems.append(
                    f"{p.name}: re-opened {p.reopened_opcodes} != the inventory's disabled set {inv_disabled}")
    return problems


def main() -> int:
    profs = all_profiles()
    print(f"lab rule profiles ({len(profs)}) — NOT money\n")
    for p in profs:
        r = p.rules()
        print(f"  {p.name:22} chain={p.chain:6} script={p.script_posture:16} "
              f"class={p.klass:14} subsidy={r.subsidy_base // r.COIN:>3} coins  halving={r.halving}")
    problems = verify()
    if problems:
        print("\nVERIFY FAILED:")
        for pr in problems:
            print("  -", pr)
        return 1
    print("\nverify: OK — every profile's declared posture matches the inventory and the live engine.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
