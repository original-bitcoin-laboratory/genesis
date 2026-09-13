# Replay runbook — the corpus against a frozen `bitcoin.exe`

**Goal.** Lift the corpus's expected values from *four reimplementations agree* to *the binary agrees*,
and record what each binary's OpenSSL does with the non-strict DER signatures the corpus leaves as
`expected_binary: null`. NOT money.

There are two binaries worth replaying, and they answer different questions:

| target | binary | OpenSSL | chain | where it is |
|---|---|---|---|---|
| `release-v0.1.x-openssl-1.0.2u` | this lab's release client (`derivatives/bitcoin/`, v0.1 source + nine chain-separation substitutions) | 1.0.2u | Bitcoin (2026): magic `f00ba726`, port 18026, genesis `00000000ad12…` | the mining VM on the mini-PC, `c:\bitcoin\bitcoin-0.1.3\` |
| `2009-fbcac071-openssl-0.9.8` | the unmodified January 2009 `bitcoin.exe` | 0.9.8 | Satoshi's: magic `f9beb4d9`, port 8333, genesis `000000000019d668…` | the R4 appliance `obl-r4-nodes.ova` (two guests; import it to run) |

Same consensus code in both. Where their verdicts differ on the DER probes, that difference is a
consensus-relevant fact about OpenSSL versions and belongs in `RELEASE.txt`.

## The one rule: do not replay against the live 2026 node

The replay mines ~112 blocks in an hour, pays their coinbases to `OP_TRUE`, and spends test outputs.
On the public 2026 chain that would break the chain's stated record (no coin spent, every coin
held by the project's keys) and distort its block tempo. **Replay only against an isolated clone**
of the VM, on a host-only network with no route to the internet or to the VPS seed. The clone's chain
forks privately from the public tip at clone time; the public chain does not see any of it.

## A. Release build — clone the mining VM and isolate it

Everything below is on the mini-PC host, in PowerShell, except the two steps marked *in the guest*.

1. **Get the harness** onto the host: `git clone https://github.com/original-bitcoin-laboratory/genesis.git C:\obl-replay`
   and put the native miner at `C:\obl-replay\derivatives\vectors\replay\miner-rs\target\release\miner.exe`
   (build it there with `cargo build --release` in `replay\miner-rs`, no dependencies, or copy a built one and
   check its hash). Python 3.10+ on the host; no packages needed.
2. **Sanity check:** in `C:\obl-replay\derivatives\vectors`, `python verify_vectors.py --no-model` must end
   with `0 failures`; `.\replay\miner-rs\target\release\miner.exe ("00" * 76) 207fffff` prints a number and,
   on stderr, `SHA-NI` or `portable`.
3. ***In the guest:*** close `bitcoin.exe` cleanly (File → Exit) so its database is flushed. Record
   `Get-FileHash c:\bitcoin\bitcoin-0.1.3\bitcoin.exe` and the `RELEASE.txt` beside it — that is the
   identity of the binary under test; it goes in the results folder.
4. **Clone:** VirtualBox → right-click the VM → Clone → *Full clone*, current machine state, name it
   `obl-replay-clone`. Then restart `bitcoin.exe` in the **original** VM so public mining continues.
5. **Isolate the clone:** clone → Settings → Network → Adapter 1 → *Host-only Adapter*. No NAT, no bridge.
   The clone must not be able to reach `bitcoin.bitcoin-lab.org` or `chat.freenode.net`.
6. **Boot the clone and give it a name to resolve.** ***In the guest***, before starting the client, add to
   `C:\Windows\System32\drivers\etc\hosts` (as administrator):
   ```
   127.0.0.1   chat.freenode.net
   ```
   then `ipconfig /flushdns`. **Without this the client crashes about one second after start** (exception
   c0000005): `irc.cpp` calls `gethostbyname("chat.freenode.net")` and dereferences the result with no NULL
   check, so a guest with no DNS takes an access violation in the IRC thread. That is 2009 behaviour, kept
   as written; the hosts entry makes the name resolve to a port nobody answers, the IRC thread logs
   `IRC connect failed` and returns, and the node runs. Then start `bitcoin.exe` from `c:\bitcoin\bitcoin-0.1.3\`.
   Options → **uncheck Generate Coins**; allow inbound
   TCP 18026 (admin prompt: `netsh advfirewall firewall add rule name="bitcoin 18026" dir=in action=allow protocol=TCP localport=18026`);
   `ipconfig` for the clone's `192.168.56.x` address (CLONE_IP). Check the guest clock is within two hours of the host's.
7. **Connection test** from the host, in `C:\obl-replay\derivatives\vectors`:
   ```
   python -c "import sys; sys.path.insert(0,'replay'); from wire01 import Peer; print(Peer('CLONE_IP', 18026, bytes.fromhex('f00ba726')).their_version)"
   ```
   Expect `{'version': 101, 'services': 1, 'time': …}`. Refused → the firewall rule in step 6.
8. **Run:**
   ```
   python replay\replay.py --chain 2026 --target release-v0.1.3-openssl-1.0.2u --node CLONE_IP --out replay\results\2026-09-DD-release
   ```
   Phases: sync (fetches and validates the whole 2026 chain locally), fund (1 block), mature (100 blocks),
   scripts, checksig, blocks (12 more mined). About an hour with SHA-NI. Interrupted → same command again, it resumes.
   **Stop** if sync reports a block on the node failing the from-spec validator; keep `replay.log`.
9. **Capture:** from the clone, `c:\bitcoin\bitcoin-0.1.3\debug.log` (v0.1 writes it to the directory it was
   launched from) and `%APPDATA%\Bitcoin\blk0001.dat`, into the results folder as `clone-debug.log` and `clone_blk0001.dat`.
10. **Grade:**
    ```
    python replay\grade_replay.py replay\results\2026-09-DD-release\results.json --log replay\results\2026-09-DD-release\clone-debug.log
    ```
11. Bring the results folder back (results.json, replay.log, state.json, the log, the block file, the binary's
    hash and RELEASE.txt). The clone can be deleted afterwards or kept as evidence; the public VM was not touched.

## B. The 2009 binary — import the appliance

Only when the OpenSSL 0.9.8 answer is wanted. Verify `obl-r4-nodes.ova` against `5C37A79E…`, import it
(both guests), snapshot, give node A a second *Host-only* adapter, boot A then B (their hosts files already
map `chat.freenode.net` to node A's `mini_ircd`, which is what keeps the 2009 client from the crash in A.6),
turn Generate Coins off in both, open TCP 8333 in each guest's firewall, and run:

```
python replay\replay.py --chain 2009 --target 2009-fbcac071-openssl-0.9.8 --node A_IP --witness B_IP --out replay\results\2026-09-DD-2009
```

Everything else is as in A, with `C:\obl\debug.log` as the log path. That appliance's chain is the isolated
2009-genesis chain from R3/R4 (height 122 at export), so no isolation step is needed beyond what it already has.

## Reading the outcome

- **Agreement** on the scripts and blocks suites moves those vectors to `JAN09-EXECUTED` for that binary.
- **A disagreement is a finding, not a failure of the run.** Record the binary's verdict; do not change the
  corpus until the cause is understood from `script.cpp` / `main.cpp`.
- The pending signature vectors (`der_trailing_byte`, `der_long_form_length`, `der_r_extra_leading_zero`) have
  **no expected value**. Each target's verdict is recorded under that target's label; `expected_binary` in
  `checksig.json` is reserved for the 2009 binary. If the release build and the 2009 binary differ, say so
  in `RELEASE.txt` — that is the OpenSSL-version dependency made visible.
- Seal every run with `scripts/capture-evidence.py` as in R3/R4, under `r5-findings/`.

## Gotchas

- The harness stamps blocks with the node's own clock (read from its `version` message), so guest/host drift is
  fine up to two hours. Beyond that, fix the guest clock, not the harness.
- `getdata` for a transaction is served from `mapRelay`, which expires after 15 minutes. The harness asks within a
  second; a manual re-check later says "not served" for everything.
- A block rejected in `ConnectBlock` is **erased** by v0.1 (`AddToBlockIndex`, `main.cpp:1107-1113`: from disk
  and from `mapBlockIndex`), so from outside every rejection looks the same as an orphan: not served, not on
  the main chain. Only acceptance is distinguishable by the two signals; the *stage* of a rejection is read
  from `debug.log`. (Later Bitcoin keeps such blocks in the index with zero work; v0.1 does not.)
- v0.1 picks its best chain by **height**, not accumulated work (`main.cpp:1097`).
- Every block the harness mines pays `OP_TRUE`. On an isolated clone that matters to nobody; on the public chain it
  would, which is why the clone is not optional.
- `state.json` is bound to a `--target`; a different target needs a different `--out`.
