# The vocabulary round trip — subtracted in August 2010, reconstructed in December 2023

**20 September 2026.** The January 2009 Script had a general vocabulary: concatenation, arithmetic
including multiplication and division, bit shifts, string slicing. Fifteen of those opcodes were
disabled on 15 August 2010 in a commit whose message reads "misc changes" (`OBL-C-0005`). Thirteen
years later, a paper showed how to verify "any computable function" on Bitcoin without changing its
consensus rules, by committing to a program bit by bit in hash-locked leaves and resolving disputes
with fraud proofs, at a cost its authors describe as significant off-chain computation and
communication. The front half of that trip is this laboratory's executed finding; the back half is a
public paper. Nobody has written the two together. This essay does, and stops at what the record
shows. Findings register: `OBL-F-0027`.

Experimental laboratory research, in progress. Not money, not advice, no warranty (`RIGHTS.md`).

---

## The front half: what was there, and when it left

**What was there.** The January 2009 interpreter carries 106 opcode values of which 94 have a branch
in `EvalScript`; the laboratory executes the whole vocabulary on its release build of that source,
136 of 136 script vectors over the wire (`OBL-F-0010`), including escrow, hash-lock and assurance
constructions built from it (`Executing the Earliest Bitcoin`, §4). Among the opcodes: `OP_CAT`,
`OP_SUBSTR`, `OP_LEFT`, `OP_RIGHT`, `OP_INVERT`, `OP_AND`, `OP_OR`, `OP_XOR`, `OP_2MUL`, `OP_2DIV`,
`OP_MUL`, `OP_DIV`, `OP_MOD`, `OP_LSHIFT`, `OP_RSHIFT`. With them, a script could assemble a
message from pieces, compare arbitrary-precision numbers, and compute; `CBigNum` arithmetic was
unbounded until the 4-byte operand cap of the same day.

**When it left.** Commit `4bd188c43`, 15 August 2010, author string `s_nakamoto`, Subversion
revision 131, message "misc changes" (`docs/SCRIPT-LIMITS-RETROFITTED.md`; `OBL-C-0005`). The diff
adds a guard before the opcode switch that fails a script containing any of the fifteen. BIP 347
documents the same commit as the one that disabled `OP_CAT` "along with another 15 opcodes". The
record contains no argument for the removal: the message does not describe it, and no failure is
named. The constitution register records that as `argument: not-in-record`, and nothing more.

## The back half: what was rebuilt, and how

BitVM (Robin Linus, "BitVM: Compute Anything on Bitcoin", 12 December 2023) states its result in
its abstract: "any computable function can be verified on Bitcoin", and "this requires no changes to
the network's consensus rules". Its architecture section says what it is made of: "It's mostly based
on hashlocks, timelocks, and large Taproot trees. The prover commits to the program literally
bit-by-bit". Its bit commitment is, in its own words, "similar to Lamport signatures": two hashes,
and a bit is set by revealing one preimage; revealing both is equivocation and forfeits a deposit.
Its stated costs: "significant amounts of off-chain computation and communication", a two-party
setting, and on-chain execution "only in case of a dispute".

Three of the paper's sentences carry the round trip.

> By design, the smart contract capabilities of Bitcoin are reduced to basic operations, such as
> signatures, timelocks, and hashlocks.

> Rather than executing computations on Bitcoin, they are merely verified, similarly to optimistic
> rollups.

> Committing to a large program in a Taproot address requires significant amounts of off-chain
> computation and communication, however the resulting on-chain footprint is minimal.

## The round trip, stated

| | January 2009 | 15 August 2010 | 12 December 2023 |
|---|---|---|---|
| where a computation runs | in the script interpreter, on chain, by every validator | (the general opcodes fail the script) | off chain, by two parties; on chain only a fraud proof |
| how a value is carried | on the stack, as bytes and numbers | — | as a preimage revealed against one of two hashes, per bit |
| what enforces correctness | the interpreter | — | a deposit forfeited on equivocation, under a timelock |
| cost | one script evaluation per validator | — | "significant amounts of off-chain computation and communication" |

What the record shows is that a capability the origin executed natively was removed under a message
that does not name it, and reconstructed thirteen years later, without changing the rules, from the
three primitives left standing, at a cost the reconstruction's authors state plainly. Whether the
removal was wise, whether the reconstruction is the right way back, and whether the two are the same
capability in any sense beyond the one stated in the table are questions this essay does not answer.

## One connection the laboratory can measure

The 2023 construction's commitments are hash-based. A Lamport-style commitment's security rests on
the preimage resistance of a hash function, which the laboratory's post-quantum notes treat as the
assumption that survives a break of the elliptic-curve signature (`PQ-SIGNATURE-COST.md`:
SLH-DSA-SHA2-128s is SHA-256 only). The reconstruction's arithmetic therefore lives in the same
assumption class as the laboratory's counter-signature, and the settlement arithmetic of
`PQ-SETTLEMENT-CAPACITY.md` applies to its on-chain footprint on the day a dispute reaches the chain.
That is an observation about assumptions, not a claim about either design.

## What this essay does not claim

No claim about why the opcodes were disabled, no claim that BitVM restores what was removed in any
sense the paper does not itself state, and no position on reactivation proposals (BIP 347 is cited
for its dating of the 2010 commit only). The 2010 commit is quoted from its record; the 2023 paper is
quoted from its published text at `bitvm.org/bitvm.pdf`.

**Corrections to this essay are published, dated, and not made silently.**
