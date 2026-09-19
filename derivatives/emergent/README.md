# The two rules nobody wrote, executed — Berkeley DB locks and OpenSSL's DER parser

**Evidence level: `MODEL`** (the DER rule also has one side executed on the release build, recorded in
the corpus). Constitution rows `OBL-C-0013` and `OBL-C-0014`; the archaeology is in
[`docs/CONSENSUS-ATLAS.md`](../../docs/CONSENSUS-ATLAS.md) §8 and §9. Same shape as
[`../overflow/`](../overflow/): port the January 2009 side and the later rule side by side, and exhibit
the input one accepts and the other rejects.

```
python bdb_locks.py          # the 8bd028818 clause against v0.1's size/count clauses
python der_strictness.py     # BIP 66 IsValidSignatureEncoding over ../vectors/checksig.json
python -m pytest -q          # 10 checks
```

## What it shows

```
BERKELEY DB LOCK RULE
  block: 2251 transactions, 139,647 B, 4501 distinct txids referenced
  v0.1  CheckBlock size/count clauses : (True, 'ok')
  0.8.1 CheckBlock 8bd028818 clause    : (False, '15 May maxlocks violation')   block time inside 11 Mar..15 May 2013
  0.8.1 same block, time after 15 May  : (True, 'ok')
  0.8.1 block with 4499 ids            : (True, 'ok')

DER STRICTNESS
  7 strict signatures in the corpus pass BIP 66
  3 probes (long-form length; redundant 0x00 pad; a byte before the sighash flag) fail BIP 66,
    and a BER-tolerant reader recovers an (r, s) whose strict re-encoding passes BIP 66
  the release build (OpenSSL 1.0.2u) rejects all three (OBL-F-0010); the 2009 binary is not replayed yet
```

## What is ported, and what is not

- **`bdb_locks.py`.** The 0.8.1 clause of commit `8bd028818` ("CheckBlock rule until 15-May for
  10,000 BDB lock compatibility") line for line: within `(1363039171, 1368576000)` a block that
  references more than 4,500 distinct transaction ids (every transaction's own id plus every
  non-coinbase input's prevout) fails with "15 May maxlocks violation". Against it, the v0.1
  `CheckBlock` clauses that bound a block's size and count (`MAX_SIZE = 0x02000000`). The lock table
  itself is not modelled: it was never a rule anyone stated, which is what the row records. The
  block is synthetic (no proof of work, no merkle check); those clauses are not under test.
- **`der_strictness.py`.** `IsValidSignatureEncoding` from BIP 66, in the reference's order. The
  tolerant reader models the three tolerances the corpus probes, so that "a tolerant parser reads
  it" is a statement the test can check; it is not a model of OpenSSL 0.9.8, and the corpus keeps
  `expected_binary: null` on the probes until that binary answers.

## What this does not claim

No claim about OpenSSL 0.9.8's verdict on the probes, no claim about how many pre-0.8 nodes rejected
block 225,430, and no position on either rule. The block bytes of March 2013 are not reproduced; the
rule written about them is. NOT money.
