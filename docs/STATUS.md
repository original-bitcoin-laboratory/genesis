# Status — Genesis (`OBL-JAN09`)

## Release 0 — Provenance freeze

- [x] Self-contained edition repository created.
- [x] Charter, evidence policy, profile, and checksum registry in place.
- [x] Whitepaper captured under `provenance/`.
- [x] Canonical v0.1.0 archives fetched (Nakamoto Institute CDN) and verified.
- [x] `.tgz` source tree extracted read-only + per-file manifest generated.
- [x] `.rar` tree extracted (7-Zip 26.02) and diffed against the `.tgz` tree.

### Verified archives (2026-07-26)

| Artifact | md5 | sha1 | sha256 |
|---|:--:|:--:|:--:|
| `bitcoin-0.1.0.rar` | OK | OK | OK (`8b17eb9a…`) |
| `bitcoin-0.1.0.tgz` | OK | OK | OK (`ce9da465…`) |

SHA-256 values match the 2012 Hal Finney recovery thread. Whitepaper matches
`manifests/PROVENANCE_SHA256SUMS`. Verified bytes live under `artifacts/jan09/`
(gitignored, never edited). Per-file hashes of the extracted tree — including the
binary — are recorded in `manifests/SOURCE_MANIFEST.json` (bytes stay local under
`extracted/`).

The `.rar` and `.tgz` source trees are **byte-identical**: all 48 files match by
SHA-256 — including `bitcoin.exe`, `script.cpp`, `script.h`, `market.cpp`, and
`key.h` — independent confirmation that both canonical archives carry the same
tree. (`bitcoin-0.1.0.rar` is a *solid* RAR, extracted with 7-Zip 26.02.)

## First finding — source inventory

The v0.1.0 `.tgz` is the **runnable release**, not just source (48 files):

- **`bitcoin.exe`** (6,440,960 B) + `libeay32.dll` (OpenSSL) + `mingwm10.dll`,
  `readme.txt`, `license.txt`.
- **`src/` — 21 source files**: `main.*`, `net.*`, `script.*` (interpreter),
  `key.h`, `db.*`, `market.*` (commerce subsystem), `irc.*`, `ui.*`/`uibase.*`,
  `sha.*`, `base58.h`, `bignum.h`, `serialize.h`, `uint256.h`, `util.*`,
  `headers.h`, plus `makefile` / `makefile.vc` and UI resources
  (`rc/`, `ui.rc`, `uiproject.fbp`).

The complete original financial machine — Script interpreter (`script.cpp`,
35,279 B), keys, and the `market.*` commerce experiments — plus a runnable
`BITCOIN.EXE` are all present, corroborating that this edition is the intended
behavioral oracle. (Contrast: the NOV08 pre-release is 5 files.)

## Release 1 — source inventory (started)

- [x] Full opcode & SIGHASH inventory, **reproducible** via
  `scripts/inventory-symbols.py` → `inventory/OPCODES.md` + `OPCODES.json`:
  **106 opcodes (+2 aliases), 94 implemented in `EvalScript`**, 4 SIGHASH modes,
  only `OP_NOTEQUAL` disabled. The later-BTC-disabled family (`OP_CAT`, `OP_MUL`,
  `OP_DIV`, `OP_LSHIFT`, `OP_INVERT`, …) is **live** in v0.1.
- [x] File/class map for all 26 `src/` units → `inventory/SOURCE_INVENTORY.md`
  (noted `market.*` commerce + a dormant poker UI in `uibase`).
- [x] NOV08 → JAN09 structural diff → `common/conformance/NOV08_JAN09_DIFF.md`.
- [x] Line-numbered consensus validation-path catalog →
  `inventory/VALIDATION_PATH.md`: `ProcessBlock → CheckBlock → AcceptBlock →
  AddToBlockIndex → ConnectBlock → ConnectInputs → VerifySignature → EvalScript`
  with `src:line` anchors + consensus-constants table; flags height-based chain
  selection (`main.cpp:1097`) and global-`nBestHeight` subsidy (`main.cpp:680`).
- [x] Executable **MODEL** (`derivatives/model/`, Python) and **PORT**
  (`derivatives/port/`, C++/OpenSSL) interpreters — differential-tested against
  each other. Built with MSYS2 g++ 16.1.0 + OpenSSL 3.6.3. Coverage:
  - Numeric/splice/bitwise vocabulary (incl. the disabled-in-BTC `OP_CAT`/`OP_MUL`/
    `OP_DIV`/`OP_LSHIFT`/`OP_INVERT`/…) — PORT uses the **real OpenSSL `BN_*`**
    engine + `bignum.h` codec (`CBigNum` ported to OpenSSL 3.x opaque `BIGNUM`).
  - Control flow (`OP_IF/NOTIF/ELSE/ENDIF/VERIFY/RETURN`), alt-stack, full stack
    ops. `run.sh` differential over **63 vectors → IDENTICAL**.
  - `CTransaction` + **`SignatureHash`** (pre-BIP143) — `run_sighash.sh`
    differential over **12 (nIn × SIGHASH) digests → IDENTICAL** (pinned).
  - **`OP_CHECKSIG` / `OP_CHECKMULTISIG` on real secp256k1** — `run_checksig.sh`:
    C++ signs + self-checks (8/8: P2PK + 2-of-3 escrow/arbitration; tamper /
    wrong-key / wrong-order rejected) and the **Python interpreter independently
    verifies the C++-signed scenarios** (4/4). Model pytest: 44.
  - Byte-level `CScript` (`cscript.py`, opcode bytes from our own `OPCODES.json`):
    `scriptCode` is now the **real subscript** (`scriptSig + OP_CODESEPARATOR +
    scriptPubKey`, script.cpp:1126), not a configured constant.
  - Executed native **instrument corpus** (`INSTRUMENTS.md`): buyer–seller–arbiter
    2-of-3 escrow, hash-lock (preimage) claim, hash-lock/refund `OP_IF` branch, and
    an assurance/crowdfund contract via `SIGHASH_ANYONECANPAY`. Model pytest: 51.
  - Evidence level **MODEL** (Python) / **PORT** (C++ + real OpenSSL EC/BN).
- [x] Headless **consensus PORT** → `derivatives/node/`:
  - `node_port` (12/12): reproduces the **exact genesis block** from the original
    construction — Merkle `4a5e1e…` **and** hash `000000000019d668…` (the live-chain
    anchor, the same startup assertion) — plus subsidy/halving, a real PoW mine, and
    difficulty retarget.
  - `chain_port` (8/8): faithful `ConnectInputs`/`ConnectBlock` over an in-memory
    UTXO index — builds a 121-block chain and **validates a real spend of a matured
    coinbase**, rejecting double-spend, inflation, tampered sig, immature-coinbase
    spend, and coinbase over-claim. Covers the ledger's core guarantees headlessly.
    Remaining boundary: the unmodified binary (persistence now covered below).
- [x] Headless **P2P relay** → `derivatives/p2p/` (MODEL, wire anchored to source):
  two nodes over localhost TCP speak the real v0.1 protocol (magic `f9beb4d9`, **no
  checksum, no verack**) — `version` handshake + `inv`/`getdata`/`block`/`tx`; the
  receiver **re-verifies PoW** before accepting and relays onward. 2 tests, no VM.
- [x] Headless **chain synchronisation** → `derivatives/p2p/chainsync.py` (MODEL):
  the real v0.1 `getblocks`/`CBlockLocator`/orphan/reorg path (main.cpp:1236,1734,
  1832; main.h:1241) — a fresh node **catches up a whole 6-block chain** from a peer,
  and an **orphan-driven** catch-up (peer announces only its tip → orphan →
  `getblocks(GetOrphanRoot)` → gap filled → reconnected). Height-based best chain
  (`nHeight > nBestHeight`) incl. a **reorg to a longer competing branch**. 5 tests.
- [x] Headless **wallet** → `derivatives/wallet/` (MODEL, real secp256k1): the v0.1
  key store (`mapKeys`/`mapPubKeys`), `IsMine`/`ExtractPubKey` over both Solver
  templates, `GetBalance`, faithful **`SelectCoins`** (exact / lowest-larger /
  stochastic subset-sum, main.cpp:2410) and **`CreateTransaction`** (main.cpp:2514)
  — payee `vout[0]`, **change-to-self as bare P2PK** `vout[1]`, `SignSignature` per
  input. Every created tx is **independently re-verified** by the lab's EvalScript
  (the v0.1 `VerifySignature` path) with value conserved; the change output is
  **re-spent** in a round-trip. 11 tests, no VM.
- [x] Headless **persistence** → `derivatives/persist/` (MODEL): the save/reload that
  lets a node restart at the same tip — byte-faithful **`CDiskBlockIndex`** record
  (128 B; main.h:1151) + `"hashBestChain"` (db.cpp:282,297) and a **`LoadBlockIndex`**
  reconstruction (db.cpp:322) that rebuilds tip/heights/main-chain/`in_main` **incl.
  after a reorg**; wallet keys as `CWalletDB ("key", pubkey)` records — a **DER-reloaded
  private key still signs a valid spend**. Boundary: the Berkeley DB 4.x *engine* /
  `.dat` container isn't reproduced (records live in a length-prefixed KV file). 7 tests.
- [x] **Descendant-conformance matrix** → `derivatives/conformance/` — **neutral,
  from the v0.1 origin**: v0.1 is the sole executed baseline / ground truth and every
  descendant (BTC, BCH, BSV, XEC) is treated identically via a documented rule-profile
  (`preserved`/`disabled`/`restored`/`→OP_SPLIT`), **none privileged**. **Two chains
  cross-checked by independent execution** (applied equally, tooling not ranking):
  BTC via `python-bitcoinlib`, BSV via `bitcoinx` — the BSV run **corrected** the
  profile (Genesis restores the set **except `OP_2MUL`/`OP_2DIV`**, still disabled;
  `0x7f`=`OP_SPLIT`). **Extended to 6 chains — every column cross-checked by execution:**
  **BTC/LTC/DOGE** via `python-bitcoinlib` (they run Bitcoin Core's `script.cpp` verbatim —
  code lineage, not cherry-picking); **BSV** via `bitcoinx`; **BCH/XEC** *execution-bounded*
  (restored ops confirmed executable by bitcoinx, disabled ops disabled by python-bitcoinlib —
  no standalone BCH interpreter exists, stated plainly). MATRIX.md has a per-chain method
  table; conformance.json schema 4. **73 tests pass.**
- [x] **Crypto conformance (v0.1 ECDSA vs real libsecp256k1)** → `derivatives/crypto_conformance/`
  (MODEL) — the crypto analog of the Script matrix, executing **Thread A** of
  `inventory/THE_OPENSSL_THREAD.md`: a genuine v0.1 `SignatureHash` + signature (OpenSSL EC,
  our MODEL) cross-checked against **libsecp256k1** (via `bitcoinx`→`electrumsv-secp256k1`,
  the real C lib). Result: **the curve math is identical** (canonical low-S sig verifies both
  ways, same secp256k1 key), and **the only divergence is malleability** — a **high-S**
  signature is accepted by OpenSSL (v0.1) but **rejected by libsecp256k1**, reproducing the
  exact fault BIP66/libsecp256k1 fixed. Neutral (libsecp256k1 = the crypto all descendants
  inherited). **21 tests.**
- [x] **Commercial-subsystem audit (R6)** → `inventory/MARKET_AUDIT.md` — static audit of
  `market.*`. **Finding: not dead code** — v0.1 shipped a working **decentralized
  marketplace** in 3 layers: a flood **publish/subscribe** advert network (`MSG_PRODUCT`,
  ephemeral, off-chain), a two-party **purchase protocol** (`checkorder`→`reply`→
  `submitorder`, wallet-integrated, pay-to-IP), and a **web-of-trust reputation** ("atoms"
  seeded by signed reviews via `CReviewDB`). Every path classified operational/reachable/
  partial/dormant with `src:line` anchors; dormant bits = origin-atom seeding + product
  notifications (both commented) + `mapMyProducts` persistence (TODO).
- [x] **NOV08-X (R8) — a live counterfactual network** → `derivatives/nov08x/` (MODEL).
  November's constitution runs headlessly. N-ORIG rules (source-anchored): **100-coin
  subsidy** halving every 100k, **leading-zero-bits PoW** (`MINPROOFOFWORK=20`, "ridiculously
  easy for testing"), primitive **±1-bit retarget**, **exact-equality coinbase**, `COIN=1e6`.
  `Nov08xNode` mines/validates a real chain; underpaid coinbase rejected; **full opcode
  vocabulary live (nothing disabled)**. `net.py` mints the **NOV08-X genesis** (`00000f08…`,
  20 leading-zero-bit PoW, experimental coinbase, 100-coin reward) + **network identity**
  (magic `f00ba708`, port `18008`, addr `0x35`) and **two isolated nodes synchronise the
  chain** over that magic (mainnet-framed messages refused). `PROVENANCE.json` (14 N-ORIG) +
  `DIFFERENTIAL.md`. **20 tests.** Design: `common/nov08x/DESIGN_LEDGER.md`. Open: NOV08-Full
  (walled-off interpretation).
- [x] **JAN09-X (R8) — released chain, full vocabulary, isolated** → `derivatives/jan09x/`
  (MODEL) — the symmetric twin. Runs the **released v0.1.0 constitution** (COIN=1e8, 50-coin
  subsidy, 210k halving, 10-min, compact PoW, `≤` coinbase) with the **full vocabulary
  re-opened**: `script_full.py` **re-enables `OP_NOTEQUAL`** (the one functional opcode v0.1
  disabled, script.cpp:486) as byte-level `!=`, disclosed NEW-EXP **with Satoshi's
  malleability caveat** — tests reproduce the `0x01 != 0x0001` footgun. Own identity (magic
  `f00ba709`, port 18009, addr 0x36, genesis message), two isolated nodes sync (compact PoW).
  **13 tests.** Together nov08x+jan09x answer the counterfactual both ways.
- [x] **Transacting on the X-chains (R8)** → `derivatives/ledger/` (MODEL) — a
  **Rules-parameterized UTXO ledger** (`ConnectInputs`/`ConnectBlock`, the Python
  counterpart of `node/chain_port.cpp`) enforcing, per chain: no double-spend, no
  inflation, coinbase maturity (100), and the chain's coinbase rule (NOV08 `==` / JAN09
  `≤`); inputs validated by the v0.1 VerifySignature path (`model` EvalScript, full
  vocabulary) with real secp256k1 via `wallet`. A wallet payment settles on JAN09-X; a
  coin locked by an **`OP_CAT` hash-lock** (unspendable on BTC) is **spent + validated on
  both X-chains**. Adds **`connect_block` (ConnectBlock)** — coinbase collects the block's
  fees per the chain rule, atomic rollback on failure — and a **two-independent-ledgers**
  test agreeing on a tx-carrying chain. **11 tests.**
- [x] **Commerce subsystem executable model (R6)** → `derivatives/market/` (MODEL) — the
  marketplace **runs**: `CProduct`/`CReview` **signed** over `GetSigHash` (`SER_SKIPSIG`)
  and verified on real secp256k1 (tamper/wrong-key rejected); the **"atoms" web-of-trust**
  reproduced exactly (`AddAtom` flow-through rate 2 / random atom / zero-never-propagates /
  origin-propagates, `AddAtomsAndPropagate` two-frontier flood over `vLinksOut`). Off-chain
  by design. **9 tests.**
- [x] **Transaction Studio (R7) — script debugger** → `derivatives/studio/` (MODEL) — a
  headless **stack tracer**: step any script through EvalScript, stack after every op +
  verdict (structural-fail / ran-not-true / VALID), full vocabulary (watch `OP_CAT`/`OP_MUL`
  run). Via a back-compat `trace` hook in `model/evalscript_model.run`. **5 tests.**
- [x] **Full-stack console (R7 capstone)** → `derivatives/console/` (MODEL) — one driver
  (`XConsole`) wiring Rules + Ledger + Wallet + studio + market. One session **mines, pays,
  creates + spends an `OP_CAT` contract (BTC-disabled), lists a signed product + review with
  reputation, and exports an evidence bundle** — on **both** NOV08-X and JAN09-X (same
  machine, two constitutions). NOV08-X here is **NOV08-Full's executable form**. **6 tests.**
- [x] **NOV08-Full (R8 step 7)** → `common/nov08x/NOV08_FULL.md` — the one **interpretive**
  artifact, walled off: the full financial machine assembled on November's constitution
  (= the console under `nov08` rules), every completion decision disclosed + classed, **never
  presented as recovered code / "true Bitcoin"**. N-ORIG rules still win over J-DONOR/NEW-EXP.
- [x] **R2 status** → `docs/R2_BUILD_RECONSTRUCTION.md` — the period **build is done**: on a
  pinned period toolchain (i686 · OpenSSL 1.0.2u · wxWidgets 2.8.12 · BDB 4.8 · Boost 1.42) the
  unmodified source compiles, links, and runs — crypto core (`period_build_wsl.sh`) and a full
  from‑source **`bitcoin.exe`** (`full_build_wsl.sh`), both **period locks** cleared. Honest
  boundary: a **byte‑exact** reproduction of `fbcac071…` is **not** claimed (structural, not
  bit‑for‑bit). Behavioural intent also met by the C++ PORT + the run binary (`r3-findings/run1`,
  `…/2026-07-31-twonode-mined-block`); NOV08 ceiling established (= NOV08-Minimal). reproduce.py
  now **11 suites / 177 tests** (13/13 steps).
- [~] **JAN09-EXECUTED — genesis witnessed (2026-07-26, `r3-findings/run1/`).** The
  unmodified v0.1.0 `bitcoin.exe` (sha256 `fbcac071…`, verified pre-run) was run and
  **reconstructed the exact genesis block** — hash `000000000019d668…`, merkle
  `4a5e1e…`, nonce `2083236893`, nTime `1231006505`, nBits `1d00ffff`, the Times-
  headline coinbase, 50-coin reward, `AddToBlockIndex … height=0`. Independently
  re-parsed the `blk0001.dat` it wrote → same canonical hash. **Live binary = PORT
  (`node_port.cpp`) = MODEL.** Wallet key-gen executed (addr `18YDsakg…`). Full GUI
  documented; observed **"version 0.1.1 Alpha"** (`VERSION=101`) and the historical
  **pay-to-IP** send mode. Findings + hashed manifest committed (raw bytes gitignored).
  - [x] **Two-node block production + relay — witnessed (2026-07-31, `r3-findings/2026-07-31-twonode-mined-block/`).**
    Two unmodified `bitcoin.exe` (both `fbcac071…`), air-gapped in VirtualBox on an isolated
    `172.20.0.0/24`, discovered each other over the **original IRC path**; node B **mined block 1** at
    real difficulty 1 (`000000005bdcfb…`, valid PoW, nonce `899943534`) on the **real genesis**, node A
    **received and accepted** it, and both `blk0001.dat` are **byte-identical** (`899c94d2…`) — verified
    from the raw block bytes, not just the GUI. This lifts **block production + relay** for the released
    binary from MODEL/PORT to **JAN09-EXECUTED**. Findings + hashed manifest committed (raw bytes gitignored).
  - [x] **Sustained multi-block mining + relay — witnessed (2026-08-01, `r4-findings/2026-08-01-sustained-relay/`; R4a).**
    In a fresh two-VM setup (`obl-r4`, both `bitcoin.exe` `fbcac071…`), node B (peer-gated miner) **mined
    three** valid difficulty-1 blocks in succession on the real genesis (`000000005df5e9…`, `00000000092b53…`,
    `00000000b719a9…`; nonces 2048796966 / 1227982862 / 309381835), and node A **received and accepted every
    one** (`inv → getdata → received block → ProcessBlock: ACCEPTED`, height 1→2→3 in lockstep). Both
    `blk0001.dat` are **byte-identical** (`aaf08aa3…`) and `verify_r4.py` confirms 0 orphans, all-valid PoW,
    and both nodes on the **same tip** — lifting sustained mining + relay for the released binary from
    MODEL to **JAN09-EXECUTED**. Findings + hashed manifest committed (raw bytes gitignored).
    **Follow-up (run B):** with **both** nodes generating, the chain reached **7 blocks bidirectionally**
    (node A mined 2 + accepted B's 4; node B mined 4 + accepted A's 2), both still byte-identical
    (`c8ff1c6c…`, 0 orphans, same tip) — production **and** relay now witnessed **A↔B**, and the chain
    **persisted across an unplanned guest reboot**. (Extended run reached 14 blocks, 0 reorgs.)
  - [x] **Chain reorganisation — witnessed (2026-08-02, `r4-findings/2026-08-02-reorg-partition/`; R4b).**
    Carrying the same two VMs on from the height-13 tip `00000000464529…`, node A mined its **own** height-14
    block `000000000234edf2…c81188fc`; the two nodes were then **partitioned** (node B's cable pulled) and
    node B mined a competing height-14 (`00000000c0383b…`) and extended to height-15 (`000000004e442b…`) —
    one block longer. On **reconnect** node A's binary fired **`*** REORGANIZE ***`**, orphaned its own
    `000000000234ed`, and adopted B's chain; both converged on tip `000000004e442b…` at height 15.
    `verify_r4.py` reads it straight from the bytes: node A = 17 blocks / **1 orphan** / `reorg witnessed: True`,
    node B = 16 blocks / 0 orphans, **same best tip**. An independent on-disk tell corroborates it: node A's
    `blk0001.dat` is exactly **+223 bytes** (one v0.1 block) larger than node B's — the retained orphan. This
    lifts a **reorganisation** for the released binary from MODEL to **JAN09-EXECUTED**. Findings + hashed
    manifest committed (raw bytes gitignored).
  - Still to capture: a **relayed spend** (R4c) between the two nodes — already covered headlessly by
    `derivatives/node` + `derivatives/p2p`. **In flight as of 2026-08-04.** A coinbase matures at **120
    confirmations, not 100**: `main.h` sets `COINBASE_MATURITY = 100` but `main.cpp:544` returns
    `max(0, (COINBASE_MATURITY+20) - depth)`, and the running wallets agree — a coin 58 blocks deep reads
    *"matures in 62 blocks"*. So the chain must reach **~height 120**; it stood at 68 when this was written,
    i.e. two to three more days at the observed 50–90 min/block.
  - **Executed-binary binding captured `pre` in both guests (2026-08-04)**, ahead of the spend, so the
    artifacts it produces are bound to a live process rather than to a binary that merely exists:
    both nodes report `bitcoin.exe` = `fbcac071d92e26d82ec917214e334bd43850c0691f113bab1d4741c9bdd30d2d`,
    **matching the oracle**, with `libeay32.dll` `d108cdff…c77a182` and `mingwm10.dll` `1badf397…2d7708f`
    identical across both and distinct PIDs (5212 / 4196). The `post` pair is taken after the spend; the
    two must bracket **one uninterrupted process** — restarting `bitcoin.exe` between them voids the pair
    and a fresh `pre` is required.
  - Two things fall out of those records that are worth stating. **The bound processes started
    `2026-08-01T01:32:00Z` and `…:32:20Z`**, twenty seconds apart, and have run continuously since —
    **R4a, R4b and R4c are one single run**, not three. That is not recalled, it is measured: R4a's
    `debug.log` is a **byte-exact prefix** of R4b's on *both* nodes (nodeA 6,248 → 22,016 bytes; nodeB
    6,982 → 22,898), so the same file was appended to and `bitcoin.exe` never restarted between them.
    (v0.1.0 writes no timestamps into `debug.log` — that arrives in v0.1.3's `util.cpp` — so the prefix
    test is the available proof, and it is a stronger one.) The binding therefore reaches **backwards over
    the whole R4 series**: the already-witnessed sustained relay and reorganisation are retroactively bound
    to a live process running `fbcac071…`, which they were not when they were written up.
    And **both guests report the same `vm_hostname` and `data_dir`** (they were cloned from one
    image), so nothing *measured* in these files distinguishes node A's machine from node B's — the `-Node`
    label is operator-supplied. That is not a flaw in the binding, whose job is process→binary; two-node
    separation is established by the two distinct `blk0001.dat` files and the peer connections in the logs.
