# R4 findings — two unmodified 2009 nodes: sustained mining, relay, and a reorganisation

Evidence level **JAN09-EXECUTED**: everything here was produced by the unmodified v0.1.0 `bitcoin.exe`
(sha256 `fbcac071…`) running in isolated VirtualBox VMs on the real Bitcoin genesis. Raw bytes
(`blk0001.dat`, `debug.log`) stay under the gitignored `r4-evidence/`; each folder here commits the
write-up, the hashed `EVIDENCE_MANIFEST.json` / `SHA256SUMS`, and a `verify_r4.py` that re-derives the
result from the raw block bytes. **NOT money** — isolated network, real genesis, valueless by design.
See `docs/R4_RUNBOOK.md` for the procedure and `../r3-findings/` for the single-block precursor.

| Run | Milestone | Result |
|---|---|---|
| [`2026-08-01-sustained-relay/`](2026-08-01-sustained-relay/FINDINGS.md) | **R4a** — sustained multi-block mining + relay | node B mined 3 blocks in succession, node A accepted every one; extended bidirectionally to 14 blocks (A↔B), byte-identical `blk0001.dat`, **0 reorgs**, survived a guest reboot |
| [`2026-08-02-reorg-partition/`](2026-08-02-reorg-partition/FINDINGS.md) | **R4b** — a chain reorganisation | nodes partitioned until chains diverged by depth 1; on reconnect node A fired `*** REORGANIZE ***`, orphaned its own height-14 block `000000000234ed…`, adopted node B's taller chain; both converged on tip `000000004e442b…` (height 15). node A `blk0001.dat` = **1 orphan** (and exactly **+223 bytes** = one v0.1 block) vs node B's 0 |

**Still deferred:** **R4c** — a relayed spend of a matured coinbase (needs block ~101, ~a day of
difficulty-1 mining). Already covered headlessly by `derivatives/node` + `derivatives/p2p`.

**Operator's-eye view:** [`screenshots/`](screenshots/INDEX.md) is a 75-frame desktop-capture gallery of the
whole run (31 Jul bring-up → 2 Aug reorg → the run climbing toward maturity at 26 blocks), hashed in its own
`SHA256SUMS` and captioned in `INDEX.md`. It corroborates the byte-level findings above; the raw block bytes
those findings are derived from remain gitignored under `r4-evidence/`.

## Verifying

```bash
# from genesis/, after staging the raw bytes under r4-evidence/<run>/
python r4-findings/2026-08-02-reorg-partition/verify_r4.py \
    r4-evidence/2026-08-02-reorg-partition/nodeA_blk0001.dat \
    r4-evidence/2026-08-02-reorg-partition/nodeB_blk0001.dat
# node A: 17 blocks / 1 orphan / reorg witnessed: True;  node B: 16 / 0;  same best tip: True
```
