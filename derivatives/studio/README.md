# Transaction Studio (R7) — headless script debugger

**Evidence level: `MODEL`.** The first R7 tool: step a v0.1 Script through the lab's
own EvalScript and see the **stack after every opcode**, then the verdict — over the
**full vocabulary**, so you can watch the ops BTC disabled actually run.

```python
from studio import render
print(render([b"\x11", b"\x22", "OP_CAT", "OP_SHA256", h, "OP_EQUAL"]))
```

```
  op         stack (after)
  -------    ------------------------
  push 1122  [1122]
  push 3344  [1122 3344]
  OP_CAT     [11223344]              <- OP_CAT (disabled in BTC) concatenates
  OP_SHA256  [1a835ed8734f8635…(32B)]
  push …     [1a835ed8734f8635…(32B) 1a835ed8734f8635…(32B)]
  OP_EQUAL   [01]
  => VALID — true on top
```

## API

- `trace(tokens, checker=None)` → `(rows, ok, is_valid)` — `rows = [(op, stack_after)]`.
- `render(tokens, checker=None, title=None)` → a printable trace table + verdict.
- `disasm(script_bytes)` → token list (trace a raw on‑the‑wire script).
- `trace_spend(scriptSig, scriptPubKey, tx, n_in)` — trace the exact v0.1
  VerifySignature script (`scriptSig + OP_CODESEPARATOR + scriptPubKey`) with a
  signature checker.

Scripts are token lists (`bytes` = data push, `"OP_NAME"` = opcode). The verdict
distinguishes **structural failure** (underflow, bad opcode) from **ran‑but‑top‑not‑
true** from **VALID**.

## Run

```bash
python studio.py         # traces an OP_CAT hash-lock and an arithmetic script
python -m pytest         # 5 passed
```

Implemented via a minimal `trace` hook added to `../model/evalscript_model.run`
(back‑compatible; the model suite is unchanged at 51). This is the debugger/stack
tracer of R7; the composer / UTXO viewer / evidence exporter build on the same engine
plus `../ledger` and are the natural next studio pieces.
