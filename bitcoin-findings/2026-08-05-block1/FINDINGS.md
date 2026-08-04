# Block 1 — the chain becomes a chain

**5 August 2026 · level `BITCOIN-EXECUTED`**

The genesis was mined on 3 August and stood alone for a day and a half: a commitment, not yet a
chain. Block 1 was mined on 4 August at 22:36:53 UTC by **the released client itself**, from the
signed `Bitcoin-v0.1.1` distribution, and relayed to the network.

```
block 1     000000007beb32b8380089595a91261a5ce4fbd4ece0cd661683cb1ce81e407c
prev        00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a
merkleroot  d52bbf2a083c949dfc2859daefc086b15e26e3d77672dd889fd73d2d006d4c6f
nTime       1785883013   2026-08-04 22:36:53 UTC
nBits       0x1d00ffff   nNonce 895691393       real difficulty-1, ~2^32 hashes
coinbase    04ffff001d0101
output      50.00000000 -> P2PK 41049a5713846fb6…ac
```

## What is established

**The signed binary built the chain.** Not a reimplementation, not a script — `bitcoin.exe`
`cfb59606c032faa933d5007e85d36f4cfd02737fc4bc485ec2d8699aeacba5ac`, the exact bytes published in
`Bitcoin-v0.1.1`. This is bound rather than asserted: `capture_binding.ps1` recorded the live process
image **before and after** the block, both under **PID 2240**, so the pair brackets one uninterrupted
process and the hash of the running executable matches the release.

**Two independent implementations agree on the result.** The block was derived from the guest's
`blk0001.dat` (C++, Windows) and read back from the seed's `blocks.dat` (Python `netnode`, Linux).
Both yield the identical hash. The client did not merely mine — it **relayed**, and a different
implementation validated and stored what it sent.

**The coinbase carries no message: `04ffff001d0101`.** That is height and extra-nonce only, which is
all `BitcoinMiner` produces. It is the reason the provenance anchor `d84a8c1a…310d6dcf` cannot live
here: adding a message hook would be an eleventh patched line, and the ten-line boundary is part of
what the release claims. The anchor belongs in a later block mined with `netnode`, which takes a
`msg` parameter without touching the client.

**`addr.txt` bootstrap, executed.** The guest was firewalled to permit outbound TCP to the seed and
nothing else — `Test-NetConnection 1.1.1.1 -Port 53` failed, so `chat.freenode.net` was unreachable
by construction and no IRC bootstrap was possible. A 16-byte `addr.txt` beside the executable was
the only source of the seed's address, and the client connected. This had been read out of
`db.cpp`'s `CAddrDB::LoadAddresses` (*"Load user provided addresses"*); it is now a run. It answers
what becomes of the released client when `chat.freenode.net` is eventually gone: nothing, given one
line of text.

## What is not established

**No `debug.log` exists**, so this write-up is thinner than the R3/R4 findings and deliberately so.
The whole of `OutputDebugStringF` sits inside `#ifdef __WXDEBUG__`, which Satoshi's makefile defines
via `DEBUGFLAGS` and **our build does not**. The client therefore emits no diagnostic output at all —
not to file, not even to `OutputDebugString`. The moment the peer was added and the moment the block
was found are unrecorded except in their consequences.

That is a defect in our build, not in the chain, and it is one of two found the first time this
binary was ever executed. The other: no `windres ui.rc` step, so the toolbar bitmaps are absent and
wxWidgets logs *"Can't load bitmap 'send20' from resources"* at startup. Neither touches consensus —
the genesis wrote correctly, the wire handshake is exact, both implementations agree on every block —
but both are divergences from the period build, and both are the reason for a future v0.1.2.

Worth stating plainly: three days of hashing, string-scanning and cross-platform auditing did not
surface either one. Running the thing surfaced both within an hour.

## Files

Raw bytes in `bitcoin-evidence/2026-08-05-block1/` (gitignored). Hashes in `SHA256SUMS` and
`EVIDENCE_MANIFEST.json` beside this file.

| file | what it shows |
|---|---|
| `blk0001.dat` | both blocks as the client wrote them; block 1 re-derives from these bytes |
| `EXECUTED_BINARY_BINDING_bitcoin-node-1_pre.json` | live process bound to `cfb59606…` before the block |
| `EXECUTED_BINARY_BINDING_bitcoin-node-1_post.json` | same PID after — the pair brackets one process |
| `addr.txt` | the 16 bytes that were the only possible route to a peer |

### Screenshots

28 desktop captures span the whole session, `21:13Z` to `22:46Z` — 19 before block 1 and 9 after.
Their filenames carry local time (UTC+05:30); the manifest records each one's UTC instant, so the
sequence is legible without knowing the operator's timezone. They corroborate the binding records
from a second, independent direction:

```
21:13:31Z   first capture
21:27:37Z   ── client process started (PID 2240), from the binding record
21:28:04Z   two captures seconds later — the startup failures
21:36:06Z   ── pre binding captured
21:39–21:54 the client running: Generating · 1 connections · 1 blocks
22:36:53Z   ── BLOCK 1, from the block header itself
22:42–22:46 nine captures after
```

Nothing in that ordering was arranged; three independent sources — process metadata, screenshot
timestamps, and the block's own `nTime` — agree.

**These are uncropped 1920×1080 desktop captures** and are not publishable as they stand: they show
host chrome and unrelated windows. They are raw evidence, hashed into the manifest, and must be
cropped to the relevant window and reviewed before appearing anywhere, exactly as R3's were before
their sanitised deposit.

The wallet holding block 1's coinbase key is **not** here. It is in
`OBL-BACKUP/01-keys-SECRET/bitcoin-chain-wallets/`, with the genesis key, and is never published.

**NOT money.** The output is 50.00000000 of nothing; no premine, no sale, no market. Block 1's coins
mature at height 120 (`COINBASE_MATURITY` 100, plus the 20 `main.cpp:544` adds).
