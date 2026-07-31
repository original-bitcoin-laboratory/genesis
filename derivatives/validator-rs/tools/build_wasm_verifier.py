#!/usr/bin/env python3
"""Regenerate the self-contained browser verifier `docs/verify.html`.

Builds the `obl-validator` crate to `wasm32-unknown-unknown` (the same consensus core the native node
and `cargo test` use), then inlines the wasm — as base64 — plus a few golden example vectors into the
page template `tools/verify.template.html`. The result runs the real validator client-side with no
server and no dependencies. Requires the wasm target: `rustup target add wasm32-unknown-unknown`.

    python tools/build_wasm_verifier.py

The example block / multisig-spend hexes are read straight from the crate's golden test vectors (which
`cargo test` asserts), so the page's prefilled demos stay in lockstep with the tested core. NOT money.
"""
from __future__ import annotations

import base64
import hashlib
import re
import subprocess
import sys
from pathlib import Path

CRATE = Path(__file__).resolve().parent.parent               # validator-rs/
GENESIS = CRATE.parents[1]                                    # genesis/
TEMPLATE = CRATE / "tools" / "verify.template.html"
OUT = GENESIS / "docs" / "verify.html"
WASM = CRATE / "target" / "wasm32-unknown-unknown" / "release" / "obl_validator.wasm"


def _find(path: Path, pattern: str) -> re.Match:
    m = re.search(pattern, path.read_text(encoding="utf-8", errors="replace"), re.S)
    if not m:
        sys.exit(f"error: expected vector not found in {path.name}")
    return m


def main() -> int:
    subprocess.run(
        ["cargo", "build", "--release", "--target", "wasm32-unknown-unknown"],
        cwd=str(CRATE), check=True,
    )
    wasm = WASM.read_bytes()

    # golden example vectors (the same ones `cargo test` validates)
    block = _find(CRATE / "tests" / "data" / "state_data.rs",
                  r'VALID.*?=\s*&\[\s*\("([0-9a-f]+)"').group(1)
    ms = _find(CRATE / "tests" / "data" / "multisig_data.rs",
               r'"good_2of2",\s*"([0-9a-f]+)",\s*"([0-9a-f]+)",\s*"([0-9a-f]+)"')
    tx, spk, sig = ms.group(1), ms.group(2), ms.group(3)
    ex_sha = "03" + "616263" + "a8" + "20" + hashlib.sha256(b"abc").hexdigest() + "87"  # <"abc"> OP_SHA256 <h> OP_EQUAL

    html = TEMPLATE.read_text(encoding="utf-8")
    subs = {
        "__WASM_B64__": base64.b64encode(wasm).decode(),
        "__EX_BLOCK__": block, "__EX_SIG__": sig, "__EX_SPK__": spk, "__EX_TX__": tx,
        "__EX_SHA__": ex_sha,
    }
    for key, val in subs.items():
        if key not in html:
            sys.exit(f"error: template is missing placeholder {key}")
        html = html.replace(key, val)

    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT.relative_to(GENESIS)}  ({round(len(html)/1024)} KB, wasm {len(wasm):,} B)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
