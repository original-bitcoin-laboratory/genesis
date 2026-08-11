# Blocks 51–60 — ten blocks, a byte-exact extension, and the post-binding gap closed

**Captured 10–11 August 2026** from `bitcoin-node-1`, continuing
[`2026-08-11-blocks29-50`](../2026-08-11-blocks29-50/FINDINGS.md). **The chain is now 61 blocks deep.**

## The chain, parsed independently

`blk0001.dat` was parsed byte-by-byte — magic-delimited records (`f00ba726`), each header
double-SHA'd — rather than reading the client's own status line. **The client's opinion of its chain
is not evidence about its chain.**

```
file                13,658 B   sha256 9d7de18d69e8805572dee802241a690b0b6f19fc6f71143dcc6ff3b817c47324
blocks parsed       61         heights 0 - 60
genesis             00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a   MATCHES
height 50           000000000fbf84aa2b5f84ecb7c274f0dd0def53606a7f44b705ad1e2c32ca1d   MATCHES prior run's tip
height 51           00000000133cef4e7762c70b59941813b17b01c3332f208a4a4517b8076c7e90   first new block
tip (height 60)     0000000099bb637d64c1a5625088cbd88697890559a8737295ce41cf695dc1e4
every prev-hash     links to its predecessor                                            PASS
every block         hash < the difficulty-1 target, nBits 0x1d00ffff                    PASS  61/61
every timestamp     monotonically non-decreasing                                        PASS
```

**Ten new blocks (51–60)**, each real difficulty-1 work of about 2³² hashes. Tip mined
**2026-08-11 14:53:37 UTC**. **Which chain this is** — read the coinbase of block 0, never the
version number:

```
The Times 03/Aug/2026 Toll of schooling 'straitjacket'
```

### ★ This run proves the extension at the byte level, not the hash level

Earlier rounds established continuity by comparing block hashes one by one. **That is sound but
weaker than what the files themselves allow**, so this round checked the stronger property directly:

```
previous blk0001.dat                              11,428 B
this blk0001.dat                                  13,658 B
growth                                             2,230 B  = 223 B x 10 blocks (215 block + 8 magic/len)

first 11,428 bytes of the new file, sha256   04513181fdd5a992b8600a88ab7c73443b2568588f8935b693cc64d83c5ddbfa
the ENTIRE previous file,           sha256   04513181fdd5a992b8600a88ab7c73443b2568588f8935b693cc64d83c5ddbfa
```

> **The new file *contains* the old file, unaltered, as a literal byte prefix.** Not "the same
> blocks" — **the same bytes.** Nothing before height 51 was rewritten, reordered or re-encoded.
> **An append-only store that is checkably append-only.**

## The binary that mined them, bound to the run

```
oracle_sha256                c3f15fc5b7bd80f4d08fe5ff356256214734eb1a3e4a7c953c9e8fc8453d2c7d
bitcoin_exe_matches_oracle   TRUE, in both the pre and the post capture
binding_method               live-process-image
pre    2026-08-10T22:05:30Z  pid 3040   create_time 2026-08-10T22:05:11Z
post   2026-08-11T19:29:38Z  pid 3040   create_time 2026-08-10T22:05:11Z
```

**The binary is byte-identical to `dist/bitcoin-0.1.3/bitcoin.exe` in this repository** — and to
`dist/bitcoin-0.1.4` and `dist/bitcoin-0.1.5`, which ship the same executable. **So the VM is
labelled 0.1.3 and is running exactly what 0.1.5 ships.**

### ★★ The limit recorded in the previous round is closed, and the evidence is the PID

Round 29–50 had to report that its `post` capture came from a *restarted* client — PIDs 4492 and
5048 — so the pair could not attest continuous execution. **The routine was amended to require
capturing `post` while the client is still running, then exiting.** This run followed it:

```
PREVIOUS ROUND    pre pid 4492  ->  post pid 5048     two processes. Continuity NOT attested
THIS ROUND        pre pid 3040  ->  post pid 3040     one process, same create_time.  ATTESTED
```

**And the debug log independently confirms the ordering** rather than relying on the JSON alone: its
final lines are `StopNode()` / `DBFlush(true)` / **`Bitcoin exiting`** — the clean exit happened
*after* the 19:29:38Z post capture, not before it.

> **So the pre/post pair now attests what it was always meant to attest:** that **one single
> process**, running the oracle-matching binary, was alive continuously from 22:05:30Z on 10 Aug to
> 19:29:38Z on 11 Aug — the window in which every one of these blocks was mined. **An amended
> routine that was actually followed the next time, and is verifiable from two independent records.**

## Network behaviour

The debug log covers blocks 2–60 cumulatively (it is appended, never truncated), 45,405 lines:

```
proof-of-work found       59      every accepted block was mined HERE
ProcessBlock: ACCEPTED    59
received: block            0      not one block arrived from the network
received: inv              0
sending: block            60      this node relayed ITS chain outward
```

**All ten new blocks were mined locally. Nothing was accepted from a peer.** The peer remains the
project's own DigitalOcean seed, confirmed live from the host at the time of writing:

```
bitcoin.bitcoin-lab.org  ->  168.144.27.117        DNS
168.144.27.117:18026         TcpTestSucceeded True  (ICMP filtered, as expected on a droplet)
```

### Mining cadence — reported, and deliberately not over-read

```
blocks 51-60      10 blocks over 17.50 h
mean interval    105.0 min      median 68.8 min
min / max         25.6 / 287.6 min
prior run 29-50   mean 68.0 min
```

**The target is 10 minutes and these are nowhere near it, which is expected and not a defect:** v0.1
retargets only every 2016 blocks, so `nBits` is still `0x1d00ffff` at height 60 and will be for a
long time. One VM at difficulty-1 finds a block when it finds one.

> ⚠️ **The apparent slowdown against the previous run is NOT a measurement of anything.** Block
> intervals are exponentially distributed, so a ten-sample mean carries a standard error of about
> 32% — 105 min against 68 min is **under two sigma, comfortably inside noise.** ⇒ **Nothing here
> measures hashrate, and this table must not be cited as if it did.** It is recorded because the raw
> numbers belong in the record, not because they support a conclusion.

## ★★ Cross-implementation validation

**A second implementation, in a different language, pulled these blocks over the network and
validated every one of them.**

```
python -m netnode --chain bitcoin --datadir <EMPTY> --no-listen --connect 168.144.27.117:18026
```

```
the 2009 C++ client, in the VM        61 blocks   blk0001.dat  13,658 B
netnode (Python), on the host         61 blocks   blocks.dat   13,414 B
framing difference                   244 B = 4 bytes x 61 blocks              EXACT
identical block hashes                61 / 61     mismatches: 0
heights 51-60 (this run's new work)   10 / 10     validated independently
height 0    00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a
height 51   00000000133cef4e7762c70b59941813b17b01c3332f208a4a4517b8076c7e90
height 60   0000000099bb637d64c1a5625088cbd88697890559a8737295ce41cf695dc1e4
```

**netnode minted the genesis itself, before connecting to anything**, and only then synced. **It
never read the VM's block file.** The blocks travelled VM → seed → netnode and were validated on
arrival by code that shares no lineage with the 2009 client.

*(The 244-byte difference is framing, not content: the C++ store writes `magic+length+block`,
netnode writes `length+block` — exactly 4 bytes × 61 blocks.)*

> **Scope, stated precisely rather than blurred.** This is cross-**implementation** and
> cross-**network**. It is **not** cross-**machine** in the stronger sense the blocks 5–28 run
> achieved with a genuinely separate third machine — netnode here ran on the host that hosts the VM.
> **The weaker property is named so nobody has to discover it later.**

## Limits, stated plainly

- **Not cross-machine.** See the scope note above.
- **No value.** These coins have never been spent, offered, priced or transferred.
- **One node mining.** Nothing here measures hashrate, difficulty or competitive network behaviour —
  see the warning under *Mining cadence*.
- **IRC bootstrap still dead.** `chat.freenode.net` is hardcoded in `src/irc.cpp` and freenode no
  longer sends the greetings the 2009 client waits for. Peers come from a seeded `addr.dat` plus the
  project's own seed. **A dead rendezvous point is not a broken protocol** — recorded in full in the
  [previous round](../2026-08-11-blocks29-50/FINDINGS.md).

## Files

```
EXECUTED_BINARY_BINDING_bitcoin-node-1_pre.json     the pre capture
EXECUTED_BINARY_BINDING_bitcoin-node-1_post.json    the post capture (same PID -- see above)
SHA256SUMS                                          hashes of everything captured, including the
                                                    bytes held outside this repository
```

**Raw bytes are not in this repository** — `blk0001.dat`, `blkindex.dat`, `wallet.dat`, the debug
log, the executable and 25 screenshots live in the cold backup under
`04-evidence/bitcoin-chain-evidence/2026-08-12-blocks51-60/`, with the wallet in the Tier-1 key
store as `wallet-clean-blk60-20260811.dat`. **Only hashes cross into the repo.** That rule is
enforced by `.gitignore`, not by memory. **40 files were copied and every one re-hashed against its
source: 0 mismatches.**

> ⚠️ **The binding JSON files carry a UTF-8 BOM.** `json.load(open(path))` fails on them at
> character 0. Read them with `encoding="utf-8-sig"`. The files are correct; the naive reader is not.

Related: [`../2026-08-11-blocks29-50/FINDINGS.md`](../2026-08-11-blocks29-50/FINDINGS.md) ·
[`../CORRECTIONS.md`](../CORRECTIONS.md) · [`../../docs/RELEASE_CHECKLIST.md`](../../docs/RELEASE_CHECKLIST.md)
