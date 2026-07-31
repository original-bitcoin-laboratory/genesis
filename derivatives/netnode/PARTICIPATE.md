# Participating in an experimental X‑chain — coins & capabilities

> **This is not money.** `NOV08‑X` / `JAN09‑X` are experimental research networks that run the earliest
> Bitcoin script vocabulary with **nothing disabled**. There is no coin to buy, sell, or hold, and the
> code runs at an easy, unaudited difficulty. Nothing here has value; treating it as money would hurt
> people. Read [`SECURITY.md`](SECURITY.md) before exposing a node.

This guide answers two questions: **how you generate, mine, send and receive coins**, and **what else you
can express** — the opcode vocabulary and the contract forms the node actually validates. For installing
and running a node (seeds, NAT, restarts, options) see [`RUN.md`](RUN.md); for the full, generated opcode
table with a `file:line` witness for every opcode see [`../../inventory/OPCODES.md`](../../inventory/OPCODES.md).

---

## The two chains

| Chain | `--chain` | P2P port | Base unit (1 coin) | Coinbase pays |
|---|---|---|---|---|
| November constitution | `nov08x` | 18008 | `1e6` | bare public key (P2PK) |
| January (v0.1.0) constitution | `jan09x` | 18009 | `1e8` | bare public key (P2PK) |

Each has its own genesis, magic and port and **cannot** connect to the other, to any historical chain, or
to live Bitcoin. Join the seeded network by dialling the public anchor:

```bash
# clone once
git clone https://github.com/original-bitcoin-laboratory/genesis && cd genesis/derivatives

# a wallet-bearing node that syncs from the seed and exposes a localhost control port
python -m netnode --chain jan09x --datadir ./data \
                  --connect seed.bitcoin-lab.org:18009 \
                  --wallet --rpc 127.0.0.1:18332
```

(For `nov08x` use `--connect seed.bitcoin-lab.org:18008`. The RPC is **loopback‑only and unauthenticated** —
never expose it. All nodes on one network must share the same `--min-difficulty` floor; ask the operator or
match the seed's published value.)

---

## Part 1 — Generate, mine, send, receive

Everything below is driven from a second shell with the `ctl` client against your node's RPC port.

### Your identity / address

```bash
python -m netnode ctl --rpc 18332 getprimaryaddress   # your existing key — mints NOTHING
python -m netnode ctl --rpc 18332 getnewaddress       # mint a fresh receive key
```

`getprimaryaddress` returns both forms of your identity:

```json
{ "pubkey": "04a1b2…",  "address": "1BvBMSE…",  "hash160": "…",  "not_money": true }
```

- The **`04…` / `02…` pubkey hex** is a raw SEC public key — paid as **bare P2PK** (`<pubkey> OP_CHECKSIG`),
  exactly how v0.1 pays a coinbase.
- The **`1…` address** is the familiar v0.1 Base58Check address (version `0x00`) — paid as **P2PKH**.

Share **either** to get paid. Prefer `getprimaryaddress` (stable, mints nothing) over `getnewaddress`
(which appends a new key to `wallet.json`).

### Mine

Add `--mine` when you start the node. A mining node produces blocks and earns each block's **coinbase**
(subsidy **+** the fees of any transactions it includes) to its wallet. A coinbase becomes spendable only
after **maturity**. On the live seeded network mining competes at the shared difficulty floor, so it takes
real work; for solo experimentation run an isolated node at the easy genesis difficulty.

```bash
python -m netnode --chain jan09x --datadir ./data --mine --wallet --rpc 127.0.0.1:18332
```

### Receive

Give a payer your pubkey hex or `1…` address. When their transaction is mined into a block your balance
updates:

```bash
python -m netnode ctl --rpc 18332 getbalance      # spendable (mature, owned), in base units
python -m netnode ctl --rpc 18332 getinfo         # chain / height / tip / peers / mempool / money:false
```

### Send

```bash
python -m netnode ctl --rpc 18332 send <ADDRESS-or-PUBKEY-HEX> <AMOUNT> [FEE]
```

`send` accepts **either** a `1…` address (paid P2PKH) **or** a raw pubkey hex (paid bare P2PK) — both are
v0.1 payment forms — builds and signs the transaction against your validated UTXO, submits it to the
mempool, broadcasts it (`inv → getdata → tx`), and returns the **txid**. Amounts and fees are in **base
units** (`1e8` on JAN09‑X, `1e6` on NOV08‑X). It confirms when some mining node includes it in a block.

**End to end:** run node → `getprimaryaddress` → mine or receive → `getbalance` → `send` → the payee sees
it after a block. That is the whole coin lifecycle, no coding required.

---

## Part 2 — What else you can express (the vocabulary)

The X‑chains carry the **complete original opcode set with nothing disabled** — 106 distinct opcode values,
94 with an execution branch. The one opcode faithful v0.1 leaves commented out, **`OP_NOTEQUAL`**, is
**re‑opened** on the experimental chains (that is precisely what makes them *experimental* rather than
faithful). The generated inventory carries a `script.h`/`script.cpp` `file:line` witness for each one
([`OPCODES.md`](../../inventory/OPCODES.md)); by functional group:

| Group | count | examples |
|---|--:|---|
| push value | 24 | `OP_0`, `OP_1`…`OP_16`, `OP_PUSHDATA1/2/4` |
| control | 10 | `OP_IF` `OP_NOTIF` `OP_ELSE` `OP_ENDIF` `OP_VERIFY` `OP_RETURN` `OP_NOP*` |
| stack ops | 19 | `OP_DUP` `OP_DROP` `OP_SWAP` `OP_ROT` `OP_PICK` `OP_ROLL` `OP_TOALTSTACK` |
| splice ops | 5 | `OP_CAT` `OP_SUBSTR` `OP_LEFT` `OP_RIGHT` `OP_SIZE` |
| bit logic | 8 | `OP_INVERT` `OP_AND` `OP_OR` `OP_XOR` `OP_EQUAL` `OP_EQUALVERIFY` |
| numeric | 27 | `OP_ADD` `OP_SUB` `OP_BOOLAND` `OP_NUMEQUAL` `OP_MIN` `OP_MAX` `OP_WITHIN` `OP_NOTEQUAL` |
| crypto | 10 | `OP_RIPEMD160` `OP_SHA1` `OP_SHA256` `OP_HASH160` `OP_HASH256` `OP_CHECKSIG` `OP_CHECKMULTISIG` |

### Contract forms the node validates

Each of the following is a **passing, tested construction** — the full‑node ones live in
[`test_chainstate.py`](test_chainstate.py) (built as real signed transactions, connected through the
`ConnectBlock` path), the interpreter‑level ones in [`../model/`](../model/). scriptPubKey tokens:

| Construction | scriptPubKey | Spent with |
|---|---|---|
| **Bare P2PK** (coinbase form) | `[<pubkey>, OP_CHECKSIG]` | `[<sig>]` |
| **P2PKH** (`1…` address) | `[OP_DUP, OP_HASH160, <h160>, OP_EQUALVERIFY, OP_CHECKSIG]` | `[<sig>, <pubkey>]` |
| **Escrow / m‑of‑n multisig** (2‑of‑3) | `[OP_2, <pubA>, <pubB>, <pubC>, OP_3, OP_CHECKMULTISIG]` | `[OP_0, <sig>, <sig>]` |
| **Hash‑lock** | `[OP_HASH256, <H>, OP_EQUALVERIFY, <pubkey>, OP_CHECKSIG]` | `[<sig>, <preimage>]` |
| **Hash‑lock OR refund** (HTLC‑style) | `[OP_IF, OP_HASH256, <H>, OP_EQUALVERIFY, <pubR>, OP_CHECKSIG, OP_ELSE, <pubS>, OP_CHECKSIG, OP_ENDIF]` | claim `[<sigR>, <preimage>, OP_1]` · refund `[<sigS>, OP_0]` |
| **Assurance / crowdfund** | pledges signed `SIGHASH_ANYONECANPAY` and aggregated into one funding transaction | each pledge commits only to its own input |

These are the same escrow, conditional‑payment, hash‑lock and assurance constructions the January client's
interpreter already made expressible — here executed end‑to‑end on a running node.

---

## Part 3 — Putting a richer script on‑chain

Two RPC methods cover the whole vocabulary, no Python required:

**Create a contract output — `sendtoscript`.** Fund *any* `scriptPubKey` straight from your wallet by
passing a JSON array of `OP_` names and hex data literals. A hash‑lock, for example:

```bash
python -m netnode ctl --rpc 18332 sendtoscript \
  '["OP_HASH256","<sha256d-of-secret-hex>","OP_EQUALVERIFY","<pubkey-hex>","OP_CHECKSIG"]' \
  5000000        # amount in base units → prints the funding txid
```

**Spend it — `sendrawtransaction`.** Build the spending transaction with any tool (the lab's helpers, or
your own), sign it, and submit the raw hex. The node runs the **same** validation a peer's transaction gets
— no double‑spend, script satisfied, no inflation, coinbase maturity — then relays it (`inv → getdata →
tx`); a mining node folds it into its next block:

```bash
python -m netnode ctl --rpc 18332 sendrawtransaction <signed-tx-hex>   # prints the txid
```

To build that raw spend in Python (e.g. `<sig> <preimage>` to open the hash‑lock above):

```python
# inside genesis/derivatives
import cscript
from tx_sighash import Tx, TxIn, TxOut, serialize as ser_tx
from spend import sign

hl   = ["OP_HASH256", H, "OP_EQUALVERIFY", pub, "OP_CHECKSIG"]     # the funded scriptPubKey (bytes tokens)
spend = Tx(1, [TxIn(prev_txid, vout, b"", 0xFFFFFFFF)], [TxOut(amount - 1000, b"\x51")], 0)
spend.vin[0].script = cscript.assemble([sign(my_priv, hl, spend, 0), secret])
print(ser_tx(spend).hex())          # hand this to `sendrawtransaction`
```

The tested `test_chainstate.py` functions (`test_fullnode_hashlock_spend_and_reject`,
`test_fullnode_conditional_refund_both_branches`, `test_fullnode_assurance_anyonecanpay_survives_added_input`)
and `test_wallet.py::test_rpc_contract_lifecycle_via_sendtoscript_and_sendrawtransaction` are working,
copyable templates for each form and for the full create‑then‑spend round trip over the RPC.

---

## Remember

It's a research microscope, not a currency: no premine, no sale, no assigned value, guardrail‑free by
design so the origin's exact behaviour can be studied. See [`SECURITY.md`](SECURITY.md) and
[`../../docs/PUBLIC_TESTNET_SCOPE.md`](../../docs/PUBLIC_TESTNET_SCOPE.md). **Not money.**
