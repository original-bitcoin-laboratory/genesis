#!/usr/bin/env bash
# Stage the unmodified v0.1.0 Windows binary + its runtime DLLs for the R3
# isolated-VM run (see docs/R3_HISTORICAL_NODE.md). Copies from the verified,
# extracted tree and writes SHA-256s so hash-anchored bytes go into the VM.
# It does NOT run anything. Requires `extracted/` (run fetch + verify + extract).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/extracted/bitcoin"
OUT="$ROOT/r3-stage"

[ -d "$SRC" ] || { echo "error: $SRC not found — fetch + verify + extract the v0.1.0 archive first" >&2; exit 1; }

mkdir -p "$OUT"
for f in bitcoin.exe libeay32.dll mingwm10.dll readme.txt license.txt; do
  if [ -f "$SRC/$f" ]; then cp "$SRC/$f" "$OUT/"; else echo "warn: missing $f" >&2; fi
done

( cd "$OUT" && python - <<'PY'
import hashlib, pathlib
for p in sorted(pathlib.Path('.').glob('*')):
    if p.is_file() and p.name != 'SHA256SUMS':
        print(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}")
PY
) | tee "$OUT/SHA256SUMS"

echo
echo "Staged to r3-stage/ (gitignored). Copy this folder into the isolated VM."
