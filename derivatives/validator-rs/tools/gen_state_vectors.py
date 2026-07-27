"""Regenerate the Rust stateful-validator golden vectors from the verified Python ChainState.

    python validator-rs/tools/gen_state_vectors.py

Writes validator-rs/tests/data/state_data.rs (a valid signed chain + rule-violating blocks with the
Python node's exact rejection reasons). Uses fresh keys each run; the vectors are self-consistent.
NOT money.
"""
import pathlib
import sys

# tools/ -> validator-rs/ -> derivatives/
D = pathlib.Path(__file__).resolve().parents[2]
for p in ("model", "p2p", "nov08x", "netnode"):
    sys.path.insert(0, str(D / p))

import cscript
from chainsync import Chain, block_hash
from p2p import block_bytes, merkle_root, pow_ok
from tx_sighash import Tx, TxIn, TxOut, dsha256, new_key, serialize as ser_tx
from spend import sign
from chainstate import ChainState, InvalidBlock
from chains import CHAINS
from difficulty import NET_TARGET_SPACING, expected_bits

RULES = CHAINS["jan09x"].rules
EASY = 0x207FFFFF
BASE = 1_231_006_506
MAT = 1
ZERO = b"\x00" * 32
_tag = [0]


def txid(tx):
    return dsha256(ser_tx(tx))


def coinbase(height, value, spk):
    _tag[0] += 1
    s = bytes([height & 0xFF, (height >> 8) & 0xFF, _tag[0] & 0xFF, (_tag[0] >> 8) & 0xFF])
    return Tx(1, [TxIn(ZERO, 0xFFFFFFFF, s, 0xFFFFFFFF)], [TxOut(value, spk)], 0)


def mine(prev, height, txs, chain, genesis=False):
    nbits = EASY if genesis else expected_bits(chain, prev, RULES)
    mr = merkle_root(txs)
    t = BASE + height * NET_TARGET_SPACING
    for nonce in range(1 << 24):
        raw = block_bytes(1, prev, mr, t, nbits, nonce, txs)
        if pow_ok(raw, nbits):
            return raw
    raise RuntimeError("no nonce")


def subsidy_at(height):
    return RULES.get_block_value(height - 1)


priv, pub = new_key()
wrong_priv, _ = new_key()
P2PK = cscript.assemble([pub, "OP_CHECKSIG"])

chain = Chain()
g = mine(ZERO, 0, [coinbase(0, 0, b"\x51")], chain, genesis=True)
chain.add_genesis(g, EASY)
st = ChainState(chain, RULES, maturity=MAT)
st.activate_best()

valid = []  # (raw, height, subsidy, is_genesis, utxo_count, balance)
valid.append((g.hex(), 0, 0, True, len(st.utxo), st.balance()))

# block 1: coinbase pays our key
cb1 = coinbase(1, subsidy_at(1), P2PK)
b1 = mine(chain.tip, 1, [cb1], chain)
assert chain.process_block(b1)[0] == "accepted"
st.activate_best()
valid.append((b1.hex(), 1, subsidy_at(1), False, len(st.utxo), st.balance()))

# block 2: coinbase + a real signed spend of block-1's (matured) coinbase
fee = 1
spend = Tx(1, [TxIn(txid(cb1), 0, b"", 0xFFFFFFFF)], [TxOut(subsidy_at(1) - fee, P2PK)], 0)
spend.vin[0].script = cscript.assemble([sign(priv, [pub, "OP_CHECKSIG"], spend, 0)])
cb2 = coinbase(2, subsidy_at(2) + fee, P2PK)
b2 = mine(chain.tip, 2, [cb2, spend], chain)
assert chain.process_block(b2)[0] == "accepted"
st.activate_best()
valid.append((b2.hex(), 2, subsidy_at(2), False, len(st.utxo), st.balance()))

# ---- invalid blocks on the tip (height 3), each connected in isolation for its error ----
SPENDABLE_TXID = txid(spend)          # block-2's spend output (non-coinbase, P2PK to us)
SPENDABLE_VAL = subsidy_at(1) - fee
CB2_TXID = txid(cb2)                   # block-2 coinbase (matured at height 3)
CB2_VAL = subsidy_at(2) + fee

invalid = []


def make_invalid(name, txs, height=3):
    prev = st.tip
    raw = mine(prev, height, txs, chain)
    chain.process_block(raw)
    h = block_hash(raw)
    try:
        st._connect(h)
        st._disconnect()
        err = "UNEXPECTEDLY_VALID"
    except InvalidBlock as e:
        err = str(e)
    return (raw.hex(), height, subsidy_at(height), err)


# double-spend: two txs spend the same coin
s1 = Tx(1, [TxIn(SPENDABLE_TXID, 0, b"", 0xFFFFFFFF)], [TxOut(SPENDABLE_VAL - 1, b"\x51")], 0)
s1.vin[0].script = cscript.assemble([sign(priv, [pub, "OP_CHECKSIG"], s1, 0)])
s2 = Tx(1, [TxIn(SPENDABLE_TXID, 0, b"", 0xFFFFFFFF)], [TxOut(SPENDABLE_VAL - 1, b"\x52")], 0)
s2.vin[0].script = cscript.assemble([sign(priv, [pub, "OP_CHECKSIG"], s2, 0)])
invalid.append(("double_spend",) + make_invalid("double_spend", [coinbase(3, subsidy_at(3) + 2, P2PK), s1, s2]))

# inflation: output > input
inf = Tx(1, [TxIn(SPENDABLE_TXID, 0, b"", 0xFFFFFFFF)], [TxOut(SPENDABLE_VAL * 5, b"\x51")], 0)
inf.vin[0].script = cscript.assemble([sign(priv, [pub, "OP_CHECKSIG"], inf, 0)])
invalid.append(("inflation",) + make_invalid("inflation", [coinbase(3, subsidy_at(3), P2PK), inf]))

# immature: spend a coinbase created in the same block (gap 0 < maturity 1)
cb_im = coinbase(3, subsidy_at(3), P2PK)
im = Tx(1, [TxIn(txid(cb_im), 0, b"", 0xFFFFFFFF)], [TxOut(subsidy_at(3) - 1, b"\x51")], 0)
im.vin[0].script = cscript.assemble([sign(priv, [pub, "OP_CHECKSIG"], im, 0)])
invalid.append(("immature",) + make_invalid("immature", [cb_im, im]))

# bad signature: spend signed by the wrong key
bad = Tx(1, [TxIn(SPENDABLE_TXID, 0, b"", 0xFFFFFFFF)], [TxOut(SPENDABLE_VAL - 1, b"\x51")], 0)
bad.vin[0].script = cscript.assemble([sign(wrong_priv, [pub, "OP_CHECKSIG"], bad, 0)])
invalid.append(("bad_sig",) + make_invalid("bad_sig", [coinbase(3, subsidy_at(3), P2PK), bad]))

# ---- emit Rust ----
out = ['// generated by gen_state_vectors.py from the verified Python ChainState — do not edit', '']
out.append(f'pub const MATURITY: i64 = {MAT};')
out.append('pub const STRICT: bool = false;   // jan09x coinbase rule is <=')
out.append('')
out.append('// (raw_hex, height, subsidy, is_genesis, utxo_count, balance)')
out.append('pub const VALID: &[(&str, i64, i64, bool, usize, i64)] = &[')
for raw, h, sub, gen, uc, bal in valid:
    out.append(f'    ("{raw}", {h}, {sub}, {"true" if gen else "false"}, {uc}, {bal}),')
out.append('];')
out.append('')
out.append('// (name, raw_hex, height, subsidy, expected_err)')
out.append('pub const INVALID: &[(&str, &str, i64, i64, &str)] = &[')
for name, raw, h, sub, err in invalid:
    out.append(f'    ("{name}", "{raw}", {h}, {sub}, {err!r}),')
out.append('];')
out.append('')

dst = D / "validator-rs" / "tests" / "data" / "state_data.rs"
dst.write_text("\n".join(out).replace("'", '"'), encoding="utf-8")
print("wrote", dst)
for name, raw, h, sub, err in invalid:
    print(f"  invalid {name}: {err}")
print("valid blocks:", [(h, uc, bal) for (_r, h, _s, _g, uc, bal) in valid])
