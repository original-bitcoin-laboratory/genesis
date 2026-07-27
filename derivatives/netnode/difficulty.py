"""NEW-EXP difficulty retarget for the experimental X-chain nodes (Path B, Stage 2).

Stage 1 mined at a fixed genesis (regtest-easy) difficulty — trivially out-run. This adds a
real retarget so difficulty tracks hashrate and the chain paces roughly evenly. It follows the
**shape** of each chain's faithful algorithm — NOV08's ±1-bit nudge on leading-zero-bits,
JAN09's proportional (4×-clamped) adjustment on the compact target — but at the **network's own**
short interval + spacing (a NEW-EXP choice; the historical 2-week / 30-day windows would never
adjust on a testnet). Difficulty is **floored at genesis** (never easier than the easy start).

`check_difficulty` lets a node reject a peer's block whose nBits doesn't match the expected
retarget for its parent — so difficulty can't be silently dropped. (A block whose parent isn't
yet known is deferred; validating the orphan path fully is part of the pre-liveness review.)
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


def _retarget(last_bits: int, actual: int, expected: int, rules, gen_bits: int) -> int:
    """Pure retarget math (deterministic, no chain): new nBits from the window's timing."""
    if rules.pow_encoding == "leading-zero-bits":
        nb = last_bits
        if actual < expected // 2:                       # too fast -> harder (more zero bits)
            nb = last_bits + 1
        elif actual > expected * 2 and last_bits > gen_bits:   # too slow -> easier
            nb = last_bits - 1
        return max(gen_bits, nb)                          # never easier than genesis
    # compact proportional, clamped 4x
    a = max(expected // 4, min(expected * 4, max(1, actual)))
    new_target = rules.pow_target(last_bits) * a // expected
    new_target = min(rules.pow_target(gen_bits), max(1, new_target))   # floor at genesis (easiest)
    return target_to_compact(new_target)


def expected_bits(chain, parent_hash: bytes, rules) -> int:
    """Required nBits for a child of `parent_hash`: unchanged except at retarget boundaries."""
    parent = chain.by_hash[parent_hash]
    height = parent.height + 1
    last_bits = parent.nBits
    if height < NET_RETARGET_INTERVAL or height % NET_RETARGET_INTERVAL != 0:
        return last_bits
    idx = parent                                          # walk back one window for its start time
    for _ in range(NET_RETARGET_INTERVAL):
        idx = chain.by_hash.get(idx.prev)
        if idx is None:
            return last_bits
    actual = _time_of(parent.raw) - _time_of(idx.raw)
    expected = NET_RETARGET_INTERVAL * NET_TARGET_SPACING
    gen_bits = chain.by_hash[chain.genesis].nBits
    return _retarget(last_bits, actual, expected, rules, gen_bits)


def check_difficulty(chain, raw: bytes, rules) -> bool:
    p = prev_hash(raw)
    if p not in chain.by_hash:                            # orphan: parent unknown, defer
        return True
    return nbits_of(raw) == expected_bits(chain, p, rules)
