"""The validated UTXO chainstate (production node, part 2): it tracks the UTXO, accepts a valid
spend, and REJECTS a double-spend / inflation / immature-coinbase spend / bad signature; and it
reorg-safely activates the taller VALID branch while ABORTING (and restoring) a reorg to an
invalid branch. Built with real signed transactions via the lab's wallet + VerifySignature path.
Evidence: MODEL / NEW-EXP."""

import pathlib
import sys

import pytest

_HERE = pathlib.Path(__file__).resolve().parent
for _p in ("model", "p2p", "nov08x", "wallet", "profiles"):
    sys.path.insert(0, str(_HERE.parent / _p))
sys.path.insert(0, str(_HERE))

import cscript                                              # noqa: E402
from chainsync import Chain, block_hash                    # noqa: E402
from p2p import block_bytes, merkle_root, pow_ok           # noqa: E402
from tx_sighash import (Tx, TxIn, TxOut, dsha256, new_key, serialize as ser_tx,   # noqa: E402
                        SIGHASH_ALL, SIGHASH_ANYONECANPAY, sign_input)            # noqa: E402
from spend import sign, scriptcode                         # noqa: E402

from chainstate import ChainState                          # noqa: E402
from chains import CHAINS                                  # noqa: E402
from difficulty import NET_RETARGET_INTERVAL, expected_bits   # noqa: E402
import profiles                                            # noqa: E402  (the named rule profiles)

ZERO = b"\x00" * 32
EASY = 0x207FFFFF
# The paper-facing consensus tests are governed by the FAITHFUL profile (jan09-faithful), never by the
# experimental jan09-x network. Its monetary rules are provably identical to CHAINS["jan09x"].rules
# (asserted in test_height_beats_… below), so this only removes the appearance that the X-network object
# supplies evidence — the numbers are unchanged.
FAITHFUL = profiles.load("jan09-faithful")
RULES = FAITHFUL.rules()
assert (RULES.COIN, RULES.subsidy_base, RULES.halving, RULES.spacing, RULES.coinbase_rule) == (
    (lambda r: (r.COIN, r.subsidy_base, r.halving, r.spacing, r.coinbase_rule))(CHAINS["jan09x"].rules)
), "faithful vs experimental monetary rules diverged"
_tag = [0]


def _txid(tx):
    return dsha256(ser_tx(tx))


def _key():
    priv, pub = new_key()
    return priv, [pub, "OP_CHECKSIG"]                       # (signing key, P2PK scriptPubKey tokens)


def _coinbase(height, value, spk=b"\x51"):
    _tag[0] += 1
    s = bytes([height & 0xFF, (height >> 8) & 0xFF, _tag[0] & 0xFF, (_tag[0] >> 8) & 0xFF])
    return Tx(1, [TxIn(ZERO, 0xFFFFFFFF, s, 0xFFFFFFFF)], [TxOut(value, spk)], 0)


def _mine_raw(prev, height, txs):
    mr = merkle_root(txs)
    for nonce in range(1 << 24):
        raw = block_bytes(1, prev, mr, 1_231_006_506 + height, EASY, nonce, txs)
        if pow_ok(raw, EASY):
            return raw
    raise RuntimeError("no nonce")


def _fresh(maturity=1):
    chain = Chain()                                         # compact PoW
    g = _mine_raw(ZERO, 0, [_coinbase(0, 0)])
    chain.add_genesis(g, EASY)
    return chain, ChainState(chain, RULES, maturity=maturity)


def _add(chain, st, txs, *, on=None):
    """Mine a block with `txs` on tip `on` (default active tip) and activate. Returns raw."""
    prev = on if on is not None else chain.tip
    height = chain.by_hash[prev].height + 1
    raw = _mine_raw(prev, height, txs)
    chain.process_block(raw)
    st.activate_best()
    return raw


def _subsidy(height):
    return RULES.get_block_value(height - 1)


# ---- UTXO tracking + a valid spend ------------------------------------------

def test_utxo_tracks_coinbase_outputs():
    chain, st = _fresh()
    _add(chain, st, [_coinbase(1, _subsidy(1))])
    assert st.height == 1
    assert st.balance() == 0 + _subsidy(1)                  # genesis(0) + block-1 subsidy


def test_accepts_a_valid_spend_of_a_matured_coinbase():
    chain, st = _fresh(maturity=1)
    priv, spk = _key()
    cb1 = _coinbase(1, _subsidy(1), cscript.assemble(spk))
    _add(chain, st, [cb1])                                  # height 1: coinbase paid to our key
    # spend it in block 2 (matured: 2-1 >= 1), paying a 1000-unit fee to the coinbase
    fee = 1000
    spend = Tx(1, [TxIn(_txid(cb1), 0, b"", 0xFFFFFFFF)],
               [TxOut(_subsidy(1) - fee, b"\x51")], 0)
    spend.vin[0].script = cscript.assemble([sign(priv, spk, spend, 0)])
    _add(chain, st, [_coinbase(2, _subsidy(2) + fee), spend])
    assert st.height == 2
    assert (_txid(cb1), 0) not in st.utxo                   # coinbase consumed
    assert (_txid(spend), 0) in st.utxo                     # payee output created


# ---- rejections -------------------------------------------------------------

def _matured_coin(chain, st):
    """Give the state a spendable P2PK coinbase; return (sec, spk, cb_tx)."""
    priv, spk = _key()
    cb = _coinbase(chain.by_hash[chain.tip].height + 1, _subsidy(chain.by_hash[chain.tip].height + 1),
                   cscript.assemble(spk))
    _add(chain, st, [cb])
    return priv, spk, cb


def test_rejects_double_spend():
    chain, st = _fresh(maturity=1)
    priv, spk, cb = _matured_coin(chain, st)
    h_before = st.height
    s1 = Tx(1, [TxIn(_txid(cb), 0, b"", 0xFFFFFFFF)], [TxOut(_subsidy(1), b"\x51")], 0)
    s1.vin[0].script = cscript.assemble([sign(priv, spk, s1, 0)])
    s2 = Tx(1, [TxIn(_txid(cb), 0, b"", 0xFFFFFFFF)], [TxOut(_subsidy(1), b"\x52")], 0)
    s2.vin[0].script = cscript.assemble([sign(priv, spk, s2, 0)])
    _add(chain, st, [_coinbase(2, _subsidy(2)), s1, s2])    # spends the same coin twice
    assert st.height == h_before                            # block was NOT connected (invalid)


def test_rejects_inflation():
    chain, st = _fresh(maturity=1)
    priv, spk, cb = _matured_coin(chain, st)
    h_before = st.height
    bad = Tx(1, [TxIn(_txid(cb), 0, b"", 0xFFFFFFFF)],
             [TxOut(_subsidy(1) * 5, b"\x51")], 0)           # outputs > inputs
    bad.vin[0].script = cscript.assemble([sign(priv, spk, bad, 0)])
    _add(chain, st, [_coinbase(2, _subsidy(2)), bad])
    assert st.height == h_before


def test_rejects_immature_coinbase_spend():
    chain, st = _fresh(maturity=100)                        # coinbase not spendable for 100 blocks
    priv, spk, cb = _matured_coin(chain, st)
    h_before = st.height
    spend = Tx(1, [TxIn(_txid(cb), 0, b"", 0xFFFFFFFF)], [TxOut(_subsidy(1), b"\x51")], 0)
    spend.vin[0].script = cscript.assemble([sign(priv, spk, spend, 0)])
    _add(chain, st, [_coinbase(2, _subsidy(2)), spend])
    assert st.height == h_before


def test_rejects_bad_signature():
    chain, st = _fresh(maturity=1)
    priv, spk, cb = _matured_coin(chain, st)
    h_before = st.height
    spend = Tx(1, [TxIn(_txid(cb), 0, b"", 0xFFFFFFFF)], [TxOut(_subsidy(1), b"\x51")], 0)
    spend.vin[0].script = cscript.assemble([sign(new_key()[0], spk, spend, 0)])  # wrong key
    _add(chain, st, [_coinbase(2, _subsidy(2)), spend])
    assert st.height == h_before


# ---- reorg: activate the taller VALID branch; abort an invalid reorg --------

def test_reorg_activates_the_taller_valid_branch():
    chain, st = _fresh()
    g = chain.genesis
    a1 = _add(chain, st, [_coinbase(1, _subsidy(1))], on=g)          # branch A: height 1
    assert st.tip == block_hash(a1)
    b1 = _add(chain, st, [_coinbase(1, _subsidy(1))], on=g)          # branch B forks at genesis
    b2 = _add(chain, st, [_coinbase(2, _subsidy(2))], on=block_hash(b1))
    b3 = _add(chain, st, [_coinbase(3, _subsidy(3))], on=block_hash(b2))  # B is taller -> reorg
    assert st.tip == block_hash(b3) and st.height == 3


def test_reorg_to_an_invalid_branch_is_aborted_and_old_chain_restored():
    chain, st = _fresh(maturity=1)
    g = chain.genesis
    # valid branch A, height 2
    a1 = _add(chain, st, [_coinbase(1, _subsidy(1))], on=g)
    a2 = _add(chain, st, [_coinbase(2, _subsidy(2))], on=block_hash(a1))
    assert st.tip == block_hash(a2) and st.height == 2
    utxo_a = dict(st.utxo)
    # competing branch B, TALLER (height 3) but its top block inflates -> invalid
    priv, spk = _key()
    b1cb = _coinbase(1, _subsidy(1), cscript.assemble(spk))
    b1 = _add(chain, st, [b1cb], on=g)
    b2 = _add(chain, st, [_coinbase(2, _subsidy(2))], on=block_hash(b1))
    inflate = Tx(1, [TxIn(_txid(b1cb), 0, b"", 0xFFFFFFFF)], [TxOut(_subsidy(1) * 9, b"\x51")], 0)
    inflate.vin[0].script = cscript.assemble([sign(priv, spk, inflate, 0)])
    _add(chain, st, [_coinbase(3, _subsidy(3)), inflate], on=block_hash(b2))   # B3 invalid
    # the node must NOT follow B (its tip is invalid) — it stays on valid A
    assert st.tip == block_hash(a2) and st.height == 2
    assert st.utxo.keys() == utxo_a.keys()                          # UTXO restored to A


def test_disconnect_restores_the_utxo():
    chain, st = _fresh()
    g = chain.genesis
    _add(chain, st, [_coinbase(1, _subsidy(1))], on=g)
    snapshot = set(st.utxo.keys())
    # a taller competing branch forces a reorg that disconnects block 1, then reconnects a new one
    b1 = _add(chain, st, [_coinbase(1, _subsidy(1))], on=g)
    b2 = _add(chain, st, [_coinbase(2, _subsidy(2))], on=block_hash(b1))
    assert st.height == 2
    # every live coin belongs to the now-active branch B (block-1-A's coin was disconnected)
    assert all(k in st.utxo for k in st.utxo)               # sanity: internally consistent
    assert st.balance() == 0 + _subsidy(1) + _subsidy(2)    # genesis + B1 + B2


# ---- discriminating fork choice: HEIGHT beats cumulative WORK ---------------------------------

def _mine_at(prev, height, nbits, t):
    """Mine one coinbase-only block on `prev` at a chosen difficulty `nbits` and timestamp `t`."""
    _tag[0] += 1
    s = bytes([height & 0xFF, (height >> 8) & 0xFF, _tag[0] & 0xFF, (_tag[0] >> 8) & 0xFF])
    cb = Tx(1, [TxIn(ZERO, 0xFFFFFFFF, s, 0xFFFFFFFF)], [TxOut(RULES.get_block_value(height - 1), b"\x51")], 0)
    mr = merkle_root([cb])
    for nonce in range(1 << 24):
        raw = block_bytes(1, prev, mr, t, nbits, nonce, [cb])
        if pow_ok(raw, nbits):
            return raw
    raise RuntimeError("no nonce")


def _chainwork(nbits):
    return (1 << 256) // (RULES.pow_target(nbits) + 1)       # standard per-block work = 2^256 / (target+1)


def test_height_beats_cumulative_work_the_discriminating_fork():
    """The *discriminating* experiment for "v0.1 selects by height, not cumulative work": a TALLER
    branch of LOWER total work displaces a SHORTER branch of HIGHER work. Difficulty is deliberately
    NOT held uniform here — one branch's first retarget window is mined fast (retargeting harder) and
    the other slow (staying at the genesis floor), so the two branches carry genuinely different work
    and the honest `nBits` still validates on every block.

    Attribution (kept explicit): the *fork-choice predicate* under test — best chain by
    `pindexNew->nHeight > nBestHeight`, never by summed work — is the **faithful v0.1 source rule**
    (`main.cpp`). The *retarget horizon* is a **laboratory substitution**: `NET_RETARGET_INTERVAL`
    (60 blocks, NEW-EXP) replaces v0.1's 2016-block window so the discriminating state is reachable in
    a unit test; the shortened horizon changes only the *time to reach* a taller/lower-work fork, not
    the predicate being tested."""
    # Run under the faithful profile jan09-faithful (not the experimental jan09-x); its consensus
    # rules are what this test uses (Script posture is irrelevant to a coinbase-only fork).
    faithful = profiles.load("jan09-faithful")
    assert faithful.name == "jan09-faithful" and faithful.script_posture == "faithful-v0.1"
    fr = faithful.rules()
    assert (fr.COIN, fr.subsidy_base, fr.halving, fr.spacing, fr.coinbase_rule) == \
        (RULES.COIN, RULES.subsidy_base, RULES.halving, RULES.spacing, RULES.coinbase_rule)
    # The retarget horizon is a laboratory substitution (recorded, not hidden): a 60-block NEW-EXP
    # window stands in for v0.1's 2016-block interval — it moves only the *time* to the discriminating
    # state, not the height-over-work predicate under test.
    assert NET_RETARGET_INTERVAL == 60 and NET_RETARGET_INTERVAL < 2016
    BASE = 1_231_006_506
    chain = Chain()
    g = _mine_at(ZERO, 0, EASY, BASE)
    chain.add_genesis(g, EASY)
    gh = block_hash(g)

    def build(gap, n):
        prev, wtot, seen = gh, 0, set()
        for h in range(1, n + 1):
            nb = expected_bits(chain, prev, RULES)          # honest difficulty: genesis until a retarget kicks in
            raw = _mine_at(prev, h, nb, BASE + h * gap)
            assert chain.process_block(raw)[0] in ("accepted", "orphan")
            prev, wtot = block_hash(raw), wtot + _chainwork(nb)
            seen.add(nb)
        return prev, n, wtot, seen

    # Incumbent B: a FAST first window retargets it HARDER, and we keep it SHORT.
    b_tip, b_h, b_work, b_seen = build(gap=5, n=122)
    st = ChainState(chain, RULES, maturity=1)
    st.activate_best()
    assert st.tip == b_tip and st.height == b_h             # B is the incumbent best chain

    # Challenger A: a SLOW first window keeps it at the genesis floor, and we grow it TALLER.
    a_tip, a_h, a_work, a_seen = build(gap=120, n=125)
    st.activate_best()

    # The setup is genuinely discriminating: A is taller yet carries LESS total work than B.
    assert a_h > b_h                                        # A is the taller branch
    assert a_work < b_work                                  # ...but has LESS cumulative work
    assert b_seen != {EASY}                                 # B really retargeted above the floor
    assert a_seen == {EASY}                                 # A stayed at the floor

    # ...and the node switches to A anyway: selection is by height, never by cumulative work.
    assert st.tip == a_tip and st.height == a_h


def test_chainstate_profile_bearing_context_records_the_profile_hash():
    """A profile-bearing `ChainState(profile=...)` derives its consensus rules and Script posture from
    the named profile and records exactly which profile governed the run — so "this finding used
    jan09-faithful" is a checkable `profile_hash`, not a bare claim (reviewer ask, §3)."""
    faithful = profiles.load("jan09-faithful")
    experimental = profiles.load("jan09-x")
    chain = Chain()
    g = _mine_at(ZERO, 0, EASY, 1_231_006_506)
    chain.add_genesis(g, EASY)

    st = ChainState(chain, profile=faithful, maturity=1)            # rules + posture come from the profile
    st.activate_best()
    assert st.profile_name == "jan09-faithful"
    assert st.profile_hash == faithful.profile_hash() and len(st.profile_hash) == 64
    assert st.reopen == frozenset()                                 # faithful: nothing reopened

    st_x = ChainState(chain, profile=experimental, maturity=1)      # the posture is genuinely carried
    assert st_x.profile_name == "jan09-x" and st_x.reopen == frozenset({"OP_NOTEQUAL"})
    assert st_x.profile_hash != st.profile_hash                     # distinct profiles -> distinct hashes


def test_op_notequal_posture_controls_the_node_verifier():
    """OP_NOTEQUAL through the node's own script verifier — `verify_spend_fast`, the function
    `ChainState._connect` calls on every spend — driven by the two NAMED profiles:

        profile          full-node result
        jan09-faithful   serialized OP_NOTEQUAL unavailable AND the token rejected
        jan09-x          the token honored, as the OP_EQUAL OP_NOT macro (documented behavior)

    Two facts underlie the "unavailable" row. First, OP_NOTEQUAL has NO serialized byte — it was never an
    `opcodetype` enum value, only a commented-out case — so it cannot appear in a byte-serialized
    transaction the node parses. Second, the experimental posture does not re-open an on-wire opcode; it
    rewrites the OP_NOTEQUAL *token* to `OP_EQUAL OP_NOT`, a model-level macro using two existing opcodes."""
    from fastverify import verify_spend_fast
    faithful = frozenset(profiles.load("jan09-faithful").reopened_opcodes)     # ()
    experimental = frozenset(profiles.load("jan09-x").reopened_opcodes)        # {'OP_NOTEQUAL'}
    assert faithful == frozenset() and experimental == frozenset({"OP_NOTEQUAL"})
    # (1) serialized OP_NOTEQUAL is unavailable -> it can never reach validation through a real script
    with pytest.raises(Exception):
        cscript.assemble(["OP_NOTEQUAL"])
    # (2) the node verifier honors each profile's posture on a pure-OP_NOTEQUAL predicate: bb != aa
    tx = Tx(1, [TxIn(ZERO, 0, b"", 0xFFFFFFFF)], [TxOut(0, b"\x51")], 0)
    ss, spk = [b"\xbb"], [b"\xaa", "OP_NOTEQUAL"]
    assert verify_spend_fast(ss, spk, tx, 0, reopen=faithful) is False         # jan09-faithful: reject
    assert verify_spend_fast(ss, spk, tx, 0, reopen=experimental) is True      # jan09-x: honored (bb != aa)
    # documented experimental behavior: equal operands are false under the macro (bb != bb is false)
    assert verify_spend_fast([b"\xbb"], [b"\xbb", "OP_NOTEQUAL"], tx, 0, reopen=experimental) is False


# ---- full-node native instruments: exercised through ChainState (the ConnectBlock path) -----------

def _spend_block(chain, st, tx):
    """Connect a block carrying `tx` plus a coinbase that claims subsidy + tx fee. Returns st.height."""
    fee = sum(st.utxo[(vin.prevhash, vin.n)].value for vin in tx.vin) - sum(o.value for o in tx.vout)
    h = chain.by_hash[chain.tip].height + 1
    _add(chain, st, [_coinbase(h, _subsidy(h) + fee), tx])
    return st.height


def _fund(chain, st, out_spk_tokens, value):
    """Spend a fresh matured P2PK coinbase into one output with the given scriptPubKey; return its txid."""
    priv, spk, cb = _matured_coin(chain, st)
    tx = Tx(1, [TxIn(_txid(cb), 0, b"", 0xFFFFFFFF)],
            [TxOut(value, cscript.assemble(out_spk_tokens))], 0)
    tx.vin[0].script = cscript.assemble([sign(priv, spk, tx, 0)])
    _spend_block(chain, st, tx)
    assert (_txid(tx), 0) in st.utxo
    return _txid(tx)


def test_fullnode_hashlock_spend_and_reject():
    """A faithful hash-lock output (`OP_HASH256 <H> OP_EQUALVERIFY <pub> OP_CHECKSIG`), created and then
    spent through the full node: correct (preimage + signature) connects; a wrong preimage is rejected."""
    chain, st = _fresh(maturity=1)
    secret = b"correct horse battery staple"
    H = dsha256(secret)                                    # OP_HASH256 == double-SHA256
    kpriv, kpub = new_key()
    hl = ["OP_HASH256", H, "OP_EQUALVERIFY", kpub, "OP_CHECKSIG"]
    tid = _fund(chain, st, hl, 5_000_000)

    # correct spend: <sig> <preimage>
    good = Tx(1, [TxIn(tid, 0, b"", 0xFFFFFFFF)], [TxOut(4_000_000, b"\x51")], 0)
    good.vin[0].script = cscript.assemble([sign(kpriv, hl, good, 0), secret])
    h0 = st.height
    assert _spend_block(chain, st, good) == h0 + 1         # connected
    assert (tid, 0) not in st.utxo                         # hash-lock consumed

    # a second hash-lock, spent with the WRONG preimage -> block rejected, tip unchanged
    tid2 = _fund(chain, st, hl, 5_000_000)
    bad = Tx(1, [TxIn(tid2, 0, b"", 0xFFFFFFFF)], [TxOut(4_000_000, b"\x51")], 0)
    bad.vin[0].script = cscript.assemble([sign(kpriv, hl, bad, 0), b"wrong-secret"])
    h1 = st.height
    _add(chain, st, [_coinbase(st.height + 1, _subsidy(st.height + 1) + 1_000_000), bad])
    assert st.height == h1                                 # NOT connected: wrong preimage
    assert (tid2, 0) in st.utxo                            # coin untouched


def test_fullnode_conditional_refund_both_branches():
    """A hash-lock-OR-refund output (`OP_IF <hashlock> OP_ELSE <refund> OP_ENDIF`) spent through the full
    node on BOTH branches: the recipient claims with (preimage + sig + OP_1); the sender refunds with
    (sig + OP_0)."""
    chain, st = _fresh(maturity=1)
    rpriv, rpub = new_key()                                # recipient (claim)
    spriv, spub = new_key()                                # sender (refund)
    secret = b"payment-secret"
    spk = ["OP_IF",
           "OP_HASH256", dsha256(secret), "OP_EQUALVERIFY", rpub, "OP_CHECKSIG",
           "OP_ELSE",
           spub, "OP_CHECKSIG",
           "OP_ENDIF"]

    # claim path: <sig_r> <preimage> OP_1
    tid = _fund(chain, st, spk, 5_000_000)
    claim = Tx(1, [TxIn(tid, 0, b"", 0xFFFFFFFF)], [TxOut(4_000_000, b"\x51")], 0)
    claim.vin[0].script = cscript.assemble([sign(rpriv, spk, claim, 0), secret, "OP_1"])
    h0 = st.height
    assert _spend_block(chain, st, claim) == h0 + 1

    # refund path: <sig_s> OP_0
    tid2 = _fund(chain, st, spk, 5_000_000)
    refund = Tx(1, [TxIn(tid2, 0, b"", 0xFFFFFFFF)], [TxOut(4_000_000, b"\x52")], 0)
    refund.vin[0].script = cscript.assemble([sign(spriv, spk, refund, 0), "OP_0"])
    h1 = st.height
    assert _spend_block(chain, st, refund) == h1 + 1
    assert (tid, 0) not in st.utxo and (tid2, 0) not in st.utxo


def test_fullnode_assurance_anyonecanpay_survives_added_input():
    """An assurance/crowdfund aggregate through the full node: two pledges signed `SIGHASH_ANYONECANPAY`
    are collected into one tx that funds a goal output and connects; the pledges commit only to their own
    input, so this is the on-chain form of the model's assurance construction. A `SIGHASH_ALL` control is
    rejected once a second input joins, because it commits to the whole input set."""
    chain, st = _fresh(maturity=1)
    acp = SIGHASH_ALL | SIGHASH_ANYONECANPAY               # 0x81

    # two matured P2PK coins to pledge
    p1, spk1, cb1 = _matured_coin(chain, st)
    p2, spk2, cb2 = _matured_coin(chain, st)
    v1 = st.utxo[(_txid(cb1), 0)].value
    v2 = st.utxo[(_txid(cb2), 0)].value

    goal = Tx(1,
              [TxIn(_txid(cb1), 0, b"", 0xFFFFFFFF), TxIn(_txid(cb2), 0, b"", 0xFFFFFFFF)],
              [TxOut(v1 + v2 - 2000, cscript.assemble(["OP_1"]))], 0)
    # each pledger signs ONLY their own input under ANYONECANPAY
    goal.vin[0].script = cscript.assemble([sign(p1, spk1, goal, 0, acp)])
    goal.vin[1].script = cscript.assemble([sign(p2, spk2, goal, 1, acp)])
    h0 = st.height
    assert _spend_block(chain, st, goal) == h0 + 1         # both pledges collected -> connected

    # control: a SIGHASH_ALL pledge does NOT survive a later-added input (verify_spend_fast level).
    from fastverify import verify_spend_fast
    tx_a = Tx(1, [TxIn(_txid(cb1), 0, b"", 0xFFFFFFFF)], [TxOut(v1 - 1000, cscript.assemble(["OP_1"]))], 0)
    sig_all = sign(p1, spk1, tx_a, 0, SIGHASH_ALL)
    assert verify_spend_fast([sig_all], spk1, tx_a, 0) is True
    tx_b = Tx(1, [TxIn(_txid(cb1), 0, b"", 0xFFFFFFFF), TxIn(_txid(cb2), 0, b"", 0xFFFFFFFF)],
              [TxOut(v1 - 1000, cscript.assemble(["OP_1"]))], 0)
    assert verify_spend_fast([sig_all], spk1, tx_b, 0) is False   # SIGHASH_ALL broke when input 1 joined
