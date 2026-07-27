//! End-to-end, self-contained (no Python): a Rust node mines coins to a key, accepts a real signed
//! spend into the mempool (rejecting a double-spend and a bad signature), and mines the spend into a
//! block — every step validated by the native consensus + the full interpreter. NOT money.

use obl_validator::mempool::Mempool;
use obl_validator::miner::{coinbase, mine};
use obl_validator::reorg::NodeState;
use obl_validator::rules::Rules;
use obl_validator::script::{pubkey_sec, sign_input};
use obl_validator::{block_hash, dsha256, serialize_tx, Tx, TxIn, TxOut};

const EASY: u32 = 0x207f_ffff;
const PRIV: [u8; 32] = [7u8; 32];
const T: u32 = 1_231_006_506;

fn p2pk(pk: &[u8]) -> Vec<u8> {
    let mut s = vec![pk.len() as u8];
    s.extend_from_slice(pk);
    s.push(0xac); // OP_CHECKSIG
    s
}

fn push(data: &[u8]) -> Vec<u8> {
    let mut s = vec![data.len() as u8];
    s.extend_from_slice(data);
    s
}

fn spend_of(txid: [u8; 32], value: i64, spk: &[u8], priv_bytes: &[u8; 32]) -> (Tx, Vec<u8>) {
    let mut tx = Tx {
        version: 1,
        vin: vec![TxIn { prevhash: txid, n: 0, script: vec![], seq: 0xffff_ffff }],
        vout: vec![TxOut { value, script: spk.to_vec() }],
        locktime: 0,
    };
    let sig = sign_input(priv_bytes, &tx, 0, spk, 1);
    tx.vin[0].script = push(&sig);
    let raw = serialize_tx(&tx);
    (tx, raw)
}

#[test]
fn node_mines_coins_and_spends_them_through_the_mempool() {
    let spk = p2pk(&pubkey_sec(&PRIV));
    let sub = Rules::jan09().subsidy(0);
    let mut st = NodeState::new(Rules::jan09(), 1, None);

    // mine genesis (anyone-can-spend OP_1, value 0) + two coinbase blocks paying our key
    let g = mine(&[0u8; 32], 0, EASY, T, 0, &[0x51], &[], 0);
    st.add_block(&g);
    st.activate_best();
    let b1 = mine(&block_hash(&g), 1, EASY, T + 30, sub, &spk, &[], 1);
    st.add_block(&b1);
    st.activate_best();
    let b2 = mine(&block_hash(&b1), 2, EASY, T + 60, sub, &spk, &[], 2);
    st.add_block(&b2);
    st.activate_best();
    assert_eq!(st.height(), 2);

    // block-1's coinbase is now mature (2 - 1 >= 1) and in the UTXO
    let cb1_txid = dsha256(&serialize_tx(&coinbase(1, sub, &spk, 1)));
    assert!(st.utxo().contains_key(&(cb1_txid, 0)));

    // a real signed spend of it, into the mempool
    let fee = 1000i64;
    let (_spend, spend_raw) = spend_of(cb1_txid, sub - fee, &spk, &PRIV);
    let spend_txid = dsha256(&spend_raw);
    let mut mp = Mempool::new(1);
    assert_eq!(mp.accept(&spend_raw, st.utxo(), st.height()).unwrap(), fee);
    assert_eq!(mp.len(), 1);
    assert!(mp.accept(&spend_raw, st.utxo(), st.height()).is_err()); // already pooled / double-spend

    // a spend signed by the wrong key is rejected
    let (_bad, bad_raw) = spend_of(cb1_txid, sub - fee, &spk, &[9u8; 32]);
    assert!(Mempool::new(1).accept(&bad_raw, st.utxo(), st.height()).is_err());

    // assemble + mine the spend into block 3
    let (fees, extra) = {
        let selected = mp.select(st.utxo());
        assert_eq!(selected.len(), 1);
        (mp.total_fees(&selected), selected.iter().map(|e| e.tx.clone()).collect::<Vec<Tx>>())
    };
    let sub3 = Rules::jan09().subsidy(2);
    let b3 = mine(&block_hash(&b2), 3, EASY, T + 90, sub3 + fees, &spk, &extra, 3);
    st.add_block(&b3);
    st.activate_best();
    assert_eq!(st.height(), 3);

    mp.reconcile(st.utxo(), st.height());
    assert_eq!(mp.len(), 0); // mined -> out of the pool
    assert!(st.utxo().contains_key(&(spend_txid, 0))); // payee output confirmed
    assert!(!st.utxo().contains_key(&(cb1_txid, 0))); // coinbase consumed
}
