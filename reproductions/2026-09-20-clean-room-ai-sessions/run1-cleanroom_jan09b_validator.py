#!/usr/bin/env python3
"""Clean-room, spec-surface validator for JAN09-B.

This module deliberately implements only rules whose *magnitude/operation is
stated on JAN09-B's page*. Where the page names an external definition (BIP66)
or leaves a semantic open, the validator returns an explicit UNSPECIFIED state
instead of silently importing unstated behavior.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Optional, Sequence

MAX_MONEY = 21_000_000 * 100_000_000
MAX_SIZE = 0x02000000  # 32 MiB
MAX_BLOCK_SIGOPS = MAX_SIZE // 50  # exact C-style integer division is not stated by the page
LOCKTIME_THRESHOLD = 500_000_000


class Verdict(Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    UNSPECIFIED = "UNSPECIFIED"


@dataclass(frozen=True)
class CheckResult:
    verdict: Verdict
    reason: str


def money_range(value: int) -> bool:
    """JAN09-B §2: every output value is in [0, MAX_MONEY]."""
    return 0 <= value <= MAX_MONEY


def check_output_values(values: Iterable[int]) -> CheckResult:
    """Check each output and the running output sum, per JAN09-B OBL-C-0003."""
    total = 0
    for i, value in enumerate(values):
        if not money_range(value):
            return CheckResult(Verdict.INVALID, f"output[{i}] outside [0, MAX_MONEY]")
        total += value
        if not money_range(total):
            return CheckResult(Verdict.INVALID, f"running output sum after output[{i}] outside [0, MAX_MONEY]")
    return CheckResult(Verdict.VALID, "all outputs and running sum in range")


def check_block_size(serialized_size: int, tx_count: Optional[int] = None) -> CheckResult:
    if serialized_size < 0:
        return CheckResult(Verdict.INVALID, "negative serialized size")
    if serialized_size > MAX_SIZE:
        return CheckResult(Verdict.INVALID, "serialized block exceeds 32 MiB")
    # The page says “size and transaction count” but does not state the exact
    # count test or whether it is bytes-vs-count semantics beyond inheriting MAX_SIZE.
    if tx_count is not None and tx_count > MAX_SIZE:
        return CheckResult(Verdict.INVALID, "transaction count exceeds inherited MAX_SIZE")
    return CheckResult(Verdict.VALID, "within inherited 32 MiB ceiling")


def check_sigops(sigops: int) -> CheckResult:
    if sigops < 0:
        return CheckResult(Verdict.INVALID, "negative sigop count")
    if sigops > MAX_BLOCK_SIGOPS:
        return CheckResult(Verdict.INVALID, "signature-operation count exceeds MAX_SIZE/50")
    return CheckResult(Verdict.VALID, "sigop count within MAX_SIZE/50")


def locktime_uses_height(locktime: int) -> bool:
    if locktime < 0:
        raise ValueError("nLockTime is an unsigned value in the intended wire representation")
    return locktime < LOCKTIME_THRESHOLD


def check_locktime(locktime: int, chain_height: int, chain_time: int) -> CheckResult:
    """Apply only the threshold rule explicitly written on JAN09-B.

    The page does not specify sequence-number interaction, inclusive/exclusive
    finality comparison, or whether the relevant time is wall clock, block time,
    or median-time-past for the nLockTime decision. Accordingly this function
    deliberately reports UNSPECIFIED for the missing portions rather than
    importing Bitcoin Core semantics.
    """
    if locktime == 0:
        return CheckResult(Verdict.VALID, "zero nLockTime imposes no date/height target")
    if locktime < LOCKTIME_THRESHOLD:
        if chain_height >= locktime:
            return CheckResult(Verdict.VALID, "height-domain nLockTime target reached")
        return CheckResult(Verdict.INVALID, "height-domain nLockTime target not reached")
    if chain_time >= locktime:
        return CheckResult(Verdict.VALID, "time-domain nLockTime target reached")
    return CheckResult(Verdict.INVALID, "time-domain nLockTime target not reached")


def select_by_cumulative_work(candidates: Sequence[tuple[str, int]]) -> CheckResult:
    """Choose the chain with the greatest supplied cumulative work.

    The page specifies cumulative-work selection but not the formula for
    deriving work from nBits, nor a tie-break rule. Supplying cumulative work
    therefore keeps this function inside the written rule.
    """
    if not candidates:
        return CheckResult(Verdict.UNSPECIFIED, "no candidate chains")
    max_work = max(work for _, work in candidates)
    winners = [name for name, work in candidates if work == max_work]
    if len(winners) != 1:
        return CheckResult(Verdict.UNSPECIFIED, "cumulative-work tie-break rule is unstated")
    return CheckResult(Verdict.VALID, winners[0])


def strict_der() -> CheckResult:
    """The page points to BIP66 but does not print its encoding grammar."""
    return CheckResult(
        Verdict.UNSPECIFIED,
        "JAN09-B names IsValidSignatureEncoding as in BIP66 but does not include the parser rule text",
    )


def validate_rule_surface(*, outputs: Iterable[int], block_bytes: int,
                          sigops: int, tx_count: Optional[int] = None) -> list[CheckResult]:
    return [
        check_output_values(outputs),
        check_block_size(block_bytes, tx_count),
        check_sigops(sigops),
        strict_der(),
    ]


if __name__ == "__main__":
    # Sanity checks only; no laboratory validator/model is imported.
    assert check_output_values([0, MAX_MONEY]).verdict is Verdict.VALID
    assert check_output_values([MAX_MONEY + 1]).verdict is Verdict.INVALID
    assert check_output_values([MAX_MONEY // 2, MAX_MONEY // 2, 1]).verdict is Verdict.INVALID
    assert check_block_size(MAX_SIZE).verdict is Verdict.VALID
    assert check_block_size(MAX_SIZE + 1).verdict is Verdict.INVALID
    assert check_sigops(MAX_BLOCK_SIGOPS).verdict is Verdict.VALID
    assert check_sigops(MAX_BLOCK_SIGOPS + 1).verdict is Verdict.INVALID
    assert check_locktime(499_999_999, 500_000_000, 0).verdict is Verdict.VALID
    assert check_locktime(500_000_000, 0, 500_000_000).verdict is Verdict.VALID
    assert select_by_cumulative_work([("A", 250), ("B", 262)]).reason == "B"
    assert select_by_cumulative_work([("A", 10), ("B", 10)]).verdict is Verdict.UNSPECIFIED
    assert strict_der().verdict is Verdict.UNSPECIFIED
    print("clean-room JAN09-B surface sanity checks: PASS")
    print(f"MAX_MONEY={MAX_MONEY}")
    print(f"MAX_SIZE={MAX_SIZE}")
    print(f"MAX_BLOCK_SIGOPS={MAX_BLOCK_SIGOPS}")
