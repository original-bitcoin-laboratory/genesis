//! Wallet + localhost RPC end-to-end: a node mines coins to its wallet, then a client drives it over
//! the control socket — `getbalance`, `getnewaddress`, `send`, `getinfo`. NOT money.

use std::io::{BufRead, BufReader, Write};
use std::net::{TcpListener, TcpStream};
use std::thread;

use obl_validator::block_hash;
use obl_validator::miner::mine;
use obl_validator::net::Node;
use obl_validator::rpc;
use obl_validator::rules::Rules;

const EASY: u32 = 0x207f_ffff;
const MAGIC: [u8; 4] = *b"OBLX";
const T: u32 = 1_231_006_506;

fn read_line(r: &mut impl BufRead) -> String {
    let mut s = String::new();
    r.read_line(&mut s).unwrap();
    s.trim().to_string()
}

fn hex(b: &[u8]) -> String {
    b.iter().map(|x| format!("{:02x}", x)).collect()
}

#[test]
fn wallet_and_rpc_over_localhost() {
    let sub = Rules::jan09().subsidy(0);
    let dir = std::env::temp_dir().join(format!("obl_rpc_{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    let g = mine(&[0u8; 32], 0, EASY, T, 0, &[0x51], &[], 0);

    let mut node = Node::open(&dir, Rules::jan09(), 1, None, MAGIC, &g).unwrap();
    node.enable_wallet([1u8; 32]);
    let spk = node.wallet_receive_spk().unwrap();

    // mine two coinbase blocks to the wallet; block 1 matures at height 2
    let b1 = mine(&block_hash(&g), 1, EASY, T + 30, sub, &spk, &[], 1);
    node.submit_block(&b1).unwrap();
    let b2 = mine(&block_hash(&b1), 2, EASY, T + 60, sub, &spk, &[], 2);
    node.submit_block(&b2).unwrap();
    assert_eq!(node.wallet_balance().unwrap(), sub); // one matured coinbase

    let to = hex(&node.wallet_new_address().unwrap()); // a recipient (another of our addresses)

    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let addr = listener.local_addr().unwrap();
    let server = thread::spawn(move || {
        let (stream, _) = listener.accept().unwrap();
        rpc::serve(&mut node, stream).unwrap();
    });

    let mut c = TcpStream::connect(addr).unwrap();
    let mut r = BufReader::new(c.try_clone().unwrap());

    c.write_all(b"getbalance\n").unwrap();
    c.flush().unwrap();
    assert_eq!(read_line(&mut r), format!("OK {sub}"));

    c.write_all(b"getnewaddress\n").unwrap();
    c.flush().unwrap();
    let a = read_line(&mut r);
    assert!(a.starts_with("OK ") && a.len() == 3 + 130); // 65-byte uncompressed pubkey

    c.write_all(format!("send {} {} 0\n", to, sub / 2).as_bytes()).unwrap();
    c.flush().unwrap();
    let s = read_line(&mut r);
    assert!(s.starts_with("OK ") && s.len() == 3 + 64, "{s}"); // a 32-byte txid

    c.write_all(b"getinfo\n").unwrap();
    c.flush().unwrap();
    assert!(read_line(&mut r).contains("money=false"));

    drop(r); // both client handles must close for the server to see EOF
    drop(c);
    server.join().unwrap();
    let _ = std::fs::remove_dir_all(&dir);
}
