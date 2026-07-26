#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

command -v curl >/dev/null 2>&1 || {
  echo "error: curl is required" >&2
  exit 1
}

fetch() {
  local url="$1"
  local output="$2"
  mkdir -p "$(dirname "$output")"
  if [[ -f "$output" ]]; then
    echo "exists: $output"
    return
  fi
  echo "fetch:  $url"
  curl --fail --location --proto '=https' --tlsv1.2 \
    --output "$output.part" "$url"
  mv "$output.part" "$output"
}

# OBL-JAN09 - January 2009 Bitcoin v0.1.0 first public release
fetch "https://cdn.nakamotoinstitute.org/code/bitcoin-0.1.0.rar" \
      "artifacts/jan09/bitcoin-0.1.0.rar"
fetch "https://cdn.nakamotoinstitute.org/code/bitcoin-0.1.0.tgz" \
      "artifacts/jan09/bitcoin-0.1.0.tgz"

echo
echo "Artifacts acquired. Run: python scripts/verify-artifacts.py"
