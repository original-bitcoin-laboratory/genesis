# JAN09-B — Satoshi's Bitcoin from the first surviving code to the last commit, specified on paper

**20 September 2026.** `JAN09-B` is the consensus design of Bitcoin as its author left it: the
January 2009 release as this laboratory executes it, with every consensus rule the author installed
between the earliest surviving code (the November 2008 pre-release) and the last commit the record
carries under the author's name (`629e37dde`, 15 December 2010, "get external ip from irc"; the last
consensus change is `97ee01ad8`, 12 December 2010, version 0.3.19), at the values the author left,
and with the author's own recorded statements where a value was said to be temporary. It is a
specification, not a chain: it is not mined, and by the decision recorded in
`CONSTITUTION-REGISTER.md` the laboratory's post-quantum successor is its implementation, adding
the one delta this specification does not contain, the signature scheme.

The principle was set by the operator on 20 September 2026 and is the only one applied here: **of
the author's own work, the best of it, at its last tuning.** Rules that entered after the last
commit are not installed, whatever their merit, with one exception that §5 states and justifies.
Every rule cites its constitution row (`OBL-C-nnnn`); every value is the value at the last commit;
where the author said in the record that a value would change, the statement is quoted and the
change is left to the implementation, marked.

Experimental laboratory research, in progress. Not money, not advice, no warranty (`RIGHTS.md`).

---

## 1. The base: the January 2009 design, as executed

The substrate is the released January 2009 client's consensus core as the laboratory has
reconstructed and executed it: serialisation, transaction and block validation, Script, value
accounting, reorganisation, the 2,016-block retarget with its fencepost (600.30 s fixed point,
`OBL-F-0006`), coinbase maturity 100, median-time-past of eleven and the two-hour future bound, the
merkle duplication on odd levels, the `CHECKMULTISIG` extra pop, and `SIGHASH_SINGLE` returning 1
(the five era-authentic behaviours of `common/conformance/CONSENSUS_BEHAVIORS.md`, executed by the
corpus of 317 vectors, `derivatives/vectors/`). The author changed none of those five before the
last commit; the specification keeps them as the author left them.

The November 2008 pre-release is the earliest surviving code and is the base's own ancestor: its
`CheckBlock` already tests the 32 MiB `MAX_SIZE` (`pre-genesis/extracted/main.cpp:1164`), its
monetary parameters differ from January's at all five values (`Executing the Earliest Bitcoin`, §5),
and its genesis carries no calendar anchor (`OBL-F-0005`). The January values supersede the November
ones by the author's own hand; nothing from November is installed that January removed.

## 2. The rules the author installed, at the values of the last commit

In the order they entered the record. "Last value" is the value in the tree at `629e37dde`.

| rule | row | entered | last value | the author's recorded statement, if any |
|---|---|---|---|---|
| time-based `nLockTime` | `OBL-C-0007` | `dd519206a`, 29 Oct 2009 | locks below 500,000,000 are heights, at or above are Unix times | source comment: "Time based nLockTime implemented in 0.1.6" |
| best chain by cumulative work | `OBL-C-0008` | `3b7cd5d89`, 25 Jul 2010 | `bnChainWork` summed from each block's target; height no longer selects | none in the commit |
| script element, script size, stack depth, numeric operand caps | `OBL-C-0002` | `757f0769d`, 29 Jul 2010; tightened `4bd188c43`, 15 Aug 2010 | 520 bytes, 10,000 bytes, 1,000 elements, 4 bytes | none in the commits |
| `MoneyRange` and the output-sum check | `OBL-C-0003` | `d4c6b90ca`, 15 Aug 2010 | every output in `[0, 21,000,000 × 10^8]`, running sum in range | commit message: "fix for block 74638 overflow output transaction" |
| fifteen opcodes disabled | `OBL-C-0005` | `4bd188c43`, 15 Aug 2010 | `OP_CAT`, `OP_SUBSTR`, `OP_LEFT`, `OP_RIGHT`, `OP_INVERT`, `OP_AND`, `OP_OR`, `OP_XOR`, `OP_2MUL`, `OP_2DIV`, `OP_MUL`, `OP_DIV`, `OP_MOD`, `OP_LSHIFT`, `OP_RSHIFT` fail the script | none in the commit ("misc changes") |
| transaction size | `OBL-C-0010` | `401926283`, 25 Aug 2010 (32 MiB); `3df62878c`, 13 Sep 2010 (1 MB) | a transaction's serialised size at most `MAX_BLOCK_SIZE` | none in the commits |
| block size | `OBL-C-0001` | `a30b56ebe`, 15 Jul 2010 (constant); `f1e1fb4bd`, 7 Sep 2010 (rule from 79,401); `172f00602`, 19 Sep 2010 (unconditional in `CheckBlock`) | `MAX_BLOCK_SIZE = 1,000,000` on serialised size and transaction count | 4 Oct 2010: "It can be phased in, like: `if (blocknumber > 115000) maxblocksize = largerlimit`" (see §4) |
| signature operations per block | `OBL-C-0004` | `f1e1fb4bd`, 7 Sep 2010; gate removed `172f00602` | `MAX_BLOCK_SIGOPS = MAX_BLOCK_SIZE / 50` = 20,000 | none in the commits |
| the 32 MiB `MAX_SIZE` | `OBL-C-0006` | the release; demoted `172f00602`, 19 Sep 2010 | bounds network messages and serialised containers, not block validity | none |

Two of the author's changes in the window are not validity rules and are recorded here so that the
list is the whole of the author's consensus-adjacent work, not a selection:

- **the alert system** (`OBL-C-0009`, `401926283`, 25 Aug 2010): a network message verified by one
  key. Not installed: the specification has no rule that depends on a key held by a person, and the
  system was retired by its own maintainers with the key published. Its exclusion is the one place
  this specification departs from the author's last tree on grounds other than "after the last
  commit", and it is stated as such.
- **`IsStandard`** (`OBL-C-0011`, `a206a2398`, 7 Dec 2010, in the author's tree by another hand)
  and the DoS limits of `97ee01ad8` (12 Dec 2010): node policy, not validity. A specification of
  block validity has no relay rules; an implementation may carry them.

## 3. What the author did not install, and is therefore not here

| rule | row | entered | status |
|---|---|---|---|
| `CScriptNum` replacing `CBigNum` | `OBL-C-0012` | 2014 | not installed as a rule: the 4-byte operand cap is the author's (row `OBL-C-0002`) and is in; the type that holds it is the implementation's business under §5 |
| the Berkeley DB lock rule and its written stand-in | `OBL-C-0013` | 2013 | not installed: after the last commit, and expired on 15 May 2013 |
| BIP 66 strict DER as a rule | `OBL-C-0014` | 2015 | after the last commit; see §5 for the one thing the specification must say about signature encoding |
| every rule after 2015 | — | — | not in the register, not here |

## 4. The one value the author said would change

The block-size limit is the only rule in §2 with a recorded statement by the author that its value
was provisional. On 3 October 2010, to a patch raising it: "Don't use this patch, it'll make you
incompatible with the network, to your own detriment. We can phase in a change later if we get
closer to needing it." On 4 October 2010: "It can be phased in, like: `if (blocknumber > 115000)
maxblocksize = largerlimit`. It can start being in versions way ahead, so by the time it reaches
that block number and goes into effect, the older versions that don't have it are already obsolete."
(Nakamoto Institute mirror, Bitcointalk posts 478 and 485.)

The specification therefore installs the author's last value, 1,000,000 bytes, and the author's
mechanism for changing it, a height-scheduled increase announced in advance; the height and the
larger limit are the implementation's to choose and to state. No other value in §2 carries such a
statement, and none is marked provisional here.

A note on the 32 MiB figure, because it is often remembered as the author's "real" limit: the
record contains no statement by the author about it. It entered as the ceiling in `CheckBlock` in
the November 2008 code and the January 2009 release, and the author replaced it with the 1 MB test
on 19 September 2010 (`172f00602`), leaving the constant as a bound on network messages. The
author's own trajectory ran from 32 MiB to 1 MB with a stated plan to raise the latter.

## 5. The laboratory's one addition: no consensus-critical third-party library

This is not the author's rule. The register's two `emergent` rows (`OBL-C-0013`, `OBL-C-0014`) are
rules that existed because a library's behaviour decided validity, and the second of them lived in
the author's own client: what OpenSSL 0.9.8 accepted as a signature encoding was what the chain
accepted, and nobody had written it down. A specification cannot leave a validity decision to a
library it does not state, so this specification requires that every validity decision be made by
code the specification states, with a library used only where its output is checked against that
statement.

The one consequence for §2: signature encoding must be stated. The specification states it as the
encoding the author's own client produced when it signed, which is strict DER with a trailing
sighash byte; that is the same set BIP 66 later wrote down, and the specification takes the
statement from the author's signer, not from the 2015 rule. `derivatives/emergent/der_strictness.py`
is the executable form. Whether OpenSSL 0.9.8 also accepted looser encodings is the open witness of
`OBL-C-0014` and does not change what the author's client emitted.

The laboratory's own reconstruction does not yet satisfy this rule in full: its release build links
OpenSSL 1.0.2u for signatures (`OBL-F-0010`). `JAN09-B` states the rule; its implementation is where
the rule is met.

## 6. What this specification leaves to its implementation

- **The signature scheme.** Written for secp256k1 ECDSA, as the author's client is; the
  implementation replaces the scheme and inherits every other line. `PQ-SIGNATURE-COST.md` and
  `PQ-SETTLEMENT-CAPACITY.md` are the costs of that replacement.
- **The block-size schedule** of §4: the height and the larger limit.
- **The chain's identity.** Genesis, network magic, port and the coinbase's calendar anchor are the
  implementation's; no two of the laboratory's chains share a genesis, and each is pinned by digest
  in its own repository.
- **Policy.** Relay, standardness and DoS limits, as the author's tree carried them or otherwise.
- **The test of completeness.** If a rule the implementation needs is not on this page and not in
  the register, the register is incomplete and the rule is entered there first, with its origin, its
  argument and its witness, before it is built.

## 7. What is open

The witnesses the register marks `open` are open here too: the transaction-size narrowing
(`OBL-C-0010`), the acceptance side of signature encoding on the 2009 binary (`OBL-C-0014`), and the
numeric-operand cap as an executed case (`OBL-C-0002`). The last commit is taken from GitHub's copy
of the repository on 20 September 2026, on the lineage that carries the Subversion trailer; the
record can be rewritten by its owners, so the date is stated with the reading.

**Corrections to this document are published, dated, and not made silently.**
