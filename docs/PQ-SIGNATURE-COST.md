# What post-quantum signing costs a 2009-shaped chain — measured

**11 August 2026.** Post-quantum signatures for Bitcoin are discussed constantly and priced in
adjectives. The question that decides whether any proposal is buildable is arithmetic: **a signature
goes in every transaction input, and a chain stores every transaction forever.**

This is that arithmetic, measured on the client this laboratory actually runs.

```
python verify/pq_signature_cost.py                          # ~5 min
python verify/pq_signature_cost.py --chain <blk0001.dat>    # validate the model against your chain
```

**This document takes no position on whether Bitcoin should change anything.** It reports costs. It
recommends no scheme, predicts nothing about when any cryptography breaks, and favours no proposal.

> **What is measured and what is computed, stated before the numbers.**
> **MEASURED** — signature sizes from real keys signing real messages, 200 samples per scheme across
> 8 keys; raw public-key sizes parsed out of the DER; sign and verify wall-clock, median of 100
> operations; and the process-spawn floor, so the timing column can be read rather than caveated.
> **COMPUTED** — transaction and block sizes, from Bitcoin v0.1's serialization rules.
> **VALIDATED BEFORE USE** — the same serialization walker parses **51 real coinbase transactions
> from a live v0.1-format `blk0001.dat`** (min 134 B, max 189 B, mean 135.1 B) before a single
> modelled figure is produced. **If it parses zero blocks, the run declares the validation VOID
> rather than reporting it as done.** *(51 is the chain's height on the day of this run; the chain
> keeps growing, so a later run validates against more records and prints its own count. A different
> number there is the check working, not a discrepancy.)*

**The baseline is secp256k1 ECDSA because that is what v0.1 actually calls** —
`EC_KEY_new_by_curve_name(NID_secp256k1)` and `ECDSA_sign` in `key.h`.

---

## 1. The primitives

```
scheme                     sig B  distinct   pk B   sign ms   verify ms
-----------------------------------------------------------------------
secp256k1-ECDSA            69-72         4     65      18.7        13.9
ML-DSA-44                   2420         1   1312      18.0        12.4
ML-DSA-65                   3309         1   1952      18.5        12.4
ML-DSA-87                   4627         1   2592      18.6        12.6
SLH-DSA-SHA2-128s           7856         1     32     304.4        13.9
SLH-DSA-SHA2-128f          17088         1     32      32.4        15.1
SLH-DSA-SHA2-192s          16224         1     48     800.0        17.2

process-spawn floor, measured: 13.34 ms   (`openssl version`, no cryptography at all)
```

**OpenSSL 3.5.4.** `pk B` is the **raw** key — the bytes that would be on a chain — parsed out of
the ASN.1, not the DER file size. *(An earlier draft reported DER sizes, which add a constant 22 B
for the lattice schemes and 18 B for the hash-based ones. That overstated the post-quantum cost.)*

### Cross-checked against the standards, not just against itself

**Every signature size matches FIPS 204 (ML-DSA) and FIPS 205 (SLH-DSA) exactly** — 2420, 3309,
4627, 7856, 17088, 16224 — and every raw public key matches too (1312, 1952, 2592, 32, 32, 48).
**So this measures the standards, not one library's quirks.**

### secp256k1 signatures are not a fixed size

An early run reported "70–72 B, three lengths" from a single key. **One key sampled repeatedly does
not characterise a distribution.** Measured properly — **20 keys × 60 signatures = 1,200 samples:**

```
69 B      3    0.2%
70 B    293   24.4%
71 B    574   47.8%     <- the mode
72 B    330   27.5%
```

DER drops leading zero bytes, so the length depends on the r and s a signature happens to produce;
**72 B is the theoretical maximum** (`0x30 len 0x02 33 r 0x02 33 s`). **"71 bytes" is widely stated
as a constant. It is the mode of a four-valued distribution, and it holds less than half the time.**

---

## 2. What it costs a chain — a v0.1 pay-to-pubkey spend

```
scheme                  1-in    1-in   x base    tx/1MB   blk MB for   chain GB/yr
                       1-out   2-out             block     same rate     same rate
-----------------------------------------------------------------------------------
secp256k1-ECDSA          200     276     1.0x     5,000          1.0          52.6
ML-DSA-44               3800    5125    19.0x       263         19.0         998.6
ML-DSA-65               5329    7294    26.6x       187         26.6       1,400.5
ML-DSA-87               7287    9892    36.4x       137         36.4       1,915.0
SLH-DSA-SHA2-128s       7954    7997    39.8x       125         39.8       2,090.3
SLH-DSA-SHA2-128f      17186   17229    85.9x        58         85.9       4,516.5
SLH-DSA-SHA2-192s      16338   16397    81.7x        61         81.7       4,293.6
```

**"Same rate"** = the block size and annual growth required to carry **the same number of
transactions per block** as secp256k1, at 2009 pacing (6 blocks/hour, 52,560 blocks/year, blocks
full — **an upper bound, not a forecast**).

> **A note on how NOT to compute this, because the first version of this table got it wrong.**
> Reporting chain growth at a **fixed 1 MB block** returns ~52 GB/yr for every scheme — of course
> it does, since `(1MB ÷ tx) × tx × blocks` is the block-size limit restated. **It measures the cap,
> not the signature.** The comparison has to hold *throughput* constant instead.

---

## 3. The finding: the objection is not CPU. It is bytes.

**Verification is essentially free, and the measurement can barely see it.** Every scheme verifies in
**12–17 ms against a measured process-spawn floor of 13.34 ms.** Subtract the floor and the
cryptographic cost is **under ~4 ms for all of them, and for several it is inside the noise.**

> **Post-quantum verification is not slow.** The intuition that PQ is "expensive to compute" does not
> survive measurement — at least not on the verify path, which is the one every node walks for every
> signature in history.

**What does not survive is size.** A transaction grows **19× to 86×**, and because a chain keeps
everything forever, that multiplier applies to the entire history:

```
secp256k1        52.6 GB/yr        the chain as it exists
ML-DSA-44       998.6 GB/yr        a terabyte a year
SLH-DSA-128s  2,090.3 GB/yr        two terabytes a year
SLH-DSA-128f  4,516.5 GB/yr        four and a half terabytes a year
```

> **⇒ The cheapest test for any post-quantum proposal, with numbers behind it: what does a signature
> cost in bytes, and what did you do about it?** *"Verification is fast enough"* answers a question
> nobody was asking.

### Signing, unlike verifying, is not free

**SLH-DSA-128s signs in ~304 ms and 192s in ~800 ms**, against ~18 ms for everything else. The `f`
("fast") variants invert it: **128f signs in ~32 ms but produces 17,088 B — more than twice 128s.**
The parameter sets are a direct trade.

### And the ranking flips with the output type

**For pay-to-pubkey, both the signature and the key are on chain.** That is what this laboratory's
own experimental chain uses (51 of 51 outputs), and what the earliest 2009 coins use.

```
                    sig B  +   pk B   =   on-chain crypto payload
secp256k1              71  +     65   =       136 B
ML-DSA-44            2420  +   1312   =     3,732 B      key is 35% of the cost
SLH-DSA-SHA2-128s    7856  +     32   =     7,888 B      key is 0.4% of the cost
```

**The two-output column above makes this visible.** A second output costs **ML-DSA-44 +1,325 B** and
**SLH-DSA-128s +43 B** — each new output carries another public key, and their key sizes differ by
forty-one times.

**Under pay-to-pubkey-hash, where the chain holds only a 20-byte hash until spend, ML-DSA's large
key is deferred and it wins comfortably. Under pay-to-pubkey it does not.** A signature scheme
cannot be chosen without choosing an output type at the same time.

---

## 4. What this does not establish

```
NOT   a recommendation. This measures costs; it does not weigh them, and it favours no scheme
NOT   a claim about migration. Coins already in pay-to-pubkey outputs have their keys exposed, and
      moving them REQUIRES a signature under the old scheme. That is a governance question, and no
      measurement settles it
NOT   absolute performance. Timings are wall-clock around a subprocess; the spawn floor is reported
      so it can be subtracted, but a library benchmark would be sharper
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
where process spawn is cheaper, which compresses the timing columns and *strengthens* §3; or a
change to the transaction model, which is the only computed part and is printed next to its
validation so it can be checked rather than trusted.

**If something here is wrong, it is a defect and will be corrected in the open rather than argued
about.** Corrections are published, dated, and never made silently.
