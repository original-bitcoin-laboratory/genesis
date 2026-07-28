//! DoS hardening: a hostile peer that floods **malformed blocks** (which an unguarded parser would
//! panic on) is dropped for misbehavior — no panic, nothing accepted. NOT money.

use std::io::{Read, Write};
use std::net::TcpListener;
use std::thread;

use obl_validator::miner::mine;
use obl_validator::net::Node;
use obl_validator::rules::Rules;
use obl_validator::wire::frame;

const MAGIC: [u8; 4] = *b"OBLX";
const EASY: u32 = 0x207f_ffff;

#[test]
fn a_peer_flooding_malformed_blocks_is_dropped_without_panic() {
    let g = mine(&[0u8; 32], 0, EASY, 1_231_006_506, 0, &[0x51], &[], 0);

    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let addr = listener.local_addr().unwrap();
    let server = thread::spawn(move || {
        let (mut s, _) = listener.accept().unwrap();
        let mut h = [0u8; 4];
        let _ = s.read_exact(&mut h); // the client's height
        for _ in 0..12 {
            // a "block" whose payload is 3 junk bytes — would index out of bounds in a naive parser
            let _ = s.write_all(&frame("block", b"\x00\x01\x02", &MAGIC));
        }
        let _ = s.flush();
    });

    let dir = std::env::temp_dir().join(format!("obl_dos_{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    let mut b = Node::open(&dir, Rules::jan09(), 1, None, MAGIC, &g).unwrap();

    let result = b.sync_from(addr); // must not panic
    let _ = server.join();

    assert!(result.is_err()); // dropped the misbehaving peer
    assert_eq!(b.height(), 0); // accepted none of the garbage
    let _ = std::fs::remove_dir_all(&dir);
}

#[test]
fn a_peer_flooding_malformed_txs_is_dropped_without_panic() {
    // The tx ingest path (mempool.accept -> parse_tx) indexes and `Vec::with_capacity(nin)` — an
    // unguarded parser would panic on a truncated tx or a huge claimed input count. The panic-safe
    // `well_formed_tx` gate must reject these before parse_tx, scoring and dropping the peer.
    let g = mine(&[0u8; 32], 0, EASY, 1_231_006_506, 0, &[0x51], &[], 0);

    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let addr = listener.local_addr().unwrap();
    let server = thread::spawn(move || {
        let (mut s, _) = listener.accept().unwrap();
        let mut h = [0u8; 4];
        let _ = s.read_exact(&mut h);
        // truncated tx (indexes out of bounds), and a tx claiming 2^64 inputs (with_capacity overflow)
        let truncated = &[0x01u8, 0x00, 0x00, 0x00, 0x01]; // version + nin=1, then nothing
        let huge_nin = &[0x01u8, 0x00, 0x00, 0x00, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff];
        for _ in 0..6 {
            let _ = s.write_all(&frame("tx", truncated, &MAGIC));
            let _ = s.write_all(&frame("tx", huge_nin, &MAGIC));
        }
        let _ = s.flush();
    });

    let dir = std::env::temp_dir().join(format!("obl_dostx_{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    let mut b = Node::open(&dir, Rules::jan09(), 1, None, MAGIC, &g).unwrap();

    let result = b.sync_from(addr); // must not panic on any malformed tx
    let _ = server.join();

    assert!(result.is_err()); // dropped the misbehaving peer
    assert_eq!(b.mempool.len(), 0); // pooled none of the garbage
    let _ = std::fs::remove_dir_all(&dir);
}
