# What post-quantum signing costs a 2009-shaped chain — measured

**11 August 2026; corrected and re-run 20 September 2026.** Post-quantum signatures for Bitcoin are
discussed constantly and priced in adjectives. The question that decides whether any proposal is
buildable is arithmetic: **a signature goes in every transaction input, and a chain keeps every
transaction.**

This is that arithmetic, measured on the client this laboratory actually runs.

```
python verify/pq_signature_cost.py                          # ~5 min
python verify/pq_signature_cost.py --chain <blk0001.dat>    # validate the model against your chain
```

**This document takes no position on whether Bitcoin should change anything.** It reports costs. It
recommends no scheme, predicts nothing about when any cryptography breaks, and favours no proposal.

> **What is measured and what is computed, stated before the numbers.**
> **MEASURED** — signature sizes from real keys signing real messages: 200 samples per scheme, and for
> ECDSA those 200 are spread across 8 keys (the table in §1); raw public-key sizes parsed out of the DER;
> sign and verify wall-clock as the median of 100 whole-process operations; and the process-spawn floor,
> measured the same way, so the timing column can be read for what it is.
> **COMPUTED** — transaction and block sizes, from Bitcoin v0.1's serialization rules, including the
> push opcode each element costs.
> **VALIDATED BEFORE USE** — the same serialization walker parses real coinbase transactions from a
> v0.1-format `blk0001.dat` before a single modelled figure is produced (this run: **2 blocks**, from a
> published evidence set, min 134 B, max 189 B; the 11 August run: 51 blocks from a live node). **If it
> parses zero blocks, the run declares the validation VOID rather than reporting it as done.** *(The
> count is whatever chain file the run is pointed at; a different number there is the check working.)*

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

---

## 1. The primitives

```
scheme                     sig B  distinct   pk B   sign ms   verify ms
-----------------------------------------------------------------------
secp256k1-ECDSA            70-72         3     65      15.2        14.1
ML-DSA-44                   2420         1   1312      15.8        12.0
ML-DSA-65                   3309         1   1952      15.6        12.6
ML-DSA-87                   4627         1   2592      19.4        15.5
SLH-DSA-SHA2-128s           7856         1     32     305.6        13.5
SLH-DSA-SHA2-128f          17088         1     32      35.7        17.1
SLH-DSA-SHA2-192s          16224         1     48     621.7        17.8

process-spawn floor, measured: 16.66 ms   (`openssl version`, no cryptography at all)
```

**OpenSSL 3.5.4, run of 20 September 2026.** `pk B` is the **raw** key — the bytes that would be on a
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
secp256k1-ECDSA          200     276     1.0x     4,999   167,771          1.0          52.5
ML-DSA-44               3804    5131    19.0x       262     8,820         19.0         999.5
ML-DSA-65               5333    7300    26.7x       187     6,291         26.7       1,401.2
ML-DSA-87               7291    9898    36.5x       137     4,602         36.4       1,915.7
SLH-DSA-SHA2-128s       7956    7999    39.8x       125     4,217         39.8       2,090.4
SLH-DSA-SHA2-128f      17188   17231    85.9x        58     1,952         85.9       4,516.1
SLH-DSA-SHA2-192s      16340   16399    81.7x        61     2,053         81.7       4,293.3
```

A transaction is `version + inputs + outputs + locktime` with v0.1's varints; the scriptSig is one push
of the signature and its hash-type byte, the scriptPubKey one push of the key and `OP_CHECKSIG`; a push
costs one opcode byte up to 75 bytes, `OP_PUSHDATA1` + 1 to 255, `OP_PUSHDATA2` + 2 to 65,535. Per-block
counts take one 135-byte coinbase first (the mean coinbase the walker parsed on the 11 August run) and
then as many spends as fit. **`tx/32MiB`** is the count under the January 2009 ceiling, `MAX_SIZE`,
the rule v0.1 itself enforces (`OBL-F-0016`); **`tx/1MB`** under the rule Bitcoin acquired in September
2010 (`OBL-C-0001`).

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
`openssl` process, and the measured floor for a process that does no cryptography is 16.66 ms on this
run (13.34 ms on the 11 August run). Most verify medians, and the lattice schemes' sign medians, sit at
or below that floor; the hash-based schemes' signing sits far above it (289, 19 and 605 ms over the
floor for 128s, 128f and 192s). A median at or below the floor is not a negative or a small
cryptographic cost: it is a cost the instrument cannot see. **What the measurement establishes is that
verification is within a few milliseconds of a bare process start for every scheme; a library
benchmark, one process for all operations, is the instrument that would put a number on it, and this
note does not have one.**

**What the measurement does establish is size.** A transaction grows **19× to 86×**, and because a
chain keeps everything, that multiplier applies to the entire history:

```
secp256k1        52.5 GB/yr        the chain as it exists
ML-DSA-44       999.5 GB/yr        a terabyte a year
SLH-DSA-128s  2,090.4 GB/yr        two terabytes a year
SLH-DSA-128f  4,516.1 GB/yr        four and a half terabytes a year
```

> **⇒ The cheapest test for any post-quantum proposal, with numbers behind it: what does a signature
> cost in bytes, and what did you do about it?**

### Signing, unlike verifying, is visible

**SLH-DSA-128s signs in ~305 ms and 192s in ~620 ms**, against a floor-bound figure for everything
else. The `f` ("fast") variants invert it: **128f signs in ~36 ms but produces 17,088 B — more than
twice 128s.** The parameter sets are a direct trade.

### And the ranking flips with the output type

**For pay-to-pubkey, both the signature and the key are on chain.** That is the output type the
earliest 2009 coins use, and the one this laboratory's own experimental chain, Bitcoin (2026), is
configured to use (its own choice, not evidence of anything beyond its configuration).

```
                    sig B  +   pk B   =   on-chain crypto payload
secp256k1              71  +     65   =       136 B
ML-DSA-44            2420  +   1312   =     3,732 B      key is 35% of the cost
SLH-DSA-SHA2-128s    7856  +     32   =     7,888 B      key is 0.4% of the cost
```

**The two-output column above makes this visible.** A second output costs **ML-DSA-44 +1,327 B** and
**SLH-DSA-128s +43 B** — each new output carries another public key, and their key sizes differ by
forty-one times.

**Under pay-to-pubkey-hash, where the chain holds only a 20-byte hash until spend, ML-DSA's large
key is deferred and it wins comfortably. Under pay-to-pubkey it does not.** A signature scheme
cannot be chosen without choosing an output type at the same time.

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
NOT   a verification cost. Timings are wall-clock around a subprocess; medians at or below the spawn
      floor are unresolved, not small. A library benchmark would be the sharper instrument
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
```

Writes `pq-cost-measurement.json` with every raw figure. Requires OpenSSL 3.5+ for the PQ
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
