# Headless consensus port (derivative)

**Evidence level: `PORT`** — a compiled, headless derivative that runs v0.1's
chain/consensus logic without the GUI or Berkeley DB. It's the automated
counterpart to the (human-gated, GUI-only) `JAN09-EXECUTED` VM run: not the
unmodified binary, but Satoshi's actual construction/consensus logic, reproduced
in C++ with real OpenSSL for hashing and big numbers.

## What it does (`node_port.cpp`, all headless)

1. **Reproduces the genesis block** exactly from the original construction
   (`main.cpp:1455-1480`): builds the coinbase (the "The Times 03/Jan/2009…"
   scriptSig, the `50 * COIN` output, the genesis pubkey), computes the Merkle
   root and the block hash, and asserts they equal the canonical values —
   - Merkle `4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b`
   - Hash   `000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f`

   This is the **same assertion the original client runs at startup**, and the
   block hash is an **external anchor** — it is the genesis on the live Bitcoin
   chain. Matching it proves our serialization + hashing are byte-exact.
2. **Subsidy / halving** (`GetBlockValue`, `main.cpp:675`): 50 → 25 → 12.5 coins
   at heights 0 / 210000 / 420000; fees add on top.
3. **Proof-of-work**: mines block 1 onto genesis by searching the nonce for a
   double-SHA-256 header hash under an (easy, for the demo) target — the real
   mining loop from `BitcoinMiner` (`main.cpp:2183`).
4. **Difficulty retarget** (`GetNextWorkRequired`, `main.cpp:685`): faster
   timespan → harder target, slower → easier (clamped ×4).

Run: `./run.sh` (or `GXX=/c/msys64/mingw64/bin/g++ ./run.sh`) → `12 PASS, 0 FAIL`.

## Original vs ported

| Part | Status |
|---|---|
| genesis coinbase/header construction, subsidy, difficulty, PoW check | reproduced from `main.cpp`/`main.h` |
| number codec (`CBigNum` getvch, incl. `CBigNum("0x…")`) | original logic on real OpenSSL BN |
| double-SHA-256, big-number arithmetic | real OpenSSL |
| tx/block **serialization** (CompactSize length-prefixed script fields) | reproduced from `serialize.h` |

## Boundary (not included)

Full **UTXO block validation** (`ConnectInputs`/`ConnectBlock`) and chain storage
pull in the Berkeley-DB layer (`db.*`) — the hard porting boundary — and the P2P
node loop (`net.*`). Those, and the unmodified `bitcoin.exe`, remain the VM's job
(see `../../docs/R3_HISTORICAL_NODE.md`). This port covers the **stateless**
consensus core: genesis, issuance, PoW, difficulty.
