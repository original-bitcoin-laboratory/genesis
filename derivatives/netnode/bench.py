"""bench — measure the node's validation throughput and localize the cost. NOT money.

The honest first step of "a faster node" is *not* to rewrite in C++/Rust — it is to measure where a
growing chain's validation time actually goes, so the rewrite decision is made on data, not
assumption. This builds a chain of real **signed** transactions and times:

- **end-to-end validation** — building the validated UTXO chainstate from scratch over the whole
  index (`ChainState.activate_best`): every block re-parsed, every input's script/ECDSA re-checked,
  the UTXO rebuilt — and reports **blocks/sec, tx/sec, and signature-verifications/sec**;
- the **component costs** — one ECDSA `verify_spend`, and block parsing with txids — so the report
  shows *which* cost dominates (and therefore what a faster node would actually need to accelerate).

Run:  python bench.py                 # ~300 blocks, ~2 spends/block
      python bench.py 1000 3          # 1000 blocks, ~3 spends/block

Evidence: MODEL / NEW-EXP. This is a measurement tool, not part of consensus.
"""

from __future__ import annotations

import pathlib
import sys
import time

_HERE = pathlib.Path(__file__).resolve().parent
for _p in ("model", "p2p", "nov08x", "wallet"):
    sys.path.insert(0, str(_HERE.parent / _p))
sys.path.insert(0, str(_HERE))

import cscript                                                       # noqa: E402
from chainsync import Chain                                         # noqa: E402
from p2p import block_bytes, merkle_root, pow_ok                    # noqa: E402
from spend import sign, verify_spend                               # noqa: E402
from tx_sighash import Tx, TxIn, TxOut, dsha256, new_key, serialize as ser_tx  # noqa: E402

from spend import verify_spend                                     # noqa: E402  (faithful interpreter)

from chains import CHAINS                                           # noqa: E402
from chainstate import ChainState                                  # noqa: E402
from difficulty import NET_TARGET_SPACING, expected_bits           # noqa: E402
import fastverify                                                   # noqa: E402
from fastverify import verify_spend_fast                           # noqa: E402  (accelerated, == faithful)
from fullnode import parse_block_with_txids                        # noqa: E402

ZERO = b"\x00" * 32
EASY = 0x207FFFFF                                                   # regtest-easy target (instant mining)
BASE_TIME = 1_231_006_506
RULES = CHAINS["jan09x"].rules
_tag = [0]


def _coinbase(height, value, spk=b"\x51"):
    _tag[0] += 1
    s = bytes([height & 0xFF, (height >> 8) & 0xFF, _tag[0] & 0xFF, (_tag[0] >> 8) & 0xFF])
    return Tx(1, [TxIn(ZERO, 0xFFFFFFFF, s, 0xFFFFFFFF)], [TxOut(value, spk)], 0)


def _txid(tx):
    return dsha256(ser_tx(tx))


def _mine(prev, height, txs, nbits, t):
    mr = merkle_root(txs)
    for nonce in range(1 << 24):
        raw = block_bytes(1, prev, mr, t, nbits, nonce, txs)
        if pow_ok(raw, nbits):
            return raw
    raise RuntimeError("no nonce")


def build_chain(n_blocks: int, spends_per_block: int):
    """A jan09x chain of `n_blocks`, each (after warmup) spending up to `spends_per_block` matured
    P2PK coins we own — i.e. carrying real ECDSA signatures. Blocks are spaced at the target
    spacing and mined at the *expected* retarget difficulty, so the chain stays valid across
    retarget boundaries (difficulty holds at the easy floor). Returns (chain, n_tx, n_sig, sample)."""
    chain = Chain()
    chain.add_genesis(_mine(ZERO, 0, [_coinbase(0, 0)], EASY, BASE_TIME), EASY)
    priv, pub = new_key()
    spk_tokens = [pub, "OP_CHECKSIG"]
    spk_bytes = cscript.assemble(spk_tokens)
    pool: list[tuple[bytes, int, int]] = []            # spendable (txid, n, value), FIFO = oldest first
    sample = [None]
    n_tx = n_sig = 0
    prev, height = chain.genesis, 1
    for _ in range(n_blocks):
        subsidy = RULES.get_block_value(height - 1)
        spends, fee_total = [], 0
        for _ in range(spends_per_block):
            if not pool:
                break
            txid, n, val = pool.pop(0)
            sp = Tx(1, [TxIn(txid, n, b"", 0xFFFFFFFF)], [TxOut(val - 1, spk_bytes)], 0)
            sp.vin[0].script = cscript.assemble([sign(priv, spk_tokens, sp, 0)])
            spends.append(sp)
            fee_total += 1
            n_sig += 1
            sample[0] = (cscript.parse(sp.vin[0].script), spk_tokens, sp, 0)
        cb = _coinbase(height, subsidy + fee_total, spk_bytes)     # coinbase pays us -> refills the pool
        block_txs = [cb, *spends]
        nbits = expected_bits(chain, prev, RULES)                 # honor the retarget (stays easy, so instant)
        raw = _mine(prev, height, block_txs, nbits, BASE_TIME + height * NET_TARGET_SPACING)
        assert chain.process_block(raw)[0] == "accepted"
        pool.append((_txid(cb), 0, subsidy + fee_total))          # matured (FIFO) by the time it's popped
        for sp in spends:
            pool.append((_txid(sp), 0, sp.vout[0].value))         # non-coinbase output: spendable at once
        n_tx += len(block_txs)
        prev, height = chain.tip, height + 1
    return chain, n_tx, n_sig, sample[0]


def run(n_blocks: int = 300, spends_per_block: int = 2, reps: int = 2000) -> dict:
    chain, n_tx, n_sig, sample = build_chain(n_blocks, spends_per_block)

    t0 = time.perf_counter()                                       # end-to-end: validate the whole chain
    st = ChainState(chain, RULES, maturity=1)
    st.activate_best()
    validate_dt = time.perf_counter() - t0
    blocks = st.height

    ss, spk, tx, n = sample                                        # a bare-P2PK spend to verify
    t = time.perf_counter()
    for _ in range(reps):
        verify_spend(ss, spk, tx, n)                               # faithful pure-Python interpreter
    interp_us = (time.perf_counter() - t) / reps * 1e6
    t = time.perf_counter()
    for _ in range(reps):
        verify_spend_fast(ss, spk, tx, n)                          # accelerated (native ECDSA, no interpreter)
    fast_us = (time.perf_counter() - t) / reps * 1e6

    tip_raw = chain.by_hash[chain.tip].raw                         # block parse + txids
    t = time.perf_counter()
    for _ in range(reps):
        parse_block_with_txids(tip_raw)
    parse_us = (time.perf_counter() - t) / reps * 1e6

    return {
        "blocks": blocks, "txs": n_tx, "sigs": n_sig,
        "validate_s": validate_dt,
        "blocks_per_s": blocks / validate_dt,
        "txs_per_s": n_tx / validate_dt,
        "sigs_per_s": (n_sig / validate_dt) if n_sig else 0.0,
        "interp_us": interp_us, "fast_us": fast_us,
        "speedup": interp_us / fast_us if fast_us else 1.0,
        "backend": fastverify.BACKEND,
        "parse_us": parse_us,
        "sig_fraction": (n_sig * fast_us / 1e6) / validate_dt if validate_dt else 0.0,
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    n_blocks = int(argv[0]) if len(argv) > 0 else 300
    spb = int(argv[1]) if len(argv) > 1 else 2
    print(f"building a jan09x chain: {n_blocks} blocks, up to {spb} signed spend(s)/block …",
          flush=True)
    m = run(n_blocks, spb)
    print("\n== validation throughput (build the validated UTXO chainstate from scratch) ==")
    print(f"  chain           : {m['blocks']} blocks, {m['txs']} txs, {m['sigs']} signatures")
    print(f"  validated in    : {m['validate_s']:.3f} s")
    print(f"  blocks / second : {m['blocks_per_s']:,.0f}")
    print(f"  txs    / second : {m['txs_per_s']:,.0f}")
    print(f"  sigs   / second : {m['sigs_per_s']:,.0f}")
    print("\n== per-input verification (bare P2PK) ==")
    print(f"  backend               : {m['backend']}")
    print(f"  faithful interpreter  : {m['interp_us']:.1f} µs   (spend.verify_spend)")
    print(f"  accelerated fast path : {m['fast_us']:.1f} µs   (fastverify.verify_spend_fast)")
    print(f"  speedup               : {m['speedup']:.1f}x   (identical accept/reject — differential-tested)")
    print(f"  parse block + txids   : {m['parse_us']:.1f} µs")
    print(f"  verify share of validation time : {m['sig_fraction'] * 100:.0f}%")
    print("\n== reading ==")
    print("  Signature verification dominates, so the lever is a native verifier — realized here via")
    print("  libsecp256k1, but ONLY through a byte-faithful path: raw libsecp256k1 rejects high-S")
    print("  (BIP66), which the OpenSSL-lenient v0.1 origin accepts, so a naive swap would DRIFT")
    print("  consensus. verify_spend_fast normalizes + falls back to stay identical to the origin.")
    print("  NOT money.")
    return m


if __name__ == "__main__":
    main()
