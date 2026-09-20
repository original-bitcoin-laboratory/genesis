# Ordinal time: the January 2009 protocol expresses time as position

**20 September 2026.** The January 2009 Bitcoin protocol orders by *position*. Chain selection counts
blocks rather than weighing work; transaction locks count blocks, with no threshold at which a lock
becomes a wall-clock time; and the single external anchor to calendar time, a newspaper headline,
sits in the coinbase outside every rule. Wall-clock timestamps enter consensus in three places, and
none of them is a clock. Two changes of 2009–2010 gave the ordering a physical basis: time-based locks
on 29 October 2009 and chain selection by cumulative work on 25 July 2010. This note states the four
executed statements behind the first claim, reads the two commits behind the second, and borrows the
vocabulary phylogenetics developed for the same problem, as a source of names for structures already in
the code and not as an analogy about nature. Findings register: `OBL-F-0040`; the statements rest on
`OBL-F-0001`, `OBL-F-0002`, `OBL-F-0005`, `OBL-F-0006` and the rows `OBL-C-0007`, `OBL-C-0008`.

> ### What is already known, and what this note adds
>
> **The code is public.** That v0.1 selects the chain with the most blocks, that its `nLockTime` is
> compared to a height, and that cumulative work arrived later are visible to anyone who reads it.
>
> ```
> ALREADY VISIBLE       the lines; the whitepaper's phrases "timestamp server" and "longest chain"
>
> ADDED HERE            the four statements executed, each with a finding identifier and the source line
>                         it ports; the two commits that changed them, dated on the trailer lineage with
>                         their messages quoted; and one vocabulary, stated with the place it stops
> ```
>
> **No priority is claimed**, and this note takes no position on any rule.

---

## The four executed statements

Grades follow `EVIDENCE_POLICY.md`: `JAN09-SOURCE` for what the January source shows, `MODEL` for what
a line-for-line port executes, `NOV08-SOURCE` for the November pre-release.

**1. Chain selection counts blocks (`OBL-F-0001`).** The January client adopts a new tip when
`pindexNew->nHeight > nBestHeight` (`main.cpp:1097`). It does not sum work. The port exhibits a
discriminating fork: a challenger at height 125 with cumulative work 250 beats the incumbent at height
122 with work 262 (`paper-artifacts/height-vs-work.json`). `MODEL`, with the selection line read at
`JAN09-SOURCE`; the release build's replay of 19 block cases executes the surrounding validation
(`OBL-F-0010`).

**2. Locks count blocks (`OBL-F-0002`).** `CTransaction::IsFinal` returns true when
`nLockTime == 0 || nLockTime < nBestHeight`; otherwise a transaction is final only if every input carries
the maximal sequence number. The comparison is to a height and nothing else; the source has no
threshold at which a lock is read as a Unix time (zero occurrences of the later constant, in a search
bounded to the January archive). A lock of 500,000,000, which later Bitcoins read as November 1985, the
January client reads as a block height and holds the transaction until then (`derivatives/temporal/`).
`JAN09-SOURCE` + `MODEL`.

**3. The wall clock is constrained, not consulted (`OBL-F-0006`; `CONSENSUS_BEHAVIORS.md`).** Three
rules read timestamps. `GetMedianTimePast` takes the median of the last eleven block times and
`AcceptBlock` requires a block's time to exceed it (`main.h:1086`, `main.cpp:1206`); `CheckBlock` rejects
a block more than two hours in the future (`main.cpp:1164`); `GetNextWorkRequired` reads the elapsed time
across a window and scales the target so that blocks arrive near one per ten minutes
(`main.cpp:685–728`). The first two bound what a timestamp may say and decide no ordering and no
finality. The third is a rate controller: it uses elapsed time to keep the *event rate* near constant,
which is what makes the event count usable as a clock at all. Its fencepost, 2,015 measured intervals
against a 2,016-interval budget, fixes the equilibrium spacing at 600.30 s, not 600 s
(`derivatives/retarget/`). `MODEL`, ported line for line.

**4. The only calendar anchor is outside every rule (`OBL-F-0005` for the November contrast).** The
January genesis coinbase carries the text of a newspaper headline dated 3 January 2009. No rule reads
it; it is a commitment that the block was made no earlier than that day, checkable by a person and by
nothing in the protocol. The November 2008 pre-release's genesis coinbase is the bare integer
`247422313`, with no external anchor, a timestamp (`1221069728`, 10 September 2008) that predates the
whitepaper's announcement, and roughly one fourteen-thousandth of January's work (`NOV08_GENESIS.md`).
`NOV08-SOURCE` and `JAN09-SOURCE`.

Together: ordering by position, finality by position, the wall clock as a bounded witness and a rate
input, and one calendar anchor the protocol carries but does not read.

## The two commits that changed it

Both are read from `bitcoin/bitcoin`'s record on the lineage that carries the Subversion trailer
(`BITCOIN-GIT-HISTORY-PROVENANCE.md`), and both are constitution rows with the message quoted and the
diff lines cited (`CONSENSUS-ATLAS.md`).

**Time-based locks, 29 October 2009** (`dd519206a`, `OBL-C-0007`). The commit adds
`if (nLockTime < (nLockTime < 500000000 ? nBestHeight : nBlockTime))` under the comment "Time based
nLockTime implemented in 0.1.6, / do not use time based until most 0.1.5 nodes have upgraded". Its
message lists "non-final tx locktime changes" among six items: the message describes the change. The
threshold's magnitude, 500,000,000, is not argued for in the record, though the comment gives a reason to
defer the time-based form. From this commit a lock is either a position or a wall-clock time, by the
value's size.

**Cumulative work, 25 July 2010** (`3b7cd5d89`, `OBL-C-0008`). The commit adds `CBigNum bnChainWork` to
the block index, computes each block's work from its target, sums it along the chain, and replaces
`if (pindexNew->nHeight > nBestHeight)` with `if (pindexNew->bnChainWork > bnBestChainWork)`. Its message
reads, in full, "Gavin Andresen's JSON-RPC HTTP authentication, faster initial block download -- version
0.3.3". Neither line names chain selection. The repository's duplicated 2010 lineage carries a second
copy (`40cd03694`, 26 July 2010) that differs in size from the first; the selection change is present in
both.

From 25 July 2010 the ordering criterion is no longer how many events occurred but how much work they
represent.

## One vocabulary, and where it stops

Phylogenetics converts an accumulated count of events, substitutions along a lineage, into elapsed
time. Doing so needs an assumed rate; the rate is not constant in practice; and the conversion is
anchored by calibration points outside the sequence data. The field's names for those structures fit
the code closely enough to be useful, and this note uses them for what they name:

| molecular clock | block chain, January 2009 | block chain, from 25 July 2010 |
|---|---|---|
| event count along a lineage | block height | block height, still carried |
| assumed constant rate (strict clock) | the retarget holds the rate near 1 per 600.30 s by feedback | same |
| rate heterogeneity | difficulty differs across branches; height ignores it | cumulative work weights each event by its difficulty |
| calibration point outside the data | the headline in the genesis coinbase, read by nobody | the same, plus every timestamp as a bounded witness |
| error bars on a calibration | none stated | the two-hour future bound and the median-of-eleven floor bound each timestamp from both sides |

Three statements the names make short, each a claim about the code and not about nature.

- **The January protocol is a strict clock enforced by a controller.** A strict molecular clock
  *assumes* a constant rate; the January protocol *manufactures* one, by adjusting the target every
  2,016 blocks so that elapsed time over the window approaches its budget. Height is a usable clock only
  because the retarget makes it one, and its fixed point is 600.30 s per block.
- **The 2010 change is the move from counting events to weighting them.** Cumulative work is the sum,
  over blocks, of the expected number of hashes each block's target demanded: a branch length measured
  in work rather than in events. That is what "the ordering acquired a physical basis" means here: the
  criterion became a quantity of expended computation rather than a count.
- **The genesis headline is a calibration point, and the November genesis has none.** A fossil
  calibration places a node no earlier than a dated stratum; the headline places the genesis no
  earlier than 3 January 2009 for anyone who reads it, and the protocol does not.

**Where it stops.** Substitution rates are properties of biology and are estimated; block rates are set
by a controller and are known to the constant. Calibration uncertainty in phylogenetics is a
distribution over a fossil's age; a block timestamp's uncertainty is a bounded interval fixed by two
rules. And a phylogeny is inferred from data that does not know it is being read, while a block chain
is produced by participants who read the rules: a miner can choose a timestamp within its bounds, which
no lineage can. The tools transfer; the epistemics do not.

## What the framing points at, and what is executed

1. Under the January rule, a branch with more blocks and less work wins. Executed: `OBL-F-0001`.
2. Under the January rule, a lock value in the range later read as a time is a height. Executed:
   `OBL-F-0002`.
3. The controller's fixed point is above 600 s, not below, because it under-measures elapsed time.
   Executed: `OBL-F-0006`, with the naive reading (599.70 s) stated beside the executed value (600.30 s).
4. Pending: the laboratory's experimental chain, running the unmodified January consensus with
   chain-separation substitutions, reaches its first retarget at height 2,016 with inter-block gaps that
   have ranged from minutes to hours; the trace of the controller's first action under that forcing will
   be published as a sealed findings set when it occurs (`WHY-THE-CHAIN-CONTINUES.md`). At difficulty 1
   the target cannot fall further, so the predicted result is a no-op; a raised target would be a
   significant finding and is not predicted.

## Limits

The four statements are executed at grade `MODEL` on line-for-line ports, and at `EXECUTED (release
build)` where the laboratory's build of the January source has replayed them; the unmodified 2009 binary
has executed the genesis derivation and the two-node runs but not the corpus. The two commits are dated
from GitHub's copy of the repository on 20 September 2026; the history can be rewritten by its owners,
and 132 of the 341 non-merge commits of 2009–2010 exist twice. The vocabulary is a source of names for
structures already in the code; nothing here is evidence about Bitcoin's design intent, and nothing in
Bitcoin is evidence about biology.

## Artifacts

`derivatives/temporal/`, `derivatives/retarget/`, `paper-artifacts/height-vs-work.json`,
`FINDINGS-REGISTER.md`, `CONSTITUTION-REGISTER.md`, `docs/CONSENSUS-ATLAS.md`. Each identifier resolves to
a row with its grade and artifact, checked in continuous integration.

**Corrections to this note are published, dated, and not made silently.**

---

*Experimental laboratory research, in progress: what re-runnable methods find, and no conclusion beyond that. Not money — no premine, no sale, no value assigned, no token. Not financial advice. No warranty. [Rights, sourcing and corrections](https://github.com/original-bitcoin-laboratory/genesis/blob/main/RIGHTS.md).*
