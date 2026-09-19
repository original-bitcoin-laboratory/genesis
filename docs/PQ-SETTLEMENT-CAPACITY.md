# What a 2009-shaped base layer can settle under post-quantum signatures — computed

**20 September 2026.** [`PQ-SIGNATURE-COST.md`](PQ-SIGNATURE-COST.md) measured the sizes and found
that size, not verification, binds: a transaction grows 19× to 86× and a chain keeps everything. This
note is the second half of that question. At those sizes, how many spends fit a block, how many
settle in a day, and how long does it take for a population of outputs to each move once? The answer
is arithmetic over the measured figures, and it is what the statement "state must move off the base
layer" rests on when it is a measurement rather than a metaphor. It also gives that statement's
limit: an output whose public key is already on the chain can be moved only by a signature under the
old scheme, and no second layer can do that for it.

```
python verify/pq_settlement_capacity.py            # the tables below
python verify/pq_settlement_capacity.py --json     # every figure, as data
```

**This document takes no position on whether any Bitcoin should change anything.** It computes costs
from measured sizes; it recommends no scheme, predicts nothing about when any cryptography breaks,
and names no chain's output count. Populations are parameters, stated as such.

> **What is measured and what is computed.** Every byte count below comes from `PQ-SIGNATURE-COST.md`
> §1 and §2: signature sizes from real keys signing real messages (FIPS 204 and 205 sizes, matched
> exactly), raw public-key sizes, and one-input one-output transaction sizes from v0.1's serialisation
> rules, validated against 51 real coinbase transactions before use. The block is 1,000,000 bytes (the
> 2010 rule; v0.1's own ceiling is 32 MiB, which multiplies every row by 33.5 and changes nothing about
> the shape). The day is 144 blocks, 2009 pacing; the executed fixed point of 600.30 s makes it 143.9.

---

## 1. Spends per block and per day, one input, one output, pay-to-pubkey

```
scheme                 tx B   per block   per day
--------------------------------------------------
secp256k1-ECDSA         200       4,999   719,856
ML-DSA-44              3800         263    37,872
ML-DSA-65              5329         187    26,928
ML-DSA-87              7287         137    19,728
SLH-DSA-SHA2-128s      7954         125    18,000
SLH-DSA-SHA2-128f     17186          58     8,352
SLH-DSA-SHA2-192s     16338          61     8,784
```

Under the baseline, the base layer settles about 720,000 one-input spends a day with every block
full. Under the smallest lattice scheme it settles about 38,000; under the hash-based scheme whose
key this laboratory counter-signs with, 18,000. A day's settlement capacity falls by a factor of 19
to 86, the same factor as the transaction size, because a full block is a fixed number of bytes.

## 2. How long a population takes to move once

With every block full of nothing but these spends, the days before N outputs have each moved once:

```
scheme                 N = 1,000,000   N = 10,000,000   N = 100,000,000
------------------------------------------------------------------------
secp256k1-ECDSA                 1.4             13.9            138.9
ML-DSA-44                      26.4            264.0          2,640.5
ML-DSA-65                      37.1            371.4          3,713.6
ML-DSA-87                      50.7            506.9          5,068.9
SLH-DSA-SHA2-128s              55.6            555.6          5,555.6
SLH-DSA-SHA2-128f             119.7          1,197.3         11,973.2
SLH-DSA-SHA2-192s             113.8          1,138.4         11,384.3
```

Ten years is 3,650 days. For a population of a hundred million outputs, the base layer under any of
the measured post-quantum schemes needs between seven and thirty-three years of full blocks for each
output to move once, with nothing else in the blocks. That is the arithmetic behind the statement
that a chain of this shape cannot carry every participant's settlement on its base layer once
signatures are this size: the population that can settle in bounded time is bounded by the day's
capacity, and the day's capacity is bounded by the signature. Whatever moves the rest off the base
layer is a design question this note does not answer; the size of the question is the table.

## 3. The limit: the migration spend is signed under the old scheme

The spend that moves an exposed key to a post-quantum one is a transaction with an old-scheme input
and a new-scheme output. Its size is the old signature plus the new key, not the new signature:

```
scheme                 migration tx B   per day    N = 1e6   N = 1e7   N = 1e8   (days)
------------------------------------------------------------------------------------------
ML-DSA-44                       1,447    99,360       10.1     100.6   1,006.4
ML-DSA-65                       2,087    68,976       14.5     145.0   1,449.8
ML-DSA-87                       2,727    52,704       19.0     189.7   1,897.4
SLH-DSA-SHA2-128s                 167   862,128        1.2      11.6     116.0
SLH-DSA-SHA2-128f                 167   862,128        1.2      11.6     116.0
SLH-DSA-SHA2-192s                 183   786,672        1.3      12.7     127.1
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
  population that must make one is bounded by the base layer's capacity in the first table, not by
  anything built above it. Outputs whose keys are not yet exposed (a hash on the chain, the key
  revealed at spend) have a different problem, deferred until they spend, and the same arithmetic
  applies on the day they do.

---

## 4. What this does not establish

```
NOT   a recommendation, or a position on any chain's choices
NOT   a claim about any chain's output population: N is a parameter; the reader supplies it
NOT   a forecast: every block is taken as full of one transaction shape, an upper bound on capacity
      and a lower bound on time, at 2009 pacing
NOT   applicable to aggregation: schemes that aggregate signatures change this arithmetic, and
      none of the three NIST standards measured aggregates
NOT   a statement about when any cryptography breaks; the window is "before a break", and this note
      measures how wide the door is, not when it closes
```

## Reproducing

`verify/pq_settlement_capacity.py` carries the measured sizes as constants with their source lines and
computes every figure above; `--json` prints them as data. A future measurement that changes a size in
`PQ-SIGNATURE-COST.md` changes this note by editing seven constants.

**If something here is wrong, it is a defect and is corrected in the open rather than argued about.**
Corrections are published, dated, and not made silently.

---

*Experimental laboratory research, in progress: what re-runnable methods find, and no conclusion beyond that. Not money — no premine, no sale, no value assigned, no token. Not financial advice. No warranty. [Rights, sourcing and corrections](https://github.com/original-bitcoin-laboratory/genesis/blob/main/RIGHTS.md).*
