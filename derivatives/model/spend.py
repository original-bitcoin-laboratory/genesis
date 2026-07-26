"""Faithful 'spend' layer for the MODEL: build and validate a spend the way v0.1
VerifySignature does — EvalScript(scriptSig + OP_CODESEPARATOR + scriptPubKey)
(script.cpp:1126) — so scriptCode is the scriptPubKey, derived from bytes.

Scripts are token lists (bytes = data push, "OP_NAME" = opcode); cscript.assemble
turns them into real v0.1 bytes for sighash. Evidence level: MODEL.
"""

from __future__ import annotations

import cscript
from evalscript_model import run, valid
from tx_sighash import SIGHASH_ALL, SigChecker, sign_input


def scriptcode(script_pubkey_tokens: list) -> bytes:
    """The scriptPubKey as serialized bytes — what a signature commits to."""
    return cscript.assemble(script_pubkey_tokens)


def sign(priv, script_pubkey_tokens: list, tx, n_in: int, hash_type: int = SIGHASH_ALL) -> bytes:
    return sign_input(priv, tx, n_in, scriptcode(script_pubkey_tokens), hash_type)


def combined(script_sig_tokens: list, script_pubkey_tokens: list) -> list:
    """scriptSig + OP_CODESEPARATOR + scriptPubKey (as v0.1 VerifySignature runs)."""
    return list(script_sig_tokens) + ["OP_CODESEPARATOR"] + list(script_pubkey_tokens)


def verify_spend(script_sig_tokens: list, script_pubkey_tokens: list, tx, n_in: int) -> bool:
    """True iff the combined script runs and leaves a true top-of-stack."""
    return valid(combined(script_sig_tokens, script_pubkey_tokens), SigChecker(tx, n_in))


def run_spend(script_sig_tokens: list, script_pubkey_tokens: list, tx, n_in: int):
    return run(combined(script_sig_tokens, script_pubkey_tokens), SigChecker(tx, n_in))
