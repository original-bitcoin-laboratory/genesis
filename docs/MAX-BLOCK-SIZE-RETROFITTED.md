# Bitcoin's 1 MB block-size limit was retrofitted in two steps in mid-2010

**19 September 2026.** `MAX_BLOCK_SIZE = 1000000` is the rule the 2015–2017 block-size dispute was
fought over. It is commonly dated to a single commit in July 2010. The record shows two commits, in two
files, seven weeks apart, neither of whose messages describes the change; and the January 2009 release
already enforced a block-size ceiling, thirty-two times larger.

This note dates both steps, gives the method to reproduce the dating, and states what the origin
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
> **No priority is claimed even for the added part.** A literature search was performed and is
> reported here; it was not exhaustive, and the commits are public to anyone who looks.

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
(30 Sep, `a790fa46`); the 0.3.12 release commit is not identified here.

**The transaction-size rule arrived later still.** `a790fa46` (30 Sep 2010) adds `CheckTransaction()`
with `::GetSerializeSize(*this, SER_NETWORK) > MAX_BLOCK_SIZE` — a transaction may not exceed the
block cap. Noted, not dated further.

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
with `MAX_SIZE = 0x02000000` (`serialize.h`). No block between 1 MB and 32 MiB was built and submitted
to the January 2009 binary for this note. That witness is the stated open item below; what it would add
is narrow: it would show the origin accepting, and 0.3.12 rejecting, one concrete block in the band the
7 September rule closed. Nobody disputes that a 1 MB cap rejects a 2 MB block, which is why the note
ships without it.

---

## Lineage

`bitcoin/bitcoin` carries its 2010 history twice, on parallel lineages converted from Subversion.
`f1e1fb4b` has a duplicate, `8c9479c6`, with the same date, author string and message; `a30b56eb`'s
duplicate carries the `Satoshi Nakamoto` author string. Dates here are from the `s_nakamoto` lineage,
which carries the SVN identifiers (`git-svn-id: ... trunk@148`) and the earlier timestamps; the other
lineage's copies differ by zero to three days.

---

## What follows, stated as record

The constant defined on 15 July 2010 is the number that BIP 101 (*Increase maximum block size*, status
Closed) proposed to raise, that Bitcoin XT, Bitcoin Classic and SegWit2x existed to change, that BIP 141
(*Segregated Witness*, deployed 2017) replaced with a weight limit, and whose retention or change split
the chain in August 2017. Nothing here takes a position on any of that. What the record adds to those
disputes is one fact: the magnitude is not argued for in the commit that defined it or in the commit
that enforced it. An argument may exist elsewhere; none is in these two commits.

---

## Limits of this note

```
NOT a novelty claim      the constant's commit is widely cited; the literature search was not exhaustive
NOT a claim about intent both commit messages are quoted, not interpreted; why a size rule shipped as
                         "cleanup" is not established here
NOT executed             the origin-side statement is read from v0.1's source; no block in the 1 MB–32 MiB
                         band was submitted to the 2009 binary (open item)
NOT a completeness claim the transaction-size rule (30 Sep 2010) and MAX_BLOCK_SIGOPS are noted, not
                         traced further; later changes to the limit are named, not dated
NOT a recommendation     nothing here argues for or against any block size
BOUNDED window           15 Jul 2010 to 30 Sep 2010 in bitcoin/bitcoin; v0.1.0 from the hash-verified
                         archives for the origin side
```

---

## Artifacts

Two `gh api` calls and two `curl` calls reproduce every quoted line. The block timestamps come from a
public block explorer's API and can be re-read from any full node.

**Corrections to this note are published, dated, and not made silently.**
