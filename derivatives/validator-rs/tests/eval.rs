//! EvalScript opcode-coverage tests: 70+ scripts (arithmetic incl. big numbers, stack/alt-stack,
//! splice, bitwise, comparisons, hashes, flow control, VERIFY/RETURN, structural errors) run through
//! the Rust interpreter must reproduce the Python model's (ok, valid) exactly. NOT money.

use obl_validator::eval::{cast_to_bool, run};

include!("data/eval_data.rs");

fn hexd(s: &str) -> Vec<u8> {
    (0..s.len())
        .step_by(2)
        .map(|i| u8::from_str_radix(&s[i..i + 2], 16).unwrap())
        .collect()
}

#[test]
fn opcode_semantics_match_the_python_model() {
    let mut checked = 0;
    for (label, hex, exp_ok, exp_valid) in EVAL {
        let (ok, stack) = run(&hexd(hex), None);
        assert_eq!(ok, *exp_ok, "ok mismatch: {label}");
        let valid = ok && stack.last().map(|s| cast_to_bool(s)).unwrap_or(false);
        assert_eq!(valid, *exp_valid, "valid mismatch: {label}");
        checked += 1;
    }
    assert!(checked >= 70, "expected the full coverage suite");
}
