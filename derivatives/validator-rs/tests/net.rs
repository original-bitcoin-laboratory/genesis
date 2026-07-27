//! Standalone-node transport tests: the hardened wire round-trips and rejects tampering; the block
//! store survives a crash-truncated tail; and **two Rust nodes sync a real signed chain over TCP**
//! (every block re-validated by the native consensus) and reload it from disk on restart. NOT money.

use std::io::Cursor;
use std::net::TcpListener;
use std::thread;

use obl_validator::net::Node;
use obl_validator::rules::Rules;
use obl_validator::store::BlockStore;
use obl_validator::wire::{frame, read_message};

include!("data/state_data.rs"); // VALID: (raw_hex, height, subsidy, is_genesis, utxo_count, balance)

const MAGIC: [u8; 4] = *b"OBLX";

fn hexd(s: &str) -> Vec<u8> {
    (0..s.len())
        .step_by(2)
        .map(|i| u8::from_str_radix(&s[i..i + 2], 16).unwrap())
        .collect()
}

// ---- hardened wire ----

#[test]
fn wire_round_trips() {
    let mut c = Cursor::new(frame("block", b"hello", &MAGIC));
    let (command, payload) = read_message(&mut c, &MAGIC).unwrap().unwrap();
    assert_eq!(command, "block");
    assert_eq!(payload, b"hello");
}

#[test]
fn wire_rejects_a_tampered_checksum() {
    let mut f = frame("block", b"hello", &MAGIC);
    let n = f.len() - 1;
    f[n] ^= 0xff;
    assert!(read_message(&mut Cursor::new(f), &MAGIC).is_err());
}

#[test]
fn wire_rejects_bad_magic_and_returns_none_on_eof() {
    assert!(read_message(&mut Cursor::new(frame("x", b"y", b"AAAA")), &MAGIC).is_err());
    assert!(read_message(&mut Cursor::new(Vec::<u8>::new()), &MAGIC).unwrap().is_none());
}

// ---- crash-safe store ----

#[test]
fn store_round_trips_and_ignores_a_truncated_tail() {
    use std::io::Write;
    let dir = std::env::temp_dir().join(format!("obl_store_{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    {
        let mut s = BlockStore::open(&dir).unwrap();
        s.append(b"aaa").unwrap();
        s.append(b"bbbb").unwrap();
    }
    let expected = vec![b"aaa".to_vec(), b"bbbb".to_vec()];
    assert_eq!(BlockStore::open(&dir).unwrap().read_all().unwrap(), expected);
    // append a header claiming 10 bytes but only 3 present (a crash mid-write)
    let mut f = std::fs::OpenOptions::new().append(true).open(dir.join("blocks.dat")).unwrap();
    f.write_all(&10u32.to_le_bytes()).unwrap();
    f.write_all(b"xyz").unwrap();
    drop(f);
    assert_eq!(BlockStore::open(&dir).unwrap().read_all().unwrap(), expected); // tail ignored
    let _ = std::fs::remove_dir_all(&dir);
}

// ---- two nodes sync over real TCP + reload from disk ----

#[test]
fn two_nodes_sync_over_tcp_and_reload_from_disk() {
    let base = std::env::temp_dir().join(format!("obl_net_{}", std::process::id()));
    let (dir_a, dir_b) = (base.join("a"), base.join("b"));
    let _ = std::fs::remove_dir_all(&base);
    let genesis = hexd(VALID[0].0);

    // seed A with the whole validated (signed) chain
    let mut a = Node::open(&dir_a, Rules::jan09(), 1, None, MAGIC, &genesis).unwrap();
    for row in &VALID[1..] {
        a.state.add_block(&hexd(row.0));
    }
    a.state.activate_best();
    let (a_height, a_tip, a_bal) = (a.height(), a.tip(), a.balance());
    assert_eq!(a_height, 2);

    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let addr = listener.local_addr().unwrap();
    let server = thread::spawn(move || {
        let (mut stream, _) = listener.accept().unwrap();
        a.serve(&mut stream).unwrap();
    });

    // B starts at genesis and syncs — validating each block through the native consensus
    let mut b = Node::open(&dir_b, Rules::jan09(), 1, None, MAGIC, &genesis).unwrap();
    assert_eq!(b.height(), 0);
    b.sync_from(addr).unwrap();
    server.join().unwrap();
    assert_eq!(b.height(), a_height);
    assert_eq!(b.tip(), a_tip);
    assert_eq!(b.balance(), a_bal);

    // restart B from disk — it reloads the synced chain
    drop(b);
    let b2 = Node::open(&dir_b, Rules::jan09(), 1, None, MAGIC, &genesis).unwrap();
    assert_eq!(b2.height(), a_height);
    assert_eq!(b2.tip(), a_tip);
    let _ = std::fs::remove_dir_all(&base);
}
