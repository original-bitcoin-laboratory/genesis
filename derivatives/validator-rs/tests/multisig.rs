//! OP_CHECKMULTISIG through the full interpreter: a real 2-of-2 bare-multisig spend validates, and
//! one with a wrong second signature is rejected — matching the Python model (including v0.1's
//! off-by-one dummy pop). NOT money.

use obl_validator::parse_tx;
use obl_validator::script::verify_spend;

include!("data/multisig_data.rs");

fn hexd(s: &str) -> Vec<u8> {
    (0..s.len())
        .step_by(2)
        .map(|i| u8::from_str_radix(&s[i..i + 2], 16).unwrap())
        .collect()
}

#[test]
fn checkmultisig_matches_the_python_model() {
    for (label, tx_hex, spk_hex, script_sig_hex, expected) in MULTISIG {
        let (tx, _) = parse_tx(&hexd(tx_hex), 0);
        let got = verify_spend(&hexd(script_sig_hex), &hexd(spk_hex), &tx, 0);
        assert_eq!(got, *expected, "case {label}");
    }
}
