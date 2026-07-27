//! `obl-validate` — validate an X-chain block (hex) with the Rust port. NOT money.
//!
//!   obl-validate <HEX_BLOCK>          # or pipe the hex on stdin
//!
//! Prints the context-free verdict + block facts (block hash, merkle root, tx count, PoW).

use std::io::Read;

use obl_validator::validate_context_free;

fn hex_decode(s: &str) -> Result<Vec<u8>, String> {
    let s = s.trim();
    if s.len() % 2 != 0 {
        return Err("odd-length hex".into());
    }
    (0..s.len())
        .step_by(2)
        .map(|i| u8::from_str_radix(&s[i..i + 2], 16).map_err(|e| e.to_string()))
        .collect()
}

fn hex_encode(b: &[u8]) -> String {
    b.iter().map(|x| format!("{:02x}", x)).collect()
}

fn main() {
    let hex = match std::env::args().nth(1) {
        Some(a) => a,
        None => {
            let mut s = String::new();
            std::io::stdin().read_to_string(&mut s).expect("read stdin");
            s
        }
    };
    let raw = match hex_decode(&hex) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("bad hex: {e}");
            std::process::exit(2);
        }
    };
    match validate_context_free(&raw) {
        Ok(s) => {
            println!("valid        : yes  (context-free: structure + merkle commitment)");
            println!("block_hash   : {}", hex_encode(&s.block_hash));
            println!("merkle_root  : {}", hex_encode(&s.merkle_root));
            println!("transactions : {}", s.ntx);
            println!("pow_ok       : {}", s.pow_ok);
            println!("NOT money.");
        }
        Err(e) => {
            eprintln!("INVALID: {e}");
            std::process::exit(1);
        }
    }
}
