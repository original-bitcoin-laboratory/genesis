# What the origin permitted: the January 2009 client has no policy layer

**20 September 2026.** The dispute over what belongs on Bitcoin's base layer is usually argued as a
dispute about the origin: that the January 2009 design was minimal and later additions made it carry
what it should not, or the reverse. Neither reading survives running it. The January 2009 client has
**no relay-side filter on what it receives**: nothing in it inspects an incoming block or transaction
and declines it for its shape. It does carry two rules the register grades as policy — replacement by
`nSequence` and the fee rule (`OBL-C-0015`, `OBL-C-0017`, rows 7 and 8 below) — and both act when the
node *builds or sends*, not when it receives. The rules that keep data off the chain by refusing it on
arrival came later: the standardness test in December 2010, the data-carrier limit in 2014. The origin permits blocks up to 32 MiB, any
script the interpreter can run with every opcode live, outputs of any value including zero, and any
transaction that validates. Minimality, where Bitcoin has it, is a choice its later versions made and
kept in node-local policy; it is not a property the origin had. Findings register: `OBL-F-0038`.

> ### What is already known, and what this note adds
>
> **The distinction between consensus and policy is known**, and so is the fact that `IsStandard`
> arrived in 0.3.19.
>
> ```
> ALREADY VISIBLE       that later Bitcoins filter what they relay and mine; that v0.1 has no IsStandard
>
> ADDED HERE            the inventory, executed against the January side, of what the origin lets through
>                         that later policy stops -- each item a register row with a witness -- and the
>                         statement, with those witnesses, that the origin's base layer is the most
>                         permissive in Bitcoin's history, not the least
> ```
>
> **No position is taken** on what the base layer should carry. The note states what the origin did.

---

## The inventory

Each row: what the January client accepts, the later rule that stops it, and the witness.

| the origin accepts | the later rule that stops it | witness |
|---|---|---|
| a block of any size up to `MAX_SIZE` = 32 MiB (`main.cpp:1160`) | 1 MB, a validity rule from 7 Sep 2010 (`f1e1fb4bd`, from block 79,401), ungated 19 Sep 2010 (`172f00602`) | `OBL-F-0016`, `OBL-C-0001` |
| a transaction of any size the block ceiling admits — January's `CheckTransaction` carries no size test at all | a per-transaction rule in two steps: 32 MiB, 25 Aug 2010 (`401926283`), then 1 MB, 13 Sep 2010 (`3df62878c`) | `OBL-C-0010` |
| any output script the interpreter runs, across 106 opcode values of which 94 have an execution branch, including `OP_CAT`, `OP_MUL`, `OP_LSHIFT` | fifteen opcodes disabled 15 Aug 2010 (`4bd188c43`, "misc changes") | `OBL-F-0010`, `OBL-C-0005` |
| script elements, stacks and operation counts of any size | the 2010 caps: element 5,000 then 520 and stack 1,000 (29 Jul – 15 Aug 2010); the op count enters separately as `nOpCount++ > 200` on 31 Jul 2010 (`6ff5f718b`) and takes the form `> 201` on 7 Sep 2010 (`f1e1fb4bd`) | `OBL-F-0003`, `OBL-F-0035`, `OBL-C-0002` |
| an output of value zero, or of any value up to the signed 64-bit range; two large outputs whose sum wraps | the bounds as `d4c6b90ca` writes them — `MAX_MONEY` and an inline output-sum test — 15 Aug 2010, after block 74638; the identifier `MoneyRange` itself enters four days later, in `05454818d` | `OBL-F-0004`, `OBL-C-0003` |
| a transaction whose outputs match no template, carries more than two signature operations, or is under 100 bytes, **relayed and mined** | `IsStandard`, a relay-and-mining policy, 7 Dec 2010 (`a206a2398`) | `OBL-F-0036`, `OBL-C-0011` |
| a transaction paying no fee, relayed (the fee rule is applied when a node *builds a block or sends a transaction*, not when it *receives* one) | the relay-side fee gate, 12 Dec 2010 (`97ee01ad8`) | `OBL-F-0030`, `OBL-C-0017` |
| a replacement of an unconfirmed transaction by `nSequence` | disabled 19 Aug 2010 (`05454818d`) | `OBL-F-0028`, `OBL-C-0015` |
| a block whose sigops are unbounded | `MAX_BLOCK_SIGOPS` = size/50, 7 Sep 2010 (`f1e1fb4bd`) | `OBL-C-0004` |
| an arbitrary-data output: any script, any length under the block ceiling, no data-carrier rule | the data-carrier relay limit is `MAX_OP_RETURN_RELAY = 40` in v0.9.0, 2014, outside this register's window | not entered |

What the origin *does* enforce is the validity core: proof of work against the target, the merkle root,
the coinbase's position and its script-size bounds, no double spend, no inflation beyond the subsidy,
signature validity as OpenSSL's parser reads it, and coinbase maturity at spend. That core is complete
enough to run a chain (`REPRODUCTIONS.md`, `r5-findings/`) and it filters nothing by shape, template or
purpose.

## What follows

- **"The origin was minimal" is false in the sense the dispute uses it.** The January base layer is the
  most permissive in Bitcoin's history: the largest block ceiling, the widest opcode vocabulary, no
  standardness, no relay fee, no data-carrier limit. Everything that keeps data off later Bitcoins is a
  later rule, and most of it is policy, node-local and changeable without a fork.
- **"Later additions loaded the base layer" conflates two things.** The 2010 consensus additions
  (`MoneyRange`, the caps, the ceiling, cumulative work) *narrowed* what a block may contain and fixed
  holes the record names (`OBL-C-0003` cites block 74638). What is argued over today (arbitrary-data
  outputs, their relay defaults) is policy the origin did not have in either direction.
- **A layered design that keeps state above the base layer needs rules the origin lacks.** Time-based
  locks are 29 October 2009 (`OBL-C-0007`); the sequence-lock and check-lock-time rules that payment
  channels rest on, and the malleability fix, are 2015–2017, outside this register's window. The origin's
  own layering is elsewhere: its marketplace ran beside the chain in a flood pub/sub channel and did not
  touch the ledger (`inventory/MARKET_AUDIT.md`), and its author argued in December 2010 for separate
  chains rather than one chain carrying everything (`BITDNS-AND-LAYERING.md`).

## Limits

```
NOT a claim about what the base layer should carry   this note states the origin's rules and dates the later ones
NOT a claim about the 2009 network                    a source line shows what the code enforces; a port shows what an
                                                      implementation does; no grade here attests what the network accepted
BOUNDED by the register's window                      rules after 2010 are not entered, including the
                                                      2014 data-carrier relay limit
```

Grades: the origin's rules `JAN09-SOURCE` where read (`main.cpp:1160`, `script.cpp`, `main.h`), `MODEL` where
a port executes the divergence (`derivatives/origin_policy/`, `overflow/`, `script_limits/`), `EXECUTED
(release build)` where the release client replayed the case (`OBL-F-0010`); the later rules `RECORD`, dated on
the trailer lineage.

**Corrections to this note are published, dated, and not made silently.**

*Corrected 25 September 2026, before signing, after a review checked the inventory against the register
rows it cites and against a clone of `bitcoin/bitcoin`. Seven statements were wrong:*

1. *"No relay policy at all. Every rule it enforces … is a validity rule." The register grades two January
   rules as policy — replacement by `nSequence` and the fee rule — and this note's own rows 7 and 8
   describe them. The claim is narrowed to what holds: no relay-side filter on what the node receives.*
2. *The data-carrier limit was placed "after 2015". `MAX_OP_RETURN_RELAY = 40` ships in v0.9.0, 2014.*
3. *The opcode row said "all 106 opcode values live". 106 values exist; 94 have an execution branch.
   `OBL-F-0038` carried the same phrasing and is corrected.*
4. *The overflow row named the rule `MoneyRange`. That identifier enters four days after the commit named,
   in `05454818d`; `OBL-C-0003` was corrected for this on 20 September and this note was not.*
5. *The script-limits row placed an op count of 201 inside a 29 Jul – 15 Aug window. Neither commit in that
   window carries the limit: it enters as `> 200` on 31 July and takes the form `> 201` on 7 September.*
6. *The transaction-size row cited only the second of the rule's two steps, omitting 32 MiB on 25 August.*
7. *The fee row said the rule applies when the wallet builds a transaction; it applies when a node builds a
   block or sends one.*

*The ten-row shape, every commit date, the fifteen disabled opcodes and the validity-core paragraph were
re-verified in the same pass and are unchanged.*

---

*Experimental laboratory research, in progress: what re-runnable methods find, and no conclusion beyond that. Not money — no premine, no sale, no value assigned, no token. Not financial advice. No warranty. [Rights, sourcing and corrections](https://github.com/original-bitcoin-laboratory/genesis/blob/main/RIGHTS.md).*
