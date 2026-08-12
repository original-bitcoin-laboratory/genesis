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

## ⚠️ What "stopping" means, stated so it cannot be misread in twenty years

**THE EXPERIMENT ends at 2016. THE MINING is not constrained by anything in this document.**

```
THE EXPERIMENT    ends when the retarget fires. After that, further height is NOT a result,
                  NOT evidence, and must not be presented as either.

THE MINING        is free. It may continue forever, stop tomorrow, pause for a year and
                  resume. Nothing here obliges it to run, and nothing here forbids it.
```

> ★ **Naming a hypothesis constrains what may be CLAIMED, never what may be DONE.** The experiment
> is a subset of the operator's freedom to run the chain, not a limit on it. **A chain that keeps
> growing after its last hypothesis is answered is perfectly fine — it is simply not evidence, and
> the honest word for it is maintenance rather than experiment.**

**If the VM stops before 2016 for any reason, that is not a failure.** Every existing result stands
— the append-only proof, the cross-validation, the custody separation, every binding. **This target
adds one result; it does not put the others at risk.**

## ★★ THE PREDICTION, pre-registered before the experiment runs

**Naming the hypothesis forced a calculation nobody had done, and the expected answer is a surprise
worth stating in advance: the retarget will execute and change nothing.**

```
this chain mines at nBits 0x1d00ffff, which IS bnProofOfWorkLimit -- difficulty 1, the easiest
                    the protocol allows

at ~105 min/block the chain is ~10.5x SLOWER than the 10-minute target, so the retarget
                    wants to LOOSEN the target

    nActualTimespan > nTargetTimespan*4          -> clamped to a 4x step
    bnNew = 0x1d00ffff * 4                       -> LARGER than bnProofOfWorkLimit
    if (bnNew > bnProofOfWorkLimit)              -> clamped straight back
        bnNew = bnProofOfWorkLimit;

=> nBits stays EXACTLY 0x1d00ffff.
```

**So the predicted result is a no-op**, and the cadence after 2016 stays ~105 min/block — which also
means height 4032 is another ~147 days, not a cheap follow-on.

> ### ⇒ What the experiment is worth, honestly, now that the answer is predictable
>
> **Less than it looked, and still worth having.** What executing it proves:
>
> ```
> the code path RUNS on a real chain rather than in a test harness
> nActualTimespan is computed from real block timestamps
> the 4x clamp behaves
> the proof-of-work-limit clamp behaves -- the branch that makes this a no-op
> ```
>
> ★★ **And the prediction is the valuable part.** A stated-in-advance expectation that is then
> checked is stronger than any observation made afterwards. **If `nBits` is anything other than
> `0x1d00ffff` at height 2016, this prediction is wrong and THAT is a significant finding** — far
> more interesting than the expected pass.
>
> ⚠️ **This is also why the target is worth keeping even though the outcome is dull:** the
> calculation only happened because the hypothesis was named. **Momentum would never have produced
> it.**

## ⚠️ Nothing was watching for it — fixed 13 August 2026

**This document pre-registered a prediction and named a boundary, and then nothing observed either.**
`retarget.py` is a MODEL — a line-for-line port of `GetNextWorkRequired` — not a monitor, and no
scheduled job mentioned height 2016.

> ★ **A pre-registered prediction that nobody is present to score is not an experiment. It is a
> hope.** The chain mines at roughly 105 min/block, so the boundary is months out and the moment it
> matters is a moment nobody would have been looking at.

**`derivatives/retarget/retarget_watch.py`** now reads the published status feed, reports the
distance to the boundary, and prints the capture list the instant the chain crosses it. It runs in
one command and has a `--json` mode for a cron job.

```
at the time of writing:  height 70 · 1,946 blocks to go · ~142 days at the observed cadence
```

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
