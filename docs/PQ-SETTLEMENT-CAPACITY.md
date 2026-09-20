# What a 2009-shaped base layer can settle under post-quantum signatures — computed

**20 September 2026, corrected the same day.** [`PQ-SIGNATURE-COST.md`](PQ-SIGNATURE-COST.md) measured
the sizes and found that size binds: a transaction grows 19× to 86× and a chain keeps everything. This
note is the second half of that question. At those sizes, how many spends fit a block, how many settle
in a day, and how long does it take for a population of outputs to each move once? The answer is
arithmetic over the measured figures, and it is what the statement "state must move off the base layer"
rests on when it is a measurement rather than a metaphor. It also gives that statement's limit: an
output whose public key is already on the chain can be moved only by a signature under the old scheme,
and no second layer can do that for it.

```
python verify/pq_settlement_capacity.py            # the tables below
python verify/pq_settlement_capacity.py --json     # every figure, as data
```

**This document takes no position on whether any Bitcoin should change anything.** It computes costs
from measured sizes; it recommends no scheme, predicts nothing about when any cryptography breaks,
and names no chain's output count. Populations are parameters, stated as such.

> **Correction, 20 September 2026, from an adversarial review.** The first text of this note computed
> one table, at the 1 MB block of the 2010 rule, in a repository whose own register records that rule as
> a retrofit the January 2009 design does not contain (`OBL-C-0001`, `OBL-F-0016`), and said the 32 MiB
> ceiling "changes nothing about the shape". It changes the conclusion: under v0.1's own ceiling a
> hundred million outputs move once in 79 to 356 days, not 7 to 33 years. The January ceiling now comes
> first and the 2010 rule second. The same review found the migration row two bytes short against the
> sibling note's model; both notes now use one serialisation model (`verify/pq_signature_cost.py`,
> `model_p2pk_spend`). The earlier text is in this repository's history.

> **What is measured and what is computed.** Signature and raw public-key sizes come from
> `PQ-SIGNATURE-COST.md` §1 (FIPS 204 and 205 sizes, matched exactly). Transaction sizes come from the
> same serialisation model that note uses, with the push opcode each element costs, validated against
> real coinbase transactions before use. A block holds one 135-byte coinbase and then as many spends as
> fit. The day is 144 blocks, 2009 pacing; the executed fixed point of 600.30 s makes it 143.9.

---

## 1. Under the January 2009 ceiling: `MAX_SIZE` = 32 MiB, the rule v0.1 enforces

One input, one output, pay-to-pubkey; per block, per day; and the days before N outputs have each
moved once with every block full of nothing else:

```
scheme                 tx B   per block      per day   N = 1,000,000   N = 10,000,000   N = 100,000,000
--------------------------------------------------------------------------------------------------------
secp256k1-ECDSA         200     167,771   24,159,024             0.0              0.4              4.1
ML-DSA-44              3804       8,820    1,270,080             0.8              7.9             78.7
ML-DSA-65              5333       6,291      905,904             1.1             11.0            110.4
ML-DSA-87              7291       4,602      662,688             1.5             15.1            150.9
SLH-DSA-SHA2-128s      7956       4,217      607,248             1.6             16.5            164.7
SLH-DSA-SHA2-128f     17188       1,952      281,088             3.6             35.6            355.8
SLH-DSA-SHA2-192s     16340       2,053      295,632             3.4             33.8            338.3
```

Under the baseline the January base layer settles about 24 million one-input spends a day with every
block full. Under the smallest lattice scheme it settles about 1.27 million; under the hash-based scheme
whose key this laboratory counter-signs with, 607,000. A day's capacity falls by a factor of 19 to 86,
the same factor as the transaction size, because a full block is a fixed number of bytes; and a
hundred million outputs move once in 79 to 356 days.

## 2. Under the 2010 rule: `MAX_BLOCK_SIZE` = 1 MB

The same arithmetic at the ceiling Bitcoin acquired on 7 September 2010 (`OBL-C-0001`):

```
scheme                 tx B   per block      per day   N = 1,000,000   N = 10,000,000   N = 100,000,000
--------------------------------------------------------------------------------------------------------
secp256k1-ECDSA         200       4,999      719,856             1.4             13.9            138.9
ML-DSA-44              3804         262       37,728            26.5            265.1          2,650.6
ML-DSA-65              5333         187       26,928            37.1            371.4          3,713.6
ML-DSA-87              7291         137       19,728            50.7            506.9          5,068.9
SLH-DSA-SHA2-128s      7956         125       18,000            55.6            555.6          5,555.6
SLH-DSA-SHA2-128f     17188          58        8,352           119.7          1,197.3         11,973.2
SLH-DSA-SHA2-192s     16340          61        8,784           113.8          1,138.4         11,384.3
```

Ten years is 3,650 days. At 1 MB a hundred million outputs need between seven and thirty-three years
of full blocks to each move once; at 32 MiB, between eleven weeks and a year. The ratio between the two
tables is the ratio of the ceilings, 33.55, and nothing else. What the two tables say together: the
population a base layer of this shape can settle in bounded time is bounded by the day's capacity, the
day's capacity is bounded by the signature size and the block ceiling, and the block ceiling is a rule
with a date. Whatever moves the rest off the base layer is a design question this note does not
answer; the size of the question is the table, and it is a different size under each ceiling.

## 3. The limit: the migration spend is signed under the old scheme

The spend that moves an exposed key to a post-quantum one is a transaction with an old-scheme input
and a new-scheme output. Its size is the old signature plus the new key, not the new signature:

```
                        migration   -- 32 MiB --                     -- 1 MB --
scheme                       tx B    per day   N = 1e8 (days)    per day   N = 1e8 (days)
------------------------------------------------------------------------------------------
ML-DSA-44                   1,451  3,329,856             30.0     99,216          1,007.9
ML-DSA-65                   2,091  2,310,768             43.3     68,832          1,452.8
ML-DSA-87                   2,731  1,769,184             56.5     52,704          1,897.4
SLH-DSA-SHA2-128s             167 28,932,912              3.5    862,128            116.0
SLH-DSA-SHA2-128f             167 28,932,912              3.5    862,128            116.0
SLH-DSA-SHA2-192s             183 26,403,264              3.8    786,672            127.1
```

Two things fall out of that table, both consequences of the sizes and not of any design.

- **The migration is cheaper than the steady state, and its cost is the key, not the signature.** A
  hash-based key is 32 bytes and a migration to it is smaller than today's spend; a lattice key is
  1.3 to 2.6 KB and the migration is seven to fourteen times larger. Under pay-to-pubkey-hash, where
  the chain holds only a hash until spend, the lattice key is deferred and the difference closes;
  `PQ-SIGNATURE-COST.md` §3 makes the same point for the steady state. A scheme cannot be chosen
  without choosing an output type.
- **A second layer does nothing for an exposed key.** The migration spend needs a signature under the
  scheme the exposed key belongs to; that is a base-layer transaction by construction, and the
  population that must make one is bounded by the base layer's capacity in the tables above, not by
  anything built above it. Outputs whose keys are not yet exposed (a hash on the chain, the key
  revealed at spend) have a different problem, deferred until they spend, and the same arithmetic
  applies on the day they do.

---

## 4. What this does not establish

```
NOT   a recommendation, or a position on any chain's choices, including its block ceiling
NOT   a claim about any chain's output population: N is a parameter; the reader supplies it
NOT   a forecast: every block is taken as full of one transaction shape, an upper bound on capacity
      and a lower bound on time, at 2009 pacing
NOT   applicable to aggregation: schemes that aggregate signatures change this arithmetic, and
      none of the three NIST standards measured aggregates
NOT   a statement about when any cryptography breaks; the window is "before a break", and this note
      measures how wide the door is, not when it closes
```

## Reproducing

`verify/pq_settlement_capacity.py` carries the measured sizes as constants with their source lines,
imports the serialisation model from `verify/pq_signature_cost.py`, and computes every figure above
under both ceilings; `--json` prints them as data. A future measurement that changes a size in
`PQ-SIGNATURE-COST.md` changes this note by editing seven constants.

**If something here is wrong, it is a defect and is corrected in the open rather than argued about.**
Corrections are published, dated, and not made silently.

---

*Experimental laboratory research, in progress: what re-runnable methods find, and no conclusion beyond that. Not money — no premine, no sale, no value assigned, no token. Not financial advice. No warranty. [Rights, sourcing and corrections](https://github.com/original-bitcoin-laboratory/genesis/blob/main/RIGHTS.md).*
