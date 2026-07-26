# NOV08-X vs JAN09 — differential

Same engine, two rule sets. NOV08 values are N-ORIG (read from the surviving
November source); JAN09 is the differential baseline.

## 1. Subsidy schedule (coins per block, by global best height)

| best height | NOV08-X | JAN09 |
|---|--:|--:|
| 0 | 100 | 50 |
| 99,999 | 100 | 50 |
| 100,000 | 50 | 50 |
| 200,000 | 25 | 50 |
| 209,999 | 25 | 50 |
| 210,000 | 25 | 25 |
| 420,000 | 6 | 12 |

NOV08-X starts at **100 coins**, halving every **100,000** blocks; JAN09 at 50, halving every 210,000.

## 2. Proof-of-work encoding

- **NOV08-X:** `nBits` = **leading zero bits**; target = `(~0) >> nBits`. MINPROOFOFWORK = **20** ('ridiculously easy for testing'). e.g. nBits=20 → target has 20 leading zero bits.
- **JAN09:** `nBits` = **compact** mantissa/exponent (e.g. `0x1d00ffff`); target = mantissa·256^(exp-3).

## 3. Retarget (one full window)

- **blocks came 3x too SLOW:** NOV08-X → nBits 24->23 (one bit EASIER);  JAN09 → target x4.00 (proportional, clamped 4x).
- **blocks came 3x too FAST:** NOV08-X → nBits 24->25 (one bit HARDER);  JAN09 → target x0.71 (proportional, clamped 4x).

NOV08-X nudges by **±1 bit** (max one change per 30-day window); JAN09 scales the target **proportionally** over its 14-day window.

## 4. Coinbase value rule

A coinbase paying **one unit less** than subsidy+fees:

- **NOV08-X:** claim 99999999 vs block value 100000000 → **REJECT** (rule: exact equality).
- **JAN09:** claim 4999999999 vs block value 5000000000 → **ACCEPT** (rule: upper bound).

## 5. Denomination & fee

- **NOV08-X:** COIN = 1,000,000 units (no 'satoshi'); fixed fee = 10,000 units (0.01 coin).
- **JAN09:** COIN = 100,000,000 units (1 'satoshi' = 1 unit); dynamic fee.

## 6. Nothing disabled

NOV08-X's Script engine (reconstructed from the interface NOV08 references) carries the **full original opcode vocabulary** — see `test_nov08x.py`, which runs `OP_CAT`/`OP_MUL`/… live. November never had a Script file to disable anything in.

