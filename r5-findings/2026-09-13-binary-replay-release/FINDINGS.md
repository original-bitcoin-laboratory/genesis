# R5 — the conformance corpus replayed against the release client, over its own wire protocol

**Witnessed 13 September 2026. Evidence level: EXECUTED on the release `bitcoin.exe`
(`c3f15fc5…`, this lab's Bitcoin (2026) client: the January 2009 source with nine chain-separation
substitutions, linked against OpenSSL 1.0.2u). Not `JAN09-EXECUTED` — that name is reserved for
the unmodified 2009 binary, which has not been replayed yet. NOT money.**

Every vector in `derivatives/vectors/` that can be expressed as a transaction or a block was
submitted to a running copy of the release client and the client's verdict was read back from the
client itself. **The binary agreed with the corpus on every vector: 136/136 scripts, 17/17
signatures, 19/19 block cases**, and each of the 19 rejected blocks produced its exact `main.cpp`
error string in the client's own `debug.log`.

---

## Environment

| Field | Value |
|---|---|
| Date / operator | 13 September 2026 (01:20–04:02 local), the lab's operator, on the machine that hosts the mining VM |
| Node under test | `bitcoin.exe` sha256 `c3f15fc5b7bd80f4d08fe5ff356256214734eb1a3e4a7c953c9e8fc8453d2c7d` (release v0.1.3 = v0.1.4 = v0.1.5 bytes), launched from `c:\bitcoin\bitcoin-0.1.3\` |
| Where it ran | a **full VirtualBox clone** of the mining VM, taken after a clean exit of the client, with its only adapter switched to Host-only: no route to the internet, to the VPS seed, or to IRC |
| Chain | Bitcoin (2026), genesis `00000000ad12…`, magic `f00ba726`, port 18026; the clone's chain was the public chain at **height 861** at clone time |
| The one guest-side change | a hosts-file line `127.0.0.1 chat.freenode.net`, without which the 2009 code crashes on start (see *Divergences*) |
| Generate Coins | off; the client's own miner never fired during either run (last `proof-of-work found` in the log predates the session) |
| Harness | `derivatives/vectors/replay/` at genesis commits `30bba3c` (run 1) and `cdd819e` (run 2); native miner `miner-rs`, SHA-NI |
| Verdict channels | a transaction: served back by `getdata` from the client's relay pool (`mapRelay`), one round trip with a sentinel block; a block: served by `getdata` (in `mapBlockIndex`) and listed by `getblocks` from the previous tip (on the main chain) |

The public mining VM and the public chain were never touched. The clone's chain forked privately from
height 861 and ended at height 966.

## What the client was given, and what it said

**Sync.** The harness fetched the clone's whole chain (862 blocks, heights 0–861) and validated every
block with the from-spec validator in `verify_vectors.py`. All 862 passed.

**Funding and maturity.** One block whose coinbase carries 159 outputs — one per script vector, one per
signature vector, six pay-to-pubkey outputs for the block cases — then 100 further blocks so those
outputs pass the client's coinbase-maturity walk (`ConnectInputs`, `main.cpp:822-826`). Heights 862–962,
all accepted and connected.

**Scripts (136).** Each vector's script was placed as the scriptPubKey of a funding output and spent
with an **empty scriptSig**, so `VerifySignature` evaluated `OP_CODESEPARATOR || script` exactly as
`script.cpp:1126` does. The client accepted the spend when the corpus said `valid: true` and refused it
otherwise — **136/136**. The 15 refusals are in the log as `ConnectInputs() : <txid> VerifySignature
failed`.

**Signatures (17).** Each variant was re-signed against the real prevout with the corpus's published
test keys and spent. **14/14 graded vectors agreed**, including high-S, the hash-type-byte cases,
compressed keys, and all three CHECKMULTISIG layouts (the leading dummy that the off-by-one pop
consumes; sig order relative to key order). The three vectors the corpus deliberately leaves without a
binary expectation — `der_trailing_byte`, `der_long_form_length`, `der_r_extra_leading_zero` — were
**all rejected**. That is OpenSSL 1.0.2u's strict DER (the January 2015 change in the 1.0.1k/1.0.2
line), now recorded per vector in `checksig.json` under `witnessed` for this target. What OpenSSL
0.9.8 does with the same bytes is the 2009 binary's question and remains open.

**Blocks (19).** The client's own log, run 2, in order (`run2/clone-debug.log`, lines 578514–579070):

```
AddToBlockIndex: new best=0000000090c69d  height=964     v_spend_with_fee        accepted
AddToBlockIndex: new best=0000000028e173  height=965     v_chain_in_block        accepted
AddToBlockIndex: new best=000000007be559  height=966     v_coinbase_underclaim   accepted
ERROR: ConnectInputs() : b5fa40 prev tx already used at (nFile=1, nBlockPos=218425, nTxPos=218581)   double_spend
ERROR: ConnectInputs() : f9504e nTxFee < 0                                                            inflation
ERROR: ConnectInputs() : tried to spend coinbase at depth 0                                           immature
ERROR: ConnectInputs() : 362023 VerifySignature failed                                                bad_sig
ERROR: CheckBlock() : hashMerkleRoot mismatch                                                         bad_merkle
ERROR: CheckBlock() : hash doesn't match nBits                                                        bad_pow
ERROR: CheckBlock() : more than one coinbase                                                          two_coinbases
ERROR: CheckBlock() : first tx is not coinbase                                                        first_tx_not_coinbase
ERROR: AcceptBlock() : block's timestamp is too early                                                 timestamp_too_early
ERROR: CTransaction::CheckTransaction() : txout.nValue negative                                       negative_output
ERROR: CTransaction::CheckTransaction() : coinbase script size                                        coinbase_script_too_short
ERROR: CTransaction::CheckTransaction() : prevout is null                                             prevout_null_in_noncoinbase
ERROR: AddToBlockIndex() : ConnectBlock failed        (main.cpp:953 is silent)                        coinbase_overclaim
ERROR: AcceptBlock() : incorrect proof of work                                                        wrong_nbits
ERROR: CheckBlock() : nBits below minimum work                                                        nbits_below_minimum
ProcessBlock: ORPHAN BLOCK, prev=43c56caa9c1262                                                       orphan
```

Each rejected block was rejected at the stage the corpus predicts, with the string the corpus
predicts. `v_chain_in_block` — a transaction spending an output created earlier in the **same
block** — had never been exercised on a binary before; it is accepted, which confirms the same-block
read-back through `CDiskTxPos` (`main.cpp:938-946`) on the file just written.

## Verification from the raw bytes

`clone-blk0001.dat` from each run, parsed by its v0.1 layout and fed to the from-spec validator with
no knowledge of the harness:

```
run1   973 records -> 964 accept, 4 side, 5 reject   tip height 963  0000000072d023   (the fee block)
run2   981 records -> 967 accept, 4 side, 10 reject  tip height 966  000000007be559   (the underclaim block)
```

The tips equal the client's `new best` lines. The "reject" records are the blocks v0.1 erased in
place after a `ConnectBlock` failure (`EraseBlockFromDisk`), which the parser meets as zeroed
regions; the "side" records are run 1's two stale-parent blocks and their kin (next section).

## Divergences, surprises, and the harness's own errors

1. **The 2009 code crashes on start when `chat.freenode.net` does not resolve.** The clone, cut off
   from DNS, died about one second after a clean start with exception c0000005 at image offset 0x5378
   (Windows Error Reporting, five identical records). Disassembly of the release binary places that
   address in `ThreadIRCSeed`: `gethostbyname` returns NULL, and `irc.cpp` dereferences it
   (`mov eax,[eax+0xc]`, the `h_addr_list` field). A hosts-file line pointing the name at 127.0.0.1
   is the whole workaround; the IRC thread then logs `IRC connect failed` and returns. The R3/R4
   guests never met this only because their hosts files pointed the name at `mini_ircd`. Recorded in
   the release-text template.
2. **Run 1's two "accept" disagreements were the harness's, not the client's.** The harness's local
   validator used the lab's Python model for signatures; on a host without the `cryptography`
   package the model's lazy import failed inside the check, the hook reported "invalid", the local
   tip fell behind the client's, and the next two cases were built on a stale parent. The client did
   the right thing with them — side blocks at equal height, then `Reorganize` attempts whose
   `ConnectBlock` failures it reported as such. Fixed (`cdd819e`): the from-spec engine verifies
   signatures itself, and the local validator follows the client's tip. Run 2 is the clean run.
3. **A 32-bit nonce space has no solution about a third of the time**, at any target. The first run
   attempt stopped on the funding block for that reason; the harness now varies the coinbase's extra
   nonce as v0.1's own miner does.
4. **v0.1 erases a block whose `ConnectBlock` fails** — from disk and from `mapBlockIndex`
   (`main.cpp:1107-1113`) — and chooses its best chain by **height** (`main.cpp:1097`). Later Bitcoin
   keeps such a block in the index with zero work. The corpus's validator and the harness's prediction
   model were corrected to the 2009 behaviour.
5. `ConnectInputs()` error lines carry a six-hex transaction id after the colon; the grader tolerates it.

## What this does and does not establish

- **Established:** the release client — the v0.1 consensus code as this lab compiles and runs it —
  agrees with the corpus's 317 vectors wherever a vector can be put to it over the wire, and the
  from-spec validator agrees with that client on the entire public chain and on both runs' block
  files. The corpus is therefore a faithful description of this binary's behaviour on those surfaces.
- **Not established:** anything about OpenSSL 0.9.8. The three non-strict DER verdicts above belong to
  1.0.2u. The unmodified 2009 `bitcoin.exe` in the R4 appliance is the only oracle for that column,
  and `expected_binary` in `checksig.json` stays null until it is run.
- **Not covered by the replay by construction:** the wall-clock rules (`nTime <= now + 2h`), retarget
  boundaries inside a chain, reorganisations between competing valid branches, `nLockTime`/`IsFinal`.

## Evidence

Raw bytes stay under the gitignored `r5-evidence/2026-09-13-binary-replay-release/`; their SHA-256
digests are in `SHA256SUMS` and `EVIDENCE_MANIFEST.json` beside this file. `bitcoin.exe` is the tested
binary itself. `run1/` and `run2/` each hold the harness's `results.json`, `replay.log` and
`state.json`, and the clone's `clone-debug.log` and `clone-blk0001.dat` as copied out after that run.
The public repository carries hashes and this account, not the files.
