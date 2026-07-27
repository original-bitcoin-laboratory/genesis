"""NEW-EXP difficulty retarget for the experimental X-chain nodes (Path B, Stages 2 + 4).

Stage 1 mined at a fixed genesis (regtest-easy) difficulty — trivially out-run. This adds a
real retarget so difficulty tracks hashrate and the chain paces roughly evenly. It follows the
**shape** of each chain's faithful algorithm — NOV08's ±1-bit nudge on leading-zero-bits,
JAN09's proportional (4×-clamped) adjustment on the compact target — but at the **network's own**
short interval + spacing (a NEW-EXP choice; the historical 2-week / 30-day windows would never
adjust on a testnet).

**Difficulty floor (`min_bits`, Stage 4).** The faithful genesis is deliberately *easy* (so the
genesis artifact reproduces exactly and a demo mines instantly), which makes the chain trivially
rewritable. Because the genesis is a fixed artifact we cannot make it harder, a **network minimum
difficulty** — harder than genesis but *independent* of it — lets an operator require real work on
a live X-network without touching the faithful genesis. It defaults to the genesis nBits (so the
easy demo/tests are unchanged), and every block, at every height, must be **no easier than the
floor**. `check_difficulty` / `expected_bits` take `min_bits`; the authoritative gate is
`ChainState._connect`, which re-checks difficulty on connect so the **orphan reconnection path**
(where the direct-receipt check is deferred) can't smuggle in a wrong-difficulty block.
"""

from __future__ import annotations

from chainsync import nbits_of, prev_hash

NET_TARGET_SPACING = 30              # seconds/block (NEW-EXP; historical: 600 / 900)
NET_RETARGET_INTERVAL = 60          # blocks per retarget window (NEW-EXP)


def _time_of(raw: bytes) -> int:
    return int.from_bytes(raw[68:72], "little")


def target_to_compact(target: int) -> int:
    """Encode a target integer as compact nBits (inverse of Rules.pow_target for compact)."""
    if target <= 0:
        return 0
    size = (target.bit_length() + 7) // 8
    compact = (target << (8 * (3 - size))) if size <= 3 else (target >> (8 * (size - 3)))
    if compact & 0x00800000:            # avoid the sign bit
        compact >>= 8
        size += 1
    return compact | (size << 24)


def not_easier(bits: int, floor: int, rules) -> int:
    """Return `bits`, but never *easier* than `floor` (the harder of the two, per encoding)."""
    if rules.pow_encoding == "leading-zero-bits":
        return max(bits, floor)                          # more required zero-bits = harder
    return bits if rules.pow_target(bits) <= rules.pow_target(floor) else floor   # smaller target = harder


def _retarget(last_bits: int, actual: int, expected: int, rules, floor_bits: int) -> int:
    """Pure retarget math (deterministic, no chain): new nBits from the window's timing,
    floored so it is never easier than `floor_bits`."""
    if rules.pow_encoding == "leading-zero-bits":
        nb = last_bits
        if actual < expected // 2:                       # too fast -> harder (more zero bits)
            nb = last_bits + 1
        elif actual > expected * 2 and last_bits > floor_bits:   # too slow -> easier
            nb = last_bits - 1
        return max(floor_bits, nb)                        # never easier than the floor
    # compact proportional, clamped 4x
    a = max(expected // 4, min(expected * 4, max(1, actual)))
    new_target = rules.pow_target(last_bits) * a // expected
    new_target = min(rules.pow_target(floor_bits), max(1, new_target))   # floor (easiest allowed)
    return target_to_compact(new_target)


def _floor_bits(chain, rules, min_bits):
    """The effective difficulty floor: `min_bits` if set, else the genesis nBits."""
    gen_bits = chain.by_hash[chain.genesis].nBits
    return gen_bits if min_bits is None else not_easier(min_bits, gen_bits, rules)


def expected_bits(chain, parent_hash: bytes, rules, min_bits: int | None = None) -> int:
    """Required nBits for a child of `parent_hash`: unchanged except at retarget boundaries, and
    never easier than the floor (`min_bits`, or genesis when unset)."""
    parent = chain.by_hash[parent_hash]
    height = parent.height + 1
    last_bits = parent.nBits
    floor_bits = _floor_bits(chain, rules, min_bits)
    if height < NET_RETARGET_INTERVAL or height % NET_RETARGET_INTERVAL != 0:
        return not_easier(last_bits, floor_bits, rules)
    idx = parent                                          # walk back one window for its start time
    for _ in range(NET_RETARGET_INTERVAL):
        idx = chain.by_hash.get(idx.prev)
        if idx is None:
            return not_easier(last_bits, floor_bits, rules)
    actual = _time_of(parent.raw) - _time_of(idx.raw)
    expected = NET_RETARGET_INTERVAL * NET_TARGET_SPACING
    return _retarget(last_bits, actual, expected, rules, floor_bits)


def check_difficulty(chain, raw: bytes, rules, min_bits: int | None = None) -> bool:
    p = prev_hash(raw)
    if p not in chain.by_hash:                            # orphan: parent unknown, defer (see _connect)
        return True
    return nbits_of(raw) == expected_bits(chain, p, rules, min_bits)
