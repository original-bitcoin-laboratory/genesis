//! Golden-vector tests: verify the Rust validator against outputs from the (verified) Python node.
//! `cargo test` here is a full cross-check — SHA-256, block hashing, merkle, PoW, and structure —
//! wherever a Rust toolchain is installed. NOT money.

use obl_validator::{block_hash, merkle_root, pow_ok, sha256, validate_context_free};

fn hexd(s: &str) -> Vec<u8> {
    (0..s.len())
        .step_by(2)
        .map(|i| u8::from_str_radix(&s[i..i + 2], 16).unwrap())
        .collect()
}

fn hexe(b: &[u8]) -> String {
    b.iter().map(|x| format!("{:02x}", x)).collect()
}

#[test]
fn sha256_matches_the_standard_abc_vector() {
    assert_eq!(
        hexe(&sha256(b"abc")),
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    );
    assert_eq!(hexe(&sha256(b"")), "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
}

// (raw, block_hash, merkle_root, nbits, pow_ok, ntx) — from the verified Python (jan09x).
const VECTORS: &[(&str, &str, &str, u32, bool, u64)] = &[
    (
        "010000000000000000000000000000000000000000000000000000000000000000000000791f94814a8946801385b403614565b3b7c729090ab608b4e2525a905e3a32ae2aab5f49ffff7f20020000000101000000010000000000000000000000000000000000000000000000000000000000000000ffffffff0400000100ffffffff010000000000000000015100000000",
        "12eaeadc0fa67e8b0f991cb3406b793fef70e99f125dc7ee927fbef23d3d9d5c",
        "791f94814a8946801385b403614565b3b7c729090ab608b4e2525a905e3a32ae",
        545259519, true, 1,
    ),
    (
        "0100000012eaeadc0fa67e8b0f991cb3406b793fef70e99f125dc7ee927fbef23d3d9d5c8697556150234c23292d843a1b0b36d3dd52c1180e8a1c29520eabdefb3053d448ab5f49ffff7f20000000000101000000010000000000000000000000000000000000000000000000000000000000000000ffffffff0401000200ffffffff0100f2052a01000000434104efc5b941837530a93126748063a246f03219d6bb9e2da2d3c28c33891816c4c50d08e9f3260a75ad91314257fdba13bf4bc92a2d8cab58ef7e35fcc280e828f9ac00000000",
        "bbfddeb68fc87a2ddf11a48408cd49fb546f4c22497d4115eab33766bba02f73",
        "8697556150234c23292d843a1b0b36d3dd52c1180e8a1c29520eabdefb3053d4",
        545259519, true, 1,
    ),
    (
        "01000000bbfddeb68fc87a2ddf11a48408cd49fb546f4c22497d4115eab33766bba02f735457648393f43b4374875689221f1964ddcc3ec9c07b6611ca4be64ef10c460066ab5f49ffff7f20010000000201000000010000000000000000000000000000000000000000000000000000000000000000ffffffff0402000300ffffffff0101f2052a01000000434104efc5b941837530a93126748063a246f03219d6bb9e2da2d3c28c33891816c4c50d08e9f3260a75ad91314257fdba13bf4bc92a2d8cab58ef7e35fcc280e828f9ac0000000001000000018697556150234c23292d843a1b0b36d3dd52c1180e8a1c29520eabdefb3053d4000000004948304502204aa9354709c7145aa839b83cc43a3dc2ff2ce6f48d0a63e57d47738af8b9de73022100bd6d24c13631941b02e14979d151d80e47498c02a8d5c867fa5663fb7fc78cf301ffffffff01fff1052a01000000434104efc5b941837530a93126748063a246f03219d6bb9e2da2d3c28c33891816c4c50d08e9f3260a75ad91314257fdba13bf4bc92a2d8cab58ef7e35fcc280e828f9ac00000000",
        "9959b5d706dac795b5814f23c57df3f12b67b3931e70d8143d2c26798168262e",
        "5457648393f43b4374875689221f1964ddcc3ec9c07b6611ca4be64ef10c4600",
        545259519, true, 2,
    ),
    (
        "010000009959b5d706dac795b5814f23c57df3f12b67b3931e70d8143d2c26798168262edf9ef634633b500203c9736605e830770190662a861351dbbedb0738240a581484ab5f49ffff7f20000000000201000000010000000000000000000000000000000000000000000000000000000000000000ffffffff0403000400ffffffff0101f2052a01000000434104efc5b941837530a93126748063a246f03219d6bb9e2da2d3c28c33891816c4c50d08e9f3260a75ad91314257fdba13bf4bc92a2d8cab58ef7e35fcc280e828f9ac0000000001000000015972ea95bc6148456989cb9af4c506b52236e4bb5d2c3c31bfa14bbff0f52437000000004847304402200092689b0dc695989285fed7fcd4903df0f8124afb79d96d67bb47f59679b2b602205a47b6da3564a5c28ad1e0b39a3ec56d5cde03f46ce16e7b3ce63580c4ca558501ffffffff0100f2052a01000000434104efc5b941837530a93126748063a246f03219d6bb9e2da2d3c28c33891816c4c50d08e9f3260a75ad91314257fdba13bf4bc92a2d8cab58ef7e35fcc280e828f9ac00000000",
        "f832e386fc889ae8152acb943092cca5f281dbe0b713b253e626494944aca723",
        "df9ef634633b500203c9736605e830770190662a861351dbbedb0738240a5814",
        545259519, true, 2,
    ),
];

#[test]
fn golden_blocks_match_the_python_node() {
    for (raw_hex, bh, mr, nbits, pk, ntx) in VECTORS {
        let raw = hexd(raw_hex);
        assert_eq!(hexe(&block_hash(&raw)), *bh, "block hash");
        assert_eq!(hexe(&merkle_root(&raw)), *mr, "merkle root");
        assert_eq!(pow_ok(&raw, *nbits), *pk, "pow");
        let s = validate_context_free(&raw).expect("valid block");
        assert_eq!(s.ntx, *ntx, "tx count");
        assert_eq!(hexe(&s.block_hash), *bh);
        assert_eq!(hexe(&s.merkle_root), *mr);
    }
}

#[test]
fn tampering_is_rejected() {
    let mut raw = hexd(VECTORS[2].0); // a 2-tx block
    let good = validate_context_free(&raw);
    assert!(good.is_ok());
    raw[36] ^= 1; // corrupt the header merkle root
    assert_eq!(validate_context_free(&raw).err(), Some("merkle root mismatch"));
}
