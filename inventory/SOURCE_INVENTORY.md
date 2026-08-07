# OBL-JAN09 — Source inventory (`v0.1.0-source-inventory`, R1)

First-pass structural map of the January 2009 Bitcoin `src/` tree (the archive distributed
as v0.1.0; its contents are v0.1.1 — see [`common/VERSION_LABEL.md`](https://github.com/original-bitcoin-laboratory/common/blob/main/VERSION_LABEL.md))
(26 source units, 19,820 lines). Line counts and class/symbol names are read
directly from the extracted, hash-verified source (`manifests/SOURCE_MANIFEST.json`).
For the full opcode vocabulary see [`OPCODES.md`](OPCODES.md).

Evidence prefix: **JAN09-SOURCE** (visible in the January source release). Claims
about execution/consensus are deferred to R3–R4.

## Release payload (non-source, in the archive)

`bitcoin.exe` (6,440,960 B), `libeay32.dll` (OpenSSL), `mingwm10.dll`,
`readme.txt`, `license.txt`, plus build files (`makefile`, `makefile.vc`) and UI
resources (`rc/` bitmaps + icons, `ui.rc`, `uiproject.fbp`). The `.tgz` ships the
**runnable** client, not just source.

## Consensus / ledger

| File | lines | Key classes / symbols | Role |
|---|--:|---|---|
| `main.h` | 1317 | COutPoint, CInPoint, CDiskTxPos, CCoinBase, CTxIn, CTxOut, CTransaction, CMerkleTx, CWalletTx, CTxIndex, CBlock, CBlockIndex, CDiskBlockIndex, CBlockLocator | transactions, blocks, chain state, mining, wallet (declarations) |
| `main.cpp` | 2660 | ProcessBlock, Reorganize, ConnectInputs/ConnectBlock, AcceptBlock, CheckBlock, mining loop | validation, chain selection, issuance, wallet, mining (impl) |

## Script (predicate engine)

| File | lines | Key classes / symbols | Role |
|---|--:|---|---|
| `script.h` | 597 | `enum opcodetype`, class CScript | opcode set + script container/parser (`GetOp`, `FindAndDelete`) |
| `script.cpp` | 1127 | EvalScript, SignatureHash, CheckSig, Solver ×2, IsMine, ExtractPubKey/Hash160, SignSignature, VerifySignature | stack-machine interpreter, sighash, template solver |

## Keys & hashing

| File | lines | Key classes / symbols | Role |
|---|--:|---|---|
| `key.h` | 156 | CKey, key_error | secp256k1 EC keys + ECDSA (via OpenSSL) |
| `sha.h` / `sha.cpp` | 177 / 554 | SHA-256 core | double-SHA-256 for PoW / hashing |

## Networking

| File | lines | Key classes / symbols | Role |
|---|--:|---|---|
| `net.h` | 856 | CMessageHeader, CAddress, CInv, CRequestTracker, CNode | P2P messages, peers, relay |
| `net.cpp` | 1020 | message loop, connection mgmt | P2P transport (port 8333) |
| `irc.h` / `irc.cpp` | 7 / 265 | IRC discovery | early peer discovery via Freenode |

## Storage (Berkeley DB)

| File | lines | Key classes / symbols | Role |
|---|--:|---|---|
| `db.h` | 420 | CDB, CTxDB, CReviewDB, CMarketDB, CAddrDB, CWalletDB | typed BDB wrappers |
| `db.cpp` | 604 | load/write blockindex, wallet, addr | persistence |

## Commerce (experimental)

| File | lines | Key classes / symbols | Role |
|---|--:|---|---|
| `market.h` | 182 | CUser, CReview, CProduct | products, orders, signed reviews, reputation |
| `market.cpp` | 264 | product/order/review handling | prototype P2P commerce |

## UI (wxWidgets)

| File | lines | Key classes / symbols | Role |
|---|--:|---|---|
| `ui.h` / `ui.cpp` | 417 / 3228 | CMainFrame + Send/AddressBook/Options/Product/Review dialogs | desktop wallet GUI |
| `uibase.h` / `uibase.cpp` | 720 / 1806 | generated `*Base` dialog classes | wxFormBuilder bases — **incl. `CPokerLobbyDialogBase`, `CPokerDialogBase` (dormant poker UI)** |

## Support / utility

| File | lines | Key classes / symbols | Role |
|---|--:|---|---|
| `serialize.h` | 1151 | CDataStream, CAutoFile, CFlatData, serialization templates | wire/disk serialization |
| `bignum.h` | 498 | CBigNum, CAutoBN_CTX | big integers (OpenSSL BN) for Script numerics |
| `uint256.h` | 750 | uint160, uint256 | fixed-width hashes |
| `base58.h` | 201 | base58 encode/decode | address text encoding |
| `util.h` / `util.cpp` | 399 / 373 | CCriticalSection, logging, helpers | general utilities |
| `headers.h` | 71 | aggregate includes | precompiled-header aggregator |

## First observations

- The **complete financial machine is co-located in one small tree**: predicate
  engine (`script.*`), keys/ECDSA (`key.h`), ledger/validation/mining (`main.*`),
  storage (`db.*`), networking (`net.*`), and a working GUI wallet (`ui*.*`).
- Two **experimental subsystems** ship in the release build: the `market.*`
  commerce layer (users/products/reviews/reputation) and a **dormant poker UI**
  (`CPoker*DialogBase` present in `uibase` but not surfaced in `ui.h`).
- Next (R1 cont. → R4): line-numbered function catalog for `main.cpp` consensus
  paths (`ConnectInputs → VerifyScript → EvalScript`), and per-opcode reachability.
