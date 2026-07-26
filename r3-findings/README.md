# R3 findings (committed evidence)

Committed manifests and written conclusions from JAN09-EXECUTED runs. Each run gets
`r3-findings/<run>/` with:

- `EVIDENCE_MANIFEST.json` — SHA-256 of every captured artifact (evidence level
  `JAN09-EXECUTED`).
- `SHA256SUMS` — the same, in checksum format.
- `FINDINGS.md` — the filled-in results (from `../docs/R3_EVIDENCE_TEMPLATE.md`).

The **raw bytes** (`debug.log`, `blk*.dat`, screenshots) live under the gitignored
`r3-evidence/<run>/` and are never committed. Generate a run's manifest with:

    python scripts/capture-evidence.py --run <run>

See `../docs/R3_HISTORICAL_NODE.md` for the run plan and checklist.
