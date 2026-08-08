# R4-C — a relayed spend of a matured coinbase, between two unmodified 2009 binaries

**Witnessed 6–8 August 2026. Evidence level: JAN09-EXECUTED. NOT money.**

This is the last cell of the R-series. A coinbase output that matured under the client's own
`COINBASE_MATURITY + 20` rule was spent, **relayed across the wire to a second node**, mined into a
block, and independently persisted by both nodes — all on the historical January 2009 `bitcoin.exe`,
byte-identical on both machines and bound to the running processes before and after.

---

## The result, from the raw bytes

```
tx f4309c…    1 input  ->  1 output of 50.00        no change, no fee
              created and sent by node B
              accepted by node A across the network
              mined into block 00000000b4ca03f9151f869b018beb009fc75082cc313385f1345ee3af339bf8
                                                                          (height 122)
```

**Block 122 contains two transactions** — its own coinbase `f14a63…` (50.00) and the spend
`f4309c…`. **Both nodes hold that block and converged on it as the tip.**

## The relay, in the clients' own words

```
nodeB_debug.log:3486   SendMoney: f4309c
nodeB_debug.log:3487   AcceptTransaction(): accepted f4309c
nodeA_debug.log:2616   AcceptTransaction(): accepted f4309c     <- the relay
nodeB_debug.log:3514   AddToWallet f4309c  update                <- on confirmation
```

> **The same transaction id appears in both nodes' logs.** Node B authored it; node A learned of it
> only from the network. That is the tx-relay path exercised on the real binary, not modelled.

**Note for anyone reproducing this:** the R4 runbook suggested grepping for `received tx`. **That
string does not appear** — v0.1 logs transaction acceptance as
`AcceptTransaction(): accepted <txid>`. The runbook has been corrected.

## Chain verification — `derivatives/r4/verify_r4.py`

```
nodeA_blk0001.dat   blocks in file 124   best-chain height 122   orphans 1
nodeB_blk0001.dat   blocks in file 123   best-chain height 122   orphans 0

genesis is the real historical genesis:        True   (000000000019d668…)
every best-chain block has valid PoW:          True
BOTH NODES converged on the same best tip:     True   (00000000b4ca03f9…)
```

**Node A retains one orphan**, `000000000234edf2…`, forked off the best chain at height 13 —
the block it mined and then abandoned during the **R4-B partition**, still on disk. That is why the
two files differ in length by one block while agreeing perfectly on the best chain. *The orphan is
evidence, not noise: it is what a reorganisation leaves behind.*

## ★ Executed-binary binding — one unchanged process, start to finish of R4c

```
                pid     process start (UTC)        pre capture           post capture
nodeA          4468     2026-08-06T01:56:52Z       2026-08-06T01:58:05   2026-08-08T19:00:36
nodeB          7632     2026-08-06T01:57:09Z       2026-08-06T01:58:11   2026-08-08T19:00:50

bitcoin.exe    fbcac071d92e26d82ec917214e334bd43850c0691f113bab1d4741c9bdd30d2d   all four
libeay32.dll   d108cdff2922a60e0054718a84178a40526ba00401fa34a87fb055947c77a182
mingwm10.dll   1badf3972d9a861a69fafb2c5e3282aecc30007b9d51c199806e542b32d7708f
matches oracle: True                                                              all four
```

> **The PID and process start time are identical in the `pre` and `post` records on each node.** It
> is not merely that a matching binary existed on disk — **the same process, launched from that exact
> image, ran continuously for roughly 65 hours and produced these blocks.** *(For what happened
> before that process started, see “The run was interrupted, and resumed” below.)*

This is the evidence the deposit previously lacked: the artifacts are bound to the executing image,
not just to a file in an archive.

## Environment

```
hosts        two VirtualBox guests, obl-r4-node-a / obl-r4-node-b, isolated network 172.20.0.0/24
discovery    mini_ircd.py on node A (0.0.0.0:6667, channel #bitcoin) -- the client's own IRC path
client       bitcoin.exe from the January 2009 archive, C:\obl\bitcoin.exe, unmodified
chain        the real historical genesis; difficulty 1 throughout
```

### The run was interrupted, and resumed

`bitcoin.exe` restarted twice between R4b and the spend — two `Loading addresses… / Done loading`
pairs in the appended `debug.log` on each node. **Cause, on the author's account: the host mini-PC powered down on its own mid-run.** The
guests were restarted and **the nodes resumed exactly where they had stopped** — same datadir, same
chain, blocks continuing straight on from R4b into R4c. *An unplanned power loss followed by a clean
resume is itself a result worth having: the 2009 client recovered its own chain state without
intervention.*

**What this means for the evidence:** the *chain* is continuous (R4c's log begins with R4b's bytes
exactly), but the *process* is not — so the binding pair here brackets the final ~65-hour process,
the one that produced the spend, and does not reach back over R4a/R4b. Those retain their own
earlier binding. **A `pre`/`post` pair is only meaningful across one uninterrupted process.**

**Clock note:** the guests run ~4–5 hours behind the host, so `debug.log` timestamps and the wallet
dates are in guest time, while the binding JSONs record UTC. **A future reader comparing a screenshot
clock against a log line should expect the offset and not read it as an inconsistency.**

## What this establishes — and what it does not

```
ESTABLISHED   a coinbase matured under the client's own MATURITY+20 rule and became spendable
              a transaction was created, signed and broadcast by the real 2009 client
              it CROSSED THE NETWORK and was independently accepted by a second instance
              it was mined into a block and both nodes persisted that block identically
              both nodes ran one unchanged bitcoin.exe THROUGH R4c, bound before and after

NOT           mining across a difficulty RETARGET window -- still exercised in the model only.
ESTABLISHED   The chain never left difficulty 1.
              anything about value. The units are 50.00 of nothing. NOT money.
```

## Reproduce

```bash
python derivatives/r4/verify_r4.py <nodeA>/blk0001.dat <nodeB>/blk0001.dat
grep -n "AcceptTransaction(): accepted f4309c" nodeA/debug.log nodeB/debug.log
sha256sum -c SHA256SUMS
```

**Raw bytes are gitignored** (`r4-evidence/`, cold copy in `OBL-BACKUP/04-evidence/r4-evidence/`).
`EVIDENCE_MANIFEST.json` and `SHA256SUMS` here hash all 104 captured files, including both
`wallet.dat` — **the hashes are published; the bytes never are.** Same discipline as R3.

**The wallets are kept because they are the only artifact that can later prove *who* ran this**: a
`blk0001.dat` can be copied by anyone, but only the key-holder can sign from
`17JDVSXwbQuGMoV8WSokEo52gNrHHcCAQg`, the address that sent `f4309c`.
