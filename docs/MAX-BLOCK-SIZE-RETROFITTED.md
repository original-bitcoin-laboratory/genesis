# Bitcoin's 1 MB block-size limit was retrofitted in three steps in 2010

**19 September 2026.** `MAX_BLOCK_SIZE = 1000000` is the rule the 2015–2017 block-size dispute was
fought over. It is commonly dated to a single commit in July 2010. The record shows three commits: a
constant in July that only the miner honoured, a validity rule in September gated at a height, and the
gate's removal twelve days later; none of the three messages describes the change; and the January 2009
release already enforced a block-size ceiling of 32 MiB, thirty-three times the later figure.

This note dates the three steps, gives the method to reproduce the dating, and states what the origin
enforced before them. Findings register: `OBL-F-0013` (the constant and the rule), `OBL-F-0015`
(the sigop limit, same commit as the rule), `OBL-F-0016` (the 32 MB ceiling of v0.1).

> ### What is already known, and what this note adds
>
> **The constant's commit is widely cited.** Public accounts of the limit's history name `a30b56eb`
> as the commit that introduced `MAX_BLOCK_SIZE` on 15 July 2010; the Bitcoin Wiki's page on the
> block-size dispute cites that hash.
>
> ```
> ALREADY DOCUMENTED    a30b56eb, 15 Jul 2010, defines MAX_BLOCK_SIZE = 1000000 in main.h
>
> ADDED HERE            that a30b56eb applies the constant ONLY in the miner (a cap on blocks it builds)
>                       that the VALIDITY rule arrives in a second commit, f1e1fb4b, 7 Sep 2010,
>                         gated on block height > 79,400, in a commit whose message says "cleanup"
>                       that the same second commit installs MAX_BLOCK_SIGOPS
>                       that v0.1's CheckBlock already rejected blocks over MAX_SIZE = 32 MiB
>                       the miner's margin: 10,000 bytes below the cap on 15 Jul, removed on 7 Sep
> ```
>
> **Prior accounts, stated in revision 2.** The two-step shape was published before this note: the
> Bitcoin wiki's *Scalability FAQ* (revision of 16 July 2021) states that "around 15 July 2010" the
> mining code was changed to build no block over 990,000 bytes and that "on 7 September 2010" the
> consensus rules were changed to reject blocks over 1,000,000 bytes above height 79,400, with block
> 79,400 produced on 12 September 2010; a public activation-history gist ("bip-activation-history",
> last updated 17 December 2025) lists the limit as committed 2010-09-07, flag-day 79400 on
> 2010-09-12, buried 2010-09-20. The first text of this note said no public account of the two-step
> shape had been found; that sentence was wrong and is withdrawn. What this note adds beyond those
> accounts is the diff-level attribution: the constant's only use in the miner, the 10,000-byte
> margin, the 32 MiB ceiling the origin already enforced, `MAX_BLOCK_SIGOPS` and the message-size
> cap in the same enforcing commit, the third step of 19 September, and the correction of the
> most-cited page, which names a different second commit (`SECONDARY-SOURCES-CHECKED.md`). The
> search was not exhaustive, and the commits are public to anyone who looks.

---

## The finding

```
Jan 2009      v0.1.0                     CheckBlock rejects a block over MAX_SIZE (0x02000000 = 32 MiB)
15 Jul 2010   a30b56eb   0.3.1           MAX_BLOCK_SIZE = 1000000 DEFINED; used only by the miner
                                         (stops adding transactions at MAX_BLOCK_SIZE - 10000 bytes)
07 Sep 2010   f1e1fb4b   SVN r148        VALIDITY RULE: AcceptBlock rejects a block over MAX_BLOCK_SIZE
                                         when its height is above 79,400; MAX_BLOCK_SIGOPS installed;
                                         the miner's 10,000-byte margin removed
12 Sep 2010   block 79,401               first block the rule applies to (79,400 mined 22:37:01 UTC,
                                         79,401 at 22:53:07 UTC)
19 Sep 2010   172f0060   SVN r156        THIRD STEP: both tests moved into CheckBlock in place of the
                                         32 MiB test and the height gate removed; the 1 MB rule now
                                         applies to every block, and MAX_SIZE stops bounding blocks
```

### The commit that defined the constant

```
a30b56ebe76ffff9f9cc8a6667186179413c6349
2010-07-15T00:18:45Z    author field: s_nakamoto    shipped in 0.3.1 (release commit 673a6d15, 16 Jul)
message: "fix openssl linkage problems, disable minimize to tray on Linux because it has too many
          problems including a CPU peg bug"

  db.cpp         +2   -0
  irc.cpp        +4   -0
  main.cpp       +4   -1
  main.h         +1   -0
  makefile.unix  +1   -1
  serialize.h    +1   -1
  ui.cpp         +13  -2
```

The one line in `main.h`, beside the ceiling that was already there:

```diff
 static const unsigned int MAX_SIZE = 0x02000000;
+static const unsigned int MAX_BLOCK_SIZE = 1000000;
```

And its only use, in `BitcoinMiner()`:

```diff
+                    unsigned int nTxSize = ::GetSerializeSize(tx, SER_NETWORK);
+                    if (nBlockSize + nTxSize >= MAX_BLOCK_SIZE - 10000)
+                        continue;
```

At this commit `CBlock::CheckBlock()` still reads `vtx.size() > MAX_SIZE || ::GetSerializeSize(*this,
SER_DISK) > MAX_SIZE` — the 32 MiB test v0.1 shipped with. A node running 0.3.1 accepted a 20 MB block
from a peer; it would not build one.

### The commit that made it a rule

```
f1e1fb4bdef878c8fc1564fa418d44e7541a7e83
2010-09-07T01:12:53Z    author field: s_nakamoto    git-svn-id: trunk@148
message: "cleanup,
          catch some recoverable exceptions and continue"

  main.cpp +61 -38   main.h +35 -15   script.cpp +55 -57   script.h +102 -76   net.cpp +0 -53
  util.cpp +30 -6    util.h +24 -16   irc.cpp +20 -0      (18 files in all)
```

In `CBlock::AcceptBlock()`:

```diff
+    int nHeight = pindexPrev->nHeight+1;
+
+    // Check size
+    if (nHeight > 79400 && ::GetSerializeSize(*this, SER_NETWORK) > MAX_BLOCK_SIZE)
+        return error("AcceptBlock() : over size limit");
```

In `main.h`, beside the constant:

```diff
 static const unsigned int MAX_BLOCK_SIZE = 1000000;
+static const int MAX_BLOCK_SIGOPS = MAX_BLOCK_SIZE/50;
```

And in the miner, the margin goes:

```diff
-                    if (nBlockSize + nTxSize >= MAX_BLOCK_SIZE - 10000)
+                    if (nBlockSize + nTxSize >= MAX_BLOCK_SIZE)
```

The height gate is a scheduled activation: nodes running this code accept oversized blocks below
height 79,401 (so the existing chain, whatever it held, stays valid) and reject them above it. The
commit sits between the 0.3.11 release (alert system, 25–28 Aug) and the commit that names 0.3.13
(30 Sep, `a790fa46`). The enforcing commit is itself the 0.3.12 release: its duplicate `8c9479c6` is
messaged `-- version 0.3.12 release`, so the gated 1 MB rule shipped in 0.3.12 and the ungated one in 0.3.13.

**The transaction-size rule is separate, and its first step came earlier.** A transaction may not
exceed the block cap: 32 MiB from `401926283` (25 August 2010) and 1 MB from `3df62878c`
(13 September 2010), so its first step precedes the 7 September block rule rather than following it
(`OBL-C-0010`). `a790fa46f` (30 September 2010) moves `CheckTransaction()` from `main.h` into
`main.cpp` with its size test unchanged on both sides of the move; it introduces no rule.

### Whether the messages describe the changes

```
a30b56eb   "fix openssl linkage problems, disable minimize to tray on Linux ..."   message_match: false
f1e1fb4b   "cleanup, catch some recoverable exceptions and continue"              message_match: false
```

Both statements are about the record: what the message says against what the diff does. Neither is a
statement about why. SVN-era commit messages in this repository were routinely terse and bundled;
`f1e1fb4b` touches eighteen files and its message describes some of them.

> **⇒ The 1 MB limit entered Bitcoin as a constant in July 2010 that only the miner honoured, and became
> a rule of block validity on 7 September 2010, activating at block 79,401, in a commit described as a
> cleanup. Before either, the January 2009 release rejected blocks over 32 MiB.**

---

## Method

**No inference. Every row above is a fetched commit or a fetched file.**

```bash
# the constant: one line in main.h, and the miner hunk
gh api repos/bitcoin/bitcoin/commits/a30b56ebe76ffff9f9cc8a6667186179413c6349 \
  --jq '.files[] | select(.filename=="main.h" or .filename=="main.cpp") | .patch'

# CheckBlock at that commit still tests MAX_SIZE
curl -s https://raw.githubusercontent.com/bitcoin/bitcoin/a30b56ebe76ffff9f9cc8a6667186179413c6349/main.cpp \
  | grep -n 'MAX_SIZE\|MAX_BLOCK_SIZE'

# every 2010 commit touching main.cpp whose patch mentions MAX_BLOCK_SIZE (eight; the first is f1e1fb4b)
for sha in $(gh api "repos/bitcoin/bitcoin/commits?path=main.cpp&since=2010-07-15T01:00:00Z&until=2010-12-31T23:59:59Z&per_page=100" --jq '.[].sha'); do
  gh api "repos/bitcoin/bitcoin/commits/$sha" --jq '.files[] | select(.filename=="main.cpp") | .patch' | grep -q MAX_BLOCK_SIZE && echo "$sha"
done

# the rule, the sigop limit and the height gate
gh api repos/bitcoin/bitcoin/commits/f1e1fb4bdef878c8fc1564fa418d44e7541a7e83 \
  --jq '.files[] | select(.filename=="main.h" or .filename=="main.cpp") | .patch' | grep -n 'MAX_BLOCK\|79400'

# the activation boundary on the public chain
curl -s https://blockstream.info/api/block/$(curl -s https://blockstream.info/api/block-height/79400) | jq .timestamp
```

**Genesis-side confirmation is read, not executed**, and the note says so: v0.1's `CheckBlock()`
(`extracted/bitcoin/src/main.cpp:1160`) tests `vtx.size() > MAX_SIZE` and `GetSerializeSize > MAX_SIZE`
with `MAX_SIZE = 0x02000000` (`main.h:17`). No block between 1 MB and 32 MiB was built and submitted
to the January 2009 binary for this note. That witness is the stated open item below; what it would add
is narrow: it would show the origin accepting, and **0.3.13** rejecting, one concrete block in the band
the 7 September rule closed. **0.3.13 and not 0.3.12**, because 0.3.12 is the release that carries the
enforcing commit while its test is still gated at height 79,400: on an isolated chain at low height
0.3.12 accepts such a block, and the gate is a fact of the record rather than a witness. It is
`172f00602`, ungating the test, that makes 0.3.13 reject it. Nobody disputes that a 1 MB cap rejects a 2 MB block, which is why the note
ships without it.

---

## Lineage

`bitcoin/bitcoin` carries much of its 2010 history twice, on parallel lineages converted from
Subversion: 264 of the 341 non-merge commits in the window stand as 132 pairs
(`BITCOIN-GIT-HISTORY-PROVENANCE.md`). `f1e1fb4b` has a duplicate, `8c9479c6`, with the same date and
author string; their messages differ, the duplicate adding a third line, `-- version 0.3.12 release`.
**`a30b56eb` has no duplicate** — it is one of the commits in the window that were not doubled.
`f1e1fb4b` and `8c9479c6` belong to the ten-pair run r148–r157 in which both copies carry the
`git-svn-id` trailer, both are authored `s_nakamoto`, and the timestamps are identical, so for this
commit neither the trailer nor the date distinguishes the two; the copy cited here is the one the
registers cite. Across the one-trailer pairs generally the untrailered copy is dated no earlier, and
at most 8.09 days later.

---

## What follows, stated as record

The constant defined on 15 July 2010 is the number that BIP 101 (*Increase maximum block size*, status
Closed) proposed to raise, that Bitcoin XT, Bitcoin Classic and SegWit2x existed to change, that BIP 141
(*Segregated Witness*, deployed 2017) replaced with a weight limit, and whose retention or change split
the chain in August 2017. Nothing here takes a position on any of that. What the record adds to those
disputes is one fact: the magnitude is not argued for in the commit that defined it or in the commit
that enforced it. An argument may exist elsewhere; none is in these two commits.

---

### Two more things the enforcing commit changed, and the third step (revision 2)

The same `f1e1fb4bd` also changes the P2P message-size cap in `net.h`, `CMessageHeader::IsValid()`:

```diff
-        if (nMessageSize > 0x10000000)
+        if (nMessageSize > MAX_SIZE)
```

Until this commit a message could carry up to 256 MiB; from it, `MAX_SIZE` (32 MiB) bounds messages as
well as blocks. The often-repeated line that early Bitcoin's block bound was "the message size limit" is
therefore inverted: the block bound was a validity test in `CheckBlock` from January 2009, and the
message cap was the looser of the two until September 2010.

Twelve days later, `172f00602` (19 September 2010, SVN r156, message about `-allowreceivebyip`) removed
both height-gated tests from `AcceptBlock()` and put them in `CheckBlock()` without a gate, replacing the
32 MiB test:

```diff
-    if (vtx.empty() || vtx.size() > MAX_SIZE || ::GetSerializeSize(*this, SER_NETWORK) > MAX_SIZE)
+    if (vtx.empty() || vtx.size() > MAX_BLOCK_SIZE || ::GetSerializeSize(*this, SER_NETWORK) > MAX_BLOCK_SIZE)
```

So the gated state lasted from 7 to 19 September 2010; after it the 1 MB rule applies to every block
back to genesis, which is what the register's row `OBL-C-0001` records as the rule's third step. The
transaction-size rule is separate and is dated in `OBL-C-0010`: 32 MiB on 25 August 2010 (`401926283`),
1 MB on 13 September 2010 (`3df62878c`); the commit of 30 September (`a790fa46f`) moves that function
between files and changes no test.

## Limits of this note

```
NOT a novelty claim      the two-step shape was published before this note (see Prior accounts); the
                         diff-level attribution is what it adds, on a search that was not exhaustive
NOT a claim about intent both commit messages are quoted, not interpreted; why a size rule shipped as
                         "cleanup" is not established here
NOT executed             the origin-side statement is read from v0.1's source; no block in the 1 MB–32 MiB
                         band was submitted to the 2009 binary (open item)
NOT a completeness claim the transaction-size rule (13 Sep 2010, `OBL-C-0010`) and MAX_BLOCK_SIGOPS are
                         noted, not traced further; later changes to the limit are named, not dated
NOT a recommendation     nothing here argues for or against any block size
BOUNDED window           15 Jul 2010 to 30 Sep 2010 in bitcoin/bitcoin; v0.1.0 from the hash-verified
                         archives for the origin side
```

---

## Artifacts

Two `gh api` calls and two `curl` calls reproduce every quoted line. The block timestamps come from a
public block explorer's API and can be re-read from any full node.

**Corrections to this note are published, dated, and not made silently.**

*Revision 2, 20 September 2026, after two outside readers checked the note against the record and the
literature: prior accounts of the two-step shape are stated and the first text's claim to have found none
is withdrawn; the third step (`172f00602`, 19 September 2010) and the message-size cap change in the
enforcing commit are added; the transaction-size rule's date is corrected to 13 September 2010. The
finding itself is unchanged. The title and opening paragraph were brought to three steps on 21 September
2026, before this revision was signed. Revision 1 and its signatures and proofs are kept beside this file as
`MAX-BLOCK-SIZE-RETROFITTED.r1.md*`; this text is signed and stamped as an operator step, recorded when done.*

*Corrected 25 September 2026, before signing, after a review checked every hash, diff hunk and block
timestamp in this note against the repository. Four statements were wrong, three of them left behind when
revision 2 added sections without reconciling the old text:*

1. *The transaction-size paragraph said `a790fa46` "adds" `CheckTransaction()` and that the rule
   "arrived later still". It moves the function between files with the test unchanged, and the rule's
   first step (25 August) precedes the 7 September block rule. Revision 2's own changelog claims this was
   corrected; the paragraph was not touched. It is rewritten.*
2. *`MAX_SIZE` was attributed to `serialize.h`. It is defined at `main.h:17`, as this note's own diff shows;
   `serialize.h` does not contain it.*
3. *The open witness was described as showing "0.3.12 rejecting". 0.3.12 carries the enforcing commit with
   its test still gated at height 79,400 and so accepts such a block on a low-height chain; the rejector is
   0.3.13, after `172f00602` ungates it. `OBL-C-0001` carried the same error and is corrected.*
4. *`a30b56eb` was said to have a duplicate carrying the `Satoshi Nakamoto` author string. It has none, as
   `CONSTITUTION-REGISTER.md` already recorded. The lineage paragraph is rewritten: the twin of `f1e1fb4b`
   does not carry the same message either, adding `-- version 0.3.12 release`.*

*The ratio of the two ceilings is stated as thirty-three rather than thirty-two, and the 0.3.12 release
commit, previously "not identified here", is identified. Every diff hunk, file stat, commit date and the
block 79,400 / 79,401 timestamps were re-verified in the same pass and are unchanged.*
