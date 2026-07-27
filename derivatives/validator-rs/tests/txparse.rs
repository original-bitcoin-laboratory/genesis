//! Structured-transaction + value-rule tests, cross-checked against the verified Python node.
//! NOT money.

use obl_validator::{check_coinbase_value, is_coinbase, parse_block_txs, sum_outputs};

fn hexd(s: &str) -> Vec<u8> {
    (0..s.len())
        .step_by(2)
        .map(|i| u8::from_str_radix(&s[i..i + 2], 16).unwrap())
        .collect()
}

fn hexe(b: &[u8]) -> String {
    b.iter().map(|x| format!("{:02x}", x)).collect()
}

// A genesis block (single coinbase) and a 2-tx block (coinbase + a real spend), from the Python node.
const B_GENESIS: &str = "010000000000000000000000000000000000000000000000000000000000000000000000791f94814a8946801385b403614565b3b7c729090ab608b4e2525a905e3a32ae2aab5f49ffff7f20020000000101000000010000000000000000000000000000000000000000000000000000000000000000ffffffff0400000100ffffffff010000000000000000015100000000";
const B_SPEND: &str = "01000000bbfddeb68fc87a2ddf11a48408cd49fb546f4c22497d4115eab33766bba02f735457648393f43b4374875689221f1964ddcc3ec9c07b6611ca4be64ef10c460066ab5f49ffff7f20010000000201000000010000000000000000000000000000000000000000000000000000000000000000ffffffff0402000300ffffffff0101f2052a01000000434104efc5b941837530a93126748063a246f03219d6bb9e2da2d3c28c33891816c4c50d08e9f3260a75ad91314257fdba13bf4bc92a2d8cab58ef7e35fcc280e828f9ac0000000001000000018697556150234c23292d843a1b0b36d3dd52c1180e8a1c29520eabdefb3053d4000000004948304502204aa9354709c7145aa839b83cc43a3dc2ff2ce6f48d0a63e57d47738af8b9de73022100bd6d24c13631941b02e14979d151d80e47498c02a8d5c867fa5663fb7fc78cf301ffffffff01fff1052a01000000434104efc5b941837530a93126748063a246f03219d6bb9e2da2d3c28c33891816c4c50d08e9f3260a75ad91314257fdba13bf4bc92a2d8cab58ef7e35fcc280e828f9ac00000000";

#[test]
fn parses_a_coinbase_only_block() {
    let txs = parse_block_txs(&hexd(B_GENESIS));
    assert_eq!(txs.len(), 1);
    let (tx, txid) = &txs[0];
    assert!(is_coinbase(tx));
    assert_eq!(hexe(txid), "791f94814a8946801385b403614565b3b7c729090ab608b4e2525a905e3a32ae");
    assert_eq!(tx.vin.len(), 1);
    assert_eq!(tx.vin[0].n, 0xffff_ffff);
    assert_eq!(tx.vin[0].prevhash, [0u8; 32]);
    assert_eq!(tx.vout.len(), 1);
    assert_eq!(sum_outputs(tx), 0);
}

#[test]
fn parses_a_coinbase_plus_a_real_spend() {
    let txs = parse_block_txs(&hexd(B_SPEND));
    assert_eq!(txs.len(), 2);

    let (cb, cb_txid) = &txs[0];
    assert!(is_coinbase(cb));
    assert_eq!(hexe(cb_txid), "5972ea95bc6148456989cb9af4c506b52236e4bb5d2c3c31bfa14bbff0f52437");
    assert_eq!(sum_outputs(cb), 5_000_000_001); // subsidy (50 coins) + 1 fee

    let (spend, sp_txid) = &txs[1];
    assert!(!is_coinbase(spend));
    assert_eq!(hexe(sp_txid), "9f27f17da6a776f245bb7f2fcee03612557f413f10d0e37a4a87a4df5428afa8");
    assert_eq!(spend.vin.len(), 1);
    assert_eq!(spend.vin[0].n, 0);
    assert_ne!(spend.vin[0].prevhash, [0u8; 32]); // spends a prior output, not the null outpoint
    assert!(!spend.vin[0].script.is_empty()); // a real scriptSig (signature)
    assert_eq!(sum_outputs(spend), 4_999_999_999); // input 50 coins − 1 fee

    // the coinbase claims exactly subsidy + the block's fees (JAN09 allows <=, so this passes)
    let subsidy = 5_000_000_000i64;
    let fees = 5_000_000_000i64 - sum_outputs(spend); // input value − output value
    assert!(check_coinbase_value(sum_outputs(cb), subsidy, fees, false));
}

#[test]
fn coinbase_value_rule_matches_both_chains() {
    // JAN09 (<=): may claim up to subsidy + fees
    assert!(check_coinbase_value(5_000_000_001, 5_000_000_000, 1, false));
    assert!(check_coinbase_value(5_000_000_000, 5_000_000_000, 1, false)); // claiming less is fine
    assert!(!check_coinbase_value(5_000_000_002, 5_000_000_000, 1, false)); // over-claim rejected
    // NOV08 (==): must equal exactly
    assert!(check_coinbase_value(5_000_000_001, 5_000_000_000, 1, true));
    assert!(!check_coinbase_value(5_000_000_000, 5_000_000_000, 1, true)); // under-claim rejected
}
