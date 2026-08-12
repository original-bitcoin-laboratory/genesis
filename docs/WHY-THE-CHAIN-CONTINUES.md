# Why this chain continues, and where it stops

**12 August 2026.** Until today this chain had no stated purpose past about a hundred blocks. It
had a *history* — every block bound to its binary, cross-validated, byte-exact append-only — but no
**hypothesis**. Block 200 would have demonstrated nothing block 64 did not.

**That is now fixed. The chain has one remaining question to answer, a stated target, and a stated
stopping point.**

---

## The question

```
Does the 2009 difficulty retarget execute correctly on the released binary?
```

**It is the last untested consensus path in v0.1.** Everything else is already `JAN09-EXECUTED` on a
real chain rather than modelled:

```
subsidy and halving arithmetic       executed
coinbase maturity                    executed (and corrected: 120, not 100 --
                                     main.cpp:544 returns max(0, (COINBASE_MATURITY+20) - depth))
script interpreter                   executed
serialization and wire format        executed
block acceptance and reorg           executed  (R4b: a retained orphan, +223 bytes)
transaction relay                    executed  (R4c: same txid in both node logs, height 122)
proof-of-work at difficulty 1        executed  64 of 64 blocks
DIFFICULTY RETARGET                  NEVER RUN
```

**The retarget fires at height 2016** — `nTargetTimespan / nTargetSpacing` in `main.cpp`. Until a
chain reaches that height, the code path has never executed outside a test harness.

## Why it is worth answering at all

**Because "we ran the earliest Bitcoin" is a claim about the whole client, and one consensus rule
in it has never run.** The laboratory's standard is `EXECUTED`, not `MODELLED` — that distinction is
the reason this project exists rather than being a description of somebody else's software.

⚠️ **And it is a genuine question, not a formality.** The retarget reads timestamps from the chain
and computes a new target from them. On a chain mined by a single node at wildly irregular intervals
— our observed gaps run from minutes to hours — **the inputs are far outside anything the 2009
network produced.** What v0.1 does with them is not obvious from reading it, and the honest way to
find out is to run it.

## The cost, stated plainly

```
current height                64
target                        2016
blocks needed                 1,952
observed cadence              ~105 min/block
                              ⚠️ NOT A MEASUREMENT -- 10 exponential samples carry ~32% standard
                              error. It is an order-of-magnitude figure and nothing more.
implied duration              roughly 4-5 MONTHS of continuous mining
```

> **This is why the decision needed making rather than drifting.** Four months of a VM running
> unattended is a real commitment, and it is only worth making for a stated result. **It now has
> one.**

## The stopping rule

```
STOP AT 2016, or at the first retarget, whichever comes first.

There is nothing after it. Height 4032 is the same code a second time. The halving at 210,000
is unreachable at any plausible rate -- roughly forty years -- and would demonstrate arithmetic
already proven from the source.
```

**When the retarget executes, the R-series and the chain series are both complete and the chain
enters maintenance: it keeps running for availability, and no further height is a result.**

⚠️ **If the VM stops before 2016 for any reason, that is not a failure.** The chain's existing
results stand exactly as they are — the append-only proof, the cross-validation, the custody
separation, every binding. **This target adds one result; it does not put the others at risk.**

## What will be recorded when it fires

```
the last block before the retarget and the first after it, with their nBits
the timestamps the retarget consumed, and the new target it computed
whether that computation matches an independent implementation of the same rule
the binary binding across the boundary -- pre and post, same process if possible
```

**And the honest negative:** if the retarget produces something surprising on a single-miner chain
with irregular timestamps, **that is the finding**, and it gets published exactly as readily as a
clean pass. A laboratory that only publishes the results it expected is not measuring anything.

---

## The rule this makes explicit

> ★ **A chain that keeps growing without a stated hypothesis is activity, not evidence.** Height by
> itself proves nothing after the first few blocks — it is the *specific rule that height unlocks*
> that is worth waiting for.
>
> **Every future round of mining should be able to name what it is evidence for. Until height 2016,
> the answer is "the difficulty retarget". After it, the honest answer is "nothing further", and the
> mining should be described as maintenance rather than as an experiment.**

**Not money.** No premine, no token, no sale, no price. Reaching height 2016 changes none of that.
