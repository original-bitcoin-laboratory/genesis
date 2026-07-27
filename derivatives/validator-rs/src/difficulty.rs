//! The NEW-EXP difficulty retarget, ported from `netnode/difficulty.py`. NOT money.
//!
//! Same shape as each chain's algorithm at the network's short interval/spacing, floored so it is
//! never easier than `min_bits` (or genesis). Compact-target math uses `num-bigint`.

use num_bigint::{BigInt, Sign};
use num_traits::{ToPrimitive, Zero};

use crate::index::BlockIndex;
use crate::rules::{Pow, Rules};
use crate::target_from_bits;

pub const NET_TARGET_SPACING: i64 = 30;
pub const NET_RETARGET_INTERVAL: i64 = 60;

/// The compact `nBits` target as a big integer.
pub fn target_bigint(nbits: u32) -> BigInt {
    BigInt::from_bytes_be(Sign::Plus, &target_from_bits(nbits))
}

/// Encode a target integer as compact `nBits` (inverse of `target_bigint`, mirrors Python).
pub fn target_to_compact(target: &BigInt) -> u32 {
    if target <= &BigInt::zero() {
        return 0;
    }
    let bits = target.bits() as usize;
    let mut size = (bits + 7) / 8;
    let mut compact: u64 = if size <= 3 {
        (target << (8 * (3 - size))).to_u64().unwrap()
    } else {
        (target >> (8 * (size - 3))).to_u64().unwrap()
    };
    if compact & 0x0080_0000 != 0 {
        compact >>= 8;
        size += 1;
    }
    (compact as u32) | ((size as u32) << 24)
}

fn time_of(raw: &[u8]) -> i64 {
    u32::from_le_bytes(raw[68..72].try_into().unwrap()) as i64
}

/// `bits`, but never *easier* than `floor` (the harder of the two, per encoding).
pub fn not_easier(bits: u32, floor: u32, rules: &Rules) -> u32 {
    match rules.encoding {
        Pow::LeadingZeroBits => bits.max(floor),
        Pow::Compact => {
            if target_bigint(bits) <= target_bigint(floor) {
                bits
            } else {
                floor
            }
        }
    }
}

fn floor_bits(index: &BlockIndex, rules: &Rules, min_bits: Option<u32>) -> u32 {
    let gen = index.by_hash[&index.genesis.unwrap()].nbits;
    match min_bits {
        None => gen,
        Some(mb) => not_easier(mb, gen, rules),
    }
}

/// Pure retarget math: new `nBits` from the window's timing, floored at `floor_bits`.
pub fn retarget(last_bits: u32, actual: i64, expected: i64, rules: &Rules, floor_bits: u32) -> u32 {
    match rules.encoding {
        Pow::LeadingZeroBits => {
            let mut nb = last_bits;
            if actual < expected / 2 {
                nb = last_bits + 1;
            } else if actual > expected * 2 && last_bits > floor_bits {
                nb = last_bits - 1;
            }
            nb.max(floor_bits)
        }
        Pow::Compact => {
            let a = actual.max(1).max(expected / 4).min(expected * 4);
            let computed = target_bigint(last_bits) * BigInt::from(a) / BigInt::from(expected);
            let nt = computed.max(BigInt::from(1)).min(target_bigint(floor_bits));
            target_to_compact(&nt)
        }
    }
}

/// Required `nBits` for a child of `parent_hash`: unchanged except at retarget boundaries, and
/// never easier than the floor.
pub fn expected_bits(index: &BlockIndex, parent_hash: &[u8; 32], rules: &Rules, min_bits: Option<u32>) -> u32 {
    let parent = index.get(parent_hash).unwrap();
    let height = parent.height + 1;
    let last_bits = parent.nbits;
    let floor = floor_bits(index, rules, min_bits);
    if height < NET_RETARGET_INTERVAL || height % NET_RETARGET_INTERVAL != 0 {
        return not_easier(last_bits, floor, rules);
    }
    let mut idx = parent;
    for _ in 0..NET_RETARGET_INTERVAL {
        match index.get(&idx.prev) {
            Some(p) => idx = p,
            None => return not_easier(last_bits, floor, rules),
        }
    }
    let actual = time_of(&parent.raw) - time_of(&idx.raw);
    retarget(last_bits, actual, NET_RETARGET_INTERVAL * NET_TARGET_SPACING, rules, floor)
}
