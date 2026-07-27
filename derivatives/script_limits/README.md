# Script resource limits, executed — v0.1's EvalScript vs the 2010 ceilings

**Evidence level: `MODEL`.** The companion to [`../overflow/`](../overflow/): it makes runnable
the *other* [`CONSENSUS_SURFACE.md`](../../../common/conformance/CONSENSUS_SURFACE.md) finding —
v0.1's Script interpreter enforces **no resource ceilings**. Verified in source, v0.1's
`EvalScript` has only *underflow* guards (`if (stack.size() < N)`), never an upper bound;
`MAX_SCRIPT_ELEMENT_SIZE`, the op‑count limit, and the stack‑size limit have **0 occurrences**.
They were all added in the 2010 Script hardening.

## What it shows

```
600-byte element (> 520)
  v0.1 EvalScript (no limits) : VALID   (peak elem 600B, ops 1, stack 1)
  2010 hardened rule          : REJECT  (element size 600 > 520)
250 opcodes (> 201)
  v0.1 EvalScript (no limits) : VALID   (peak elem 1B, ops 250, stack 1)
  2010 hardened rule          : REJECT  (op count 250 > 201)
1500-deep stack (> 1000)
  v0.1 EvalScript (no limits) : VALID   (peak elem 1B, ops 0, stack 1500)
  2010 hardened rule          : REJECT  (stack size 1500 > 1000)
```

Each script is a **valid v0.1 script** that exceeds one modern ceiling. It runs to completion
on the lab's real v0.1 interpreter ([`../model/evalscript_model.py`](../model/evalscript_model.py),
the one differential‑tested against the C++/OpenSSL PORT on 63 vectors) and leaves *true* —
while the peak it reached is over the limit. The hardened checker then applies the documented
2010 bounds and rejects it. Same "one engine, v0.1 rule vs later rule" structure as the
overflow suite.

## How the peaks are obtained

`measure()` runs the **genuine v0.1 model** and reads the peak element size, op count, and
peak stack depth *through the model's own trace hook* — so the numbers come from a real
execution, not a re‑implementation. The three ceilings are isolated cleanly: the op‑heavy
script grows the stack by only 1 (so it trips *only* the op limit), and the deep‑stack script
is grown with pushes (op_count `0`, so it trips *only* the stack limit).

## Tests (`test_script_limits.py`, 9)

The three divergences (v0.1 valid, hardened rejects — element/ops/stack); controls (a normal
arithmetic script passes both; a structural underflow fails both); exact boundaries (201 ops
ok / 202 rejected; 520 B ok / 521 rejected; 1000 deep ok / 1001 rejected); and op‑count
fidelity (data pushes and OP_1..OP_16 don't count; OP_DUP/OP_DROP do).

```bash
python script_limits.py   # the demo above
python -m pytest          # 9 passed
```

## Boundary

MODEL; the v0.1 side is the lab's executed interpreter; the ceilings are the documented 2010
constants (`MAX_SCRIPT_ELEMENT_SIZE = 520`, op limit `201`, stack limit `1000`). Not a
live‑exploit claim — these are prudential DoS bounds, and v0.1 simply predates them. A tool,
never authority (`../../../common/AUTHORITY.md`).
