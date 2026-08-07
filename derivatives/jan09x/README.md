# JAN09‑X — the released chain, full vocabulary, isolated (R8)

**Evidence level: `MODEL`.** The symmetric twin of NOV08‑X. JAN09‑X runs the
**released January 2009 constitution** — `COIN=1e8`, 50‑coin subsidy, 210k halving, 10‑min
spacing, **compact** proof‑of‑work, `≤` coinbase rule (exactly what the lab's
`../p2p/chainsync` + `../node` already execute) — with the **full opcode vocabulary
re‑opened** and its own isolated network identity.

## Nothing disabled — re‑opening `OP_NOTEQUAL`

v0.1's EvalScript already runs the broad vocabulary BTC later removed (`OP_CAT`,
`OP_MUL`, `OP_DIV`, `OP_LSHIFT`, `OP_INVERT`, `OP_2MUL`, …). The **one** functional
opcode Satoshi disabled is **`OP_NOTEQUAL`** (byte‑level inequality), commented out at
`script.cpp:486`. JAN09‑X re‑opens it — a **NEW‑EXP** decision, disclosed *with*
Satoshi's own reason (`script.cpp:494`):

> *"OP_NOTEQUAL is disabled because it would be too easy to say something like n != 1
> and have some wiseguy pass in 1 with extra zero bytes after it (numerically,
> 0x01 == 0x0001 == 0x000001)."*

`script_full.py` realises it as `OP_EQUAL` then `OP_NOT` (both live) — so nothing new
is invented — and the tests **reproduce that exact footgun**: `0x01 OP_NOTEQUAL
0x0001` is *true* (byte‑unequal) even though `1 == 1` numerically. This is the honest
face of "nothing disabled": the full expressive power is available, and the reason it
was fenced off is preserved alongside it.

## Isolated network identity (NEW‑EXP)

| Item | JAN09‑X | vs |
|---|---|---|
| network magic | `f0 0b a7 09` | mainnet `f9 be b4 d9`, NOV08‑X `f0 0b a7 08` |
| default port | `18009` | `8333` |
| address version | `0x36` | `0x00` |
| genesis | freshly mined (compact regtest‑easy PoW), coinbase *"JAN09‑X lab chain: v0.1.0 released rules, full vocabulary, not money"*, 50‑coin reward | JAN09 `000000000019d668…` |

Two isolated nodes synchronise the JAN09‑X chain over that magic; a mainnet‑framed
message is refused.

## Files & run

```bash
python net.py           # mint the JAN09-X genesis + sync two nodes
python -m pytest        # 13 passed (OP_NOTEQUAL semantics + footgun, full vocab, identity, sync)
```

`script_full.py` (re‑opened vocabulary), `net.py` (identity + genesis + two‑node
sync, reusing `../p2p/chainsync`), `test_jan09x.py`.

## Boundary

JAN09‑X reuses the lab's already‑executed JAN09 semantics (subsidy/PoW/coinbase live
in `../node`, script in `../model`+`../port`); it adds only the **re‑opened opcode**
and the **isolated identity**. It is **not** the historical Bitcoin chain and **not**
"true Bitcoin" — a new experimental descendant, units are not historical satoshis,
no inherited balances. Paired with `../nov08x`, the two give the counterfactual
question both answers: *what the November design and the January release each become
when completed with nothing disabled.*
