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

## What the demo shows (`test_p2p.py`)

Node A (with a mined block + a tx) connects to Node B; they exchange `version`;
A announces via `inv`; B requests via `getdata`; A sends the `block` and `tx`; **B
independently re-verifies the block's proof-of-work** before accepting, and relays
the block onward via `inv`. Verified: B ends up with both, and the wire framing
round-trips. Run:

```bash
python -m pytest        # 2 passed
python test_p2p.py      # prints B's inventory + message log
```

## Boundary

This covers the message/relay layer and receive-time PoW/integrity checks. Full
consensus validation of a relayed block (UTXO `ConnectBlock`) is the job of
`../node/chain_port.cpp`; `addr`/`getblocks` chain sync, orphan handling, and the
IRC discovery that seeds peers (`../r3/mini_ircd.py`) are separate. Two *unmodified
binaries* exchanging over a socket is the isolated-VM run (`../../docs/R3_*`).
