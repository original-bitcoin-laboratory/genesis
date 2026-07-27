# Original Bitcoin Laboratory — Genesis (`OBL-JAN09`)

Self-contained reconstruction of the **January 2009 Bitcoin v0.1.0** release — the
first publicly announced Bitcoin implementation (node + wallet + miner + validator
+ Script interpreter + P2P networking + database + market experiments). This is the
principal **behavioral oracle** for "original Bitcoin". One of the two editions of
the Original Bitcoin Laboratory (the other is the sibling `pre-genesis` repo,
November 2008 pre-release).

## Quick start

```bash
./scripts/fetch-artifacts.sh          # pull the 2 canonical v0.1.0 archives (Nakamoto Institute CDN)
python scripts/verify-artifacts.py    # hash-check against manifests/EXPECTED_CHECKSUMS.json
```

Archives land in `artifacts/jan09/` (gitignored) and are never edited. Verified
values: MD5/SHA-1 (SNI catalogue) plus SHA-256 matching the 2012 Hal Finney
recovery thread — `bitcoin-0.1.0.rar` = `8b17eb9a…`, `bitcoin-0.1.0.tgz` =
`ce9da465…`.

## Reproduce the executable reconstruction

`derivatives/` is v0.1.0 made to **run, with nothing disabled**: the full Script engine
(Python MODEL + C++ PORT), sighash, `OP_CHECKSIG`/`CHECKMULTISIG` on real secp256k1,
native instruments (escrow / hash‑lock / assurance), a UTXO `ConnectInputs`/`ConnectBlock`
ledger, a wallet, the P2P wire + chain sync, persistence, the neutral descendant matrix
(BTC + BSV **executed**), the commerce subsystem (signed listings + atoms reputation), a
script **debugger**, a **full‑stack console**, and two live counterfactual networks —
**NOV08‑X** and **JAN09‑X**.

```bash
python scripts/reproduce.py        # every derivatives suite + regenerated artifacts
python scripts/verify_genesis.py   # both experimental genesis blocks re-derive from source
```

The unmodified 2009 `bitcoin.exe` was also run and hash‑verified against these
reconstructions — the exact genesis reproduces three independent ways (`r3-findings/run1/`,
level `JAN09-EXECUTED`). Findings, the honest claim, and scope live in the umbrella:
[`common/README.md`](https://github.com/original-bitcoin-laboratory/common/blob/main/README.md) · [`common/CLAIMS.md`](https://github.com/original-bitcoin-laboratory/common/blob/main/CLAIMS.md).
These chains are **not money** (stamped in the coinbase): a research microscope, not a coin.

## Layout

```text
docs/         charter, evidence policy, status
provenance/   whitepaper + provenance sources
manifests/    expected checksums + generated manifests
profiles/     frozen OBL-JAN09 profile
scripts/      acquisition / verification / inventory tooling
artifacts/    acquired archive bytes (gitignored)
derivatives/  all modified / instrumented / modernized code
```

## Boundaries

- `artifacts/` holds acquired historical bytes and is never edited.
- `derivatives/` holds every patch, port, harness, UI, or experiment; a
  derivative is never described as canonical original code.
- The program-wide roadmap lives in the lab umbrella (`common/ROADMAP.md`);
  see `docs/PROJECT_CHARTER.md` for method and evidence rules.

## License

MIT © 2026 Parth Mauria Saxena (new laboratory material only). Original Bitcoin
source retains Satoshi Nakamoto's original notices. See `LICENSE`.
