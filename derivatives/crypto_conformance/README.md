# Crypto conformance — v0.1's ECDSA vs libsecp256k1

**Evidence level: `MODEL`.** The Script matrix cross‑checks the *interpreter* against
independent implementations; this does the same for the **crypto**. It takes a genuine
v0.1 `SignatureHash` and an ECDSA signature made the v0.1 way (OpenSSL EC, via the lab's
MODEL) and cross‑checks it against **libsecp256k1** — the curve library every modern
Bitcoin‑lineage chain runs — through `bitcoinx`, which is backed by
`electrumsv-secp256k1` (a real libsecp256k1 C binding).

This *is* **Thread A** of [`../../inventory/THE_OPENSSL_THREAD.md`](../../inventory/THE_OPENSSL_THREAD.md), executed.

## What it shows

```
v0.1 SignatureHash: 25a913b2…
model (OpenSSL) verifies own sig       : True
libsecp256k1 verifies canonical (low-S): True   ← the ECDSA math is identical
libsecp256k1 rejects high-S (malleable): True   ← the anti-malleability strictness
  ...but OpenSSL accepts that high-S   : True   ← v0.1's leniency (the problem)
model verifies a libsecp256k1 signature: True   ← round-trips both ways
```

- **The curve math is identical** — a canonical (low‑S) v0.1 signature verifies under
  libsecp256k1, and a libsecp256k1 signature verifies under our MODEL. Same curve, same
  key (the SEC pubkeys are byte‑equal).
- **The one real divergence is malleability** — a **high‑S** signature is valid ECDSA and
  OpenSSL (v0.1's stack) accepts it, but **libsecp256k1 rejects it**. That is exactly the
  issue **BIP66 / libsecp256k1** fixed (see the essay). So the crypto cross‑check doesn't
  just confirm compatibility — it *reproduces the historical fault line*.

## Tests (`test_crypto_conformance.py`, 21)

Canonical v0.1 sig ↔ libsecp256k1 both directions; high‑S accepted by OpenSSL but
rejected by libsecp256k1 (Thread A); identical secp256k1 key across both stacks;
libsecp256k1 always low‑S; canonicalization correct. All over a **real v0.1 sighash**.

```bash
python crypto_conformance.py   # the five-line demo above
python -m pytest               # 21 passed (skips if libsecp256k1 absent)
```

## Neutrality & boundary

`libsecp256k1` is the crypto **every descendant inherited** (Thread A *converged* — see the
essay's neutrality note), so this is a neutral cross‑check, not a privileging of any chain;
it is a *tool*, never authority (`common/AUTHORITY.md`). Backed by
`electrumsv-secp256k1` because the standalone `coincurve` / `secp256k1` wheels don't build
on this Python; the underlying C library is the same libsecp256k1. Degrades gracefully
(tests skip) if the binding is absent.
