//! SignatureHash deletes OP_CODESEPARATOR at opcode boundaries only, and keeps a truncated push, as
//! v0.1's FindAndDelete does (script.h:535). Digests are the corrected Python model's
//! (`derivatives/model/tx_sighash.py`), so this is a cross-language check, not a self-check.
//! The Python and C++ implementations dropped the strip-every-0xab reading in September 2026; this
//! node kept it until 14 October 2026, and no shared vector exercised the case. NOT money.

use obl_validator::eval::find_and_delete;
use obl_validator::parse_tx;
use obl_validator::sighash::signature_hash;

fn hexd(s: &str) -> Vec<u8> {
    (0..s.len())
        .step_by(2)
        .map(|i| u8::from_str_radix(&s[i..i + 2], 16).unwrap())
        .collect()
}

fn hexe(b: &[u8]) -> String {
    b.iter().map(|x| format!("{:02x}", x)).collect()
}

const TX: &str = "0100000002000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f0000000000ffffffff202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f0100000000feffffff0200f2052a010000000151e803000000000000015200000000";

// (scriptCode, hash type, digest from the Python model)
const CASES: &[(&str, u8, &str)] = &[
    ("2102abababababababababababababababababababababababababababababababababac", 0x01,
     "6c7ccfe86f69aa1970a3d61857acbdd463b9d8462c0b0c618ef9d1f972447e21"),
    ("2102abababababababababababababababababababababababababababababababababac", 0x81,
     "a2fef52b6b76827e1917bb7141e33f7941983198fcb80bb32fd56aaa872cf9e5"),
    ("ab5105ab01", 0x01, "49641a6943baf88aabb9c17898d4b778e4f602f766288a5111bd979fe44bd030"),
    ("ab5105ab01", 0x81, "5361082994f8c69b70aebc1d7534b25386fefd36881ad3a9d7c5f183144ec7dc"),
];

#[test]
fn codeseparator_is_deleted_only_at_opcode_boundaries() {
    // <push 33: 0x02 then 32 bytes of 0xab> OP_CODESEPARATOR OP_CHECKSIG
    let mut key_push = vec![0x21, 0x02];
    key_push.extend_from_slice(&[0xab; 32]);
    let mut script = key_push.clone();
    script.extend_from_slice(&[0xab, 0xac]);
    let mut want = key_push;
    want.push(0xac);
    assert_eq!(find_and_delete(&script, &[0xab]), want);
}

#[test]
fn a_truncated_push_is_kept_as_v01_keeps_it() {
    assert_eq!(hexe(&find_and_delete(&hexd("ab5105ab01"), &[0xab])), "5105ab01");
}

#[test]
fn signature_hash_matches_the_python_model() {
    let raw = hexd(TX);
    let (tx, used) = parse_tx(&raw, 0);
    assert_eq!(used, raw.len());
    for (sc, ht, want) in CASES {
        assert_eq!(hexe(&signature_hash(&hexd(sc), &tx, 0, *ht)), *want, "scriptCode {} hash type {:#x}", sc, ht);
    }
}
