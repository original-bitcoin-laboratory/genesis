//! `addr` gossip / peer discovery over real TCP: node B, connecting to A, learns A's own advertised
//! address *and* the peers A already knows — the primitive a fresh node uses to find the network.
//! NOT money.

use std::net::TcpListener;
use std::thread;

use obl_validator::miner::mine;
use obl_validator::net::Node;
use obl_validator::rules::Rules;

const EASY: u32 = 0x207f_ffff;
const MAGIC: [u8; 4] = *b"OBLX";

#[test]
fn a_node_learns_peers_via_addr_gossip() {
    let base = std::env::temp_dir().join(format!("obl_disc_{}", std::process::id()));
    let (dir_a, dir_b) = (base.join("a"), base.join("b"));
    let _ = std::fs::remove_dir_all(&base);
    let g = mine(&[0u8; 32], 0, EASY, 1_231_006_506, 0, &[0x51], &[], 0);

    // A advertises itself and already knows one other peer
    let mut a = Node::open(&dir_a, Rules::jan09(), 1, None, MAGIC, &g).unwrap();
    a.set_advertise("198.51.100.7", 18009);
    a.add_peer("203.0.113.9", 18009);

    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let addr = listener.local_addr().unwrap();
    let server = thread::spawn(move || {
        let (mut stream, _) = listener.accept().unwrap();
        a.serve(&mut stream).unwrap();
    });

    // B connects to A and gossips
    let mut b = Node::open(&dir_b, Rules::jan09(), 1, None, MAGIC, &g).unwrap();
    assert!(b.known_peers().is_empty());
    b.sync_from(addr).unwrap();
    server.join().unwrap();

    let learned = b.known_peers();
    assert!(learned.contains(&("198.51.100.7".to_string(), 18009))); // A's own address
    assert!(learned.contains(&("203.0.113.9".to_string(), 18009))); // the peer A knew
    let _ = std::fs::remove_dir_all(&base);
}
