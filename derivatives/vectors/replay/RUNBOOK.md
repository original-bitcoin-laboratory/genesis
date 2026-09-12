# Replay runbook — the corpus against the frozen 2009 `bitcoin.exe`

**Goal.** Lift the corpus's expected values from *four reimplementations agree* to *the unmodified
January 2009 binary agrees*, and record what that binary's OpenSSL 0.9.8 does with the non-strict DER
signatures the corpus leaves as `expected_binary: null`. Evidence level target: **JAN09-EXECUTED**.
NOT money.

This is a solo run on the machine that holds the R4 appliance (`obl-r4-nodes.ova`, sha256
`5C37A79E…`). Everything the harness needs is in this directory; nothing in `src/` changes. The run
mines about 112 difficulty-1 blocks on the isolated 2009-genesis chain the appliance carries — with the
native miner on a SHA-NI CPU that is roughly an hour; with the Python fallback it is most of a day.

## 0. What you need

- The appliance imported and both guests bootable (`OVA-RECORD.md`: verify the hash first; node A before B).
- Python 3.10+ on the **host** (the mini-PC). No packages are required for the replay itself; `cryptography`
  lets the harness grade full-vocabulary spends locally as well, which is optional.
- This directory copied to the host: `derivatives/vectors/` (the JSON corpus, `recipes.py`,
  `verify_vectors.py`, and `replay/`).
- The native miner: `replay/miner-rs/target/release/miner.exe`. Build it there with `cargo build --release`
  in `replay/miner-rs/` (no dependencies), or copy the one built on the workspace machine and check its
  hash against the one recorded in the findings. Without it the harness falls back to Python
  automatically.

## 1. Make node A reachable from the host

The R4 guests sit on an **Internal Network** (`obl-r4`), which the host cannot reach. Add a second
adapter rather than changing the first, so the two guests keep seeing each other exactly as before:

```
VirtualBox → obl-r4-node-a → Settings → Network → Adapter 2 → Enable, Host-only Adapter
                                                                (VirtualBox Host-Only Ethernet Adapter)
```

Boot node A, note its host-only address (`ipconfig` in the guest, typically `192.168.56.x`). `bitcoin.exe`
listens on every interface on port 8333, and **`IsRoutable` only affects what the node advertises over IRC,
not whom it accepts**, so an inbound connection from `192.168.56.1` is fine. Do the same on node B if you
want it as the relay witness (`--witness`); it is optional.

Confirm from the host:

```
python -c "import sys; sys.path.insert(0,'replay'); from wire01 import Peer; p=Peer('192.168.56.101'); print(p.their_version)"
```

You should see `{'version': 101, 'services': 1, 'time': ...}`.

## 2. Turn the guests' own miners off

The replay builds on the current tip and must not race the guests' `/gen` mining. In each node's GUI,
Options → **uncheck Generate Coins**, and leave it unchecked for the duration.

## 3. Run

```
cd derivatives/vectors
python replay/replay.py --node 192.168.56.101 --witness 192.168.56.102 --out replay/results/2026-MM-DD
```

Phases, each resumable from `--out/state.json` if interrupted:

| phase | what happens | mining |
|---|---|---|
| sync | fetches the node's whole main chain and validates every block with the from-spec validator | — |
| fund | one block whose coinbase carries an output per vector: 136 script outputs, 17 signature outputs, 6 P2PK outputs | 1 block |
| mature | 100 blocks so the funding outputs pass the coinbase-maturity walk | 100 blocks |
| scripts | one spend per EvalScript vector, empty scriptSig; verdict = does the node serve it back from its relay pool | — |
| checksig | one spend per signature variant, re-signed against the real prevout | — |
| blocks | the 19 block cases rebuilt on the live tip; verdict = in the index (getdata) and on the main chain (getblocks) | 12 blocks |

If `sync` reports that a block the node holds fails the local validator, **stop**: either the validator is
wrong or the chain is not what the appliance record says. Do not continue on a chain you cannot validate.

## 4. Capture and grade

Copy `C:\obl\debug.log` from node A (and B) into the results directory, then:

```
python replay/grade_replay.py replay/results/2026-MM-DD/results.json --log replay/results/2026-MM-DD/nodeA-debug.log
```

The grader prints, per suite, how many vectors the binary agreed with, every disagreement, the binary's
verdict on each `expected_binary: null` signature vector, and whether each rejected block case produced its
exact `main.cpp` error string in the log.

Then run `python scripts/capture-evidence.py --run <date>-binary-replay` as in R3/R4 to hash the results,
the logs and both nodes' `blk0001.dat` into a sealed findings set, and file it under `r5-findings/`.

## 5. Reading the outcome honestly

- **Agreement** on the scripts and blocks suites moves those vectors from `MODEL` to `JAN09-EXECUTED`.
- **A disagreement is a finding, not a failure of the run.** Record the binary's verdict; do not change the
  corpus until the cause is understood from `script.cpp`/`main.cpp`. Four reimplementations agreeing with
  each other and disagreeing with the original is exactly what this replay exists to detect.
- The pending signature vectors (`der_trailing_byte`, `der_long_form_length`, `der_r_extra_leading_zero`)
  have **no expected value**. Whatever OpenSSL 0.9.8 does with them is the answer; the grader prints it and
  a later export freezes it into `checksig.json` as `expected_binary`.
- The release build (`derivatives/bitcoin/`, linked against OpenSSL 1.0.2u) can be replayed the same way
  on its own chain. **If it differs from the 2009 binary on the DER vectors, that is a consensus-relevant
  difference between the two OpenSSL versions**, and it belongs in `RELEASE.txt`.

## Gotchas

- The harness reads the node's clock from its `version` message and stamps blocks with that clock, so a
  guest whose clock drifts from the host is fine. A guest clock **more than two hours behind the host** is
  not: fix the guest clock, not the harness.
- `getdata` for a transaction is served from `mapRelay`, which expires entries after 15 minutes. The
  harness asks within a second of sending; a manual re-check later will say "not served" for everything.
- Blocks rejected in `ConnectBlock` stay in the node's index with zero work (`AddToBlockIndex` runs before
  `SetBestChain`). The harness expects exactly that: `in_index: true, in_main: false`. It is not a bug in
  either side.
- Every block the harness mines pays its coinbase to `OP_TRUE`. Anyone can spend those outputs; there is
  nothing to steal because there is nothing of value.
