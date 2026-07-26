# OBL-JAN09 — Consensus validation path (R1)

Line-numbered map of the block/transaction validation call graph in Bitcoin
v0.1.0, and the consensus constants it enforces. Anchors are `src/<file>:<line>`
into the extracted, hash-verified tree (hashes in `manifests/SOURCE_MANIFEST.json`).

Evidence prefix: **JAN09-SOURCE**. This catalogs *reachability* (rung 3); actual
execution/consensus witnesses come in R3–R4.

## Call graph — a block arriving from a peer

```text
ProcessBlock                         src/main.cpp:1236   (entry from net message "block")
 ├─ CBlock::CheckBlock               src/main.cpp:1154   context-free checks
 │   ├─ PoW: GetHash() <= nBits      src/main.cpp:1180   (bnProofOfWorkLimit floor)
 │   ├─ CheckTransaction (each tx)   src/main.h:442      structure / value / coinbase
 │   └─ BuildMerkleTree == root      src/main.h:868
 └─ CBlock::AcceptBlock              src/main.cpp:1192
     ├─ CBlock::AddToBlockIndex      src/main.cpp:1072
     │   └─ *chain selection*        src/main.cpp:1097   if (pindexNew->nHeight > nBestHeight)
     │       ├─ CBlock::ConnectBlock src/main.cpp:937
     │       │   └─ CTransaction::ConnectInputs   src/main.cpp:772
     │       │       ├─ coinbase maturity check   src/main.cpp:824  (COINBASE_MATURITY)
     │       │       ├─ VerifySignature            src/script.cpp:1115
     │       │       │   └─ EvalScript             src/script.cpp:44   (scriptSig + scriptPubKey)
     │       │       │       └─ CheckSig           src/script.cpp:881
     │       │       │           └─ SignatureHash  src/script.cpp:818  (SIGHASH_*)
     │       │       └─ value-in >= value-out      src/main.cpp (ConnectInputs)
     │       └─ coinbase value <= GetBlockValue    src/main.cpp:953   (see note B)
     └─ Reorganize (on side-branch win) src/main.cpp:974
```

Template recognition (which outputs the wallet understands) is separate from
consensus: `Solver` — `src/script.cpp:913` and `:975` — recognises only the
pay-to-pubkey and pay-to-pubkey-hash templates, even though `EvalScript` can run
the full opcode set (see `OPCODES.md`). This is the "consensus engine is broader
than the wallet" gap.

## Consensus constants (`src/main.h`, `src/main.cpp`)

| Constant | Value | Anchor |
|---|---|---|
| `COIN` | 100,000,000 (1e8 → the satoshi) | `src/main.h:18` |
| `CENT` | 1,000,000 | `src/main.h:19` |
| block subsidy | `50 * COIN` | `src/main.cpp:677` |
| halving | `nSubsidy >>= (nBestHeight / 210000)` | `src/main.cpp:680` |
| `COINBASE_MATURITY` | 100 | `src/main.h:20` |
| PoW floor | `bnProofOfWorkLimit(~uint256(0) >> 32)` | `src/main.h:22` |
| target spacing | `10 * 60` (10 min) | `src/main.cpp:688` |
| retarget timespan | `14*24*60*60` (2 weeks → 2016 blocks) | `src/main.cpp:687` |
| max size | `MAX_SIZE = 0x02000000` | `src/main.h` |
| genesis hash | `0x000000000019d6689…a8ce26f` | `src/main.cpp:24` |

## Two notable v0.1 implementation facts

**A. Chain selection is by block *height*, not accumulated work.**
`AddToBlockIndex` switches to a new best branch on `pindexNew->nHeight >
nBestHeight` (`src/main.cpp:1097`), and sets `nBestHeight = pindexBest->nHeight`
(`:1135`). The whitepaper frames the winner as the *greatest-proof-of-work* chain;
v0.1 implements greatest-*height*. Under a constant difficulty regime these
coincide, but they are not the same rule — a distinction that matters for any
strict succession test.

**B. Subsidy halves on the *global* `nBestHeight`, not the block's own height.**
`GetBlockValue` (`src/main.cpp:675`) computes `nSubsidy >>= (nBestHeight /
210000)` — it reads the node's current best height, not `pindex->nHeight` of the
block being valued. A consensus/reproducibility subtlety to test in R4.

## Per-opcode reachability (seed for R4)

`EvalScript` is reached for every non-coinbase input via
`ConnectInputs → VerifySignature → EvalScript`, executing `scriptSig` then
`scriptPubKey`. Therefore every opcode with an `EvalScript` case
(`OPCODES.md`: 94 of 106) is *reachable* from transaction validation. Open R4
questions per opcode: (1) is it reachable through a **standard** template, or only
via a raw/custom script; (2) does it terminate the script `true`; (3) is a block
carrying it accepted by an unmodified node. Those require executable witnesses.
