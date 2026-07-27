"""Full block validation for the X-chain nodes — Path B toward a production node (part 1).

Beyond proof‑of‑work, a real node validates what a block *claims*. The lab had `serialize` but no
deserialize, so this adds a **block/tx parser** and enforces, on top of PoW, the checks that are
**context‑free** (need only the block and its parent):

- **structure** — ≥1 transaction; `tx[0]` is the coinbase; no other tx is a coinbase;
- **merkle commitment** — the header's merkle root equals the recomputed root of the txs;
- **difficulty** — `nBits` equals the expected retarget for the parent.

The **value** rules — no double‑spend, script satisfaction, no inflation, and the coinbase‑value
rule *with fees* (`Rules.coinbase_ok`) — need the UTXO set, so they live in `ChainState._connect`,
which runs when a block is connected to the validated chain. (Fees can only be known from the
inputs' prior values, which is a UTXO fact, not a block‑local one.) Splitting it this way keeps
this parser‑level check total on any single block while the stateful checks gate activation.

The difficulty check is deferred for a block whose parent isn't yet known (an orphan).
Evidence: MODEL / NEW‑EXP.
"""

from __future__ import annotations

from chainsync import ZERO, merkle_root, nbits_of, prev_hash, read_compact  # noqa: F401
from tx_sighash import Tx, TxIn, TxOut

from difficulty import expected_bits

NULL_N = 0xFFFFFFFF


def parse_tx(b: bytes, i: int):
    """Deserialize one transaction from `b` at offset `i` (inverse of tx_sighash.serialize)."""
    ver = int.from_bytes(b[i:i + 4], "little"); i += 4
    nin, i = read_compact(b, i)
    vin = []
    for _ in range(nin):
        prev = b[i:i + 32]; i += 32
        n = int.from_bytes(b[i:i + 4], "little"); i += 4
        slen, i = read_compact(b, i)
        script = b[i:i + slen]; i += slen
        seq = int.from_bytes(b[i:i + 4], "little"); i += 4
        vin.append(TxIn(prev, n, script, seq))
    nout, i = read_compact(b, i)
    vout = []
    for _ in range(nout):
        val = int.from_bytes(b[i:i + 8], "little", signed=True); i += 8   # value is signed int64
        slen, i = read_compact(b, i)
        script = b[i:i + slen]; i += slen
        vout.append(TxOut(val, script))
    lock = int.from_bytes(b[i:i + 4], "little"); i += 4
    return Tx(ver, vin, vout, lock), i


def parse_block(raw: bytes):
    body = raw[80:]                                    # after the 80-byte header
    ntx, i = read_compact(body, 0)
    txs = []
    for _ in range(ntx):
        tx, i = parse_tx(body, i)
        txs.append(tx)
    return txs


def is_coinbase(tx: Tx) -> bool:
    return len(tx.vin) == 1 and tx.vin[0].prevhash == ZERO and tx.vin[0].n == NULL_N


def validate_block(raw: bytes, chain, rules, min_bits=None):
    """(ok, reason). Context‑free checks (structure, merkle) always; difficulty when the parent is
    known (deferred for orphans, but re‑checked authoritatively in `ChainState._connect`). The
    value/coinbase rules are UTXO‑stateful — see `chainstate.ChainState._connect`."""
    try:
        txs = parse_block(raw)
    except Exception:
        return False, "unparseable"
    if not txs:
        return False, "no transactions"
    if not is_coinbase(txs[0]):
        return False, "first tx is not a coinbase"
    if any(is_coinbase(t) for t in txs[1:]):
        return False, "more than one coinbase"
    if merkle_root(txs) != raw[36:68]:
        return False, "merkle root mismatch"
    prev = prev_hash(raw)
    if prev in chain.by_hash:                          # parent known -> difficulty checkable
        if nbits_of(raw) != expected_bits(chain, prev, rules, min_bits):
            return False, "wrong difficulty"
    return True, "ok"
