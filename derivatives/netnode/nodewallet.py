"""An experimental on-disk wallet for an X-chain node — Path B usability layer. NOT money.

Sending a payment shouldn't require writing Python. This wraps the lab's **faithful v0.1 wallet
MODEL** ([`../wallet/wallet.py`](../wallet/wallet.py): `IsMine` / `SelectCoins` / `CreateTransaction`
/ `SignSignature`) with the three things a *node* wallet needs:

- a **persistent key store** (`<datadir>/wallet.json`) so keys survive restarts,
- **coin discovery from the node's *validated* UTXO** — only outputs the wallet owns *and* that are
  spendable (mature coinbases), rebuilt from the live UTXO each time so it is always reorg‑correct,
- a bare‑**P2PK receive script** so a mining node can pay its coinbase to itself and, after
  maturity, spend it.

An "address" here is simply a secp256k1 public key (SEC, hex) — payments are bare P2PK, exactly
what v0.1 pays its coinbase and change to. Keys are private scalars stored as hex: an **experimental
testnet wallet on a valueless chain**, not a secure store for anything of value. **NOT money.**
Evidence: MODEL / NEW‑EXP.

Named `nodewallet` (not `wallet`) so it does not shadow the MODEL `wallet` module on `sys.path`.
"""

from __future__ import annotations

import json
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
for _p in ("model", "p2p", "nov08x", "wallet"):
    sys.path.insert(0, str(_HERE.parent / _p))
sys.path.insert(0, str(_HERE))

import cscript                                              # noqa: E402
from tx_sighash import new_key, serialize as ser_tx        # noqa: E402
from wallet import Wallet as ModelWallet, hash160, p2pk    # the faithful MODEL wallet  # noqa: E402


def _priv_to_hex(priv) -> str:
    return priv.private_numbers().private_value.to_bytes(32, "big").hex()


def _priv_from_hex(h: str):
    from cryptography.hazmat.primitives.asymmetric import ec
    return ec.derive_private_key(int(h, 16), ec.SECP256K1())


class InsufficientFunds(Exception):
    pass


class NodeWallet:
    def __init__(self, path):
        self.path = pathlib.Path(path)
        self.keys: list[tuple[object, bytes]] = []          # (private key object, SEC pubkey bytes)
        self._load()
        if not self.keys:
            self.new_address()                              # a fresh wallet starts with one key

    # -- persistence -----------------------------------------------------------
    def _load(self):
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            for k in data.get("keys", []):
                self.keys.append((_priv_from_hex(k["priv"]), bytes.fromhex(k["pub"])))

    def _save(self):
        data = {"not_money": True,
                "keys": [{"priv": _priv_to_hex(p), "pub": s.hex()} for p, s in self.keys]}
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # -- addresses (a SEC pubkey is the address) -------------------------------
    def new_address(self) -> bytes:
        priv, sec = new_key()
        self.keys.append((priv, sec))
        self._save()
        return sec

    def primary_pubkey(self) -> bytes:
        """The wallet's first (primary) SEC pubkey — the coinbase receive key. Does NOT mint a
        new key, so it's safe to call to display 'your address' repeatedly."""
        return self.keys[0][1]

    def addresses(self) -> list[bytes]:
        return [s for _, s in self.keys]

    def receive_script(self) -> bytes:
        """A coinbase/payout scriptPubKey (bytes) paying our primary key, as bare P2PK."""
        return cscript.assemble(p2pk(self.keys[0][1]))

    # -- a MODEL wallet loaded with our keys + the node's spendable coins -------
    def _loaded(self, utxo, height: int, maturity: int) -> ModelWallet:
        w = ModelWallet()
        for priv, sec in self.keys:
            w.map_keys[sec] = priv
            w.map_pubkeys[hash160(sec)] = sec
        for (txid, n), coin in utxo.items():
            if not w.is_mine(coin.spk):
                continue
            if coin.coinbase and coin.height >= 0 and height - coin.height < maturity:
                continue                                    # immature coinbase — not yet spendable
            w.add_coin(txid, n, coin.value, coin.spk)
        return w

    def balance(self, utxo, height: int, maturity: int) -> int:
        return self._loaded(utxo, height, maturity).get_balance()

    def create_payment(self, utxo, height: int, maturity: int,
                       to_pubkey: bytes, amount: int, fee: int) -> bytes:
        """Build + sign a payment of `amount` (+`fee`) to `to_pubkey` (bare P2PK), change back to
        self. Returns raw tx bytes; raises `InsufficientFunds` if the spendable balance is short."""
        return self.create_payment_to_script(utxo, height, maturity,
                                              p2pk(bytes(to_pubkey)), amount, fee)

    def create_payment_to_script(self, utxo, height: int, maturity: int,
                                 recipient_spk: list, amount: int, fee: int) -> bytes:
        """Build + sign a payment to an arbitrary recipient scriptPubKey (bare P2PK **or** P2PKH —
        both v0.1 forms), change back to self as bare P2PK. Returns raw tx bytes; raises
        `InsufficientFunds` if the spendable balance is short."""
        w = self._loaded(utxo, height, maturity)
        try:
            tx, _coins, _change = w.create_transaction(recipient_spk, int(amount), int(fee))
        except ValueError as e:
            raise InsufficientFunds(str(e)) from e
        return ser_tx(tx)
