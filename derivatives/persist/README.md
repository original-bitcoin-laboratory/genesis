# Headless v0.1 persistence (derivative)

**Evidence level: `MODEL`.** Save the block index and the wallet to disk, shut
down, reload, and **resume at the same tip with the same spendable wallet** — the
"restart" half of what a VM run would show, headlessly.

## Faithful to the v0.1 database (db.cpp / db.h / main.h)

- **Block index** — `CDiskBlockIndex` keyed by `("blockindex", hashBlock)`
  (db.cpp:282) plus the best-chain pointer `"hashBestChain"` (db.cpp:297). The
  record layout is byte-faithful (main.h:1151), **128 bytes**:

  ```
  [nVersion:i32][hashNext:u256][nFile:u32][nBlockPos:u32][nHeight:i32]
  [block nVersion:i32][hashPrev:u256][hashMerkleRoot:u256][nTime:u32][nBits:u32][nNonce:u32]
  ```

- **`LoadBlockIndex`** (db.cpp:322) — rebuild every `CBlockIndex`, re-wire
  `pprev`/`pnext` by hash, then `pindexBest = mapBlockIndex[hashBestChain]`,
  `nBestHeight = pindexBest->nHeight`. Our `load_chain` reconstructs the exact
  same tip, heights, main-chain order, per-block bytes, and `in_main` flags —
  **including after a reorg** (main branch and the abandoned side branch both
  survive the round-trip).

- **Wallet** — `CWalletDB` records `("key", vchPubKey) -> CPrivKey` (db.h:378-384,
  written by AddKey at main.cpp:72), plus the wallet's coins. A private key
  restored from disk **still signs**: a reloaded wallet creates a transaction that
  the lab's independent EvalScript verifies.

## What is / isn't reproduced

Faithful: the **record key/value contents** and the LoadBlockIndex reconstruction
logic. Not reproduced: the **Berkeley DB 4.x engine** and its `.dat` container.
Records live in a plain length-prefixed key/value file (`DiskStore`), and raw
blocks are held in a `("block", hash)` record standing in for `blk*.dat` at
`(nFile, nBlockPos)`. Private keys are serialised as PKCS8 DER (standing in for
`i2d_ECPrivateKey` / `CPrivKey`).

## What the tests show (`test_persist.py`, 7)

`CDiskBlockIndex` is 128 bytes and round-trips its fields; a 6-block chain survives
save→reload (in-memory *and* to a real file); a **reorged** chain reloads with the
new main chain and the abandoned blocks off-chain; wallet keys/coins reload with the
right balance (spent coins excluded); and a **DER-reloaded private key still signs a
valid spend**.

```bash
python -m pytest        # 7 passed
python test_persist.py  # chain blob size + reloaded height
```
