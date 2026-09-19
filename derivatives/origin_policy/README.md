# Three policies of the origin, and what 2010 did to them — executed

**Evidence level: `MODEL`.** Constitution rows `OBL-C-0015`, `OBL-C-0016`, `OBL-C-0017`; the
archaeology is in [`docs/CONSENSUS-ATLAS.md`](../../docs/CONSENSUS-ATLAS.md) §10–§12. Same shape as
[`../overflow/`](../overflow/) and [`../emergent/`](../emergent/): the January 2009 rule and the 2010
rule ported line for line, side by side, and the input one accepts and the other refuses.

```
python replacement.py    # transaction replacement by nSequence: shipped in v0.1, disabled 19 Aug 2010
python checkpoints.py    # hard-coded checkpoints: absent in v0.1, added 17 Jul 2010, five by 15 Aug
python fees.py           # the fee rule: a build-and-send policy in v0.1, a relay gate from 12 Dec 2010
python -m pytest -q      # 13 checks
```

## What it shows

```
REPLACEMENT              v0.1 accepts a newer version of a held transaction (same inputs, higher nSequence)
                         and erases the old one; 0.3.11 refuses every conflicting transaction
CHECKPOINTS              v0.1 follows proof of work alone; from 0.3.2 a block at height 11111 (then 33333,
                         68555, 70567, 74000) with a hash other than the named one is rejected
FEES                     v0.1: one cent per started kilobyte, free under 10 KB with the discount, applied
                         when building and sending, nothing applied on receipt; 0.3.19: relay refuses a
                         transaction below GetMinFee(1000), and free transactions are rate-limited to
                         150,000 bytes per ten minutes under -limitfreerelay (601 of 250 B, then refused)
```

## What is ported, and what is not

- **`replacement.py`.** `CTransaction::IsNewerThan` (v0.1 `main.h:408`) and the conflict branch of
  `AcceptTransaction` (`main.cpp:428-446`, `463-474`) line for line; then the two lines `05454818d`
  adds at the top of that branch (`// Disable replacement feature for now` / `return false;`). The
  pool is a dictionary; `ConnectInputs` is out of scope for the decision under test.
- **`checkpoints.py`.** The clause `ae922a36a` adds to `AcceptBlock` and `4bd188c43` extends to five
  heights, with the hashes as the source spells them. The block is a stand-in: its hash is the input;
  proof of work and ancestry are taken as valid, since the checkpoint clause is the only one under test.
- **`fees.py`.** `GetMinFee` from v0.1 (`main.h:504`) and from 0.3.19 (`main.h:576-612` at
  `97ee01ad8`, including the dust clause and the price rise near a full block), and the relay gate
  `97ee01ad8` adds to `AcceptToMemoryPool`. Policy on both sides: no block is invalid under either.

## What this does not claim

Nothing about why any of the three changed; the commit messages are quoted in the atlas and the
constitution register records whether they describe the change. Nothing about later replacement
designs (the December 2010 post on fee-based replacement is quoted in the atlas as the author's
words; it was not implemented in the record). NOT money.
