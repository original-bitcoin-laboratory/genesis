"""Regenerate the Rust reorg + difficulty golden vectors from the verified Python ChainState.

    python validator-rs/tools/gen_reorg_vectors.py

Writes validator-rs/tests/data/reorg_data.rs: three reorg scenarios (valid reorg to a taller branch;
abort + restore when a taller branch is invalid; a forged-difficulty block rejected) recorded from
the Python chainsync.Chain + chainstate.ChainState, plus difficulty retarget/round-trip math. NOT money.
"""
import pathlib
import sys

D = pathlib.Path(__file__).resolve().parents[2]
for p in ("model", "p2p", "nov08x", "netnode"):
    sys.path.insert(0, str(D / p))

from chainsync import Chain, block_hash
from p2p import block_bytes, merkle_root, pow_ok
from tx_sighash import Tx, TxIn, TxOut
from chainstate import ChainState
from chains import CHAINS
from difficulty import _retarget, target_to_compact

RULES = CHAINS["jan09x"].rules
EASY = 0x207FFFFF
BASE = 1_231_006_506
ZERO = b"\x00" * 32
_tag = [0]


def sub(h):
    return RULES.get_block_value(h - 1)


def mine(prev, height, value, nbits=EASY):
    _tag[0] += 1
    s = bytes([height & 0xFF, (height >> 8) & 0xFF, _tag[0] & 0xFF, (_tag[0] >> 8) & 0xFF])
    cb = Tx(1, [TxIn(ZERO, 0xFFFFFFFF, s, 0xFFFFFFFF)], [TxOut(value, b"\x51")], 0)
    mr = merkle_root([cb])
    t = BASE + height * 30
    for nonce in range(1 << 24):
        raw = block_bytes(1, prev, mr, t, nbits, nonce, [cb])
        if pow_ok(raw, nbits):
            return raw
    raise RuntimeError("no nonce")


def run_scenario(steps):
    """steps: list of (label, raw). Returns rows recorded after each activate_best."""
    chain = Chain()
    g = steps[0][1]
    chain.add_genesis(g, EASY)
    st = ChainState(chain, RULES, maturity=1)
    rows = [("genesis", g.hex(), st.tip.hex(), st.height, len(st.utxo), st.balance(), False)]
    for label, raw in steps[1:]:
        chain.process_block(raw)
        st.activate_best()
        inv = block_hash(raw) in st.invalid
        rows.append((label, raw.hex(), st.tip.hex(), st.height, len(st.utxo), st.balance(), inv))
    return rows


# ---- scenario A: valid reorg to a taller branch ----
g = mine(ZERO, 0, 0)
gh = block_hash(g)
a1 = mine(gh, 1, sub(1))
b1 = mine(gh, 1, sub(1))
b2 = mine(block_hash(b1), 2, sub(2))
b3 = mine(block_hash(b2), 3, sub(3))
A = run_scenario([("genesis", g), ("A1", a1), ("B1_side", b1), ("B2_reorg", b2), ("B3", b3)])

# ---- scenario B: a taller branch whose top over-claims -> abort + restore ----
g = mine(ZERO, 0, 0)
gh = block_hash(g)
a1 = mine(gh, 1, sub(1))
a2 = mine(block_hash(a1), 2, sub(2))
b1 = mine(gh, 1, sub(1))
b2 = mine(block_hash(b1), 2, sub(2))
b3bad = mine(block_hash(b2), 3, sub(3) * 99)  # over-claims the coinbase
B = run_scenario([("genesis", g), ("A1", a1), ("A2", a2), ("B1_side", b1),
                  ("B2_side", b2), ("B3_invalid_taller", b3bad)])

# ---- scenario C: a forged-difficulty block is rejected ----
g = mine(ZERO, 0, 0)
gh = block_hash(g)
a1 = mine(gh, 1, sub(1))
a2 = mine(block_hash(a1), 2, sub(2))
f = mine(block_hash(a2), 3, sub(3), nbits=0x207FFFFE)  # nBits != expected -> wrong difficulty
C = run_scenario([("genesis", g), ("A1", a1), ("A2", a2), ("F_forged_difficulty", f)])

# ---- scenario D: a mutated body under an honest header is erased, and the honest block accepted ----
# [cb, A, B] and [cb, A, B, B] share a Merkle root (v0.1 BuildMerkleTree duplicates the odd last hash),
# so they share a header hash. The mutated body spends B's input twice and fails ConnectBlock; v0.1
# erases it from mapBlockIndex (main.cpp:1104-1112), so the honest block is accepted when it arrives.
def mine_txs(prev, height, txs, body=None):
    mr = merkle_root(txs)
    t = BASE + height * 30
    for nonce in range(1 << 24):
        raw = block_bytes(1, prev, mr, t, EASY, nonce, txs)
        if pow_ok(raw, EASY):
            return raw, block_bytes(1, prev, mr, t, EASY, nonce, body) if body else None
    raise RuntimeError("no nonce")


def coinbase_txid(raw):
    from fullnode import parse_block_with_txids       # the parser ChainState itself connects with
    return parse_block_with_txids(raw)[0][1]


g = mine(ZERO, 0, 0)
gh = block_hash(g)
a1 = mine(gh, 1, sub(1))
a2 = mine(block_hash(a1), 2, sub(2))
spend_a = Tx(1, [TxIn(coinbase_txid(a1), 0, b"", 0xFFFFFFFF)], [TxOut(1, b"\x51")], 0)
spend_b = Tx(1, [TxIn(coinbase_txid(a2), 0, b"", 0xFFFFFFFF)], [TxOut(1, b"\x51")], 0)
_tag[0] += 1
cb3 = Tx(1, [TxIn(ZERO, 0xFFFFFFFF, bytes([3, 0, _tag[0] & 0xFF, 0]), 0xFFFFFFFF)], [TxOut(sub(3), b"\x51")], 0)
honest, mutated = mine_txs(block_hash(a2), 3, [cb3, spend_a, spend_b], [cb3, spend_a, spend_b, spend_b])
assert block_hash(honest) == block_hash(mutated) and honest != mutated
D_ = run_scenario([("genesis", g), ("A1", a1), ("A2", a2), ("D3_mutated_first", mutated),
                   ("D3_honest_after", honest)])

# ---- difficulty math (compact / jan09) ----
WIN = 60 * 30
retargets = [
    (EASY, WIN // 10, WIN, EASY),        # too fast -> harder
    (EASY, WIN * 10, WIN, EASY),         # too slow -> floored at genesis (stays)
    (EASY, WIN, WIN, EASY),              # on target
    (0x1D00FFFF, WIN * 10, WIN, EASY),   # harder start, slow -> eases toward the floor
    (0x1D00FFFF, WIN // 10, WIN, EASY),  # harder start, fast -> harder still
]
retarget_rows = [(lb, ac, ex, fl, _retarget(lb, ac, ex, RULES, fl)) for (lb, ac, ex, fl) in retargets]
roundtrip = [nb for nb in (EASY, 0x1D00FFFF, 0x1C0FFFFF, 0x1B0404CB) if target_to_compact(RULES.pow_target(nb)) == nb]


def emit_rows(name, rows):
    out = [f"pub const {name}: &[(&str, &str, &str, i64, usize, i64, bool)] = &["]
    for label, raw, tip, h, uc, bal, inv in rows:
        out.append(f'    ("{label}", "{raw}", "{tip}", {h}, {uc}, {bal}, {"true" if inv else "false"}),')
    out.append("];")
    return out


lines = ["// generated by gen_reorg_vectors.py from the verified Python ChainState — do not edit", ""]
lines += ["// (label, block_hex, expected_tip_hex, height, utxo_count, balance, this_block_invalid)"]
lines += emit_rows("REORG_A", A) + [""]
lines += emit_rows("REORG_B", B) + [""]
lines += emit_rows("REORG_C", C) + [""]
lines += emit_rows("REORG_D", D_) + [""]
lines += ["// (last_bits, actual, expected, floor_bits, result)"]
lines += ["pub const RETARGET: &[(u32, i64, i64, u32, u32)] = &["]
lines += [f"    (0x{lb:08x}, {ac}, {ex}, 0x{fl:08x}, 0x{r:08x})," for (lb, ac, ex, fl, r) in retarget_rows]
lines += ["];", ""]
lines += ["pub const TARGET_ROUNDTRIP: &[u32] = &[" + ", ".join(f"0x{nb:08x}" for nb in roundtrip) + "];", ""]

dst = D / "validator-rs" / "tests" / "data" / "reorg_data.rs"
dst.write_bytes("\n".join(lines).encode("utf-8"))    # LF everywhere; write_text gives CRLF on Windows
print("wrote", dst)
for name, rows in (("A", A), ("B", B), ("C", C), ("D", D_)):
    print(f"  scenario {name}: " + " ".join(f"{r[0]}=h{r[3]}{'!' if r[6] else ''}" for r in rows))
print("  retargets:", [f"0x{r[4]:08x}" for r in retarget_rows])
print("  roundtrip nbits:", [f"0x{nb:08x}" for nb in roundtrip])
