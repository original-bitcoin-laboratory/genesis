# Internal robustness audit — NOV08‑X / JAN09‑X node

**Date:** 2026‑07‑28 · **Scope:** adversarial transport / parser robustness of the two node
implementations (Python `netnode`, Rust `validator‑rs`). **NOT money.**

> **What this is — and is not.** This is an *internal, engineering‑level* robustness audit: a
> deliberate adversarial pass over the untrusted‑input paths, with the findings fixed and pinned by
> regression tests. **It is not the independent third‑party security review scoped in
> [`AUDIT_SCOPE.md`](AUDIT_SCOPE.md)**, and it does not change the project's posture: the node
> remains an **unaudited, valueless research microscope**. The load‑bearing invariant is unchanged —
> *"nothing disabled" is safe only because it is "not money."* Nothing here makes the chain money,
> makes it safe to attach value to, or substitutes for the review [`SECURITY.md`](../derivatives/netnode/SECURITY.md)
> says must happen before any value is *ever* considered (which it must not be).

## Why this pass happened

A real defect had shipped: a chain past ~252 blocks silently stalled during initial‑block‑download
because `parse_inv` read only the first byte of the `inv` count instead of the full CompactSize
varint (any count ≥ `0xfd` misparsed). That is a *scaling* bug — invisible on a short chain, fatal
on a real one — so we did a systematic sweep for the same *class*: every place a length/count comes
off the wire and drives a loop or an allocation. "Anyone can plug in and play seamlessly" is only
true if a hostile or buggy peer can't hang or crash an honest node.

## Method

- **Read every untrusted‑input path** in both nodes: wire framing, `inv` / `getblocks` / `getdata` /
  `addr` / `tx` / `block` parsers, mempool ingest, the block‑connect gate.
- **Adversarial probe** — fired a barrage of malformed frames (empty, truncated, huge‑claimed‑count,
  random‑byte, unknown‑command) at a live node and checked it stayed **responsive** (RPC still
  answered; a fresh peer could still fully sync).
- **Cross‑implementation differential** — the two nodes are held byte‑for‑byte via generated golden
  vectors; a divergence in either parser shows up as a vector mismatch.
- **Pinned every fix with a regression test** that runs in `reproduce.py` / `cargo test`.

## Findings & fixes

| # | Severity | Path | Defect | Fix | Regression |
|---|---|---|---|---|---|
| **F1** | High (liveness) | `p2p/p2p.py` `parse_inv` | Read only `payload[0]` as the count; any `inv` ≥ 253 items misparsed → IBD silently stalled past ~252 blocks | Decode the full CompactSize varint | `test_inv_roundtrips_across_compactsize_boundary` |
| **F2** | High (DoS) | `p2p/p2p.py` `parse_inv`, `p2p/chainsync.py` `parse_getblocks` | A huge claimed count (up to 2⁶⁴) spun an unbounded loop over empty slices → **hung the event loop** (one‑packet DoS; confirmed: RPC timed out under probe) | Bound the loop to the real bytes (`if i + item > len(payload): break`) | `test_inv_and_getblocks_bound_a_huge_claimed_count`, `test_node_survives_a_malformed_message_flood_and_still_serves` |
| **F3** | Medium (availability) | `netnode/livenode.py` `_session` | A parse that *raised* on a malformed payload could drop the whole session ungracefully | Broad `except` around per‑message handling → **drop the peer, never the node**; log `peer dropped (bad message)` | covered by the flood‑survival test |
| **F4** | High (DoS) | `validator-rs/src/mempool.rs` `accept` → `lib.rs` `parse_tx` | The **tx** ingest path had no panic‑safe gate (the **block** path has `well_formed_block`); a malformed tx (`Vec::with_capacity(nin)` with `nin`=2⁶⁴, or a truncated slice) **panicked** the parser | Added the sibling `well_formed_tx` bounds‑safe gate in `net.rs` before `mempool.accept`; a peer flooding malformed tx is scored and dropped | `dos.rs::a_peer_flooding_malformed_txs_is_dropped_without_panic` |

All counts that drive a loop or allocation are now **bounded by the actual payload length** before
use, in both nodes, on every untrusted path.

## Checked and found sound (defenses that held)

- **Wire** (both nodes): 4 MiB size cap enforced *before* allocation, double‑SHA‑256 checksum, bad
  magic rejected. A frame can't force a giant allocation.
- **Rust block ingest**: `well_formed_block` (fully bounds‑checked, `checked_add` / `.get()`, never
  panics) gates *before* the indexing `validate_context_free` via short‑circuit `||`, and requires
  the txs to consume **exactly** the body — which also caps `ntx`, so `Vec::with_capacity(ntx)`
  can't overflow.
- **Python `addr`** (`livenode.decode_addrs`): already bounded (`range(min(n, 1000))` +
  break‑on‑exhaustion).
- **Python block ingest** (`fullnode.validate_block`): wraps the parse in try/except → returns
  `(False, "unparseable")` rather than raising.
- **Resource bounds**: per‑peer misbehavior scoring + ban threshold, per‑peer message **rate limit**,
  inbound‑connection cap, bounded gossiped peer table, size‑capped mempool with a bounded orphan
  buffer and fee‑rate eviction. (Existing tests: `test_rate_limit_drops_a_flooding_peer`,
  `test_inbound_connection_cap`, `test_known_addrs_are_bounded`.)
- **Consensus authority**: a PoW‑valid but tx‑invalid block is flagged and never served/mined/
  followed; reorg to an invalid branch aborts and restores. The mempool can only *avoid* relaying a
  bad tx, never *admit* one (consensus re‑checked on connect).

## Explicitly *out* of this pass

This is a robustness pass over transport/parsers, not a full security review. It does **not** cover:
the deep cryptographic fidelity axis (pre‑BIP66 / OpenSSL‑lenient verification — see `AUDIT_SCOPE.md`
§2); eclipse / Sybil / partition resistance; a sustained coverage‑guided fuzzing campaign; formal
resource accounting; or anything requiring a production‑grade node. The **known gaps** in
[`SECURITY.md`](../derivatives/netnode/SECURITY.md) (easy default difficulty, no peer auth/encryption,
plaintext wallet, loopback‑only unauthenticated RPC) stand as documented — confirmed, not closed.

## Reproduce

```bash
python scripts/reproduce.py            # full lab, 25/25 steps (both node suites, incl. the DoS-survival test)
cd derivatives/validator-rs && cargo test    # Rust node, 30 tests (incl. both malformed-block and malformed-tx floods)
python -m pytest derivatives/p2p/test_p2p.py -q          # parser CompactSize + huge-count bounds
```

Manual red‑team probe (starts a node, then floods it): see
[`../derivatives/netnode/adversarial_probe.py`](../derivatives/netnode/adversarial_probe.py).

## Verdict

Against the adversarial classes tested — malformed, truncated, oversize, huge‑claimed‑count, and
unknown‑command messages on every untrusted path — **both nodes now stay up and keep serving**; a
hostile peer is dropped, never the node. That is the bar for "plug in and play" on a hobbyist network.

It is **not** a clean bill of health, and it is **not** independent. Until the review in
`AUDIT_SCOPE.md` signs off **and** the "not money" framing holds, this remains a **valueless
experiment**. **Not money.**
