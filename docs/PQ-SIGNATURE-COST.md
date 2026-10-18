# What post-quantum signing costs a 2009-shaped chain — measured

**11 August 2026; corrected and re-run 20 September 2026 and 18 October 2026.** Post-quantum signatures for Bitcoin are
discussed constantly and priced in adjectives. The question that decides whether any proposal is
buildable is arithmetic: **a signature goes in every transaction input, and a chain keeps every
transaction.**

This is that arithmetic: sizes and timings measured with OpenSSL, and transaction and block sizes
computed under the serialization rules of the January 2009 client.

```
python verify/pq_signature_cost.py                          # ~8 min
python verify/pq_signature_cost.py --chain <blk0001.dat>    # validate the model against your chain
python verify/bench_inprocess.py --n 100                    # in-process timings, ~3 min
```

**This document takes no position on whether Bitcoin should change anything.** It reports costs. It
recommends no scheme, predicts nothing about when any cryptography breaks, and favours no proposal.

> **What is measured and what is computed, stated before the numbers.**
> **MEASURED** — signature sizes from real keys signing real messages: 200 samples per scheme, and for
> ECDSA those 200 are spread across 8 keys (the table in §1); raw public-key sizes parsed out of the DER;
> sign and verify wall-clock as the median of 100 whole-process operations; the process-spawn floor,
> measured the same way, so the timing column can be read for what it is; and, separately, sign and
> verify as the median of 100 in-process calls into the same library (§3a).
> **COMPUTED** — transaction and block sizes, from Bitcoin v0.1's serialization rules, including the
> push opcode each element costs.
> **VALIDATED BEFORE USE** — the same serialization walker reads every block of a v0.1-format
> `blk0001.dat` to its exact recorded length, and the transaction model reproduces the size of every
> spend in it, before a single modelled figure is produced. This run: **124 blocks** of the published
> evidence set kept beside the script as `verify/data/v01-relayed-spend-blk0001.dat` (a relayed-spend
> run of the January 2009 binary); coinbases 134–204 B; one real spend, pay-to-pubkey into
> pay-to-pubkey-hash, **158 B on disk and 158 B by the model** (signature 71 B, one 25-byte output
> script). **If it parses zero blocks, a block does not end at its recorded length, or a modelled spend
> differs from the real one, the run fails rather than reporting the validation as done.** Every push in
> the sample is under 76 bytes, so it uses the single-byte push opcode; the `OP_PUSHDATA2` path the
> post-quantum rows take is checked against `CScript::operator<<`, not against a chain.

**The baseline is secp256k1 ECDSA because that is what v0.1 actually calls** —
`EC_KEY_new_by_curve_name(NID_secp256k1)` and `ECDSA_sign` in `key.h`.

> **Corrections, 20 September 2026, from an adversarial review.** (1) The transaction model charged one byte
> for every push; v0.1's `CScript::operator<<` writes `OP_PUSHDATA2` for anything over 255 bytes, so every
> post-quantum row in §2 was two to four bytes short (ML-DSA-44: 3,800 → 3,804). (2) This note said "5,000
> transactions per 1 MB block" where its companion said 4,999; both now count one 135-byte coinbase first.
> (3) §3 read "verification is essentially free" from timings that sit at or below the spawn floor; a median
> at or below the floor is a cost the method cannot resolve, not a small one, and §3 now says so. (4) A
> "widely stated" attribution and a "51 of 51 outputs" figure offered as evidence of output-type prevalence
> are withdrawn: the 51 were this laboratory's own coinbases, under an output type it chose. The earlier
> text is in this repository's history.

> **Corrections, 18 October 2026, from two internal reviews.** (1) The per-block counts left out the
> 80-byte block header and the transaction-count varint, although v0.1 checks the size of the whole
> serialized block; every 1 MB count moves by at most one (secp256k1: 4,999 → 4,998) and the coinbase
> is now the 134 B smallest coinbase of the validation file rather than a 135 B mean. (2) "The ranking
> flips with the output type" said ML-DSA wins under pay-to-pubkey-hash and loses under pay-to-pubkey.
> It does not lose a one-output spend under either: ML-DSA-44's 3,804 B is below SLH-DSA-128s's 7,956 B.
> What the output type changes is fan-out, and §3c now gives the table. (3) The model was validated
> against coinbases only; it is now validated against a real spend as well, and the run fails if any
> modelled spend differs. (4) Both timing instruments were re-run back to back with n = 100 for every
> scheme, the CPU and the binaries recorded; the in-process instrument's call-cost figure had timed a
> hashing call in Python rather than a call into the library, and now times a call into the library.
> (5) "Measured on the client this laboratory actually runs" overstated the method: the sizes are
> computed under the client's serialization rules, not observed from it. (6) Later the same day, after
> two further reviews, both instruments were run again on final scripts: the in-process benchmark now
> includes a secp256k1 baseline and keeps every sample in run order, the key-size parser fails rather
> than returning a DER size, and the SLH-DSA-192s difference left "not explained" by the first run is
> located by the per-sample record (§3a). The figures below are from that second run.

---

## 1. The primitives

```
scheme                     sig B  distinct   pk B   sign ms   verify ms
-----------------------------------------------------------------------
secp256k1-ECDSA            70-72         3     65     20.35       19.71
ML-DSA-44                   2420         1   1312     22.39       16.51
ML-DSA-65                   3309         1   1952     23.38       21.16
ML-DSA-87                   4627         1   2592     31.56       27.97
SLH-DSA-SHA2-128s           7856         1     32    354.54       16.81
SLH-DSA-SHA2-128f          17088         1     32     38.72       17.49
SLH-DSA-SHA2-192s          16224         1     48    747.92       17.18

process-spawn floor, measured: 13.68 ms   (`openssl version`, no cryptography at all)
```

**OpenSSL 3.5.4, run of 18 October 2026 (16:21 UTC), 12th Gen Intel Core i5-1240P** (a hybrid part with
performance and efficiency cores; the operating system chooses which core runs each process). The
binary, its SHA-256 and `openssl version -a` are recorded in `verify/pq-cost-measurement.json`.
`pk B` is the **raw** key — the bytes that would be on a
chain — parsed out of the ASN.1, not the DER file size. *(An earlier draft reported DER sizes, which add
a constant 22 B for the lattice schemes and 18 B for the hash-based ones. That overstated the
post-quantum cost.)* Each timing is a whole `openssl` process; see §3 for what that means.

### Cross-checked against the standards, not just against itself

**Every signature size matches FIPS 204 (ML-DSA) and FIPS 205 (SLH-DSA) exactly** — 2420, 3309,
4627, 7856, 17088, 16224 — and every raw public key matches too (1312, 1952, 2592, 32, 32, 48).
**So this measures the standards, not one library's quirks.**

### secp256k1 signatures are not a fixed size

An early run reported "70–72 B, three lengths" from a single key. **One key sampled repeatedly does
not characterise a distribution.** A separate sampling run on 11 August 2026 — **20 keys × 60
signatures = 1,200 samples** — gave the distribution below; the 200-sample, 8-key run behind the table
in §1 saw three of its four lengths, which is what a smaller sample of the same distribution does:

```
69 B      3    0.2%
70 B    293   24.4%
71 B    574   47.8%     <- the mode
72 B    330   27.5%
```

DER drops leading zero bytes, so the length depends on the r and s a signature happens to produce;
**72 B is the maximum** (`0x30 len 0x02 33 r 0x02 33 s`). **71 bytes is the mode of a four-valued
distribution, and it holds less than half the time**; the rest of this note uses 71 as the
representative size.

---

## 2. What it costs a chain — a v0.1 pay-to-pubkey spend

```
scheme                  1-in    1-in   x base    tx/1MB  tx/32MiB   blk MB for   chain GB/yr
                       1-out   2-out             block     block    same rate     same rate
---------------------------------------------------------------------------------------------
secp256k1-ECDSA          200     276     1.0x     4,998   167,771          1.0          52.5
ML-DSA-44               3804    5131    19.0x       262     8,820         19.0         999.3
ML-DSA-65               5333    7300    26.7x       187     6,291         26.7       1,401.0
ML-DSA-87               7291    9898    36.5x       137     4,602         36.4       1,915.3
SLH-DSA-SHA2-128s       7956    7999    39.8x       125     4,217         39.8       2,090.0
SLH-DSA-SHA2-128f      17188   17231    85.9x        58     1,952         85.9       4,515.2
SLH-DSA-SHA2-192s      16340   16399    81.7x        61     2,053         81.7       4,292.4
```

A transaction is `version + inputs + outputs + locktime` with v0.1's varints; the scriptSig is one push
of the signature and its hash-type byte, the scriptPubKey one push of the key and `OP_CHECKSIG`; a push
costs one opcode byte up to 75 bytes, `OP_PUSHDATA1` + 1 to 255, `OP_PUSHDATA2` + 2 to 65,535. Per-block
counts take the 80-byte header, the transaction-count varint and one 134-byte coinbase (the smallest in
the validation file) and then as many spends as fit, because both limits apply to the whole serialized
block. **`tx/32MiB`** is the count under the January 2009 ceiling, `MAX_SIZE`, which v0.1's
`CheckBlock` applies to the serialized block; **`tx/1MB`** under `MAX_BLOCK_SIZE`, defined with the
miner's limit in commit `a30b56e` (15 July 2010) and applied to accepted blocks from version 0.3.12
(commit `8c9479c`, 7 September 2010). **`chain GB/yr`** counts the spends only; headers and coinbases
add the same amount to every row.

**"Same rate"** = the block size and annual growth required to carry **the same number of
transactions per block** as secp256k1 at 1 MB, at 2009 pacing (6 blocks/hour, 52,560 blocks/year,
blocks full — **an upper bound, not a forecast**).

> **A note on how NOT to compute this, because the first version of this table got it wrong.**
> Reporting chain growth at a **fixed block size** returns the same figure for every scheme — of course
> it does, since `(block ÷ tx) × tx × blocks` is the block-size limit restated. **It measures the cap,
> not the signature.** The comparison has to hold *throughput* constant instead.

---

## 3. The finding: the objection is not CPU. It is bytes.

**Verification cost sits below what this method can resolve.** Every timing in §1 is a whole
`openssl` process, and the measured floor for a process that does no cryptography is 13.68 ms on this
run (16.66 ms on 20 September, 13.34 ms on 11 August). Every verify median, and the sign medians of
secp256k1 and the lattice schemes, sit within about 18 ms of that floor; the hash-based schemes' signing
sits far above it (341, 25 and 734 ms over the floor for 128s, 128f and 192s). A small excess over the
floor is not a clean measurement of the cryptography: the floor itself moves by several milliseconds
between runs. **What this instrument establishes is that verification is within a few milliseconds of a
bare process start for every scheme. The in-process instrument in §3a puts a number on it: 0.1 to
0.9 ms for the post-quantum schemes, against 0.33 ms for secp256k1 in the same library.**

**What the measurement does establish is size.** A transaction grows **19× to 86×**, and because a
chain keeps everything, that multiplier applies to the entire history:

```
secp256k1        52.5 GB/yr        the chain as it exists
ML-DSA-44       999.3 GB/yr        a terabyte a year
SLH-DSA-128s  2,090.0 GB/yr        two terabytes a year
SLH-DSA-128f  4,515.2 GB/yr        four and a half terabytes a year
```

> **⇒ The cheapest test for any post-quantum proposal, with numbers behind it: what does a signature
> cost in bytes, and what did you do about it?**

### Signing, unlike verifying, is visible

**SLH-DSA-128s signs in ~0.34 s in-process (~0.35 s as a whole process) and 192s in ~0.97 s (~0.75 s)**,
against milliseconds or less for everything else. The `f` ("fast") variants invert it: **128f signs in
~16 ms but produces 17,088 B — more than twice 128s.** The parameter sets are a direct trade.

## 3a. In-process timings

`verify/bench_inprocess.py` calls the same `libcrypto` through `EVP_PKEY_sign` and `EVP_PKEY_verify`,
one process for all operations, n = 100 for every scheme, a 32-byte message, run straight after the
whole-process run on the same machine. Microseconds, median [first–third quartile]:

```
scheme                  sign us                            verify us
secp256k1-ECDSA             349.3  [342.5 – 359.1]             334.3  [329.6 – 342.6]
ML-DSA-44                   541.6  [341.1 – 760.9]             126.1  [125.4 – 126.7]
ML-DSA-65                   642.0  [490.2 – 972.9]             197.7  [191.5 – 202.3]
ML-DSA-87                   724.5  [510.6 – 1,239.0]           290.9  [286.3 – 296.9]
SLH-DSA-SHA2-128s       336,330.9  [322,423 – 394,747]         349.7  [319.8 – 385.2]
SLH-DSA-SHA2-128f        15,576.8  [15,143 – 15,946]           931.3  [887.1 – 959.4]
SLH-DSA-SHA2-192s       970,977.9  [782,506 – 1,192,576]       757.9  [660.5 – 1,103.7]

one ctypes call into the same library that does no cryptography: 0.4 us median (calibration
context; nothing is subtracted)
```

The secp256k1 row signs a 32-byte message with OpenSSL's composite ECDSA-SHA256, which hashes it once;
OpenSSL's secp256k1 is a general-purpose implementation, not the specialised library Bitcoin nodes use.

**The two instruments use the same library**: the `openssl` on the path links the `libcrypto` file in its
own directory, which is the file the benchmark loads; its path and SHA-256 are in
`inprocess-timings.json`, the CLI's in both JSON files. ML-DSA signing is variable by
design (the scheme rejects and retries), which is why its quartiles are wide and its verify quartiles
narrow. Every ML-DSA set verifies faster than secp256k1 in the same library, and ML-DSA-44 at about
126 µs agrees in order of magnitude with the published Dilithium reference figures.

**SLH-DSA-192s signs in 0.97 s in-process against 0.75 s as a whole process**, although the in-process
figure has no process to start. The benchmark keeps every sample in run order, and the record locates
the difference: in the 192s loop, about a hundred seconds of uninterrupted signing, the first twenty
signatures have a median of 0.72 s and the last twenty 1.21 s, and its verifications slow from 648 to
1,032 µs; no other scheme's loop drifts so. The whole-process instrument starts a
process between operations and never runs the processor that long without a pause. A sustained-load
clock limit (power or temperature) is consistent with that record; the clock was not logged, so it is
not established. Core type does not explain it: run pinned to one performance core
(`verify/run_pinned.py 0`), 30 signatures had a median of 1.34 s, and pinned to one efficiency core
(`verify/run_pinned.py 15`) 0.95 s, both straight after the main run (`verify/diag/`). Verification is
two to three orders of magnitude cheaper than signing for the hash-based schemes and under 1 ms for
every scheme.

## 3c. Output type and fan-out

**For pay-to-pubkey, both the signature and the key are on chain.** That is the output type the
earliest 2009 coins use.

```
                    sig B  +   pk B   =   on-chain crypto payload
secp256k1              71  +     65   =       136 B
ML-DSA-44            2420  +   1312   =     3,732 B      key is 35% of the cost
SLH-DSA-SHA2-128s    7856  +     32   =     7,888 B      key is 0.4% of the cost
```

**The two-output column above makes this visible.** A second output costs **ML-DSA-44 +1,327 B** and
**SLH-DSA-128s +43 B** — each new output carries another public key, and their key sizes differ by
forty-one times. One-input spends, bytes, by number of outputs (`verify/pq_settlement_capacity.py`):

```
scheme              form     1-out   2-out   3-out   4-out   5-out   6-out
ML-DSA-44           p2pk     3,804   5,131   6,458   7,785   9,112  10,439
ML-DSA-44           p2pkh    3,826   3,860   3,894   3,928   3,962   3,996
ML-DSA-65           p2pk     5,333   7,300   9,267  11,234  13,201  15,168
ML-DSA-87           p2pk     7,291   9,898  12,505  15,112  17,719  20,326
ML-DSA-87           p2pkh    7,313   7,347   7,381   7,415   7,449   7,483
SLH-DSA-SHA2-128s   p2pk     7,956   7,999   8,042   8,085   8,128   8,171
SLH-DSA-SHA2-128s   p2pkh    7,980   8,014   8,048   8,082   8,116   8,150
```

**Under pay-to-pubkey, ML-DSA-87, -65 and -44 become larger than SLH-DSA-128s from 2, 3 and 5 outputs.
Under pay-to-pubkey-hash every output is 25 bytes whatever the scheme, so each further output adds the
same 34 bytes under every scheme, and no ML-DSA set becomes larger at any fan-out.** Per coin over its whole life the two forms carry the same thing, one
signature and one key; they differ in which transaction carries the key, and so in what a single
transaction costs. A comparison of schemes by transaction size has to state the output type and the
fan-out it assumes.

---

## 3b. The second half of the question

At these sizes, how many spends fit a block, how many settle in a day, and how long a population of
outputs takes to move once: [`PQ-SETTLEMENT-CAPACITY.md`](PQ-SETTLEMENT-CAPACITY.md), computed from the
figures above by `verify/pq_settlement_capacity.py` (20 September 2026), under both ceilings.

## 4. What this does not establish

```
NOT   a recommendation. This measures costs; it does not weigh them, and it favours no scheme
NOT   a claim about migration. Coins already in pay-to-pubkey outputs have their keys exposed, and
      moving them REQUIRES a signature under the old scheme. That is a governance question, and no
      measurement settles it
NOT   a cycle-accurate benchmark, or a node's validation throughput. Both instruments are
      wall-clock on one machine with a hybrid CPU, n = 100; the whole-process figures include
      process start-up, and the in-process SLH-DSA-192s sign and verify medians include a slowdown
      over its long uninterrupted loop
NOT   a forecast. "chain GB/yr" assumes every block full at 2009 pacing -- an upper bound
NOT   applicable to aggregation. Schemes that aggregate signatures change this arithmetic
      completely, and none of the three NIST standards measured here aggregates
NOT   a position on whether Bitcoin should change anything, or on when any cryptography breaks
```

---

## Reproducing

```
python verify/pq_signature_cost.py                          # full
python verify/pq_signature_cost.py --quick                  # smoke test
python verify/pq_signature_cost.py --chain <blk0001.dat>    # validate against your own chain
python verify/bench_inprocess.py --n 100 --out verify/inprocess-timings.json
python verify/pq_settlement_capacity.py                     # the companion note's tables
```

Writes `pq-cost-measurement.json` and `inprocess-timings.json` with the measured sizes and medians
(and, for the in-process run, every sample), the binaries' paths and SHA-256s, `openssl version -a` and
the CPU; the process-spawn floor is printed by the run rather than stored. Without `--chain`, the validation uses
`verify/data/v01-relayed-spend-blk0001.dat`. Requires OpenSSL 3.5+ for the PQ
algorithms; nothing else is needed and nothing is installed.

**If a future run disagrees, the likeliest causes in order:** a different OpenSSL — the PQ
implementations are young, and while FIPS fixes the sizes the DER wrapping is not fixed; a machine
where process spawn is cheaper or dearer, which moves every timing column together; or a change to the
transaction model, which is the only computed part and is printed next to its validation so it can be
checked rather than trusted.

**If something here is wrong, it is a defect and is corrected in the open rather than argued
about.** Corrections are published, dated, and not made silently.

---

*Experimental laboratory research, in progress: what re-runnable methods find, and no conclusion beyond that. Not money — no premine, no sale, no value assigned, no token. Not financial advice. No warranty. [Rights, sourcing and corrections](https://github.com/original-bitcoin-laboratory/genesis/blob/main/RIGHTS.md).*
