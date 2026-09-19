# JAN09-B — the constitution's executable expression, specified on paper

**20 September 2026.** `JAN09-B` is the January 2009 design with the rules the record argues for
installed, the rules the record does not argue for chosen deliberately and marked as chosen, and no
consensus-critical third-party library in the validation path. It is a specification, not a chain:
it is not mined, and it has no implementer (`CONSTITUTION-REGISTER.md`, "Where a designed successor
fits", corrected 20 September 2026: the laboratory's post-quantum instrument is not one, since its
charter confines it to the signature change on the January base). Writing it is the test the
direction document set for the constitution: whether the register is complete enough to construct
from.

Every rule below cites its constitution row (`OBL-C-nnnn`) and takes its status from that row's
`argument` field. Where the field reads `not-in-record`, the magnitude below is a choice, and the
specification says so in the same line, so that a reader who disagrees with the choice can see that
it is one. Nothing here claims that the chosen values are right; it claims that they are stated.

Experimental laboratory research, in progress. Not money, not advice, no warranty (`RIGHTS.md`).

---

## 1. The base: the January 2009 design, as executed

The substrate is the released January 2009 client's consensus core as the laboratory has
reconstructed and executed it: serialisation, transaction and block validation, the full Script
vocabulary with nothing disabled beyond what v0.1 itself disabled, value accounting, reorganisation,
the 2,016-block retarget with its fencepost (600.30 s fixed point, `OBL-F-0006`), coinbase maturity
100, median-time-past of eleven and the two-hour future bound, the merkle duplication on odd levels,
the `CHECKMULTISIG` extra pop, and `SIGHASH_SINGLE` returning 1 (all five era-authentic behaviours of
`common/conformance/CONSENSUS_BEHAVIORS.md`, executed by the corpus of 317 vectors,
`derivatives/vectors/`). The 32 MiB `MAX_SIZE` ceiling on a block's serialised size and transaction
count is inherited (`OBL-C-0006`, `JAN09-SOURCE`).

What "the January 2009 design" denotes, for a reader building from this page: the opcode vocabulary with
its numbers and the disabled set is `inventory/OPCODES.json`; the monetary constants (`COIN = 10^8`, a
50-coin subsidy halving every 210,000 blocks, `nTargetSpacing = 600`) and the coinbase value rule (at most
subsidy plus fees) are in `common/conformance/NOV08_JAN09_DIFF.md`; the seven era-authentic behaviours,
including the `OP_VERIFY`/`OP_RETURN` stop and the coinbase-maturity fencepost, are in
`common/conformance/CONSENSUS_BEHAVIORS.md`; Script semantics beyond those exist as the executed corpus
(`derivatives/vectors/`) and the January source itself, not as prose. The one opcode v0.1 disabled,
`OP_NOTEQUAL`, stays disabled here; the laboratory's JAN09-X profile re-opens it as a model-level macro,
and the two documents now say so of each other (`derivatives/profiles/`). A clean-room reproduction on
20 September 2026 built a validator from this page with the January source open beside it and found the
cross-references above missing; they are added, and its report is in `REPRODUCTIONS.md`.

Two of the era-authentic behaviours are consequences of defects, and the specification keeps them,
because the specification is the January design and a design that fixes them is a different one:
the `CHECKMULTISIG` extra pop and `SIGHASH_SINGLE`'s constant. Their status is recorded, not
silently repaired. A third, the retarget fencepost, is kept for the same reason. The value-overflow
defect is not kept; §2 installs its rule.

## 2. Installed: rules whose argument is in the record (`argument: cited`)

| rule | row | what the record argues | installed as |
|---|---|---|---|
| `MoneyRange` and the output-sum overflow check | `OBL-C-0003` | block 74638, 15 August 2010: the commit message names the failure | as in `d4c6b90ca`: every output in `[0, MAX_MONEY]` and the running sum in range; `MAX_MONEY = 21,000,000 × 10^8` |
| strict DER signature encoding | `OBL-C-0014` | BIP 66 cites OpenSSL 1.0.0p and 1.0.1k rejecting encodings earlier releases accepted | `IsValidSignatureEncoding` as in BIP 66, from genesis, with no changeover (`derivatives/emergent/der_strictness.py`) |
| script arithmetic without a third-party bignum | `OBL-C-0012` | PR 3965 states the reason: remove the library from the validation path | numeric operands of at most four bytes, in a type of the specification's own |

The DER rule is installed for the reason its own record gives, and for a second reason the
constitution makes explicit: a rule that lived in a library's parser was a rule nobody wrote
(`OBL-C-0014`, kind `emergent`), and this specification has no such rules by construction (§5).

## 3. Chosen: rules whose magnitude the record does not argue for (`argument: not-in-record`)

Each is installed because the January design without it has an executed failure mode the laboratory
has exhibited; each magnitude is a choice, and is marked as one.

| rule | row | the failure the January design has without it | chosen value | why this value, stated as a choice |
|---|---|---|---|---|
| block validity size limit | `OBL-C-0001` | none exhibited below 32 MiB; the origin's own cap holds | **32 MiB, the inherited `MAX_SIZE`; no 1 MB rule** | the record argues for no magnitude; the specification keeps the origin's and installs no second one |
| script element, script size, stack depth, numeric operand caps | `OBL-C-0002` | the January interpreter runs a 600-byte element and a 1,500-deep stack; unbounded resource use per script (`OBL-F-0003`, `OBL-F-0034`) | **520 bytes, 10,000 bytes, 1,000 elements (stack plus altstack), 4 bytes on numeric operands as read, not on results; an over-cap operand fails the script, as `CastToBigNum`'s throw does** | the 2010 values, taken as they are because no argued alternative exists in the record; the choice is the 2010 committer's, adopted here and marked |
| signature-operation count per block | `OBL-C-0004` | unbounded signature checks per block | **`MAX_SIZE / 50`**, the 2010 ratio applied to the inherited ceiling, counted as `GetSigOpCount` does: one per `OP_CHECKSIG`/`OP_CHECKSIGVERIFY`, twenty per `OP_CHECKMULTISIG`/`OP_CHECKMULTISIGVERIFY` | the 2010 rule's ratio, not its absolute |
| transaction size | `OBL-C-0010` | a transaction may fill the block | **no separate rule: the block ceiling bounds it** | the 2010 rule's first step (32 MiB per transaction, `401926283`) is the block ceiling restated; its second step is the 1 MB choice this specification does not make |
| disabled opcodes | `OBL-C-0005` | the record names no failure; the 2010 commit's message is "misc changes" | **none disabled beyond v0.1's own `OP_NOTEQUAL`** | the specification keeps the January vocabulary because the record argues for removing none of it; a reader who wants the 2010 set has the row |
| time-based `nLockTime` | `OBL-C-0007` | a lock cannot name a date | **the 500,000,000 split, as in `dd519206a`**; finality is consulted where the January client consults it (relay and the miner), not at block acceptance | the message describes the change; the magnitude is the 2009 committer's, adopted and marked |
| chain selection by cumulative work | `OBL-C-0008` | a branch with more blocks and less work wins (`OBL-F-0001`) | **cumulative work, as in `3b7cd5d89`** | the record does not argue for it; the laboratory installs it because the executed failure is exhibited and the whitepaper's own words are "longest proof-of-work chain" |

## 4. Excluded: rules that are not consensus, or that expired

| rule | row | status here | reason |
|---|---|---|---|
| `IsStandard` | `OBL-C-0011` | not part of the specification | policy, node-local; a specification of block validity has no relay rules |
| the alert system | `OBL-C-0009` | not part of the specification | a network message, not a validity rule; retired by its own maintainers with the key published |
| the Berkeley DB lock rule and its written stand-in | `OBL-C-0013` | not part of the specification | the written rule expired on 15 May 2013; the emergent rule is excluded by §5 |

## 5. The construction rule: no consensus-critical third-party library

The two emergent rows (`OBL-C-0013`, `OBL-C-0014`) are rules that existed because a library's
behaviour decided validity. The specification forbids the class: every validity decision is made by
code the specification states, and a library may be used only where its output is checked against
that statement (a hash function whose test vectors are part of the corpus, for instance). The
laboratory's own reconstruction does not yet satisfy this rule in full: its release build links
OpenSSL 1.0.2u for signatures, and the corpus records what that library decides (`OBL-F-0010`).
`JAN09-B` states the rule; its implementation is where the rule is met.

## 6. What this specification leaves to its implementation

- **The signature scheme.** This specification is written for secp256k1 ECDSA, as the January design
  is. An implementer may replace the scheme and inherit every other line; `PQ-SIGNATURE-COST.md` and
  `PQ-SETTLEMENT-CAPACITY.md` are the costs of that replacement. No implementer exists yet.
- **The chain's identity.** Genesis, network magic, port and the coinbase's calendar anchor are the
  implementation's, and are not assigned here; no two of the laboratory's chains share a genesis,
  and each is pinned by digest in its own repository.
- **The test of completeness.** If a rule the implementation needs is not on this page and not in
  the register, the register is incomplete and the rule is entered there first, with its origin, its
  argument and its witness, before it is built.

## 7. What is open

The five witnesses the register marks `open` are open here too: the 1 MB narrowing against the
2009 binary (`OBL-C-0001`), the sigop count against the 2009 binary (`OBL-C-0004`), the
transaction-size narrowing (`OBL-C-0010`), the acceptance side of DER strictness on the 2009 binary
(`OBL-C-0014`), and the numeric-operand cap as an executed case (`OBL-C-0002`, `OBL-C-0012`). Four of
the five need the unmodified 2009 binary. Rules Bitcoin acquired after 2015 are not in the register
and so not in this specification.

**Corrections to this document are published, dated, and not made silently.**
