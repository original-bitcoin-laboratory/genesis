"""MODEL of the Bitcoin v0.1 wallet (derivative) — key store, coin selection, and
CreateTransaction, built on the lab's MODEL (real secp256k1 signatures via
`../model`). Anchored to main.cpp / script.cpp of the v0.1.0 release:

- key store `mapKeys` (pubkey -> privkey) + `mapPubKeys` (hash160 -> pubkey)
  (main.h:1314); `IsMine` / `ExtractPubKey` via the two Solver templates
  (script.cpp:913-1067): bare `OP_PUBKEY OP_CHECKSIG` and
  `OP_DUP OP_HASH160 OP_PUBKEYHASH OP_EQUALVERIFY OP_CHECKSIG`.
- `GetBalance` sums unspent mine credits (main.cpp:2386); `SelectCoins` is the
  exact / lowest-larger / stochastic subset-sum picker (main.cpp:2410).
- `CreateTransaction` (main.cpp:2514): vout[0] pays the payee, vout[1] returns the
  change to self as a **bare P2PK** (`scriptPubKey << vchPubKey << OP_CHECKSIG`,
  main.cpp:2559), vin covers every mine output of the chosen coins, and each input
  is signed by `SignSignature` (script.cpp:1090): hash = SignatureHash(scriptPubKey,
  txTo, nIn, SIGHASH_ALL), Solver builds the scriptSig, then it is checked by
  EvalScript before returning.

Evidence level: MODEL. Signatures are real ECDSA on secp256k1; every input is
independently re-verified by the lab's EvalScript (the v0.1 VerifySignature path).
"""

from __future__ import annotations

import hashlib
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "model"))
from cscript import assemble                                   # noqa: E402
from spend import sign, verify_spend                           # noqa: E402
from tx_sighash import SIGHASH_ALL, Tx, TxIn, TxOut, new_key   # noqa: E402

COIN = 100_000_000


def hash160(b: bytes) -> bytes:
    return hashlib.new("ripemd160", hashlib.sha256(b).digest()).digest()


# ---- script templates (the two v0.1 Solver templates) ------------------------

def p2pk(sec: bytes) -> list:
    return [bytes(sec), "OP_CHECKSIG"]


def p2pkh(sec: bytes) -> list:
    return ["OP_DUP", "OP_HASH160", hash160(sec), "OP_EQUALVERIFY", "OP_CHECKSIG"]


def _is_p2pk(spk) -> bool:
    return (len(spk) == 2 and isinstance(spk[0], (bytes, bytearray)) and spk[1] == "OP_CHECKSIG")


def _is_p2pkh(spk) -> bool:
    return (len(spk) == 5 and spk[0] == "OP_DUP" and spk[1] == "OP_HASH160"
            and isinstance(spk[2], (bytes, bytearray)) and spk[3] == "OP_EQUALVERIFY"
            and spk[4] == "OP_CHECKSIG")


class Coin:
    __slots__ = ("txid", "n", "value", "spk", "spent")

    def __init__(self, txid: bytes, n: int, value: int, spk: list):
        self.txid = txid; self.n = n; self.value = value; self.spk = spk; self.spent = False


class Wallet:
    """Faithful v0.1 wallet: key store + coin selection + CreateTransaction."""

    def __init__(self, rng: random.Random | None = None):
        self.map_keys: dict[bytes, object] = {}       # pubkey(SEC) -> privkey
        self.map_pubkeys: dict[bytes, bytes] = {}     # hash160 -> pubkey
        self.coins: list[Coin] = []
        self.rng = rng or random.Random()

    # -- key management --------------------------------------------------------
    def new_key(self) -> bytes:
        priv, sec = new_key()
        self.map_keys[sec] = priv
        self.map_pubkeys[hash160(sec)] = sec
        return sec

    # -- IsMine / ExtractPubKey (Solver, script.cpp) ---------------------------
    def is_mine(self, spk) -> bool:
        if _is_p2pk(spk):
            return bytes(spk[0]) in self.map_keys
        if _is_p2pkh(spk):
            pub = self.map_pubkeys.get(bytes(spk[2]))
            return pub is not None and pub in self.map_keys
        return False

    def extract_pubkey(self, spk):
        if _is_p2pk(spk):
            return bytes(spk[0])
        if _is_p2pkh(spk):
            return self.map_pubkeys.get(bytes(spk[2]))
        return None

    # -- learn of a received output (AddToWalletIfMine) ------------------------
    def add_coin(self, txid: bytes, n: int, value: int, spk: list) -> bool:
        if not self.is_mine(spk):
            return False
        self.coins.append(Coin(txid, n, value, spk))
        return True

    def unspent(self):
        return [c for c in self.coins if not c.spent]

    def get_balance(self) -> int:
        return sum(c.value for c in self.unspent())

    # -- SelectCoins (main.cpp:2410) ------------------------------------------
    def select_coins(self, target: int):
        lowest_larger = None
        lowest_larger_val = None
        vvalue = []
        total_lower = 0
        for c in self.unspent():
            n = c.value
            if n <= 0:
                continue
            if n < target:
                vvalue.append(c); total_lower += n
            elif n == target:
                return [c]
            elif lowest_larger_val is None or n < lowest_larger_val:
                lowest_larger_val = n; lowest_larger = c

        if total_lower < target:
            return [lowest_larger] if lowest_larger is not None else None

        # subset-sum by stochastic approximation (1000 reps, two passes)
        vvalue.sort(key=lambda c: c.value, reverse=True)
        best = [True] * len(vvalue)
        nbest = total_lower
        for _ in range(1000):
            if nbest == target:
                break
            incl = [False] * len(vvalue)
            ntotal = 0
            reached = False
            for npass in range(2):
                if reached:
                    break
                for i, c in enumerate(vvalue):
                    take = (self.rng.random() < 0.5) if npass == 0 else (not incl[i])
                    if take:
                        ntotal += c.value; incl[i] = True
                        if ntotal >= target:
                            reached = True
                            if ntotal < nbest:
                                nbest = ntotal; best = incl[:]
                            ntotal -= c.value; incl[i] = False

        if lowest_larger is not None and lowest_larger_val - target <= nbest - target:
            return [lowest_larger]
        return [vvalue[i] for i in range(len(vvalue)) if best[i]]

    # -- SignSignature (script.cpp:1090) --------------------------------------
    def sign_signature(self, coin: Coin, txto: Tx, n_in: int, hashtype: int = SIGHASH_ALL) -> bool:
        spk = coin.spk
        if _is_p2pk(spk):
            priv = self.map_keys[bytes(spk[0])]
            script_sig = [sign(priv, spk, txto, n_in, hashtype)]
        elif _is_p2pkh(spk):
            pub = self.map_pubkeys[bytes(spk[2])]
            priv = self.map_keys[pub]
            script_sig = [sign(priv, spk, txto, n_in, hashtype), pub]
        else:
            return False
        txto.vin[n_in].script = assemble(script_sig)
        # "Test solution": SignSignature re-runs EvalScript before accepting
        return verify_spend(script_sig, spk, txto, n_in)

    # -- CreateTransaction (main.cpp:2514) ------------------------------------
    def create_transaction(self, recipient_spk: list, value: int, fee: int = 0):
        """Returns (tx, coins_used, change) or raises if it cannot fund `value`.
        Mirrors CreateTransaction: payee vout[0], change-to-self vout[1] (bare
        P2PK), vin over the chosen coins, each input signed by SignSignature."""
        if value < 0:
            raise ValueError("negative value")
        target = value + fee
        coins = self.select_coins(target)
        if not coins:
            raise ValueError("insufficient funds")
        value_in = sum(c.value for c in coins)

        vout = [TxOut(value, assemble(recipient_spk))]
        change = value_in - target
        change_spk = None
        if change > 0:
            # change goes back to a key of the first selected coin (main.cpp:2547)
            pub = self.extract_pubkey(coins[0].spk)
            if pub is None:
                raise ValueError("no change key")
            change_spk = p2pk(pub)                      # scriptPubKey << vchPubKey << OP_CHECKSIG
            vout.append(TxOut(change, assemble(change_spk)))

        vin = [TxIn(c.txid, c.n, b"", 0xFFFFFFFF) for c in coins]
        tx = Tx(1, vin, vout, 0)
        for i, c in enumerate(coins):
            if not self.sign_signature(c, tx, i):
                raise ValueError(f"signing input {i} failed")
        return tx, coins, (change, change_spk)

    # -- CommitTransactionSpent (main.cpp:2595) -------------------------------
    def mark_spent(self, coins):
        for c in coins:
            c.spent = True


# ---- independent verification of a created transaction ------------------------

def verify_transaction(wallet: Wallet, tx: Tx, coins_used) -> bool:
    """The v0.1 acceptance checks we can enforce headlessly, independent of the
    wallet that built the tx: every input's VerifySignature (EvalScript over
    scriptSig + OP_CODESEPARATOR + scriptPubKey) passes, and value is conserved
    (sum inputs >= sum outputs — ConnectInputs' no-inflation rule)."""
    for i, c in enumerate(coins_used):
        # reconstruct scriptSig tokens is unnecessary — verify from the coin's spk:
        script_sig_bytes = tx.vin[i].script
        if not _verify_input(script_sig_bytes, c.spk, tx, i):
            return False
    value_in = sum(c.value for c in coins_used)
    value_out = sum(o.value for o in tx.vout)
    return value_in >= value_out


def _verify_input(script_sig_bytes: bytes, spk_tokens: list, tx: Tx, n_in: int) -> bool:
    # rebuild the scriptSig token list from the signed bytes so we can run the
    # exact VerifySignature path (EvalScript(scriptSig + OP_CODESEPARATOR + spk)).
    from cscript import parse
    ss_tokens = parse(script_sig_bytes)
    return verify_spend(ss_tokens, spk_tokens, tx, n_in)
