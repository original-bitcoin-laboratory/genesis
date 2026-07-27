//! Two Rust nodes relay a transaction over real TCP: node A mines a chain, pools a real signed
//! spend, and serves; node B syncs the blocks *and* requests the mempool tx (inv → getdata → tx),
//! validating it into its own mempool against the just-synced UTXO. NOT money.

use std::net::TcpListener;
use std::thread;

use obl_validator::miner::{coinbase, mine};
use obl_validator::net::Node;
use obl_validator::rules::Rules;
use obl_validator::script::{pubkey_sec, sign_input};
use obl_validator::{block_hash, dsha256, serialize_tx, Tx, TxIn, TxOut};

const EASY: u32 = 0x207f_ffff;
const PRIV: [u8; 32] = [7u8; 32];
const T: u32 = 1_231_006_506;
const MAGIC: [u8; 4] = *b"OBLX";

fn p2pk(pk: &[u8]) -> Vec<u8> {
    let mut s = vec![pk.len() as u8];
    s.extend_from_slice(pk);
    s.push(0xac);
    s
}

fn push(data: &[u8]) -> Vec<u8> {
    let mut s = vec![data.len() as u8];
    s.extend_from_slice(data);
    s
}

#[test]
fn two_nodes_relay_a_transaction_over_tcp() {
    let spk = p2pk(&pubkey_sec(&PRIV));
    let sub = Rules::jan09().subsidy(0);
    let base = std::env::temp_dir().join(format!("obl_relay_{}", std::process::id()));
    let (dir_a, dir_b) = (base.join("a"), base.join("b"));
    let _ = std::fs::remove_dir_all(&base);

    // A: mine genesis + two coinbase blocks paying our key
    let g = mine(&[0u8; 32], 0, EASY, T, 0, &[0x51], &[], 0);
    let mut a = Node::open(&dir_a, Rules::jan09(), 1, None, MAGIC, &g).unwrap();
    let b1 = mine(&block_hash(&g), 1, EASY, T + 30, sub, &spk, &[], 1);
    a.submit_block(&b1).unwrap();
    let b2 = mine(&block_hash(&b1), 2, EASY, T + 60, sub, &spk, &[], 2);
    a.submit_block(&b2).unwrap();
    assert_eq!(a.height(), 2);

    // A: pool a real signed spend of block-1's (now mature) coinbase
    let cb1_txid = dsha256(&serialize_tx(&coinbase(1, sub, &spk, 1)));
    let mut spend = Tx {
        version: 1,
        vin: vec![TxIn { prevhash: cb1_txid, n: 0, script: vec![], seq: 0xffff_ffff }],
        vout: vec![TxOut { value: sub - 1000, script: spk.clone() }],
        locktime: 0,
    };
    spend.vin[0].script = push(&sign_input(&PRIV, &spend, 0, &spk, 1));
    let spend_raw = serialize_tx(&spend);
    let spend_txid = dsha256(&spend_raw);
    a.submit_tx(&spend_raw).unwrap();
    assert_eq!(a.mempool.len(), 1);

    let (a_height, a_tip) = (a.height(), a.tip());
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let addr = listener.local_addr().unwrap();
    let server = thread::spawn(move || {
        let (mut stream, _) = listener.accept().unwrap();
        a.serve(&mut stream).unwrap();
    });

    // B: start at genesis, sync — pulling the blocks and then the mempool tx
    let mut b = Node::open(&dir_b, Rules::jan09(), 1, None, MAGIC, &g).unwrap();
    b.sync_from(addr).unwrap();
    server.join().unwrap();

    assert_eq!(b.height(), a_height); // caught up on blocks
    assert_eq!(b.tip(), a_tip);
    assert!(b.mempool.has(&spend_txid)); // …and received + validated the relayed transaction
    let _ = std::fs::remove_dir_all(&base);
}
