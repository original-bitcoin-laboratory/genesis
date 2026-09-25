# The vocabulary round trip — subtracted in August 2010, reconstructed in December 2023

**20 September 2026.** The January 2009 Script had a general vocabulary: concatenation, arithmetic
including multiplication and division, bit shifts, string slicing. Fifteen of those opcodes were
disabled on 15 August 2010 in a commit whose message reads "misc changes" (`OBL-C-0005`). Thirteen
years later, a paper showed how to verify "any computable function" on Bitcoin without changing its
consensus rules, by committing to a program bit by bit in hash-locked leaves and resolving disputes
with fraud proofs, at a cost its author describes as significant off-chain computation and
communication. The front half of that trip is this laboratory's executed finding; the back half is a
public paper. No account joining the two was found in the search this note made, which was not
exhaustive. This essay joins them, and stops at what the record shows. Findings register: `OBL-F-0027`.

Experimental laboratory research, in progress. Not money, not advice, no warranty (`RIGHTS.md`).

---

## The front half: what was there, and when it left

**What was there.** The January 2009 interpreter carries 106 opcode values of which 94 have a branch
in `EvalScript`; the laboratory executes that vocabulary on its release build of that source,
136 of 136 script vectors over the wire (`OBL-F-0010`) — a suite exercising 74 of the 94 execution
branches and every one of the fifteen opcodes this note is about, carrying no `OP_CHECKSIG`, whose
family the separate 14 signature vectors cover — and escrow, hash-lock and assurance
constructions built from it (`Executing the Earliest Bitcoin`, §4). Among the opcodes: `OP_CAT`,
`OP_SUBSTR`, `OP_LEFT`, `OP_RIGHT`, `OP_INVERT`, `OP_AND`, `OP_OR`, `OP_XOR`, `OP_2MUL`, `OP_2DIV`,
`OP_MUL`, `OP_DIV`, `OP_MOD`, `OP_LSHIFT`, `OP_RSHIFT`. With them, a script could assemble a
message from pieces, compare arbitrary-precision numbers, and compute; `CBigNum` arithmetic was
unbounded in the January source; a 258-byte operand cap arrived on 29 July 2010
(`757f0769d`) and this commit narrowed it to 4 bytes (`OBL-C-0002`).

**When it left.** Commit `4bd188c43`, 15 August 2010, author string `s_nakamoto`, Subversion
revision 131, message "misc changes" (`docs/SCRIPT-LIMITS-RETROFITTED.md`; `OBL-C-0005`). The diff
adds a guard before the opcode switch that fails a script containing any of the fifteen. BIP 347
documents the same commit as the one that disabled `OP_CAT` "along with another 15 opcodes" — which
reads as sixteen, one more than the fifteen the diff carries and than this note counts
(`SECONDARY-SOURCES-CHECKED.md` §3 enters the difference). The
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
three primitives left standing, at a cost the reconstruction's author states plainly. Whether the
removal was wise, whether the reconstruction is the right way back, and whether the two are the same
capability in any sense beyond the one stated in the table are questions this essay does not answer.

## A third point on the same line, September 2026

The shape the table describes has a later instance. A paper of 24 September 2026, *Shielded Bitcoin:
Private Transfers on the Bitcoin L1* (Shikhelman, Komarov and Moskvin), sets out private
Bitcoin-denominated transfers "requiring no changes to Bitcoin consensus", and states the same
constraint this essay's table describes, in its own words:

> "More expressive constructions may be possible with proposed opcodes such as `OP_CAT` and
> `OP_CSFS`, but those constructions depend on changes to Bitcoin's consensus rules."

Two facts from this laboratory's own record sit beside that. Neither is a claim about the paper.

**Its current carrier is an opcode whose January behaviour is a different one.** The paper's stated
implementation profile publishes the envelope in an `OP_RETURN` output, which later Bitcoin treats
as provably unspendable; it keeps a witness-carried alternative and other Bitcoin-valid structures
open as deployment choices, so this is a property of that profile and not of the design. `OBL-F-0032`
records that the January 2009 interpreter reaches `OP_RETURN` and sets `pc = pend` rather than
failing the script, so the script completes with its stack as it stands (`script.cpp:170-174`). The
property the modern carrier rests on is a later one.

**Its carrier budget is policy, not consensus.** The paper fixes its footprint against a relay
default, stating that Bitcoin Core v30.0 raised `-datacarriersize` from 83 to 100,000 bytes and that
operators may restore the former limit. `WHAT-THE-ORIGIN-PERMITTED.md` records that the January
client has no relay-side filter on what it receives — nothing in it declines an incoming block or
transaction for its shape — and places the data-carrier relay limit in 2014, outside that note's
window.

⇒ **This is a third instance of the shape, not new evidence about the origin.** It is recorded
because this essay's claim is about a pattern in the record, and a pattern is worth more when its
instances are counted than when one of them is described.

## One connection the laboratory can measure

The 2023 construction's commitments are hash-based. A Lamport-style commitment's security rests on
the preimage resistance of a hash function, which is the assumption a hash-based signature
scheme also rests on. The laboratory measures one such scheme, SLH-DSA-SHA2-128s, in
`PQ-SIGNATURE-COST.md`; that note reports sizes and timings and takes no position on when any
cryptography breaks, and neither does this one. The reconstruction's arithmetic therefore lives in the same
assumption class as the laboratory's counter-signature, and the settlement arithmetic of
`PQ-SETTLEMENT-CAPACITY.md` applies to its on-chain footprint on the day a dispute reaches the chain.
That is an observation about assumptions, not a claim about either design.

## What this essay does not claim

No claim about why the opcodes were disabled, no claim that BitVM restores what was removed in any
sense the paper does not itself state, and no position on reactivation proposals (BIP 347 is cited
for its documentation of that commit, not for its date: BIP 347 gives "Aug 25 2010" where the
commit's own fields say 15 August 2010, and this note uses the commit's). The 2010 commit is quoted from its record; the 2023 paper is
quoted from its published text at `bitvm.org/bitvm.pdf`. The 2026 paper is quoted from its published
text and is cited for the two statements reproduced above and for nothing else; this essay takes no
position on its design, its security, or its deployment.

**Corrections to this essay are published, dated, and not made silently.**

*Added and corrected 25 September 2026, before this essay was signed. Added: the section "A third
point on the same line, September 2026", which gives a later instance of the pattern and two facts
already in the register. Corrected: the script suite is stated at the branches it exercises rather
than as the whole vocabulary; the operand cap is dated to 29 July 2010 with this commit narrowing
it; BIP 347 is cited for its documentation of the commit and its differing date is entered, as is
its opcode count; BitVM's author is referred to in the singular; the claim that nobody had written
the two together is replaced by what this note's own search found; the citation to
`PQ-SIGNATURE-COST.md` is reduced to what that note contains; and the carrier is stated as the 2026
paper's implementation profile rather than its design. The essay's claim, its table, and its
findings-register row `OBL-F-0027` are unchanged.*
