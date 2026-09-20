# Script resource limits, executed — v0.1's EvalScript vs the 2010 ceilings

**Evidence level: `MODEL`.** The companion to [`../overflow/`](../overflow/): it makes runnable
the *other* [`CONSENSUS_SURFACE.md`](https://github.com/original-bitcoin-laboratory/common/blob/main/conformance/CONSENSUS_SURFACE.md) finding —
v0.1's Script interpreter enforces **no resource ceilings**. Verified in source, v0.1's
`EvalScript` has only *underflow* guards (`if (stack.size() < N)`), no upper bound; the element cap,
the op‑count limit, the stack‑size limit and the numeric-operand cap have **0 occurrences**. Each was
added in mid-2010, and each is dated here to the commit that carries it.

## The ceilings, dated

```
element size   5000 in 757f0769d (29 Jul 2010, 0.3.6) -> 520 in 4bd188c43 (15 Aug 2010, 0.3.10)
stack depth    1000 (stack + altstack) in 757f0769d
numeric cap    258 in 757f0769d -> 4 in 4bd188c43
script size    20000 in 757f0769d -> 10000 in 6ff5f718b (31 Jul 2010, 0.3.7)
op count       `nOpCount++ > 200` in 6ff5f718b ("additional security limits"): 201 allowed;
               `opcode > OP_16 && ++nOpCount > 201` in f1e1fb4bd (7 Sep 2010), same boundary,
               pushes and OP_1..OP_16 excluded -- the form modelled here
```

Constitution row `OBL-C-0002`; the archaeology is `docs/SCRIPT-LIMITS-RETROFITTED.md` (four caps) and
`docs/CONSENSUS-ATLAS.md` §13 (the op count). *Until 20 September 2026 this README attributed the
op-count limit to "the 2010 Script hardening" of 29 July and 15 August; neither commit carries it. An
adversarial review caught that (`OBL-F-0035`).*

## What it shows

```
600-byte element (> 520)
  v0.1 EvalScript (no limits) : VALID   (peak elem 600B, ops 1, stack 1)
  2010 hardened rule          : REJECT  (clause: element-size)
250 opcodes (> 201)
  v0.1 EvalScript (no limits) : VALID   (peak elem 1B, ops 250, stack 1)
  2010 hardened rule          : REJECT  (clause: op-count)
1500-deep stack (> 1000)
  v0.1 EvalScript (no limits) : VALID   (peak elem 1B, ops 0, stack 1500)
  2010 hardened rule          : REJECT  (clause: stack-size)
9-byte numeric operand
  v0.1 EvalScript (no cap)    : VALID
  29 Jul 2010 cap (258)       : (True, 'ok')
  15 Aug 2010 cap (4)         : (False, 'numeric-operand')
```

Each script is a **valid v0.1 script** that exceeds one 2010 ceiling. It runs to completion
on the lab's real v0.1 interpreter ([`../model/evalscript_model.py`](../model/evalscript_model.py),
the one differential‑tested against the C++/OpenSSL PORT on 63 vectors) and leaves *true* —
while the peak it reached is over the limit. The hardened checker then applies the dated
2010 bounds and rejects it. Same "one engine, v0.1 rule vs later rule" structure as the
overflow suite.

## How the peaks are obtained

`measure()` runs the **genuine v0.1 model** and reads the peak element size, op count, and
peak stack depth *through the model's own trace hook* — so the numbers come from a real
execution, not a re‑implementation. The ceilings are isolated cleanly: the op‑heavy
script grows the stack by only 1 (so it trips *only* the op limit), and the deep‑stack script
is grown with pushes (op_count `0`, so it trips *only* the stack limit). `measure_numeric()` records
the largest element a numeric opcode read as a number, operands not results.

Every check returns `(ok, clause)` with the clause from a fixed vocabulary (`ok`, `structural`,
`op-count`, `element-size`, `stack-size`, `numeric-operand`); the tests assert the clause, and write the
expected ceilings as literals of their own rather than importing them from the module under test.

## Tests (`test_script_limits.py`, 10; `test_numeric_cap.py`, 6)

The three divergences (v0.1 valid, hardened rejects — element/ops/stack); controls (a normal
arithmetic script passes both; a structural underflow fails both); exact boundaries (201 ops
ok / 202 rejected; 520 B ok / 521 rejected; 1000 deep ok / 1001 rejected); the module's constants
against the dated values; op‑count fidelity (data pushes and OP_1..OP_16 don't count; OP_DUP/OP_DROP
do); the numeric cap at both of its 2010 values (a 9-byte operand passes 258 and fails 4; 258 bites at
259; 4 bites at 5), on operands not results, and a structural failure reported as v0.1's own.

```bash
python script_limits.py   # the demo above
python -m pytest          # 16 passed
```

## Boundary

MODEL; the v0.1 side is the lab's executed interpreter; the ceilings are the dated 2010 constants. The
script-size cap (20,000 → 10,000 bytes) is dated above and not exercised here, since the model's scripts
are token lists rather than serialised bytes. Not a live‑exploit claim — these are prudential DoS
bounds, and v0.1 simply predates them. A tool, not authority (`common/AUTHORITY.md`).
