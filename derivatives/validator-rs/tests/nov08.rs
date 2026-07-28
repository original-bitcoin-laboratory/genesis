//! NOV08-X parity tests — make the second reconstruction a byte-for-byte twin, like JAN09-X.
//!
//! The Nov 2008 pre-release uses a *different* proof-of-work (leading-zero-bits, not compact) and a
//! *stricter* coinbase rule (`==`, not `<=`). These tests prove the Rust node implements both:
//!   1. it agrees with the verified Python nov08x on hash / merkle / **leading-zero-bits PoW**
//!      (golden), and the *compact* reading disagrees — so the encoding genuinely matters;
//!   2. it runs NOV08 consensus natively — mines leading-zero-bits blocks and **enforces the `==`
//!      coinbase rule** (rejecting an under-claim a `<=` chain would accept);
//!   3. two NOV08 nodes sync the chain over real TCP.
//! Vectors are generated from the deployed chain by `tools/gen_nov08_vectors.py`. NOT money.

use std::net::TcpListener;
use std::thread;

use obl_validator::miner::mine_lzb;
use obl_validator::net::Node;
use obl_validator::rules::Rules;
use obl_validator::{block_hash, merkle_root, pow_ok, pow_ok_lzb, validate_context_free};

include!("data/nov08_data.rs"); // MAGIC, GENESIS, CHAIN

fn hexd(s: &str) -> Vec<u8> {
    (0..s.len()).step_by(2).map(|i| u8::from_str_radix(&s[i..i + 2], 16).unwrap()).collect()
}
fn hexe(b: &[u8]) -> String {
    b.iter().map(|x| format!("{:02x}", x)).collect()
}

/// (1) The Rust node agrees with the Python on every NOV08 block — under leading-zero-bits PoW —
/// and the compact reading of the same `nBits` disagrees, proving the encoding is what differs.
#[test]
fn golden_nov08_leading_zero_bits_matches_python() {
    let r = Rules::nov08();
    for row in CHAIN {
        let (raw_hex, _height, nbits, bh, mr, pk, ntx) = *row;
        let raw = hexd(raw_hex);
        assert_eq!(hexe(&block_hash(&raw)), bh, "block hash");
        assert_eq!(hexe(&merkle_root(&raw)), mr, "merkle root");

        // NOV08 leading-zero-bits PoW matches the Python result exactly …
        assert_eq!(r.pow_ok(&raw, nbits), pk, "nov08 pow");
        assert_eq!(pow_ok_lzb(&raw, nbits, 20), pk, "leading-zero-bits pow");
        // … while the JAN09 *compact* reading of the same nBits does NOT accept it.
        assert!(!pow_ok(&raw, nbits), "compact reading must reject a nov08 block (encoding matters)");

        let s = validate_context_free(&raw).expect("structurally valid");
        assert_eq!(s.ntx, ntx, "tx count");
        assert_eq!(hexe(&s.block_hash), bh);
    }
}

/// (2a) The Rust node validates the *exact* chain the Python nov08x produced — leading-zero-bits
/// PoW, the retarget floor, and the 100-coin `==` coinbase rule — reaching the Python's tip.
#[test]
fn rust_node_validates_the_python_nov08_chain() {
    let dir = std::env::temp_dir().join(format!("obl_nov08_val_{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    let g = hexd(GENESIS);
    let mut node = Node::open(&dir, Rules::nov08(), 100, None, MAGIC, &g).unwrap();
    assert_eq!(node.height(), 0);
    assert_eq!(node.tip().map(|h| hexe(&h)).as_deref(), Some(CHAIN[0].3)); // genesis hash

    for row in &CHAIN[1..] {
        node.state.add_block(&hexd(row.0));
    }
    node.state.activate_best();
    assert_eq!(node.height(), (CHAIN.len() - 1) as i64, "reached the Python tip");
    assert_eq!(node.tip().map(|h| hexe(&h)).as_deref(), Some(CHAIN[CHAIN.len() - 1].3));
    let _ = std::fs::remove_dir_all(&dir);
}

/// (2b) The Rust node *mines* NOV08 blocks (leading-zero-bits) and enforces the strict `==` coinbase
/// rule: a coinbase that under-claims — which a `<=` (JAN09) chain would accept — is rejected here.
#[test]
fn rust_mines_nov08_and_enforces_the_equal_coinbase_rule() {
    let dir = std::env::temp_dir().join(format!("obl_nov08_mine_{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    let g = hexd(GENESIS);
    let r = Rules::nov08();
    let mut node = Node::open(&dir, r.clone(), 100, None, MAGIC, &g).unwrap();

    // block 1: coinbase claims EXACTLY the subsidy -> valid
    let tip = node.tip().unwrap();
    let sub1 = r.subsidy(0);
    assert_eq!(sub1, 100 * 1_000_000, "NOV08 subsidy is 100 coins at COIN=1e6");
    let b1 = mine_lzb(&tip, 1, 20, 1_226_793_700, sub1, &[0x51u8], &[], 1);
    node.submit_block(&b1).unwrap();
    assert_eq!(node.height(), 1);

    // block 2: coinbase UNDER-claims by 1 -> valid under `<=`, rejected under NOV08's `==`
    let tip1 = node.tip().unwrap();
    let sub2 = r.subsidy(1);
    let bad = mine_lzb(&tip1, 2, 20, 1_226_793_730, sub2 - 1, &[0x51u8], &[], 2);
    let bad_hash = block_hash(&bad);
    node.state.add_block(&bad);
    node.state.activate_best();
    assert_eq!(node.height(), 1, "under-claiming coinbase must not extend the chain");
    assert!(node.state.is_invalid(&bad_hash), "rejected by the NOV08 == coinbase rule");
    let _ = std::fs::remove_dir_all(&dir);
}

/// (3) Two NOV08 nodes sync the leading-zero-bits chain over real TCP — every block re-validated by
/// the native consensus (magic f00ba708, distinct from JAN09-X's f00ba709).
#[test]
fn two_nov08_nodes_sync_over_tcp() {
    let base = std::env::temp_dir().join(format!("obl_nov08_net_{}", std::process::id()));
    let (dir_a, dir_b) = (base.join("a"), base.join("b"));
    let _ = std::fs::remove_dir_all(&base);
    let g = hexd(GENESIS);

    let mut a = Node::open(&dir_a, Rules::nov08(), 100, None, MAGIC, &g).unwrap();
    for row in &CHAIN[1..] {
        a.state.add_block(&hexd(row.0));
    }
    a.state.activate_best();
    let (ah, at) = (a.height(), a.tip());
    assert_eq!(ah, (CHAIN.len() - 1) as i64);

    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let addr = listener.local_addr().unwrap();
    let server = thread::spawn(move || {
        let (mut s, _) = listener.accept().unwrap();
        a.serve(&mut s).unwrap();
    });

    let mut b = Node::open(&dir_b, Rules::nov08(), 100, None, MAGIC, &g).unwrap();
    assert_eq!(b.height(), 0);
    b.sync_from(addr).unwrap();
    server.join().unwrap();
    assert_eq!(b.height(), ah);
    assert_eq!(b.tip(), at);
    let _ = std::fs::remove_dir_all(&base);
}
