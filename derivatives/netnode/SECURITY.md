# Security posture & threat model — read before running publicly

**This is a MODEL / NEW‑EXP research node. It has not been audited. It is not money, and it is not
production‑secure.** This document is deliberately blunt about what is and isn't defended, so
nobody mistakes it for something it isn't.

## The one load‑bearing invariant

The X‑chains faithfully carry the **origin's *missing* guardrails** — no `MoneyRange`/overflow
check, no block‑size cap, no script element/op/stack limits, unbounded arithmetic (see
[`CONSENSUS_SURFACE.md`](https://github.com/original-bitcoin-laboratory/common/blob/main/conformance/CONSENSUS_SURFACE.md)).
On a **value‑bearing** chain those are exploitable; on a **non‑monetary** chain they are harmless
research curiosities. **"Nothing disabled" is safe only because it is "not money."** Attaching
value would force adding the 2010 guardrails — at which point it stops being the undrifted origin.
**So: never attach value, never present it as money.** That is the security boundary.

## What *is* defended (Stages 1–4 + full‑node core)

- **Wire**: message checksums, a 4 MiB size cap, read timeouts, and per‑peer misbehavior scoring
  → a peer that sends garbage, oversize, or bad‑magic frames is dropped (`wire.py`, `livenode.py`).
- **Difficulty**: a block's `nBits` must equal the expected retarget for its parent — checked on
  the direct path (`difficulty.py`) **and authoritatively on connect** (`ChainState._connect`), so
  a wrong‑difficulty block can't slip in via the **orphan reconnection** path either. An optional
  **network difficulty floor** (`--min-difficulty`) lets a live network require real work above the
  deliberately‑easy genesis without altering the faithful genesis artifact.
- **Block validation** (`fullnode.py`): beyond PoW — block structure (one coinbase first) and the
  **merkle commitment** are enforced context‑free; difficulty when the parent is known.
- **Validated UTXO chainstate** (`chainstate.py`), the **sole authority** for what the node serves
  and mines: a UTXO set with reorg‑safe connect/disconnect (undo) enforcing **no double‑spends,
  script satisfaction (VerifySignature), no inflation, coinbase maturity, and the coinbase‑value
  rule with fees** — a PoW‑valid but tx‑invalid block is flagged and **never served, mined on, or
  followed**, and a reorg to an invalid branch is **aborted and the prior chain restored**.
- **Mempool** (`mempool.py`): relayed `tx` messages are fully validated against the UTXO and pooled
  parents before being accepted or re‑broadcast — an invalid or conflicting transaction is dropped,
  not relayed. The pool and the **orphan buffer** (txs that arrive before their parent) are both
  **bounded**, and a full pool uses **fee‑rate eviction** (a cheaper newcomer is refused; a dearer
  one evicts the cheapest childless entry). Consensus is still re‑checked when the block connects,
  so the mempool can only *avoid* relaying/mining bad txs, never *admit* one.
- **Persistence**: the block store is fsync'd and tolerates a crash‑truncated tail.
- **Resource bounds**: inbound connections are capped, the gossiped peer table is bounded, the
  mempool is size‑capped, and a per‑peer message **rate limit** drops flooding peers — basic
  connection‑/addr‑/message‑/mempool‑flood resistance (`livenode.py`, `mempool.py`).
- **Wallet + control interface** (`nodewallet.py`, `rpc.py`): the wallet builds payments with the
  faithful v0.1 `SelectCoins` / `CreateTransaction` / `SignSignature` path (real secp256k1
  signatures, every input re‑verified). The RPC control socket is **bound to loopback (127.0.0.1)
  only** and is off unless `--rpc` is passed.
- **Accelerated verification stays faithful** (`fastverify.py`): the optional libsecp256k1 verifier
  is wired so it returns **exactly what the origin's OpenSSL verify would** — it normalizes to low‑S
  and falls back to OpenSSL, so it does **not** silently adopt the BIP66 strict‑DER / low‑S rule
  (which would be a consensus change). This equivalence is differential‑tested (`test_fastverify.py`);
  if the native library is absent it uses the faithful path directly.

## What is *not* defended (known gaps)

- **Mempool policy is still basic.** The pool now bounds its orphan buffer, retries orphans when a
  parent arrives, and evicts by fee rate when full — but there is **no fee bumping / replace‑by‑fee,
  no package relay, and only leaf‑level eviction** (a low‑fee tx with a high‑fee child isn't rescued
  by the child's fee). These are *policy* gaps — they cannot admit an invalid tx to the validated
  chain (consensus is re‑checked on connect), only degrade relay quality.
- **The difficulty floor defaults to easy.** The retarget and the optional `--min-difficulty` floor
  work, but **unless an operator sets a real floor** the network starts at regtest‑easy difficulty
  and is **trivially rewritable** by anyone with modest hashpower. Choosing and coordinating a real
  floor across all nodes is an operator responsibility, not a default. (The orphan‑reconnection
  difficulty gap is now closed — see "what is defended.")
- **No peer authentication or encryption.** Connections are plaintext; there is no defense against
  a man‑in‑the‑middle, and no identity for peers.
- **No *strong* eclipse / Sybil resistance.** `addr` gossip and auto‑connect are now bounded
  (peer cap, bounded table, dedup, size caps, rate limit), but not *hardened* — a determined,
  resourceful adversary can still attempt to partition or eclipse a node.
- **Python resource limits.** There are now connection / table / rate caps, but no rigorous
  memory/CPU accounting; an adversary spending real resources could still degrade a node.
- **Local trust of the datadir.** The block store isn't integrity‑signed; a tampered datadir is
  not defended against.
- **The RPC has no authentication, and the wallet is not a secure key store.** The control
  interface trusts anything that can reach its loopback port — **never expose it** (no bind to a
  public interface, no port‑forward, no reverse proxy). Wallet keys are private scalars stored in
  plaintext (`<datadir>/wallet.json`), unencrypted — appropriate for an experimental, valueless
  chain, **not** for protecting anything of value. There is no key encryption, no HD derivation, no
  watch‑only mode, and no backup discipline beyond copying the file.

## What a real security review must cover before *any* value is ever attached

Full transaction/script/value validation; difficulty as a validated consensus rule on **every**
path (incl. orphans/reorgs) at real (non‑easy) difficulty; eclipse/Sybil/DoS resistance and peer
authentication; rigorous resource bounds; wire/parser fuzzing; and — realistically — a
production‑grade node (not this Python MODEL). Until all of that exists **and** an independent
audit signs off, treat this strictly as a **valueless experiment.**

## Reporting

Found a problem? Open an issue on the repository:
<https://github.com/original-bitcoin-laboratory/genesis/issues>. Because there is no value at
stake, disclosure can be public; please still be considerate.

See also [`RUN.md`](RUN.md) and
[`../../docs/PUBLIC_TESTNET_SCOPE.md`](../../docs/PUBLIC_TESTNET_SCOPE.md).
