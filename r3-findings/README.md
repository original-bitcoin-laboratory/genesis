# R3 findings (committed evidence)

Committed manifests and written conclusions from JAN09-EXECUTED runs. Each run gets
`r3-findings/<run>/` with:

- `EVIDENCE_MANIFEST.json` — SHA-256 of every captured artifact (evidence level
  `JAN09-EXECUTED`).
- `SHA256SUMS` — the same, in checksum format.
- `FINDINGS.md` — the filled-in results (from `../docs/R3_EVIDENCE_TEMPLATE.md`).

The **raw bytes** (`debug.log`, `blk*.dat`, screenshots) live under the gitignored
`r3-evidence/<run>/` and are not committed. Generate a run's manifest with:

    python scripts/capture-evidence.py --run <run>

See `../docs/R3_HISTORICAL_NODE.md` for the run plan and checklist.

## Corrections (13 September 2026)

Recorded here rather than edited into the sets:

- `2026-07-31-twonode-mined-block/EVIDENCE.md` says the manifest's OK lines cover `FINDINGS.md`. The manifests
  list the verifier and the raw captures only; the narrative is not in them.
- `run1/FINDINGS.md` gives coinbase maturity as 100 blocks. The client's own rule is 120
  (`COINBASE_MATURITY` plus the 20-block margin), as `r4-findings/2026-08-06-relayed-spend/` established.
- Where a set says a step was deferred to a Windows-XP guest, the runs were made on Windows 10 guests.

## A statement added 20 September 2026

The block 1 of `2026-07-31-twonode-mined-block/` (`000000005bdcfb22…`) was mined on Bitcoin's own genesis at
difficulty 1, so it is a valid alternative block 1 for the historical chain. It is published so the run can be
checked, and it is inert on the live network: a block at height 1 sits below every checkpoint since 2010 and
under sixteen years of cumulative work, so no current node would follow it. The two VMs were isolated from
the outside network and connected to each other on an internal network (not air-gapped from each other).

