//! A minimal **localhost** control interface for the node — mirrors `netnode/rpc.py`. NOT money.
//!
//! A line protocol (no JSON dependency): each request is one line `METHOD [args...]`, each reply one
//! line `OK ...` / `ERR ...`. **No authentication** — bind to loopback only, on a trusted machine.
//! Methods: `getinfo`, `getnewaddress`, `getbalance`, `send <pubkey_hex> <amount> [fee]`.

use std::io::{self, BufRead, BufReader, Write};
use std::net::TcpStream;

use crate::net::Node;

fn hex(b: &[u8]) -> String {
    b.iter().map(|x| format!("{:02x}", x)).collect()
}

fn unhex(s: &str) -> Option<Vec<u8>> {
    if s.len() % 2 != 0 {
        return None;
    }
    (0..s.len()).step_by(2).map(|i| u8::from_str_radix(&s[i..i + 2], 16).ok()).collect()
}

/// Handle one request line, returning the response line (without the trailing newline).
pub fn handle(node: &mut Node, line: &str) -> String {
    let mut it = line.split_whitespace();
    match it.next() {
        Some("getinfo") => {
            format!("OK height={} mempool={} money=false", node.height(), node.mempool.len())
        }
        Some("getnewaddress") => match node.wallet_new_address() {
            Some(pk) => format!("OK {}", hex(&pk)),
            None => "ERR no wallet".into(),
        },
        Some("getbalance") => match node.wallet_balance() {
            Some(b) => format!("OK {b}"),
            None => "ERR no wallet".into(),
        },
        Some("send") => {
            let to = it.next().and_then(unhex);
            let amount = it.next().and_then(|s| s.parse::<i64>().ok());
            let fee = it.next().and_then(|s| s.parse::<i64>().ok()).unwrap_or(0);
            match (to, amount) {
                (Some(to), Some(amount)) => match node.wallet_send(&to, amount, fee) {
                    Ok(txid) => format!("OK {}", hex(&txid)),
                    Err(e) => format!("ERR {e}"),
                },
                _ => "ERR usage: send <pubkey_hex> <amount> [fee]".into(),
            }
        }
        Some(m) => format!("ERR unknown method: {m}"),
        None => "ERR empty".into(),
    }
}

/// Serve the control interface over one connection (loopback only): read request lines, reply.
pub fn serve(node: &mut Node, stream: TcpStream) -> io::Result<()> {
    let mut reader = BufReader::new(stream.try_clone()?);
    let mut writer = stream;
    let mut line = String::new();
    loop {
        line.clear();
        if reader.read_line(&mut line)? == 0 {
            break; // client closed
        }
        let resp = handle(node, line.trim_end());
        writer.write_all(resp.as_bytes())?;
        writer.write_all(b"\n")?;
        writer.flush()?;
    }
    Ok(())
}
