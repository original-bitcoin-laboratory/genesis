# The retrofit atlas — where each consensus rule came from, dated to the commit

**20 September 2026.** One section per rule that Bitcoin acquired after the January 2009 release, or
carried from it: the commit that introduced the rule, on the `s_nakamoto` lineage of `bitcoin/bitcoin`;
its message, verbatim; what its diff does, by the lines it adds and removes; the copy the duplicated
2010 lineage carries; what the record argues; and what has been executed. The rows of
`CONSTITUTION-REGISTER.md` (`OBL-C-`) are the index of this document; the notes it cites carry the
detail for the four rules already written up.

Every commit below was read from GitHub's record of `bitcoin/bitcoin` on 20 September 2026, by
listing the commits that touch a file in a date window and reading each commit's patch. Where a
commit is dated here, the date is the author date on the copy that carries the `git-svn-id` trailer
(`docs/BITCOIN-GIT-HISTORY-PROVENANCE.md` explains why that copy is cited).

Cite; do not characterise. This document records what the messages say against what the diffs do.
It does not say why.

> ### What is already known, and what this document adds
>
> **The events are known.** The 2010 hardening, the March 2013 fork, BIP 66, the alert system's
> retirement: each is documented by a BIP, a release note or an alert page, cited in its section.
>
> ```
> ALREADY DOCUMENTED    the block-size and script-limit commits      (docs/MAX-BLOCK-SIZE-RETROFITTED.md,
>                                                                     docs/SCRIPT-LIMITS-RETROFITTED.md)
>                       the value-overflow fix                       (derivatives/overflow/, BIP-free: block 74638)
>                       the March 2013 fork                          (BIP 50)
>                       strict DER                                   (BIP 66)
>                       the alert system's retirement                (bitcoin.org alert page, dated updates)
>
> ADDED HERE            the origin commit, message and diff for:  cumulative-work chain selection (25 Jul 2010),
>                         time-based nLockTime (29 Oct 2009), the transaction-size rule (25 Aug and 13 Sep 2010),
>                         IsStandard (7 Dec 2010), the alert system (25 Aug 2010), CScriptNum (26 Mar 2014)
>                       that the register's earlier date for the transaction-size rule (a790fa46f, 30 Sep 2010)
>                         was a move of the function, not its origin: corrected below
>                       the message_match value for every rule, in one place, with the denominator
>                       the lineage copy of each 2009-2010 origin commit
> ```
>
> **No priority is claimed.** The commits are public to anyone who reads them.

---

## The chronology, in one table

| date (UTC) | commit | author string | rule | message describes the change? |
|---|---|---|---|---|
| Jan 2009 | v0.1 release, `main.h:17` | — | `MAX_SIZE = 0x02000000` (32 MiB) as a block ceiling — inherited | — |
| 2009-10-29 | `dd519206a` (r18) | `s_nakamoto` | time-based `nLockTime`: the 500,000,000 split | yes ("non-final tx locktime changes") |
| 2010-07-15 | `a30b56ebe` | `s_nakamoto` | `MAX_BLOCK_SIZE = 1000000`, miner-only | no |
| 2010-07-17 | `ae922a36a` (r107) | `s_nakamoto` | hard-coded checkpoints at 11111, 33333, 68555 | yes ("security safeguards") |
| 2010-07-25 | `3b7cd5d89` (r109) | `s_nakamoto` | best chain by cumulative work, not height | no |
| 2010-07-29 | `757f0769d` | `s_nakamoto` | script element, size, stack and numeric caps | no |
| 2010-07-31 | `6ff5f718b` (r121) | `s_nakamoto` | op-count limit (200); script-size cap 20,000 → 10,000 | yes ("additional security limits") |
| 2010-08-15 | `d4c6b90ca` | `s_nakamoto` | output value bounds and the output-sum check (named `MoneyRange` in `05454818d`, four days later) | yes |
| 2010-08-15 | `4bd188c43` | `s_nakamoto` | disabled opcodes; element and numeric caps tightened; checkpoint at 74000 | no |
| 2010-08-19 | `05454818d` (r140) | `s_nakamoto` | transaction replacement by `nSequence` disabled | no |
| 2010-08-25 | `401926283` (r142) | `s_nakamoto` | alert system; per-transaction 32 MiB size check | yes / no |
| 2010-09-07 | `f1e1fb4bd` (r148) | `s_nakamoto` | 1 MB block validity rule from block 79,401; `MAX_BLOCK_SIGOPS` | no |
| 2010-09-13 | `3df62878c` (r154) | `s_nakamoto` | per-transaction size bound lowered to `MAX_BLOCK_SIZE` | no |
| 2010-09-19 | `172f00602` (r156) | `s_nakamoto` | the 1 MB test moved into `CheckBlock`, replacing the 32 MiB test; the 79,400 gate removed for size and sigops | no |
| 2010-12-07 | `a206a2398` (r197) | `gavinandresen` | `IsStandard` (policy) | yes |
| 2010-12-12 | `97ee01ad8` (r199) | `s_nakamoto` | relay requires the fee; free transactions rate-limited (policy) | yes |
| 2011-07-09 | `aa496b75c` | Wladimir J. van der Laan | the split named `LOCKTIME_THRESHOLD` (no rule change) | yes |
| 2013-03-15 | `8bd028818`, `fc6deb521` | Gavin Andresen | the written response to the Berkeley DB lock rule nobody wrote | yes |
| 2014-03-26 | `48d8eb184` … `05e3ecffa` (PR 3965) | Cory Fields | `CScriptNum` replaces `CBigNum` in script arithmetic (no rule change) | yes |
| 2015-01-13 | `80ad135a5`, `5a47811da` (PR 5713) | Pieter Wuille | BIP 66: DER strictness written into consensus, out of OpenSSL | yes |
| 2016-03-21 | PR 7692 (merge `29b2be6ad`) | BtcDrak, Thomas Kerin | alert system removed (Core 0.13.0) | yes |

Thirteen rules have an origin commit in the record (the 32 MiB ceiling is the release's own); the
introducing message describes the change for seven of them and does not for six. Added later on 20 September:
`172f00602` (19 September 2010, r156, message "only accept transactions sent by IP address if -allowreceivebyip is
specified") replaced `CheckBlock`'s 32 MiB `MAX_SIZE` test with the 1 MB `MAX_BLOCK_SIZE` test and removed the
`nHeight > 79400` gate from the size and sigop rules, twelve days after they entered; from that commit the 32 MiB
constant bounds only network messages (`net.h`) and block files. Rows `OBL-C-0001`, `0004` and `0006` carry it; the
signed note of 19 September does not, and is not edited. The register prints
the same tally with its denominator every time it runs (`python scripts/check_register.py`).

---

## 1. `MAX_SIZE = 0x02000000` — the ceiling the origin carried (`OBL-C-0006`)

The January 2009 release rejects a block whose serialised size, or transaction count, exceeds
32 MiB: `main.h:17` defines the constant and `CheckBlock` tests it (`docs/MAX-BLOCK-SIZE-RETROFITTED.md`,
finding `OBL-F-0016`). It is the rule the 1 MB limit later narrowed. Kind: consensus. Argument:
inherited. Grade: `JAN09-SOURCE`.

## 2. Time-based `nLockTime` — the 500,000,000 split (`OBL-C-0007`)

**The origin has height-only locks.** The repository's first commit (`e071a3f6c`, 30 August 2009,
`VERSION = 105`, the 0.1.5 source) reads, in `main.h`:

```
bool IsFinal() const
{
    if (nLockTime == 0 || nLockTime < nBestHeight)
        return true;
```

**The split enters in `dd519206a`** (SVN r18, 2009-10-29T02:52:48Z, `s_nakamoto`). Message, verbatim:

```
addr relaying fixes, proxy option and privacy patches, detect connect to self, non-final tx locktime changes, fix hide unconfirmed generated
```

The diff adds, in `main.h` (the hunk in full; an earlier text of this section quoted its first and last lines as if adjacent):

```
+        // Time based nLockTime implemented in 0.1.6,
+        // do not use time based until most 0.1.5 nodes have upgraded.
+        if (nBlockTime == 0)
+            nBlockTime = GetAdjustedTime();
+        if (nLockTime == 0)
+            return true;
+        if (nLockTime < (nLockTime < 500000000 ? nBestHeight : nBlockTime))
```

A lock below 500,000,000 is a height; at or above it, a Unix time. The message names "non-final tx
locktime changes": it describes the change. The number itself, 500,000,000 (5 November 1985 00:53:20
UTC as a Unix time), is not argued for in the commit. The source comment attributes the change to a
version, 0.1.6, between the 0.1.5 the record starts from and the next release, and gives a reason for
deferring the time-based form: until most 0.1.5 nodes have upgraded. The same commit adds to
`AcceptTransaction` in `main.cpp` a refusal of any `nLockTime` above `INT_MAX`, "To help v0.1.5 clients
who would see it as negative number. please delete this later."

Two later commits touch the check without changing the rule: `2c06be915` (2010-08-03, "new safety
feature displays a warning message and locks down RPC if it detects a problem that may require an
upgrade -- version 0.3.8") compares against a block height passed in rather than the global
`nBestHeight`; `aa496b75c` (2011-07-09, Wladimir J. van der Laan, "remove magic number: change threshold
for nLockTime to constant") names the number `LOCKTIME_THRESHOLD`.

- **Kind:** consensus. **message_match:** `true`. **Argument:** not-in-record for the threshold's
  magnitude; the diff's comment states a reason for the deferral.
- **Witness:** `OBL-F-0002` — the January 2009 source has no threshold and the laboratory's temporal
  port runs the height-only rule (`derivatives/temporal/`). Grade: `JAN09-SOURCE` + `MODEL`.
- **Lineage:** `cc0b4c3b6`, same timestamp, author string `s_nakamoto`, no trailer.

## 3. Best chain by cumulative work, not height (`OBL-C-0008`)

**The origin selects by height.** First commit, `main.cpp:1097`:

```
if (pindexNew->nHeight > nBestHeight)
```

**The change is `3b7cd5d89`** (SVN r109, 2010-07-25T16:45:21Z, `s_nakamoto`; 18 files, +405 −137).
Message, verbatim:

```
Gavin Andresen's JSON-RPC HTTP authentication,
faster initial block download
-- version 0.3.3
```

The diff adds `CBigNum bnChainWork` to `CBlockIndex` and a `GetBlockWork()` method (`main.h`), a global
`bnBestChainWork` (`main.cpp`), computes each index entry's work as its parent's plus its own on
connection and on load (`main.cpp`, `db.cpp`), and replaces the selection test:

```
-    if (pindexNew->nHeight > nBestHeight)
+    if (pindexNew->bnChainWork > bnBestChainWork)
```

Neither line of the message mentions chain selection or work.

- **Kind:** consensus (which chain a node follows). **message_match:** `false`. **Argument:**
  not-in-record.
- **Witness:** `OBL-F-0001` — under the January rule a challenger branch at height 125 with work 250
  beats the incumbent at height 122 with work 262 (`paper-artifacts/height-vs-work.json`). Grade: `MODEL`.
- **Lineage:** `40cd03694`, 2010-07-26T17:40:05Z, author string `Satoshi Nakamoto`, no trailer; 12 files,
  +93 −25. This is one of the eight pairs whose copies differ (`docs/BITCOIN-GIT-HISTORY-PROVENANCE.md`);
  the chain-selection change is present in both copies.

## 4. The alert system (`OBL-C-0009`)

**Introduced in `401926283`** (SVN r142, 2010-08-25T00:05:37Z, `s_nakamoto`). Message, verbatim (two lines):

```
alert system
-- version 0.3.11
```

The diff adds the `CAlert` message type, its hard-coded verification key, and the safe-mode behaviour
that restricts RPC when an alert applies. Not a block-validity rule: a network message that any node
accepts from anyone holding one private key.

**Retired, in four dated steps** (the bitcoin.org alert page "Alert System Retirement", whose dated
updates are the record cited here; and `bitcoin/bitcoin` pull request 7692):

- 2016-03-21: PR 7692 "Remove p2p alert system" merged (`29b2be6ad`, Wladimir J. van der Laan; commits by
  BtcDrak and Thomas Kerin, 6–18 March 2016, among them `1b77471bd` "Remove alert keys" and `6601ce508`
  "protocol.h/cpp: Removes NetMsgType::ALERT", 18 March, Thomas Kerin); shipped in Bitcoin Core 0.13.0.
- 2017-01-19: the final alert broadcast, overriding all others and displaying "Alert Key Compromised".
- 2017-03-08: Bitcoin Core 0.14.0 released with that final alert hard-coded.
- 2018-07-03: the key and the alert system's vulnerabilities published.

- **Kind:** policy (network-wide message; not consensus). **message_match:** `true` for the
  introduction; the removal's title describes the removal. **Argument:** not-in-record at
  introduction; the retirement page states its reasons.
- **Witness:** none applies; the rule decides no block's validity.
- **Lineage:** `522dfe342`, 2010-08-28T00:51:52Z, author string `Satoshi Nakamoto`, no trailer.

## 5. The transaction-size rule — two steps, and a correction (`OBL-C-0010`)

**Step 1, 32 MiB per transaction, in `401926283`** (the alert-system commit above). Its diff adds to
`CTransaction::CheckTransaction` in `main.h`:

```
+        if (::GetSerializeSize(*this, SER_DISK) > MAX_SIZE)
+            return error("CTransaction::CheckTransaction() : size limits failed");
```

`f1e1fb4bd` (2010-09-07, "cleanup, …") changes the serialisation flag to `SER_NETWORK`, same constant.

**Step 2, 1 MB per transaction, in `3df62878c`** (SVN r154, 2010-09-13T22:14:24Z, `s_nakamoto`).
Message, verbatim:

```
reorganize BitcoinMiner to make it easier to add different SHA256 routines
```

The diff changes the bound in `main.h`:

```
+        if (::GetSerializeSize(*this, SER_NETWORK) > MAX_BLOCK_SIZE)
```

**The correction.** `CONSTITUTION-REGISTER.md` (19 September 2026) and this laboratory's notes dated
this rule to `a790fa46f`, 30 September 2010. That commit moves `CheckTransaction` from `main.h` to
`main.cpp` with the check unchanged; it is not the origin. The origin is the two commits above.
Recorded here and in the register's row; the earlier text is not rewritten.

- **Kind:** consensus. **message_match:** `false` (both steps). **Argument:** not-in-record.
- **Witness:** open — a transaction between 1 MB and 32 MiB submitted to the January client and to a
  build carrying `3df62878c` would show the narrowing executed; no artifact does this yet. Grade:
  `DESCENDANT`.
- **Lineage:** `401926283` as in section 4; `3df62878c` has a second copy `71cc095cb` at the same
  timestamp that also carries the trailer.

## 6. `IsStandard` — a policy, entered as one (`OBL-C-0011`)

**Introduced in `a206a2398`** (SVN r197, 2010-12-07T13:43:31Z, `gavinandresen`; 6 files, +49 −11).
Message, verbatim:

```
IsStandard() check for CScripts: only relay/include in blocks CScripts we can understand.
```

The diff adds `bool IsStandard(const CScript& scriptPubKey)` in `script.cpp`, matching a script
against a fixed set of templates; `CTransaction::IsStandard()` in `main.h`, which applies it to every
output; and in `main.cpp`, in the mempool path:

```
+    if (!IsStandard() || GetSigOpCount() > 2 || ::GetSerializeSize(*this, SER_NETWORK) < 100)
```

`97ee01ad8` (2010-12-12, `s_nakamoto`, "added some DoS limits, removed safe mode") adds a second
`if (!IsStandard())` in `main.cpp`. A non-standard transaction is not relayed or mined by a node
applying the check; a block containing one is valid.

- **Kind:** policy. **message_match:** `true`. **Argument:** cited — the message states the reason
  ("CScripts we can understand").
- **Witness:** `OBL-F-0036` — the January memory-pool path, ported, relays a hash-lock transaction
  (`OP_SHA256 <h> OP_EQUAL`) that the `a206a2398` clause refuses as nonstandard, and `CheckTransaction`
  accepts it in both eras (`derivatives/origin_policy/is_standard.py`). Grade: `MODEL`. Until 20 September
  2026 this cell cited `OBL-F-0010`, the release build executing non-template scripts; that is the script
  engine, the consensus side, and not this policy.
- **Lineage:** no second copy within nine days of the same first line.

## 7. `CScriptNum` — the numeric type after the numeric cap (`OBL-C-0012`)

The four-byte cap on numeric operands is a 2010 rule and is entered under `OBL-C-0002`
(`4bd188c43`, 2010-08-15, "misc changes", `nMaxNumSize = 4`). The 2014 change replaces the type that
holds those operands, `CBigNum` over OpenSSL's `BIGNUM`, with a class of the same semantics:

- `48d8eb184` "script: add CScriptNum class", `27bff74e3` "script: switch to CScriptNum usage for
  scripts", `4f497cd97`, `05e3ecffa` "script: remove bignum dependency" (all 2014-03-26, Cory Fields),
  with tests `90320d677`, `b1fdd5475` (2014-04-22); pull request 3965 "Remove bignum dependency for
  scripts", merged 2014-05-09 (`1c0319bb2`).

- **Kind:** consensus (script arithmetic), with the rule unchanged by these commits: the change is in
  which code enforces it. **message_match:** `true`. **Argument:** cited — the pull request's title
  states the reason, removing a third-party library from the validation path.
- **Witness:** `OBL-F-0003` covers the element and stack caps of the same 2010 commits; `OBL-F-0034`
  executes the numeric cap (a 9-byte operand accepted by v0.1, rejected by the 4-byte cap; operands,
  not results), added 20 September 2026 after a clean-room reproduction pointed out the gap. Grade:
  `DESCENDANT` + `MODEL`.

## 8. Berkeley DB lock limits — the rule nobody wrote (`OBL-C-0013`)

**The rule had no commit.** Every node before 0.8 stored the block index in Berkeley DB with a
lock table configured by the application; BIP 50 (assigned 2013-03-20) states the consequence:

> Bitcoin versions prior to 0.8 configure an insufficient number of Berkeley DB locks to process large
> but otherwise valid blocks.

> With the insufficiently high BDB lock configuration, it implicitly had become a network consensus
> rule determining block validity (albeit an inconsistent and unsafe rule, since the lock usage could
> vary from node to node).

**The failure:** the bitcoin.org alert "11/12 March 2013 Chain Fork Information" records that a
0.8.0 miner created a block at height 225,430 that earlier versions rejected, forking the chain, and
that large pools were asked to return to 0.7 so one chain remained.

**The written response, four days later** — `8bd028818` (2013-03-15T17:10:34Z, Gavin Andresen).
Message, verbatim:

```
CheckBlock rule until 15-May for 10,000 BDB lock compatibility
```

The diff adds to `CheckBlock` in `src/main.cpp`:

```
+    // Special short-term limits to avoid 10,000 BDB lock limit:
+    if (GetBlockTime() > 1363039171 && // 11 March 2013, timestamp of block before the big fork
+        GetBlockTime() < 1368576000)  // 15 May 2013 00:00:00
+    {
+        // Rule is: #unique txids referenced <= 4,500
+        // ... to prevent 10,000 BDB lock exhaustion on old clients
...
+        if (nTxids > 4500)
+            return error("CheckBlock() : 15 May maxlocks violation");
```

`fc6deb521` (same day, "Before 15 May, limit created block size to 500K") bounds the blocks a node
creates; 0.8.1 was released the same day (`34d62a8ef`). BIP 50 records the end of the episode: on 16
August 2013 block 252,451 was accepted by the network, forking unpatched nodes off.

- **Kind:** emergent. **message_match:** `true` (for the written rule; the emergent rule has no
  message). **Argument:** accidental. **Failure cited:** block 225,430, 11 March 2013.
- **Witness:** `OBL-F-0025` — a block referencing 4,501 distinct transaction ids passes v0.1's size
  and count clauses and fails the 0.8.1 clause inside its window; the same block passes after 15 May
  2013, and a block with 4,499 ids passes throughout (`derivatives/emergent/bdb_locks.py`). Grade:
  `DESCENDANT` + `MODEL`.

## 9. OpenSSL's DER parsing — the second rule nobody wrote (`OBL-C-0014`)

**The rule had no commit.** The January 2009 client hands every signature to OpenSSL, and what
OpenSSL accepts is what the chain accepts. BIP 66 (Pieter Wuille, assigned 2015-01-10) states it:

> Bitcoin's reference implementation currently relies on OpenSSL for signature validation, which
> means it is implicitly defining Bitcoin's block validity rules.

> Until recently, OpenSSL's releases would accept various deviations from the DER standard and accept
> signatures as valid. When this changed in OpenSSL 1.0.0p and 1.0.1k, it made some nodes reject the
> chain.

**The written rule** — pull request 5713 "Implement BIP66": `80ad135a5` (2015-01-13, Pieter Wuille,
"Change IsDERSignature to BIP66 implementation", `src/script/interpreter.cpp`, +63 −63) and
`5a47811da` ("BIP66 changeover logic"); merged 2015-02-03 (`41e6e4cab`). Deployment reuses BIP 34's
thresholds for block `nVersion = 3`: enforced from the block at which 750 of the preceding 1,000 are
version 3; version-2 blocks rejected from 950. Strict DER had been relay policy since 0.8.0 (BIP 66,
Compatibility).

**The activation:** the bitcoin.org alert "Some Miners Generating Invalid Blocks" (2015-07-04) records
that the 950-of-1,000 threshold was reached, that a miner produced an invalid version-2 block at about
02:10 UTC on 4 July 2015, and that pools building on unvalidated headers extended it.

- **Kind:** emergent. **message_match:** `true` (for the written rule). **Argument:** accidental, and
  the written rule cites its failure. **Failure cited:** OpenSSL 1.0.0p and 1.0.1k changing what they
  accept (BIP 66, Motivation).
- **Witness:** `OBL-F-0025` — BIP 66's function, ported line for line, passes the corpus's seven
  strict signatures and fails its three probes (a long-form length, a redundant pad, a byte before
  the flag), each of which a BER-tolerant reader recovers to an (r, s) that verifies under the vector's
  own key over its own signature hash (`derivatives/emergent/der_strictness.py`, `test_emergent.py`);
  `OBL-F-0010` — the OpenSSL 1.0.2u of the laboratory's release build rejects the three. That is the
  rejection side. The acceptance side, that OpenSSL 0.9.8 on the 2009 binary accepts them, has no
  artifact at any grade and stays open. Grade: `EXECUTED (release build)` + `MODEL`, rejection side.

## 10. Transaction replacement by sequence number — shipped, then disabled (`OBL-C-0015`)

**The origin has it.** `CTransaction::IsNewerThan` (`main.h:408`) compares two transactions with the
same inputs by their sequence numbers, and `AcceptTransaction` (`main.cpp:428–446`) accepts a newer
version of a transaction it already holds, erasing the old one ("Allow replacing with a newer version
of the same transaction"). That is the machinery under the author's contract ideas; the December 2010
post on fee-based replacement (mirror post 534: "You intentionally write a double-spend. You write it
with the same inputs and outputs, but this time with a fee.") describes a later design for the same
mechanism that the record does not implement.

**Disabled in `05454818d`** (SVN r140, 2010-08-19T22:43:19Z, `s_nakamoto`; 5 files, +126 −62).
Message, verbatim:

```
block index checking on load, extra redundant checks, misc refactoring
```

The diff adds, at the top of the conflict branch:

```
+            // Disable replacement feature for now
+            return false;
```

and leaves the replacement code below it in place, unreachable. The message names three things;
none of them is this.

- **Kind:** policy (memory pool). **message_match:** `false`. **Argument:** not-in-record.
- **Witness:** `OBL-F-0028` — the January port accepts the newer version and erases the old; the
  0.3.11 port refuses every conflict (`derivatives/origin_policy/replacement.py`). Grade:
  `JAN09-SOURCE` + `MODEL`.
- **Lineage:** `7a37c906a`, 2010-08-28, author string `Satoshi Nakamoto`, no trailer.

## 11. Hard-coded checkpoints (`OBL-C-0016`)

**The origin names no block but the genesis.** Its `AcceptBlock` follows proof of work and ancestry.

**Introduced in `ae922a36a`** (SVN r107, 2010-07-17T23:51:16Z, `s_nakamoto`; +20 −7). Message,
verbatim:

```
security safeguards,
limited addr messages
-- version 0.3.2
```

The diff adds to `AcceptBlock`:

```
+    // Check that the block chain matches the known block chain up to a checkpoint
+    if (pindexPrev->nHeight+1 == 11111 && hash != uint256("0x0000000069e2...7c1d"))
+        return error("AcceptBlock() : rejected by checkpoint lockin at 11111");
```

with the same for 33333 and 68555. `813505cc1` (2010-07-27, a message about Crypto++ and SHA-256
speed) adds 70567; `4bd188c43` (2010-08-15, "misc changes") adds 74000 and folds the five into one
test. The author's post of that evening, during the overflow incident, calls the last one "the most
recent security lockin" (`docs/INCIDENT-2010-08-15.md`).

- **Kind:** consensus (a chain that does not pass through the named blocks is rejected).
  **message_match:** `true` for the first commit, `false` for the two that extended it. **Argument:**
  not-in-record.
- **Witness:** `OBL-F-0029` — a block at height 11111 with another hash: the January port accepts,
  the 0.3.2 port rejects (`derivatives/origin_policy/checkpoints.py`). Grade: `JAN09-SOURCE` + `MODEL`.
- **Lineage:** `4110f33cd`, 2010-07-19, author string `Gavin Andresen`, no trailer.

## 12. The fee rule: a build-and-send policy, then a relay gate (`OBL-C-0017`)

**The origin's rule** is `GetMinFee` (`main.h:504`): one cent (`CENT = 1,000,000` satoshi) per started
kilobyte, and zero for a transaction under 10,000 bytes when the discount applies. The miner applies
the discount to the first 100 transactions of a block it builds (`main.cpp:2250`); the wallet applies
it when it sends (`main.cpp:2577`). A received transaction is not tested for its fee, and a block is
valid whatever its transactions paid.

**The relay gate is `97ee01ad8`** (SVN r199, 2010-12-12T18:20:36Z, `s_nakamoto`; +37 −40). Message,
verbatim:

```
added some DoS limits, removed safe mode
```

The diff adds to `AcceptToMemoryPool`:

```
+        // Don't accept it if it can't get into a block
+        if (nFees < GetMinFee(1000))
+            return error("AcceptToMemoryPool() : not enough fees");
+
+        // Limit free transactions per 10 minutes
+        if (nFees < CENT && GetBoolArg("-limitfreerelay"))
...
+            if (nFreeCount > 150000 && !IsFromMe())
+                return error("AcceptToMemoryPool() : free transaction rejected by rate limiter");
```

By then `GetMinFee` (`main.h:576` at that commit) also carries a dust clause (a one-cent fee if any
output is under one cent) and a price that rises as the block being built passes half of
`MAX_BLOCK_SIZE_GEN`.

- **Kind:** policy, on both sides. **message_match:** `true`. **Argument:** cited (the message names
  the class of change; no incident is named).
- **Witness:** `OBL-F-0030` — the January port relays anything; the 0.3.19 port refuses a 26,500-byte
  fee-less transaction and the 602nd free 250-byte transaction in a ten-minute window
  (`derivatives/origin_policy/fees.py`). Grade: `JAN09-SOURCE` + `MODEL`.

## 13. The op-count limit — the fifth script cap, dated (`OBL-C-0002`)

`docs/SCRIPT-LIMITS-RETROFITTED.md` dates four caps to `757f0769d` and leaves the op-count limit "noted but not
dated". Neither that commit nor `4bd188c43` carries it.

**Introduced in `6ff5f718b`** (SVN r121, 2010-07-31T19:15:48Z, `s_nakamoto`; 6 files, +39 −24). Message,
verbatim (four lines):

```
fixed segfault in bignum.h,
additional security limits,
refactoring
-- version 0.3.7
```

The diff adds to `EvalScript` in `script.cpp`:

```
+    int nOpCount = 0;
...
+            if (opcode > OP_16 && nOpCount++ > 200)
```

and lowers the script-size cap installed two days earlier:

```
-    if (script.size() > 20000)
+    if (script.size() > 10000)
```

`f1e1fb4bd` (2010-09-07, section 5's "cleanup," commit) rewrites the test as `if (opcode > OP_16 && ++nOpCount > 201)`,
the same boundary (201 counted opcodes pass, the 202nd fails); `a790fa46f` (2010-09-30) and `5cbf75324`
(2010-10-19) add the keys of a `CHECKMULTISIG` to the count (`nOpCount += nKeysCount`).

- **Kind:** anti-DoS. **message_match:** `true` ("additional security limits" names the class). **Argument:**
  not-in-record (no failure named, no magnitude argued).
- **Witness:** `OBL-F-0035` — 201 counted opcodes pass and 202 fail on the ported rule; pushes and
  `OP_1`–`OP_16` do not count (`derivatives/script_limits/`). Grade: `MODEL`.
- **Lineage:** no second copy within nine days of the same first line.

## 14–18. The four rules already written up

| rule | row | note |
|---|---|---|
| `MAX_BLOCK_SIZE = 1000000` — constant 15 Jul 2010, validity rule 7 Sep 2010 from block 79,401 | `OBL-C-0001` | `docs/MAX-BLOCK-SIZE-RETROFITTED.md` |
| script element, size, stack and numeric caps — 29 Jul 2010, tightened 15 Aug 2010; the op count, 31 Jul 2010, in section 13 | `OBL-C-0002` | `docs/SCRIPT-LIMITS-RETROFITTED.md` |
| output value bounds and the output-sum check — 15 Aug 2010, block 74638 (named `MoneyRange` four days later) | `OBL-C-0003` | `derivatives/overflow/README.md` |
| `MAX_BLOCK_SIGOPS` — 7 Sep 2010 | `OBL-C-0004` | `docs/MAX-BLOCK-SIZE-RETROFITTED.md` |
| disabled opcodes — 15 Aug 2010 | `OBL-C-0005` | `docs/SCRIPT-LIMITS-RETROFITTED.md` |

---

## Method

```bash
# every commit touching a file in a window, with author string, date and message
gh api "repos/bitcoin/bitcoin/commits?path=main.h&since=2010-07-01T00:00:00Z&until=2010-09-30T23:59:59Z&per_page=100"
# a commit's message, statistics and patch
gh api repos/bitcoin/bitcoin/commits/3b7cd5d89a226426df9c723d1f9ddfe08b7d1def
# a file as it stood at a commit
gh api "repos/bitcoin/bitcoin/contents/main.h?ref=e071a3f6c" -H "Accept: application/vnd.github.raw"
```

Each rule's origin was found by listing the commits that touch `main.h`, `main.cpp` or `script.*` in
a window and reading every patch for the first added line that carries the rule; the window was then
widened until the first commit's own copy of the file showed the rule absent. The reference for a
2009–2010 commit is the copy with the `git-svn-id` trailer; the other copy is recorded under Lineage. Where
both copies carry the trailer (SVN r148–r157), the reference is the copy on the chain the r158 trailer commit
`a790fa46f` descends from (`docs/BITCOIN-GIT-HISTORY-PROVENANCE.md`, revision 2).
The later rules are dated by their pull requests' commits and merge dates; a merge is cited by the merge commit
on `master`, read from the repository's history, and not by the sha the pull-request API reports as
`merge_commit_sha`, which for a merged request is a test merge GitHub computes.

## Limits of this document

```
NOT a claim about intent    no statement about why any message reads as it does
NOT complete                the rules named in the register's target list are covered, and three
                            policies of the origin (replacement, checkpoints, fees); rules added after
                            2015 (BIP 65, 68, 112, 113, 141 and later) are not entered
BOUNDED by the record       GitHub's copy of bitcoin/bitcoin on 20 September 2026; the history can be
                            rewritten by its owners, so a re-run is dated
WITNESS gaps stated         the transaction-size rule has no executed witness; the DER rule's
                            acceptance side waits on the 2009 binary
```

**Corrections, 20 September 2026, from two adversarial reviews.** The merge commits of PR 7692, PR 5713 and PR 3965 had been cited as `9e17aac6b`, `bd03a1cb9` and `681f02551`, the `merge_commit_sha` values of GitHub's pull-request records; none is on the repository's history. They are `29b2be6ad`, `41e6e4cab` and `1c0319bb2`. The 18 March 2016 commit of PR 7692 is Thomas Kerin's, not BtcDrak's. `401926283`'s message is two lines, quoted here as one. The `dd519206a` hunk was quoted as two adjacent lines; it is seven, and the omitted comment line gives a reason. Section 13 (the op-count limit) is new. Section 6's witness and section 9's grade wording are corrected as marked. The earlier text is kept in this repository's history.

**Corrections to this document are published, dated, and not made silently.**
