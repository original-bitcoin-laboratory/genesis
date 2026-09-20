# Secondary sources checked against the commit record

**20 September 2026.** Three statements in public secondary sources about when and how a 2010 rule
entered Bitcoin, each quoted verbatim with the source's own revision date, each checked against the
`bitcoin/bitcoin` commit record read on 20 September 2026 (trailer lineage; `BITCOIN-GIT-HISTORY-PROVENANCE.md`
says why the lineage is named). This note states what the source says and what the record says. It
attributes no motive to any author and repeats none of the sources' characterisations. Findings register:
`OBL-F-0039`.

> ### The rule for entries
>
> A statement is entered only when it is quoted verbatim from a source a reader can open, with the
> source's revision date, and only when the record contradicts it on a checkable fact: a hash, a date,
> a version, a number. Paraphrases of a source, and disagreements about what a rule *meant*, are not
> entries. One candidate was dropped from this note for exactly that reason (see the last section).

---

## 1. The Bitcoin wiki, *Block size limit controversy* (revision of 17 May 2025, 09:51): what limited block size before 2010

**The source says:** "Originally, Bitcoin's block size was limited by the number of database locks
required to process it (at most 10000). This limit was effectively around 500-750k in serialized bytes,
and was forgotten until 2013 March. In 2010, an explicit block size limit of 1 MB was introduced into
Bitcoin by Satoshi Nakamoto."

**The record says:** the January 2009 client rejects, as a validity rule, any block over `MAX_SIZE` =
`0x02000000` = 32 MiB (`main.cpp:1160`: `if (vtx.empty() || vtx.size() > MAX_SIZE ||
::GetSerializeSize(*this, SER_DISK) > MAX_SIZE)`), and its miner stops filling a block at half that
(`main.cpp:2237`). The origin had an explicit block-size limit; 2010 narrowed it. The Berkeley DB lock
limit the sentence describes is real and is the emergent rule that split the network at block 225,430
on 11 March 2013 (`OBL-C-0013`); it was a second, lower, unwritten ceiling that existed *beside* the
written 32 MiB one, not the only limit. `OBL-F-0016`, `OBL-C-0001`.

## 2. The same page, references 2 and 3: the two commits that introduced the 1 MB limit

**The source cites**, as the two commits that introduced the limit: "fix openssl linkage problems"
(commit `a30b56eb`) and "don't count or spend payments until they have 1 confirmation" (commit
`a790fa46f40`).

**The record says:** `a30b56ebe` (15 July 2010) defines `MAX_BLOCK_SIZE = 1000000` and uses it only in the
miner (`OBL-F-0013`). The **validity** rule is `f1e1fb4bd` (7 September 2010), which adds
`if (nHeight > 79400 && ::GetSerializeSize(*this, SER_NETWORK) > MAX_BLOCK_SIZE)` to `AcceptBlock`, and
`172f00602` (19 September 2010), which moves the test into `CheckBlock` in place of the 32 MiB one and
removes the height gate. `a790fa46f` (30 September 2010) is a different commit doing a different thing:
its diff removes `CTransaction::CheckTransaction()` from `main.h` and adds the same function to
`main.cpp` — a move — and the *transaction*-size test that function carries
(`::GetSerializeSize(*this, SER_NETWORK) > MAX_BLOCK_SIZE`) had entered on 13 September 2010 in `3df62878c`
(`OBL-C-0010`). So the page's second commit is neither the block-size validity rule nor the origin of
the transaction-size rule; it is the commit that moved the latter between files. The laboratory's own
register carried the same error for one day (19–20 September 2026) and corrected it in the row.
`OBL-C-0001`, `OBL-C-0010`, `docs/CONSENSUS-ATLAS.md`.

## 3. BIP 347, *OP_CAT in Tapscript* (assigned 2023-12-11): the date of the commit that disabled the opcodes

**The source says** (reference list): "S. Nakamoto, 'misc changes', Aug 25 2010,
https://github.com/bitcoin/bitcoin/commit/4bd188c4383d6e614e18f79dc337fbabe8464c82"; and in the text: "In
2010, a single commit disabled OP_CAT, along with another 15 opcodes."

**The record says:** `4bd188c43` is dated 2010-08-15 on both of the repository's lineages (author date
`2010-08-15T23:53:55Z` on the trailer copy; the pair list in `bitcoin-git-history-pairs.tsv`). The hash
and the message are right; the date is ten days late and is not explained by the duplicated lineages,
whose copies of this commit agree. The count is fifteen opcodes disabled in that commit, which matches
"another 15" when `OP_CAT` is counted separately. `OBL-C-0005`, `OBL-F-0014`.

---

## A candidate dropped, and why

The wiki's *Common Vulnerabilities and Exposures* page (revision of 26 May 2025, 16:22) was read as saying
the value-overflow fix shipped in 0.3.11. Its table, read verbatim, has the columns CVE / Announced /
Affects / Severity / Attack is… / Flaw / Net, and its CVE-2010-5139 row is "2010-08-15 | wxBitcoin and
bitcoind | Inflation | Easy | Combined output overflow | 100%": **no fix version appears in the row.** The
"0.3.11" came from a summary of the page, not from its text, and a statement the source does not make
cannot be contradicted. (For the record: `d4c6b90ca`, the fix, is two commits behind the `v0.3.10` tag,
so the fix shipped in 0.3.10, 15 August 2010; `OBL-C-0003`.) The same page's row for CVE-2010-5138
("2010-07-29 … Unlimited SigOp DoS") states an announcement date, not a fix, and which limit it means is
unstated; it is not entered either.

## Limits

```
NOT a claim about cause or motive     the sources' own characterisations of the commits are not repeated
NOT exhaustive                        three statements from three sources; the sweep that produced them
                                      (SEAM-SCAN, internal) read four wiki pages and two BIPs
BOUNDED by the sources' revisions     wiki pages change; each entry names the revision it quotes, and a later
                                      revision that corrects the sentence makes the entry historical, not wrong
```

**Corrections to this note are published, dated, and not made silently.**

---

*Experimental laboratory research, in progress: what re-runnable methods find, and no conclusion beyond that. Not money — no premine, no sale, no value assigned, no token. Not financial advice. No warranty. [Rights, sourcing and corrections](https://github.com/original-bitcoin-laboratory/genesis/blob/main/RIGHTS.md).*
