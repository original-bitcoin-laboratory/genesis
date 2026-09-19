# Start here

The Original Bitcoin Laboratory makes the earliest Bitcoin code run, so that a claim about what
Bitcoin originally did can be checked by executing it rather than by citing someone. Its findings are
statistical and machine-verifiable, graded by their evidence, and draw no conclusion beyond them.

**What it is not.** Not money: no unit on any chain here was sold, priced, allocated or transferred to
a third party. The two reconstructions (`NOV08-X`, `JAN09-X`) are the laboratory's subject; the third
chain, Bitcoin (2026), runs the January 2009 client on a genesis of its own, is not a reconstruction of
anything, and its author "Satoshi Nakamoto" is a 2026 AI agent — a program, not a person, and not the
historical Satoshi. Nothing here recommends changing any rule of any Bitcoin. Not advice, no warranty
([RIGHTS.md](RIGHTS.md)).

**Five findings to read first**, by register ID:

- `OBL-F-0013` — the 1 MB block-size limit entered in two steps: a constant on 15 Jul 2010 that only
  the miner honoured, and a validity rule on 7 Sep 2010 under the message "cleanup", from block 79,401.
  The January 2009 release already rejected blocks over 32 MiB. [The note](docs/MAX-BLOCK-SIZE-RETROFITTED.md)
- `OBL-F-0003` — Bitcoin's script resource limits arrived on 29 Jul 2010 under a makefile commit
  message; the January 2009 interpreter runs a 600-byte element and a 1500-deep stack.
  [The note](docs/SCRIPT-LIMITS-RETROFITTED.md)
- `OBL-F-0009` — two unmodified January 2009 binaries mine, relay, reorganise and spend a matured
  coinbase across the wire, witnessed and hashed. [R4](r4-findings/2026-08-06-relayed-spend/FINDINGS.md)
- `OBL-F-0001` — v0.1 selects the best chain by height, not cumulative work.
  [The artifact](paper-artifacts/height-vs-work.json)
- `OBL-F-0010` — a 323-vector conformance corpus replayed over the wire against the release client:
  136/136 scripts, 17/17 signature checks, 19/19 blocks agree. [R5](r5-findings/2026-09-13-binary-replay-release/FINDINGS.md)

**Where every rule came from:** [docs/CONSENSUS-ATLAS.md](docs/CONSENSUS-ATLAS.md), one section per consensus rule
with its origin commit and message, indexed by [CONSTITUTION-REGISTER.md](CONSTITUTION-REGISTER.md) (`OBL-C-0001` …).

**One command that reproduces something** (Python 3.12, no network):

```bash
python scripts/verify_genesis.py    # re-mints both experimental genesis blocks from source and checks the pinned hashes
```

**Everything else.** The full list of findings, with grades and artifacts, is
[FINDINGS-REGISTER.md](FINDINGS-REGISTER.md); cite the ID. The evidence grades are defined in
[docs/EVIDENCE_POLICY.md](docs/EVIDENCE_POLICY.md). The website version of this page is
[bitcoin-lab.org/about.html](https://bitcoin-lab.org/about.html). The reconstruction itself is under
`derivatives/`, the November 2008 edition in the sibling `pre-genesis` repository, and the thesis,
governance and conformance matrices in `common`.
