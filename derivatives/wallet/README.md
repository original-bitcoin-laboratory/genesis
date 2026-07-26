# Headless v0.1 wallet (derivative)

**Evidence level: `MODEL`** (real ECDSA on secp256k1; every input independently
re-verified by the lab's EvalScript). Key store, coin selection, and
`CreateTransaction` — no VM, no GUI.

## Faithful to the v0.1 wallet (main.cpp / script.cpp)

- **Key store** — `mapKeys` (pubkey → privkey) + `mapPubKeys` (hash160 → pubkey)
  (main.h:1314). Ownership via the two `Solver` templates (script.cpp:913):
  the bare `OP_PUBKEY OP_CHECKSIG` (P2PK) and
  `OP_DUP OP_HASH160 OP_PUBKEYHASH OP_EQUALVERIFY OP_CHECKSIG` (P2PKH). `IsMine`
  and `ExtractPubKey` follow those templates (script.cpp:1028, 1035).
- **`GetBalance`** — sums unspent *mine* credits (main.cpp:2386).
- **`SelectCoins`** — the v0.1 picker (main.cpp:2410): exact match wins outright;
  else if no subset reaches the target, take the lowest larger coin; else a
  **stochastic subset-sum approximation** (1000 reps, two passes) minimising the
  overshoot, comparing against the lowest-larger fallback.
- **`CreateTransaction`** — (main.cpp:2514): `vout[0]` pays the payee, `vout[1]`
  returns change to self as a **bare P2PK** (`scriptPubKey << vchPubKey <<
  OP_CHECKSIG`, main.cpp:2559 — the same bare-P2PK output that dominates the early
  chain), `vin` covers every mine output of the selected coins, and the fee is the
  unspent remainder.
- **`SignSignature`** — (script.cpp:1090): `hash = SignatureHash(scriptPubKey,
  txTo, nIn, SIGHASH_ALL)`; `Solver` emits the scriptSig (`<sig>` for P2PK,
  `<sig> <pubkey>` for P2PKH); the input is then **re-run through EvalScript**
  before the tx is returned — exactly as the original does.

## What the tests show (`test_wallet.py`, 11)

Balance counts only mine-and-unspent; `IsMine`/`ExtractPubKey` on both templates;
`SelectCoins` exact / lowest-larger / subset-sum; `CreateTransaction` for a P2PK
*and* a P2PKH coin, each signed and **independently verified** (the v0.1
`VerifySignature` path `EvalScript(scriptSig + OP_CODESEPARATOR + scriptPubKey)`)
with value conserved; exact-amount (no change) tx; insufficient-funds refusal; fee
drawn from change with `value_in − value_out == fee`; and a **round-trip**: the
wallet's own change output is fed back and **re-spent**, proving it is a valid coin.

```bash
python -m pytest        # 11 passed
python test_wallet.py   # balance + a funded spend + independent verify
```

## Boundary

The signatures are real; verification is the lab's independent EvalScript, and the
no-inflation check mirrors `ConnectInputs`. What this model does *not* do: broadcast
(that is `../p2p`), persist keys to `wallet.dat` (Berkeley-DB — separate), or the
`AddSupportingTransactions`/relay bookkeeping. A wallet-built tx validated by the
UTXO `ConnectBlock` in `../node/chain_port.cpp` is the natural cross-check.
