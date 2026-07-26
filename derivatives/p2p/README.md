# Headless P2P relay (derivative)

**Evidence level: `MODEL`** (wire format anchored to source). Two headless v0.1
nodes talk over localhost TCP — no VM, no GUI — using the real v0.1 network
protocol, and relay a block and a transaction between them.

## Faithful to the v0.1 wire (net.h / main.cpp)

- Message = `[magic:4][command:12][size:4 LE][payload]` with **no checksum**
  (`CMessageHeader`, net.h). Magic = `f9 be b4 d9` (net.h:54).
- `PROTOCOL_VERSION = 101` (serialize.h:22).
- Handshake is a plain `version` exchange with **no verack** (main.cpp:1705) —
  `version` payload = `int nVersion, uint64 nServices, int64 nTime, CAddress`.
- Relay: `inv` → `getdata` → `block` / `tx` (main.cpp:1772-1955); `CInv` =
  `int type, uint256 hash` with `MSG_TX=1`, `MSG_BLOCK=2`.
- `block` = 80-byte header + `CompactSize(vtx)` + txs; `tx` = a serialized
  transaction (same serialization as the rest of the lab, `tx_sighash`).

## What the relay demo shows (`test_p2p.py`)

Node A (with a mined block + a tx) connects to Node B; they exchange `version`;
A announces via `inv`; B requests via `getdata`; A sends the `block` and `tx`; **B
independently re-verifies the block's proof-of-work** before accepting, and relays
the block onward via `inv`. Verified: B ends up with both, and the wire framing
round-trips.

## Chain synchronisation (`chainsync.py` / `test_chainsync.py`)

A fresh node **catches up a whole multi-block chain** from a peer — the real v0.1
sync path, anchored to `main.cpp` / `main.h`:

- On `version` the behind node asks `getblocks(CBlockLocator(pindexBest), 0)`
  (main.cpp:1734). `CBlockLocator::Set` records the tip, steps back exponentially
  (step 1 for the first 10, then doubling) and **always ends with genesis**
  (main.h:1241).
- The `getblocks` handler does `pindex = locator.GetBlockIndex(); pindex->pnext`
  and walks the main chain forward, `inv`-ing each block until `hashStop`
  (main.cpp:1832-1864).
- `ProcessBlock` (main.cpp:1236): a block whose `hashPrevBlock` is unknown is held
  in `mapOrphanBlocks` and triggers `getblocks(pindexBest, GetOrphanRoot)` to fill
  the gap; when the parent arrives, waiting orphans are **reconnected recursively**.
- Best chain is **height-based** in this earliest release (`nHeight > nBestHeight`,
  main.cpp:1097): extending the tip appends; a longer competing branch **reorgs**.

Three unit checks (locator shape, out-of-order orphan reconnection, height-based
reorg to a longer branch) plus two end-to-end scenarios over localhost TCP:

- **linear** — B (genesis only) reaches A's 6-block tip via
  version → getblocks → inv → getdata → block; `B.main_chain() == A.main_chain()`.
- **orphan-driven** — A broadcasts only its tip; B orphans it, fires
  `getblocks(GetOrphanRoot)`, fills b1..b4, and the tip reconnects — B ends fully
  synced with **no orphans left**.

```bash
python -m pytest          # 7 passed (2 relay + 5 chain-sync)
python test_p2p.py        # relay: B's inventory + message log
python test_chainsync.py  # sync: heights reached + B's message log
```

## Boundary

This covers the message/relay layer, receive-time PoW/integrity checks, and
end-to-end chain sync (getblocks / locator / orphans / height-based reorg). Full
consensus validation of each synced block (UTXO `ConnectBlock`) is the job of
`../node/chain_port.cpp` — here `CheckBlock` enforces PoW headlessly. The IRC
discovery that seeds peers (`../r3/mini_ircd.py`) and two *unmodified binaries*
exchanging over a socket (the isolated-VM run, `../../docs/R3_*`) remain separate.
