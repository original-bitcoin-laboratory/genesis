# Native v0.1 financial instruments (executed)

Each instrument is built **only from original v0.1 primitives** and runs through
the MODEL interpreter with real secp256k1, `scriptCode` derived from the real
subscript (byte-level `cscript`). This is the executable form of Satoshi's
Jan 10 2009 claim that Bitcoin's network "can support a full range of escrow
transactions and contracts". Evidence level: **MODEL** (cross-validated against
the C++/OpenSSL port for the CHECKSIG/multisig core). Tests: `test_checksig.py`,
`test_instruments.py`.

Notation: a spend runs `scriptSig + OP_CODESEPARATOR + scriptPubKey` (v0.1
`VerifySignature`, script.cpp:1126); `scriptCode` = the scriptPubKey.

## 1. Buyer–seller–arbitrator escrow (2-of-3 multisig)

```
scriptPubKey:  OP_2 <buyer> <seller> <arbiter> OP_3 OP_CHECKMULTISIG
scriptSig:     OP_0 <sigX> <sigY>          # any 2 of the 3, in key order
```
Any two settle: buyer+seller (normal), buyer+arbiter (refund), seller+arbiter
(release). Outsider signatures and wrong-order signatures are rejected; the
arbiter alone cannot move funds. (`OP_0` is the faithful v0.1 off-by-one dummy.)

## 2. Hash-lock (preimage) claim

```
scriptPubKey:  OP_HASH256 <H> OP_EQUALVERIFY <pubkey> OP_CHECKSIG
scriptSig:     <sig> <preimage>            # where HASH256(preimage) == H
```
Value moves only on revealing a secret whose double-SHA256 equals `H` *and* a
valid signature. Wrong preimage or wrong key ⇒ rejected. This is the
delivery-versus-payment / proof-of-knowledge primitive.

## 3. Hash-lock **or** refund (branch via `OP_IF`)

```
scriptPubKey:  OP_IF
                 OP_HASH256 <H> OP_EQUALVERIFY <recipient> OP_CHECKSIG   # claim
               OP_ELSE
                 <sender> OP_CHECKSIG                                    # refund
               OP_ENDIF
claim  scriptSig:  <sig_recipient> <preimage> OP_1
refund scriptSig:  <sig_sender> OP_0
```
Two settlement paths in one output. In v0.1 the *timeout* on the refund path is
enforced at the **transaction** level (`nLockTime`/sequence on a pre-signed refund
tx — v0.1 has no script-level timelock opcode), while the branch selection and the
hash-lock are pure Script, shown here executing.

## 4. Assurance contract / crowdfund (`SIGHASH_ANYONECANPAY`)

```
each pledge input i:  scriptSig <sig_i>   over  scriptPubKey_i = <pledger_i> OP_CHECKSIG
                      signed with SIGHASH_ALL | SIGHASH_ANYONECANPAY (0x81)
single shared output: the campaign goal
```
Because `ANYONECANPAY` commits a signature to **only its own input** (plus the
output), pledges are signed independently and **a later pledge can be added
without invalidating earlier ones** — the Tabarrok assurance-contract / crowdfund
construction. Demonstrated directly: an `0x81` pledge stays valid when a third
input is appended, whereas a plain `SIGHASH_ALL` pledge breaks the moment any
input is added.

## Still transaction-level (not script opcodes) in v0.1

Timelocks/refund-expiry use `nLockTime` + per-input sequence on pre-signed
transactions (finality rule `main.h:400`: final when `nLockTime < nBestHeight`) —
there is no `CLTV`/`CSV` opcode in v0.1. Those instruments are constructed as
pre-signed transaction graphs, not single scripts.
