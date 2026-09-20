# The `bitcoin/bitcoin` history of 2009–2010 is carried twice

**19 September 2026.** The repository the field treats as the record of Bitcoin's early development
was converted from Subversion. For the period from its first commit (30 August 2009) to the end of
2010 it carries many commits twice: 132 of its 341 non-merge commits exist as a pair with the same first
message line. In 121 pairs one copy carries the `git-svn-id` trailer that names the SourceForge revision and
the other does not, dated the same day or up to eight days later, under one of three author strings; in ten
pairs (SVN r148–r157) both copies carry the trailer; in one neither does. A date or hash cited from the second
copy of a one-trailer pair can differ from the first by up to eight days and, in eight cases, by a few lines
of content.

This note measures that from GitHub's own commit records, states what follows for citing the record,
and states what it does not claim. Findings register: `OBL-F-0014`.

> ### What is already known, and what this note adds
>
> **The conversion is known.** That `bitcoin/bitcoin` began as an SVN import, and that early
> commits carry `git-svn-id` trailers, is visible to anyone who reads the log.
>
> ```
> ALREADY VISIBLE       git-svn-id trailers on the early history; author strings in three forms
>
> ADDED HERE            the count: 132 of 341 non-merge commits in the window exist as a pair
>                         (121 with the trailer on one copy, 10 on both, 1 on neither), and one first
>                         line, "misc", eight times
>                       that 124 of the 132 pairs carry identical additions, deletions and file lists,
>                         and 8 differ by a few lines
>                       that in the one-trailer pairs the copy without the trailer is dated later in every
>                         pair (median same day, 90 % within 1.75 days, at most 8.09 days), and is the copy
>                         that carries the strings "Satoshi Nakamoto" and "--author=Satoshi Nakamoto"
>                       that the doubling starts at the root: two "First commit" objects, 30 Aug 2009
> ```
>
> **No priority is claimed.** The commits are public to anyone who counts them; a literature search
> was not exhaustive.

---

## The finding

```
window                     2009-08-30T03:46:39Z .. 2010-12-24T09:25:21Z (default-branch history)
commits in the window      385         merge commits 42        non-merge 341 (root excluded)
with git-svn-id trailer    202         last trailer commit 2010-12-17T20:16:27Z
author strings             s_nakamoto 245 · Satoshi Nakamoto 26 · "--author=Satoshi Nakamoto" 8
                           Gavin Andresen 58 · gavinandresen 19 · sirius-m 26 · laszloh 1 · Witchspace 2
author addresses           <name>@1a98c847-1fd6-4fd8-948a-caf3550aa51b (the SVN uuid) ·
                           satoshin@gmx.com 34 (26 Jul .. 28 Aug 2010) · gavinandresen@gmail.com 58 · witchspace81@gmail.com 2

duplicate pairs            132 groups of two non-merge commits with the same first message line
  trailer on               one copy 121 · both copies 10 (SVN r148–r157, 7–23 Sep 2010) · neither 1 (20 Dec 2010, Gavin Andresen)
  same change?             124 identical (additions, deletions, file list) · 8 differ (all one-trailer pairs) · 0 not compared
  date offset              non-trailer minus trailer, one-trailer pairs: min 0.00 d · median 0.00 · p90 1.75 · max 8.09 · earlier: 0
  non-trailer author       s_nakamoto 72 · Satoshi Nakamoto 25 · --author=Satoshi Nakamoto 7 · sirius-m 12 · Gavin Andresen 5
  eight copies             the first line "misc" (Dec 2009 – Mar 2010): four trailer and four non-trailer commits, not paired by this method
root                       e071a3f6c and 4405b78d6, both "First commit", sirius-m, 2009-08-30
```

### The eight pairs whose copies differ

```
trailer copy   other copy   +/- trailer     +/- other      dated         message (first line)
d01eaf042      9d2174b6f    +5    / -5      +30   / -9     15 → 19 Jul   version 0.3.1 rc1
3b7cd5d89      40cd03694    +405  / -137    +93   / -25    25 → 26 Jul   Gavin Andresen's JSON-RPC HTTP authentication,
6966768a5      f0c11b191    +2    / -5      +2    / -1     25 → 26 Jul   Gavin: BIO_FLAGS_BASE64_NO_NL
793200e5e      b6dc3b517    +539  / -483    +537  / -469   26 Jul        bitcoind now compiles without wxWidgets or wxBase
813505cc1      3dd20ff2f    +6085 / -893    +6091 / -893   27 Jul        added a subset of Crypto++ 5.6.0 ...
01bed1828      e1cb7ce01    +13   / -18     +12   / -29    30 → 31 Jul   simplified makefile.unix, updated build-unix.txt ...
4bd188c43      6ac7f9f14    +538  / -52     +538  / -58    15 Aug        misc changes
15399da9f      bb3fd0293    +81   / -48     +91   / -49    16 Aug        blocks-1,
```

The two pairs the first run could not compare (`53d508072`/`2939cab06`, `e39bc50eb`/`25b12b883`) are identical
on the re-run of 20 September 2026, which compared every pair.

### The eight `--author=` commits

`2689f4d02`, `3dd20ff2f`, `9f35575ca` (27 Jul 2010), `a75560d82`, `ec82517c8`, `31ffe954b`, `872d60f6e`
(30 Jul), `e1cb7ce01` (31 Jul): the author-name field holds the literal string `--author=Satoshi Nakamoto`,
with the address `satoshin@gmx.com`. The record shows the string; it does not show how it got there.

### What follows for citing the record

- A commit from this period has two hashes and, in a pair, up to two dates. A citation that names one
  hash and one date without saying which lineage it reads is under-specified by up to eight days.
- The trailer copy carries the SourceForge revision (`git-svn-id: ... trunk@N`) and the earlier date in
  every one-trailer pair. This laboratory cites that copy and records the other in a `lineage_note`
  (`CONSTITUTION-REGISTER.md`). For the ten pairs where both copies carry the trailer (r148–r157) the two share
  revision, date and author string; the cited copy is the one on the chain that the r158 trailer commit
  `a790fa46f` descends from by first parent (`f1e1fb4bd`, `3f6475377`, `7629d36a5`, `496823249`, `c39b06866`,
  `fdbf76d4f`, `3df62878c`, `efae3da41`, `172f00602`, `9b8eb4d69`); the other chain ends in a merge commit of
  23 September 2010 (`6ce5af574`, "Merge commit 'svn/trunk' into svn"). Where the two copies' messages differ,
  as `f1e1fb4bd` and `8c9479c6b` do (the latter adds "-- version 0.3.12 release"), `message_match` is read on
  the cited copy. Example: the alert system is `401926283` (25 Aug 2010, trailer) and
  `522dfe342` (28 Aug 2010, "Satoshi Nakamoto"); 0.3.11 shipped later still.
- The eight differing pairs mean "the same commit" is not the same change in every pair. A claim about the
  content of a 2010 commit should name the hash it read, not the message.
- BIP 347's date of "Aug 25 2010" for `4bd188c43` is not explained by the lineages: both copies of that
  commit are dated 15 August (recorded in `docs/SCRIPT-LIMITS-RETROFITTED.md`).

> **⇒ For 2009–2010 the canonical Bitcoin repository is two records of one history, and they do not
> agree on the date, or on the bytes, in every pair. Reading it as one record is where dating errors come from.**

---

## Method

**Every number above is a fetched record; nothing is inferred from the log's shape.**

```bash
# every commit on the default-branch history in the window (four pages), with author string, address,
# first message line, parent count and whether the message carries a git-svn-id trailer
gh api "repos/bitcoin/bitcoin/commits?since=2009-08-30T00:00:00Z&until=2011-01-01T00:00:00Z&per_page=100&page=1" \
  --jq '.[] | [.sha, .commit.author.date, .commit.author.name, .commit.author.email, (.commit.message|split("\n")[0]), (.parents|length), (.commit.message|test("git-svn-id")|tostring)] | @tsv'
# ... page=2, 3, 4

# per commit, the change statistics compared across each pair
gh api repos/bitcoin/bitcoin/commits/<sha> --jq '[(.stats.additions|tostring),(.stats.deletions|tostring),([.files[].filename]|sort|join(","))] | @tsv'
```

The pairing is by first message line among non-merge commits; the comparison of additions, deletions and
file lists is what makes a pair a fact rather than a coincidence of wording. The same census runs as one
script in the sibling project that keeps Satoshi's dated record:
`satoshi-onchain/verify/github_history_census.py` (`--out census.json`; four unauthenticated API calls; add
`--stats` to compare each pair's change statistics, which needs a token). GitHub's API was read on 19 September 2026; the repository's history can be
rewritten by its owners, so a re-run is dated.

---

## Limits of this note

```
NOT a claim about cause   how the second lineage arose (a re-import, a rebase, a second push) is not
                          established here; the literal "--author=" strings are shown, not explained
NOT a claim about intent  no statement about anyone's purpose
NOT a completeness claim  the window ends at 2010-12-31; the conversion's later effects, and merge
                          commits, are not examined
BOUNDED by the API        GitHub's records on the run date; every pair compared on the re-run; commit
                          metadata is author-supplied for the non-trailer copies, server-numbered
                          (SVN revision) for the trailer copies
```

---

## Artifacts

Four paginated API calls and one per-commit call reproduce every number. The census script's JSON
output for this run is kept beside the satoshi-onchain event that cites it. `bitcoin-git-history-pairs.tsv`, beside
this note, lists every pair: both copies' sha, date, author string, trailer, SVN revision, additions and
deletions, the pair type, whether the change is identical, and the offset in days; written 20 September 2026 from
the same API.

**Corrections to this note are published, dated, and not made silently.**

*Revision 2, 20 September 2026, after an adversarial review recounted the pairs: the first text counted 122 pairs
of one trailer copy and one without, did not distinguish the ten pairs where both copies carry the trailer or the
one where neither does, left two pairs uncompared, and stated no citation rule for the both-trailer pairs. The
counts, the author tally, the citation rule and the pair list are corrected and published above; `OBL-F-0014` is
restated to match. Nothing else changed. Revision 1 and its signatures and proofs are kept beside this file as
`BITCOIN-GIT-HISTORY-PROVENANCE.r1.md*`; this text is signed and stamped as an operator step, recorded when done.*
