# What this directory does and does not contain

`SHA256SUMS` lists **every artifact of this run**, including the raw captures — the nodes'
`blk0001.dat` block files and `debug.log` transcripts. Those raw captures are **not in this
repository.** Running `sha256sum -c SHA256SUMS` on a fresh clone therefore reports

```
sha256sum: <capture>: No such file or directory
<capture>: FAILED open or read
```

**That is the file being absent, not the evidence being wrong.** Every entry in `SHA256SUMS` is a raw
capture, so on a fresh clone every line reports `No such file`; the manifest is the commitment, and
`FINDINGS.md` cites the files by hash.

## Why they are not here

The captures are taken from live VM disks. They carry node wallets, local addresses and host
network detail, so they are published only after sanitisation, as a versioned deposit accompanying
the write-up rather than as loose files in a source tree. The sanitised deposit is
`obl-historical-binary-evidence.zip` (47 entries, no images); the manifest here is the commitment its
contents are checked against: the hashes were fixed when the run happened and are in this repo's history, so the
captures cannot be quietly swapped for different ones later. A hash published before its file is
released is the useful ordering — the reverse would prove nothing.

## Checking the run without them

`FINDINGS.md` cites its evidence by file and line. The verifiers in the later directories of this series
(`verify_*.py`) reproduce a result from `blk0001.dat` alone: point one at these captures once you have them
and it rebuilds the block index, follows the best chain by height, and re-derives the finding independently
of any log text.
