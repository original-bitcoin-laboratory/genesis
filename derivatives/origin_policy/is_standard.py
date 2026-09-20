"""IsStandard, executed as the policy it is -- MODEL.

Constitution row OBL-C-0011 (docs/CONSENSUS-ATLAS.md section 6): commit a206a2398 (7 December 2010,
gavinandresen, "IsStandard() check for CScripts: only relay/include in blocks CScripts we can
understand.") adds `bool IsStandard(const CScript&)` in script.cpp, `CTransaction::IsStandard()` in
main.h over every output, and in the memory-pool path of main.cpp:

    if (!IsStandard() || GetSigOpCount() > 2 || ::GetSerializeSize(*this, SER_NETWORK) < 100)

A transaction that fails it is not relayed or mined by a node applying the check. A block containing
one is valid: nothing in CheckBlock or ConnectBlock consults it.

What this module executes, side by side:

  * `is_standard_output`: the two templates Solver() carries in the January 2009 release
    (script.cpp:913), which a206a2398 reuses unchanged: `<pubkey> OP_CHECKSIG`, where the push is
    longer than 32 bytes, and `OP_DUP OP_HASH160 <20 bytes> OP_EQUALVERIFY OP_CHECKSIG`;
  * `sigop_count`: CScript::GetSigOpCount as f1e1fb4bd counts it (one per CHECKSIG/CHECKSIGVERIFY,
    twenty per CHECKMULTISIG/CHECKMULTISIGVERIFY), over every input script and output script;
  * `accept_to_memory_pool_v01`: the January client has no such clause: every transaction that passes
    CheckTransaction and its inputs is relayed;
  * `accept_to_memory_pool_20101207`: the three-part clause above.

The exhibit is a hash-lock output (`OP_SHA256 <32 bytes> OP_EQUAL`, one of the corpus's own
constructions): the January node relays it, the December 2010 node refuses it as nonstandard, and
CheckTransaction accepts it in both eras. Written 20 September 2026 after an adversarial review
observed that the row's witness (the release build executing non-template scripts) speaks to the
script engine, not to this policy. Evidence level: MODEL. NOT money.
"""
from __future__ import annotations

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "model"))
sys.path.insert(0, str(_HERE.parent / "overflow"))
from tx_sighash import Tx, TxIn, TxOut, serialize        # noqa: E402
from overflow import check_transaction_hardened, check_transaction_v01   # noqa: E402

OP_PUSHDATA1, OP_PUSHDATA2, OP_PUSHDATA4 = 0x4c, 0x4d, 0x4e
OP_DUP, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG = 0x76, 0xa9, 0x88, 0xac
OP_SHA256, OP_EQUAL = 0xa8, 0x87
OP_CHECKSIGVERIFY, OP_CHECKMULTISIG, OP_CHECKMULTISIGVERIFY = 0xad, 0xae, 0xaf

MIN_STANDARD_TX_BYTES = 100      # a206a2398: `GetSerializeSize(*this, SER_NETWORK) < 100` refused
MAX_STANDARD_SIGOPS = 2          # a206a2398: `GetSigOpCount() > 2` refused


def get_ops(script: bytes) -> list:
    """CScript::GetOp: (opcode, pushed bytes or None) for each element; raises on a truncated push."""
    out, i = [], 0
    while i < len(script):
        op = script[i]; i += 1
        if op <= 0x4b:
            n = op
        elif op == OP_PUSHDATA1:
            n = script[i]; i += 1
        elif op == OP_PUSHDATA2:
            n = int.from_bytes(script[i:i + 2], "little"); i += 2
        elif op == OP_PUSHDATA4:
            n = int.from_bytes(script[i:i + 4], "little"); i += 4
        else:
            out.append((op, None)); continue
        if i + n > len(script):
            raise ValueError("push runs past the script")
        out.append((op, script[i:i + n])); i += n
    return out


def is_standard_output(script_pubkey: bytes) -> bool:
    """Solver() over the two templates, as the January release carries them and a206a2398 applies them."""
    try:
        ops = get_ops(script_pubkey)
    except ValueError:
        return False
    # template 1: OP_PUBKEY OP_CHECKSIG -- a push of more than sizeof(uint256) = 32 bytes, then CHECKSIG
    if len(ops) == 2 and ops[0][1] is not None and len(ops[0][1]) > 32 and ops[1] == (OP_CHECKSIG, None):
        return True
    # template 2: OP_DUP OP_HASH160 OP_PUBKEYHASH OP_EQUALVERIFY OP_CHECKSIG -- the push exactly sizeof(uint160)
    if (len(ops) == 5 and ops[0] == (OP_DUP, None) and ops[1] == (OP_HASH160, None)
            and ops[2][1] is not None and len(ops[2][1]) == 20
            and ops[3] == (OP_EQUALVERIFY, None) and ops[4] == (OP_CHECKSIG, None)):
        return True
    return False


def script_sigop_count(script: bytes) -> int:
    """CScript::GetSigOpCount (f1e1fb4bd): 1 per CHECKSIG/CHECKSIGVERIFY, 20 per CHECKMULTISIG(VERIFY)."""
    n = 0
    try:
        ops = get_ops(script)
    except ValueError:
        return n
    for op, data in ops:
        if data is None and op in (OP_CHECKSIG, OP_CHECKSIGVERIFY):
            n += 1
        elif data is None and op in (OP_CHECKMULTISIG, OP_CHECKMULTISIGVERIFY):
            n += 20
    return n


def sigop_count(tx: Tx) -> int:
    """CTransaction::GetSigOpCount: every input's scriptSig plus every output's scriptPubKey."""
    return sum(script_sigop_count(i.script) for i in tx.vin) + sum(script_sigop_count(o.script) for o in tx.vout)


def is_standard_tx(tx: Tx) -> bool:
    """CTransaction::IsStandard() as a206a2398 adds it: every output passes Solver's templates."""
    return all(is_standard_output(o.script) for o in tx.vout)


def accept_to_memory_pool_v01(tx: Tx):
    """The January 2009 memory-pool path has no standardness clause: (ok, clause), where the only
    refusals are CheckTransaction's own (the inputs' checks are outside this module)."""
    ok, why = check_transaction_v01(tx)
    return (True, "ok") if ok else (False, why)


def accept_to_memory_pool_20101207(tx: Tx):
    """The same path with a206a2398's clause: (ok, clause)."""
    ok, why = check_transaction_hardened(tx)
    if not ok:
        return False, why
    if not is_standard_tx(tx) or sigop_count(tx) > MAX_STANDARD_SIGOPS or len(serialize(tx)) < MIN_STANDARD_TX_BYTES:
        return False, "nonstandard"
    return True, "ok"


def block_validity_unaffected(tx: Tx) -> tuple[bool, bool]:
    """What consensus says of the transaction in each era: CheckTransaction (January; the 2010 form),
    neither of which consults IsStandard. (january_ok, december_2010_ok)."""
    return check_transaction_v01(tx)[0], check_transaction_hardened(tx)[0]


# -- the exhibit ---------------------------------------------------------------------------------
PREV = b"\x22" * 32
SCRIPT_SIG = b"\x14" + b"\x07" * 20             # one 20-byte push: keeps the transaction over 100 bytes
PUBKEY = b"\x04" + b"\x33" * 64                 # a 65-byte uncompressed key shape


def p2pk_tx() -> Tx:
    return Tx(1, [TxIn(PREV, 0, SCRIPT_SIG)], [TxOut(50 * 100_000_000, b"\x41" + PUBKEY + bytes([OP_CHECKSIG]))], 0)


def hashlock_tx() -> Tx:
    """`OP_SHA256 <32 bytes> OP_EQUAL`: a valid v0.1 script that matches neither template."""
    return Tx(1, [TxIn(PREV, 0, SCRIPT_SIG)], [TxOut(50 * 100_000_000, bytes([OP_SHA256, 0x20]) + b"\x5a" * 32 + bytes([OP_EQUAL]))], 0)


def report() -> None:
    print("ISSTANDARD -- the January node against the 7 December 2010 node (MODEL)")
    for label, tx in (("pay-to-pubkey (template 1)", p2pk_tx()), ("hash-lock OP_SHA256 <h> OP_EQUAL", hashlock_tx())):
        jan, dec = accept_to_memory_pool_v01(tx), accept_to_memory_pool_20101207(tx)
        cj, cd = block_validity_unaffected(tx)
        print(f"  {label}")
        print(f"    relay/mine, January 2009 : {jan}")
        print(f"    relay/mine, a206a2398    : {dec}")
        print(f"    CheckTransaction (consensus) January {cj}, 2010 form {cd}   <- a block carrying it is valid under both")
    print("  => the December 2010 clause changes what a node relays and mines, not what a block may contain. NOT money.")


if __name__ == "__main__":
    report()
