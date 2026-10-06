//! Fidelity to the January 2009 client at the points where a stranger could split the network along
//! our own implementation boundary. Mirrors netnode/test_fidelity_2009.py (6 Oct 2026). NOT money.

use std::io::Cursor;

use obl_validator::wire::{frame, read_message};
use obl_validator::{check_coinbase_value, check_transaction_2009, sum_outputs, Tx, TxIn, TxOut};

const OVERFLOW_OUT: i64 = 9_223_372_036_854_277_039; // block 74638, 15 Aug 2010
const MAGIC: [u8; 4] = [0xf9, 0xbe, 0xb4, 0xd9];

fn tx(vin: Vec<TxIn>, vout: Vec<TxOut>) -> Tx {
    Tx { version: 1, vin, vout, locktime: 0 }
}
fn spend_in() -> TxIn {
    TxIn { prevhash: [0x11; 32], n: 0, script: vec![0x51], seq: 0xffff_ffff }
}
fn coinbase_in(script: Vec<u8>) -> TxIn {
    TxIn { prevhash: [0; 32], n: 0xffff_ffff, script, seq: 0xffff_ffff }
}
fn out(v: i64) -> TxOut {
    TxOut { value: v, script: vec![0x51] }
}

#[test]
fn overflow_output_sum_wraps_as_v01() {
    let t = tx(vec![spend_in()], vec![out(OVERFLOW_OUT), out(OVERFLOW_OUT)]);
    assert_eq!(sum_outputs(&t), -997_538); // int64 wrap, the Aug 2010 mechanism
    assert!(check_transaction_2009(&t, false).is_none()); // each output non-negative: passes
}

#[test]
fn check_transaction_rejects_what_v01_rejects() {
    assert!(check_transaction_2009(&tx(vec![spend_in()], vec![out(-1)]), false).is_some());
    assert!(check_transaction_2009(&tx(vec![spend_in()], vec![]), false).is_some());
    assert!(check_transaction_2009(&tx(vec![], vec![out(1)]), false).is_some());
    let null_in = TxIn { prevhash: [0; 32], n: 0xffff_ffff, script: vec![], seq: 0 };
    assert!(check_transaction_2009(&tx(vec![spend_in(), null_in], vec![out(1)]), false).is_some());
}

#[test]
fn coinbase_script_bounds_follow_the_profile() {
    let one = tx(vec![coinbase_in(vec![1])], vec![out(0)]);
    assert!(check_transaction_2009(&one, false).is_some(), "JAN09: size < 2 rejected");
    assert!(check_transaction_2009(&one, true).is_none(), "NOV08: only > 100 is checked");
    let big = tx(vec![coinbase_in(vec![0; 101])], vec![out(0)]);
    assert!(check_transaction_2009(&big, false).is_some());
    assert!(check_transaction_2009(&big, true).is_some());
}

#[test]
fn coinbase_value_rule_uses_int64_block_value() {
    assert!(check_coinbase_value(50, 50, 0, false));
    assert!(!check_coinbase_value(51, 50, 0, false));
    // GetBlockValue(nFees) = nSubsidy + nFees wraps in v0.1; it is not widened here.
    assert!(!check_coinbase_value(0, i64::MAX, 1, false));
}

#[test]
fn wire_block_up_to_max_size_others_4_mib() {
    let block = vec![0u8; 5 * 1024 * 1024];
    let got = read_message(&mut Cursor::new(frame("block", &block, &MAGIC)), &MAGIC).unwrap().unwrap();
    assert_eq!((got.0.as_str(), got.1.len()), ("block", block.len()));
    let inv = vec![0u8; 4 * 1024 * 1024 + 1];
    assert!(read_message(&mut Cursor::new(frame("inv", &inv, &MAGIC)), &MAGIC).is_err());
    let mut hdr = Vec::new();
    hdr.extend_from_slice(&MAGIC);
    let mut cmd = [0u8; 12];
    cmd[..5].copy_from_slice(b"block");
    hdr.extend_from_slice(&cmd);
    hdr.extend_from_slice(&((0x0200_0000u32 + 1).to_le_bytes()));
    hdr.extend_from_slice(&[0; 4]);
    assert!(read_message(&mut Cursor::new(hdr), &MAGIC).is_err());
}
