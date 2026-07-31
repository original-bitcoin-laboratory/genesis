#!/usr/bin/env python3
"""Generate the OBL-JAN09 opcode inventory from the extracted v0.1.0 source.

Reproducible R1 artifact: parses the real `opcodetype` enum in `script.h` and the
`case OP_*` execution branches in `script.cpp`'s EvalScript, then emits a
declared-vs-implemented opcode table. Run after fetch + verify + extract:

    python scripts/inventory-symbols.py

Writes inventory/OPCODES.md and inventory/OPCODES.json. The extracted source is
read-only input (gitignored under extracted/); only the generated inventory and
its source hashes are committed.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED = ROOT / "extracted"
OUT_DIR = ROOT / "inventory"


def find(name: str) -> Path:
    hits = sorted(EXTRACTED.rglob(name))
    if not hits:
        sys.exit(f"error: {name} not found under {EXTRACTED} — run fetch + verify + extract first")
    return hits[0]


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _git_commit() -> str | None:
    """The repo commit this inventory was generated at (None outside a checkout)."""
    import subprocess
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT), capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else None
    except OSError:
        return None


def parse_named_enum(lines: list[str], header_re: str) -> list[dict]:
    """Parse a C enum body into ordered entries, evaluating C value semantics."""
    start = next(i for i, l in enumerate(lines) if re.search(header_re, l))
    i = start
    while "{" not in lines[i]:
        i += 1
    i += 1
    entries: list[dict] = []
    values: dict[str, int] = {}
    nextval = 0
    category: str | None = None
    while i < len(lines):
        lineno = i + 1                        # 1-indexed source line of this entry
        s = lines[i].strip()
        i += 1
        if s.startswith("}"):
            break
        if not s:
            continue
        if s.startswith("//"):
            category = s[2:].strip()
            continue
        code = s.split("//")[0].strip().rstrip(",").strip()
        if not code:
            continue
        m = re.match(r"([A-Z][A-Z0-9_]+)\s*(?:=\s*(.+))?$", code)
        if not m:
            continue
        name, expr = m.group(1), m.group(2)
        alias_of = None
        if expr is not None:
            expr = expr.strip()
            if re.fullmatch(r"0x[0-9a-fA-F]+", expr):
                val = int(expr, 16)
            elif re.fullmatch(r"\d+", expr):
                val = int(expr)
            elif expr in values:
                val = values[expr]
                alias_of = expr
            else:
                sys.exit(f"error: cannot evaluate {name} = {expr}")
        else:
            val = nextval
        values[name] = val
        entries.append({"name": name, "value": val, "category": category, "alias_of": alias_of, "_enum_line": lineno})
        nextval = val + 1
    return entries


def main() -> int:
    script_h = find("script.h")
    script_cpp = find("script.cpp")
    h_lines = script_h.read_text(encoding="latin-1").splitlines()
    cpp_text = script_cpp.read_text(encoding="latin-1")

    opcodes = parse_named_enum(h_lines, r"\benum\s+opcodetype\b")
    # SIGHASH lives in an anonymous enum; match its members directly (all are `= value`).
    sighash = [
        {"name": m.group(1), "value": int(m.group(2), 0)}
        for m in re.finditer(r"\b(SIGHASH_[A-Z]+)\s*=\s*(0x[0-9a-fA-F]+|\d+)", "\n".join(h_lines))
    ]

    # Line-track each execution branch so every opcode carries a file:line witness: a real
    # `case OP_X:` (implemented) versus a disabled `//case OP_X` (commented out). setdefault
    # keeps the FIRST occurrence, which is the branch label the case falls through from.
    impl_line: dict[str, int] = {}
    disabled_line: dict[str, int] = {}
    for n, line in enumerate(cpp_text.splitlines(), 1):
        mc = re.search(r"//\s*case\s+(OP_[A-Z0-9_]+)", line)
        if mc:
            disabled_line.setdefault(mc.group(1), n)
            continue
        mi = re.search(r"\bcase\s+(OP_[A-Z0-9_]+)\s*:", line)
        if mi:
            impl_line.setdefault(mi.group(1), n)
    implemented, commented = set(impl_line), set(disabled_line)

    src = {
        "script.h": {"sha256": sha256(script_h), "lines": len(h_lines)},
        "script.cpp": {"sha256": sha256(script_cpp), "lines": cpp_text.count(chr(10)) + 1},
    }
    # per-opcode source witnesses: the declaration in script.h and, when present, the
    # execution (or disabled) branch in script.cpp — each carrying its file's source hash
    # so a single opcode entry is independently checkable against the extracted source.
    for op in opcodes:
        op["evalscript_case"] = op["name"] in implemented
        op["enum_witness"] = {
            "file": "script.h",
            "line": op.pop("_enum_line"),
            "source_sha256": src["script.h"]["sha256"],
        }
        if op["name"] in impl_line:
            op["execution_witness"] = {
                "file": "script.cpp", "line": impl_line[op["name"]],
                "disabled": False, "source_sha256": src["script.cpp"]["sha256"],
            }
        elif op["name"] in disabled_line:
            op["execution_witness"] = {
                "file": "script.cpp", "line": disabled_line[op["name"]],
                "disabled": True, "source_sha256": src["script.cpp"]["sha256"],
            }
        else:
            op["execution_witness"] = None    # push-decoded / template sentinel / reserved: no EvalScript branch
    real = [o for o in opcodes if o["alias_of"] is None]
    impl_count = sum(1 for o in real if o["evalscript_case"])

    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "OPCODES.json").write_text(
        json.dumps(
            {
                "schema": 2,        # 2: each opcode carries enum_witness + execution_witness (file:line)
                "profile": "OBL-JAN09",
                "generated": date.today().isoformat(),
                "generator": {"script": Path(__file__).name, "sha256": sha256(Path(__file__).resolve()), "commit": _git_commit()},
                "sources": src,
                "sighash": sighash,
                "opcodes": opcodes,
                "disabled_commented_out": sorted(commented),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    L = []
    L.append("# OBL-JAN09 — Opcode & SIGHASH inventory")
    L.append("")
    L.append("> **Generated** by `scripts/inventory-symbols.py` from the extracted v0.1.0 source.")
    L.append("> Declaration is from the `opcodetype` enum in `script.h`; **EvalScript case** means an")
    L.append("> execution branch of that opcode is present in `script.cpp`'s `EvalScript` — i.e. it is")
    L.append("> *implemented* (rung 2 of the evidence ladder), not merely declared (rung 1). Reachability")
    L.append("> and consensus-execution are established later (R3–R4).")
    L.append("")
    L.append("## Source provenance")
    L.append("")
    L.append("| File | lines | sha256 |")
    L.append("|---|--:|---|")
    for name, meta in src.items():
        L.append(f"| `{name}` | {meta['lines']} | `{meta['sha256']}` |")
    L.append("")
    L.append("## Signature-hash modes (`script.h`)")
    L.append("")
    L.append("| Mode | value |")
    L.append("|---|--:|")
    for s in sighash:
        L.append(f"| `{s['name']}` | 0x{s['value']:02x} ({s['value']}) |")
    L.append("")
    L.append(f"## Opcodes ({len(real)} distinct values, {len(opcodes) - len(real)} aliases)")
    L.append("")
    L.append(f"**{impl_count}** opcodes have an `EvalScript` execution branch.")
    if commented:
        L.append(f" Explicitly disabled / commented-out in `script.cpp`: {', '.join('`'+c+'`' for c in sorted(commented))}.")
    L.append("")
    L.append("Each opcode carries a `file:line` source witness: `script.h` for its `opcodetype`")
    L.append("declaration and `script.cpp` for its `EvalScript` execution branch (both hashed above).")
    L.append("")
    L.append("| Opcode | hex | dec | category | decl (`script.h`) | EvalScript (`script.cpp`) | note |")
    L.append("|---|---|--:|---|--:|--:|---|")
    for o in opcodes:
        hexv = f"0x{o['value']:02x}" if o["value"] <= 0xFF else f"0x{o['value']:04x}"
        note = f"alias of `{o['alias_of']}`" if o["alias_of"] else ""
        decl = f"L{o['enum_witness']['line']}"
        xw = o["execution_witness"]
        if o["alias_of"]:
            case = ""
        elif xw:
            case = f"L{xw['line']}" + (" (disabled)" if xw["disabled"] else "")
        else:
            case = "—"
        L.append(f"| `{o['name']}` | {hexv} | {o['value']} | {o['category'] or ''} | {decl} | {case} | {note} |")
    L.append("")
    (OUT_DIR / "OPCODES.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    print(f"wrote {OUT_DIR/'OPCODES.md'} and OPCODES.json")
    print(f"  opcodes: {len(real)} distinct (+{len(opcodes)-len(real)} aliases), {impl_count} implemented in EvalScript")
    print(f"  sighash modes: {len(sighash)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
