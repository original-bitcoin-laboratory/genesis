//! Reorg + difficulty tests: the reorg-safe chainstate reproduces the Python node — it reorgs to a
//! taller valid branch, **aborts and restores** the prior chain when a taller branch is invalid,
//! and **rejects a forged-difficulty block**; and the retarget math + compact-target round-trip
//! match. NOT money.

use obl_validator::block_hash;
use obl_validator::difficulty::{retarget, target_bigint, target_to_compact};
use obl_validator::reorg::NodeState;
use obl_validator::rules::Rules;

include!("data/reorg_data.rs");

fn hexd(s: &str) -> Vec<u8> {
    (0..s.len())
        .step_by(2)
        .map(|i| u8::from_str_radix(&s[i..i + 2], 16).unwrap())
        .collect()
}

fn hexe(b: &[u8]) -> String {
    b.iter().map(|x| format!("{:02x}", x)).collect()
}

fn run_scenario(rows: &[(&str, &str, &str, i64, usize, i64, bool)]) {
    let mut st = NodeState::new(Rules::jan09(), 1, None);
    for (label, raw_hex, tip_hex, height, utxo, balance, inv) in rows {
        let raw = hexd(raw_hex);
        let h = block_hash(&raw);
        st.add_block(&raw);
        st.activate_best();
        assert_eq!(hexe(&st.tip().unwrap()), *tip_hex, "tip after {label}");
        assert_eq!(st.height(), *height, "height after {label}");
        assert_eq!(st.utxo_count(), *utxo, "utxo after {label}");
        assert_eq!(st.balance(), *balance, "balance after {label}");
        assert_eq!(st.is_invalid(&h), *inv, "invalid flag after {label}");
    }
}

#[test]
fn reorg_to_a_taller_valid_branch() {
    run_scenario(REORG_A);
}

#[test]
fn abort_and_restore_on_an_invalid_taller_branch() {
    run_scenario(REORG_B);
}

#[test]
fn forged_difficulty_block_is_rejected() {
    run_scenario(REORG_C);
}

#[test]
fn difficulty_retarget_matches_python() {
    let rules = Rules::jan09();
    for (last_bits, actual, expected, floor, result) in RETARGET {
        assert_eq!(retarget(*last_bits, *actual, *expected, &rules, *floor), *result);
    }
}

#[test]
fn compact_target_round_trips() {
    for nbits in TARGET_ROUNDTRIP {
        assert_eq!(target_to_compact(&target_bigint(*nbits)), *nbits);
    }
}
