# Value-overflow surface, executed — v0.1's `CheckTransaction` vs the 2010 fix

**Evidence level: `MODEL`.** This makes the sharpest finding of
[`CONSENSUS_SURFACE.md`](https://github.com/original-bitcoin-laboratory/common/blob/main/conformance/CONSENSUS_SURFACE.md) *runnable* — the
same way [`../crypto_conformance/`](../crypto_conformance/) made the OpenSSL malleability
thread runnable. It ports v0.1's transaction sanity check and the post‑Aug‑2010 hardened
version **side by side**, and exhibits the exact transaction that one **accepts** and the
other **rejects**.

## What it shows

```
two outputs of 9223372036854277039 sat each (~92,233,720,368.54 BTC)
  v0.1 CheckTransaction (main.h:442) : ACCEPT  (ok)
  2010 CheckTransaction (d4c6b90ca)  : REJECT  (output-above-max-money)
  output total as int64 (C++)  :                  -997538 sat  <- wraps negative
  output total, true value     :     18446744073708554078 sat  = 184,467,440,737 BTC minted
  => v0.1's 'inputs >= outputs' sees outputs = -997538 and passes with a tiny input.
```

- **v0.1 `CheckTransaction`** ([`main.h:442`], ported verbatim) checks only `nValue < 0` per
  output — **no upper bound, no output‑sum check**. It **accepts** the transaction.
- **The post‑Aug‑2010 rule** adds `MoneyRange()` (per‑output and on the running total). It
  **rejects** the transaction.
- **The mechanism**: two outputs, each large but positive (so each passes `nValue < 0`),
  whose sum overflows a signed 64‑bit accumulator and wraps to a small **negative** number.
  A downstream `inputs >= outputs` check then sees a tiny (negative) total and passes, while
  the true minted value is ~184 billion BTC. Those are the **exact satoshi amounts** from the
  transaction in **block 74638 (15 Aug 2010)**; the incident and its 184,467,440,737 BTC total are recorded on
  the Bitcoin wiki's [Value overflow incident](https://en.bitcoin.it/wiki/Value_overflow_incident) page. The overflow block was replaced
  after the fix, so a present-day explorer at height 74638 ([blockstream.info](https://blockstream.info/block/000000000069e1affe7161ab4bcbeacebb4ddf155b50e807f42de971b688a09b)) shows a different block.

## Why the wrap is modelled explicitly

Python integers do not overflow, so the lab's big‑int ledger
([`../ledger/ledger.py`](../ledger/ledger.py)) sums outputs as arbitrary‑precision values and
therefore **does not reproduce the bug** — it would reject the transaction as inflation. That
gap between **fixed‑width C++ `int64`** and **big‑int Python** *is* the vulnerability, so this
module reproduces it faithfully with an explicit `to_int64` / `add_i64` (two's‑complement
64‑bit arithmetic) rather than hand‑waving it. Honest boundary: this is a **port**, not the
original binary executing; the value it adds is showing the accept/reject divergence on a
real, historical input.

## Tests (`test_overflow.py`, 10)

The finding (v0.1 accepts, hardened rejects the overflow tx); the mechanism (int64 sum wraps
to `-997538` while the true total is 2× the historical amount, > 184 billion BTC); the
divergence (`value_in >= value_out` passes on the wrapped total); controls (both rules reject
a negative output, both accept a normal tx, both keep the coinbase‑script‑size bound); and the
missing‑upper‑bound gap (v0.1 accepts an output of `MAX_MONEY + 1`, the 2010 rule rejects it).

```bash
python overflow.py     # the demo above
python -m pytest       # 10 passed
```

## Boundary

MODEL; objective source port of `main.h:442` + the documented Aug‑2010 fix; historical
amounts from the public record (the Bitcoin wiki's Value overflow incident page, linked above); no chain privileged; not a live‑exploit claim (the surface was
patched in 0.3.10). It is a *tool*, not authority (`common/AUTHORITY.md`).
