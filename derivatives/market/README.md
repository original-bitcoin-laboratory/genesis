# Commerce subsystem — executable model (R6)

**Evidence level: `MODEL`.** The static audit ([`../../inventory/MARKET_AUDIT.md`](../../inventory/MARKET_AUDIT.md))
showed v0.1 shipped a working, off‑chain decentralized marketplace. This makes its
two core mechanisms **run**.

## 1. Signed listings / reviews

`CProduct` / `CReview` are signed over their hash **excluding the signature**
(`GetSigHash = SerializeHash(*this, SER_GETHASH|SER_SKIPSIG)`, market.h:107,165) and
verified with `CKey::Verify` (market.cpp:203,239). Here that is real ECDSA on
secp256k1: `make_product` / `make_review` sign; `verify()` checks; tampering any
signed field or swapping the key fails verification. (The field serialization is a
*model* one — the sign→verify mechanism is faithful, not v0.1's exact CDataStream.)

## 2. The "atoms" web‑of‑trust reputation

Reproduced **exactly** from `market.cpp` (pure algorithm):

- `CUser::AddAtom` (market.cpp:109) — the flow‑through rule: incoming atoms collect in
  `vAtomsNew`; once `nFlowthroughRate = 2` (or nothing has flowed yet) a **randomly
  chosen** atom moves to `vAtomsOut` to propagate; the **zero atom never propagates**;
  **origin** atoms always do; duplicates are ignored.
- `AddAtomsAndPropagate` (market.cpp:143) — a two‑frontier flood pushing newly‑out
  atoms along each user's `vLinksOut` (the links a review adds, market.cpp:219).

## What the tests show (`test_market.py`, 9)

Product/review signatures verify and reject tampering / wrong key; atom flow‑through
needs rate 2 once seeded; the zero atom stays put; duplicates are ignored; and atoms
**propagate one hop along review links** — a signed review then a reputation update,
end to end.

```bash
python market_model.py   # sign a product + seed reputation
python -m pytest         # 9 passed
```

## Boundary

Off‑chain by design (the audit's finding): this is the commerce layer a node carries,
not blockchain state — it pairs with an X‑chain node (`../nov08x`, `../jan09x`) rather
than living in its UTXO set. The signature model is mechanism‑faithful, not byte‑exact
to v0.1's serialization; the atoms algorithm is exact.
