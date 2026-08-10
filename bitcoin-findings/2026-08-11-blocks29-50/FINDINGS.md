# Blocks 29–50 — twenty-two blocks, and a post-binding taken after the client had already exited

**Captured 9–11 August 2026** from `bitcoin-node-1`, continuing
[`2026-08-10-blocks5-28`](../2026-08-10-blocks5-28/FINDINGS.md). **The chain is now 51 blocks deep.**

## The chain, parsed independently

`blk0001.dat` was parsed byte-by-byte — magic-delimited records (`f00ba726`), each header
double-SHA'd — rather than reading the client's own status line. **The client's opinion of its chain
is not evidence about its chain.**

```
file                11,428 B   sha256 04513181fdd5a992b8600a88ab7c73443b2568588f8935b693cc64d83c5ddbfa
blocks parsed       51         heights 0 - 50
genesis             00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a   MATCHES
height 1            000000007beb32b8380089595a91261a5ce4fbd4ece0cd661683cb1ce81e407c   MATCHES
height 28           000000009b6d2e544e07e799362bd62d4a83dfb6146aa7d3be43ee16d800a4a8   MATCHES prior run's tip
height 29           000000005d1babdd909102e1abaa14886096ad8bdc3b3b5a86ea9289e099e995   first new block
tip (height 50)     000000000fbf84aa2b5f84ecb7c274f0dd0def53606a7f44b705ad1e2c32ca1d
every prev-hash     links to its predecessor                                            PASS
every block         hash < the difficulty-1 target, nBits 0x1d00ffff                    PASS  51/51
```

**The first 29 block hashes are identical to the previous run's file, one by one.** This extends that
chain; it does not replace it. **Twenty-two new blocks (29–50)**, each real difficulty-1 work of
about 2³² hashes. Tip mined **2026-08-10 21:23:48 UTC**.

**Which chain this is** — read the coinbase of block 0, never the version number:

```
The Times 03/Aug/2026 Toll of schooling 'straitjacket'
```

## The binary that mined them, bound to the run

```
oracle_sha256                c3f15fc5b7bd80f4d08fe5ff356256214734eb1a3e4a7c953c9e8fc8453d2c7d
bitcoin_exe_matches_oracle   TRUE, in both the pre and the post capture
binding_method               live-process-image
pre    2026-08-09T23:23:22Z  pid 4492
post   2026-08-10T21:36:19Z  pid 5048
```

**The binary is byte-identical to `dist/bitcoin-0.1.3/bitcoin.exe` in this repository** — and to
`dist/bitcoin-0.1.4` and `dist/bitcoin-0.1.5`, which ship **the same executable**. `git diff
Bitcoin-v0.1.3..Bitcoin-v0.1.5 -- derivatives/bitcoin/src/` is **empty**: those releases changed
documentation and verification scripts, never consensus code. **So the VM is labelled 0.1.3 and is
running exactly what 0.1.5 ships.**

## ⚠️ The post binding was taken from a restarted client, and that is a real limit

**What happened, recorded as it happened:** the client was closed, the `post` capture was then run
and **failed** — the capture images a *live process*, and there was no longer a process to image.
The client was restarted, `post` was run again, and the file backups were taken.

**The two PIDs prove it rather than merely describing it: 4492 in the pre capture, 5048 in the
post.** The pre/post pair therefore attests:

```
ATTESTED       the binary at that path hashed to c3f15fc5... at 23:23:22Z on 9 Aug,
               and again at 21:36:19Z on 10 Aug, matching the oracle both times
NOT ATTESTED   that one single process ran continuously between those two moments.
               A same-PID pair would have shown that; this pair cannot
```

**What it does not touch:** the blocks. Their validity does not rest on the binding at all — every
one carries its own proof-of-work and its own link to its predecessor, and all 51 were re-derived
here from the raw file. **The binding answers *which binary*; the chain answers *whether the work is
real*, and it answers for itself.**

> **The routine is being amended, not just noted:** `post` must be captured **while the client is
> still running**, then the client exited. That ordering was already implicit in earlier runs — the
> block-2 findings describe *"the post binding, clean exit, capture, relaunch"* in that order — but
> it was never written down as a requirement, and an implicit ordering is one somebody eventually
> performs in the wrong order.

### ★★ The error was the instrument working, and that is the point worth keeping

`capture_binding.ps1` line 33:

```powershell
$proc = Get-CimInstance Win32_Process -Filter "Name='bitcoin.exe'" | Select-Object -First 1
if (-not $proc) { Write-Error "no running bitcoin.exe found in this guest"; exit 1 }
```

**It exits before writing anything.** With no live process there is no hollow JSON, no file of nulls,
no binding that looks complete and attests to nothing. **The capture refused to manufacture evidence
it could not substantiate, and said so.**

> **Contrast it with what this laboratory measured the same day in a third party's tooling**
> ([entry 88](../../../../bitcoin-origin-claims/88_the-coins-that-were-already-spent.md)): a
> verifier that checks its inputs against its own unvalidated input file and prints
> `ALL CHECKS PASSED` while thirteen of them are provably spent.
>
> **Two instruments, two failures to have the thing they wanted. One stopped. One reported success.**
> An error message from a tool that should have data is worth more than a green tick from a tool
> that never looked.

## Network behaviour — measured, because for the first time there is some

The debug log covers blocks 2–50 cumulatively (it is appended, never truncated):

```
proof-of-work found       49      every accepted block was mined HERE
ProcessBlock: ACCEPTED    49
received: block            0      not one block arrived from the network
received: inv              0
sending: block            52      this node relayed ITS chain outward
```

**All twenty-two new blocks were mined locally. Nothing was accepted from a peer.**

The peer is `168.144.27.117:18026` — **the project's own DigitalOcean seed**, already named in the
blocks 5–28 cross-validation. 4,424 log lines of repeated connect/disconnect.

### ★ A live demonstration of why the 2009 client adjusts network time carefully

That peer's `version` messages carry **timestamp 0**, producing offsets of about **−1.786 billion
seconds** (≈ −29.77 million minutes):

```
Added time data, samples 2, ip 751b90a8, offset -1786397777 (-29773296 minutes)
```

**It was never applied.** Every such line reports `samples 2`, and v0.1.x only takes the median once
it holds at least five samples. `GetAdjustedTime()` was never poisoned — **and the block timestamps
confirm it independently**, running monotonically to a tip of 2026-08-10 21:23:48 UTC, which is the
real time.

> **Worth keeping as a finding rather than a footnote.** A single peer feeding a nonsense clock is
> exactly the case that guard exists for, and here it is, in a running 2009 client, doing its job.

## Limits, stated plainly

- ~~**No cross-implementation validation for 29–50 yet.**~~ **★ CLOSED the same day — see below.**
- **No value.** These coins have never been spent, offered, priced or transferred.
- **The post-binding gap above.** Not hidden, not minimised.
- **One node mining.** Nothing here measures hashrate, difficulty or competitive network behaviour.

## ★★ Cross-implementation validation — the limit above, closed

**A second implementation, in a different language, pulled these blocks over the network and
validated every one of them.**

```
python -m netnode --chain bitcoin --datadir <EMPTY> --no-listen --connect 168.144.27.117:18026
```

```
the 2009 C++ client, in the VM       51 blocks   blk0001.dat  11,428 B
netnode (Python), on the host        51 blocks   blocks.dat   11,224 B
                                     synced from the seed, 168.144.27.117:18026
identical block hashes               51 / 51     mismatches: 0
heights 29-50 (this run's new work)  22 / 22     validated independently
height 0    00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a
height 29   000000005d1babdd909102e1abaa14886096ad8bdc3b3b5a86ea9289e099e995
height 50   000000000fbf84aa2b5f84ecb7c274f0dd0def53606a7f44b705ad1e2c32ca1d
```

**It minted the genesis itself, before connecting to anything** — deriving
`00000000ad12f3ec…` from the chain parameters alone and confirming it meets difficulty-1 — and only
then synced. **netnode never read the VM's block file.** The blocks travelled VM → seed → netnode,
and were validated on arrival by code that shares no lineage with the 2009 client.

*(The 204-byte size difference is framing, not content: the C++ store writes `magic+length+block`,
netnode writes `length+block` — exactly 4 bytes × 51 blocks. The same arithmetic held at 29 blocks
in the previous run.)*

> **Scope, stated precisely rather than blurred.** This is cross-**implementation** and
> cross-**network**. It is **not** cross-**machine** in the stronger sense the blocks 5–28 run
> achieved, which used a genuinely separate third machine — netnode here ran on the host that hosts
> the VM. The blocks still round-tripped through a remote seed and were validated by an independent
> codebase, which is what the limit was about. **The weaker property is named so nobody has to
> discover it later.**

## Files

```
EXECUTED_BINARY_BINDING_bitcoin-node-1_pre.json     the pre capture
EXECUTED_BINARY_BINDING_bitcoin-node-1_post.json    the post capture (restarted client)
SHA256SUMS                                          hashes of everything captured, including the
                                                    bytes held outside this repository
```

**Raw bytes are not in this repository** — `blk0001.dat`, `blkindex.dat`, `wallet.dat`, the debug
log, the executable and 41 screenshots live in the cold backup under
`04-evidence/bitcoin-chain-evidence/2026-08-11-blocks29-50/`, with the wallet in the Tier-1 key
store. **Only hashes cross into the repo.** That rule is enforced by `.gitignore`, not by memory.

> ⚠️ **The binding JSON files carry a UTF-8 BOM.** `json.load(open(path))` fails on them at
> character 0. Read them with `encoding="utf-8-sig"`. The files are correct; the naive reader is not.

Related: [`../2026-08-10-blocks5-28/FINDINGS.md`](../2026-08-10-blocks5-28/FINDINGS.md) ·
[`../CORRECTIONS.md`](../CORRECTIONS.md) · [`../../docs/RELEASE_CHECKLIST.md`](../../docs/RELEASE_CHECKLIST.md)
