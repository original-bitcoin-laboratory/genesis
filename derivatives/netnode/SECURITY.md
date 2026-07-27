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

## What *is* defended (Stages 1–3)

- **Wire**: message checksums, a 4 MiB size cap, read timeouts, and per‑peer misbehavior scoring
  → a peer that sends garbage, oversize, or bad‑magic frames is dropped (`wire.py`, `livenode.py`).
- **Difficulty**: a received block is rejected if its `nBits` doesn't match the expected retarget
  for its parent (`difficulty.py`), so difficulty can't be silently dropped on the direct path.
- **Block validation** (`fullnode.py`): beyond PoW — block structure (one coinbase first), the
  **merkle commitment**, difficulty, and the chain's **coinbase‑value rule** are enforced.
- **Persistence**: the block store is fsync'd and tolerates a crash‑truncated tail.
- **Resource bounds**: inbound connections are capped, the gossiped peer table is bounded, and a
  per‑peer message **rate limit** drops flooding peers — basic connection‑/addr‑/message‑flood
  resistance (`livenode.py`).

## What is *not* defended (known gaps)

- **Transaction/UTXO validation is not yet complete.** The node now validates block structure,
  the merkle commitment, difficulty, and the **coinbase‑value rule** (`fullnode.py`) — but not yet
  full transaction validity (double‑spends, script satisfaction, no‑inflation), which needs a UTXO
  set with reorg‑safe connect/disconnect. The network is **coinbase‑only** today, so this fully
  validates it; spend validation is the next increment.
- **Difficulty floor is easy, and the orphan path is unvalidated.** Difficulty starts at a
  regtest‑easy floor — the chain is **trivially rewritable** by anyone with modest hashpower — and
  `check_difficulty` defers blocks whose parent is unknown (orphans reconnect without a re‑check).
- **No peer authentication or encryption.** Connections are plaintext; there is no defense against
  a man‑in‑the‑middle, and no identity for peers.
- **No *strong* eclipse / Sybil resistance.** `addr` gossip and auto‑connect are now bounded
  (peer cap, bounded table, dedup, size caps, rate limit), but not *hardened* — a determined,
  resourceful adversary can still attempt to partition or eclipse a node.
- **Python resource limits.** There are now connection / table / rate caps, but no rigorous
  memory/CPU accounting; an adversary spending real resources could still degrade a node.
- **Local trust of the datadir.** The block store isn't integrity‑signed; a tampered datadir is
  not defended against.

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
