# R4 screenshot gallery — the two-node runs as they were operated

75 desktop screenshots of the R4 exercise, from first network bring-up (31 Jul 2026) to the run still
climbing toward coinbase maturity (2 Aug 2026, height 25 / "26 blocks"). They are the **human-readable
layer** over the R4 findings: the load-bearing results are proven from the raw block bytes in the sibling
bundles ([`../2026-08-01-sustained-relay/`](../2026-08-01-sustained-relay/FINDINGS.md) = R4a,
[`../2026-08-02-reorg-partition/`](../2026-08-02-reorg-partition/FINDINGS.md) = R4b) via `verify_r4.py`;
these images corroborate that record and show the operator's-eye view (both VMs' GUIs, the PowerShell
`Get-FileHash` checks, the reorg as the wallet displays it). Every file is hashed in
[`SHA256SUMS`](SHA256SUMS). **NOT money** — isolated network, real genesis, valueless by design.

Both nodes are unmodified 2009 `bitcoin.exe` (sha256 `fbcac071…`) in Oracle VirtualBox VMs
(`obl-r4-node-a` left, `obl-r4-node-b` right) on the air-gapped Internal Network `172.20.0.0/24`.

## Reading the timestamps

**File names carry the host clock, which is authoritative and monotonic** (`YYYY-MM-DD_HHMMSS`). The two
guests run **≈4.5 h behind** the host (a guest showing `23:15 31-07` was captured at host `03:45 01-08`),
and the v0.1 wallet also shows each block's own `nTime`. So order the run by the filename, not by the
clock inside a window. The wallet "matures in *N* blocks" text is v0.1's coinbase-maturity countdown (100
confirmations), not a difficulty or value figure.

## Verified anchors

These frames were read directly and tie to specific facts in the findings:

| Screenshot | Host time | What it shows |
|---|---|---|
| [`2026-07-31/2026-07-31_223114`](2026-07-31/2026-07-31_223114.png) | 31 Jul 22:31 | **Setup / connectivity** — each VM `ping`s the other across `172.20.0.0/24` (A↔B, 0% loss) before any node starts |
| [`2026-08-01/2026-08-01_034539`](2026-08-01/2026-08-01_034539.png) | 1 Aug 03:45 | **R4a byte-identical result** — both nodes' `Get-FileHash blk0001.dat` = `AAF08AA3…6DBEBC4C` (the `aaf08aa3…` in the R4a manifest): the two independent nodes agree on the chain byte for byte |
| [`2026-08-02/2026-08-02_044409`](2026-08-02/2026-08-02_044409.png) | 2 Aug 04:44 | **R4b reorg, as the wallet shows it** — node A's top transaction is `0/unconfirmed — Generated (not accepted)` (its orphaned, self-mined block), both nodes at 16 blocks (height 15) |
| [`2026-08-02/2026-08-02_044538`](2026-08-02/2026-08-02_044538.png) | 2 Aug 04:45 | **R4b `REORGANIZE` confirmed** — `Select-String REORGANIZE C:\obl\debug.log` on node A returns `debug.log:542:*** REORGANIZE ***`, alongside the orphaned-block wallet entry |
| [`2026-08-02/2026-08-02_044616`](2026-08-02/2026-08-02_044616.png) | 2 Aug 04:46 | **R4b on-disk divergence** — post-reorg `Get-FileHash` shows the two nodes' `blk0001.dat` now **differ** (`909852B7…D8DAF0` on A vs `48A84CE7…60BDCD9` on B, the exact values in the R4b manifest): A carries the retained orphan (+223 B = one block) |
| [`2026-08-02/2026-08-02_173207`](2026-08-02/2026-08-02_173207.png) | 2 Aug 17:32 | **Current** — both nodes at **26 blocks** (height 25), node B still `Generating`; node A still retains its reorg orphan at the top of the wallet. The run continues toward R4c's ~101-block coinbase maturity |

## The run, by phase

### `2026-07-31/` — bring-up and first blocks (12 shots, 22:31–23:40 host)
Network connectivity, IRC discovery, and the first mined/relayed blocks between the two unmodified nodes —
the transition from the R3 single-block witness into R4a's sustained mining. Includes the initial wallet
and block-count views as heights 1–3 appear.

### `2026-08-01/` — R4a: sustained and bidirectional (44 shots, 01:48–22:29 host)
The bulk of R4a: both nodes mining and relaying, periodic `Get-FileHash blk0001.dat` checks confirming the
databases stay byte-identical as the chain grows (the byte-identical `AAF08AA3…` anchor at 03:45, and later
the extended bidirectional run whose 14-block chain hashes to `d674d3f6…` — the value seen at the top of
the first 2 Aug frame). This span also covers the run persisting across an unplanned guest restart. Each
node shows blocks it mined and blocks it accepted from the other.

### `2026-08-02/` — R4b reorg and the continued run (19 shots, 02:13–17:32 host)
The R4b sequence at **04:44–04:46**: node A's self-mined height-14 block, the deliberate partition (node
B's cable pulled), node B mining one block ahead in isolation, reconnection driving node A's
`*** REORGANIZE ***` (visible in the wallet as the orphaned `Generated (not accepted)` entry), and the
post-reorg `Get-FileHash` showing the two `blk0001.dat` now differ by exactly one block. The 06:25–17:32
frames are the **post-reorg continuation** — both nodes back in agreement and mining on toward coinbase
maturity, reaching 26 blocks (height 25) at the latest capture.

## Provenance boundary

These are unretouched desktop captures, hashed in `SHA256SUMS`. The **raw** evidence they depict — both
nodes' `blk0001.dat` and `debug.log` — stays under the gitignored `r4-evidence/` and is what `verify_r4.py`
actually re-derives the results from; the screenshots are corroborating documentation, not the primary
record, and (like the raw bytes) are part of the archival deposit. A screenshot is a *witness of what the
operator saw*, never an authority (`common/AUTHORITY.md`); where a screenshot and the verified bytes could
ever disagree, the bytes win.
