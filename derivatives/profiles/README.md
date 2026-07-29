# Rule profiles

> Make **"which rules is this run using"** an explicit, verifiable object — not an implicit
> code path. Evidence level: **MODEL**. **NOT money.**

The lab runs the origin's rules in two distinguishable postures, and it matters which one a
given result rests on. A **profile** names one configuration by pairing:

- a **consensus rule set** — the monetary / PoW / coinbase parameters, read faithfully from a
  source edition (`derivatives/nov08x/rules_nov08.json`, `rules_jan09.json`); and
- a **script-vocabulary posture** — how the EvalScript vocabulary is treated.

## The two script postures

| Posture | Engine | `OP_NOTEQUAL` | Class |
|---|---|---|---|
| `faithful-v0.1` | `model/evalscript_model.py` (`run`) | **disabled** — as v0.1 shipped it (commented out, `script.cpp:486`; reason `script.cpp:494`) | faithful |
| `nothing-disabled` | `jan09x/script_full.py` (`run_full`) | **re-opened** — realized as `OP_EQUAL` then `OP_NOT`, both native to v0.1 | NEW-EXP |

`OP_NOTEQUAL` is the *only* functional opcode v0.1 disabled (see `inventory/OPCODES.md`), so it
is the single bit that separates the faithful reconstruction from the "nothing disabled"
experimental networks.

## The load-bearing invariant

**"Nothing disabled" is safe only because it is "not money."** Re-opening a rule the origin
disabled is defensible on an isolated, valueless experimental network and nowhere else. The
faithful postures reproduce v0.1 exactly as written; the `NEW-EXP` postures (`jan09-x`,
`nov08-x`) are the live isolated networks and carry no value. See `docs/PUBLIC_TESTNET_SCOPE.md`
and `docs/AUDIT_SCOPE.md`.

## The profiles

| Profile | Chain | Consensus | Script | Class |
|---|---|---|---|---|
| `jan09-faithful` | jan09 | `rules_jan09` | `faithful-v0.1` | faithful |
| `jan09-x` | jan09 | `rules_jan09` | `nothing-disabled` | NEW-EXP |
| `nov08-source-bounded` | nov08 | `rules_nov08` | `faithful-v0.1` | source-bounded |
| `nov08-x` | nov08 | `rules_nov08` | `nothing-disabled` | NEW-EXP |

`jan09-faithful` and `jan09-x` share consensus and differ **only** in script vocabulary;
`nov08-source-bounded` applies the November constitution over the v0.1-derived script substrate
the preview itself lacks.

## Use it

```bash
python profiles.py            # print the registry and verify every declaration
python -m pytest -q           # test_profiles.py binds declaration -> engine + inventory
```

```python
import profiles
p = profiles.load("jan09-faithful")
run = p.runner()              # the faithful engine (OP_NOTEQUAL disabled)
rules = p.rules()             # consensus.Rules for the monetary / PoW / coinbase math
```

`profiles.verify()` returns an empty list only when, for every profile, the declared
disabled/re-opened opcode set matches the reproducible inventory **and** the live engine
actually behaves that way (the faithful engine fails on `OP_NOTEQUAL`; the nothing-disabled
engine runs it and computes byte inequality). A declaration cannot drift from the code without
turning the check red.
