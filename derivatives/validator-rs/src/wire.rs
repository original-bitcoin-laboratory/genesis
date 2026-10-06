//! Hardened message framing for the standalone node — mirrors `netnode/wire.py`. NOT money.
//!
//! `[magic:4][command:12][length:4 LE][checksum:4][payload]`, where checksum is the first 4 bytes
//! of the payload's double-SHA-256. A size cap rejects oversize frames; a bad magic or checksum is
//! an error. Works over anything `Read`/`Write` (a `TcpStream`, a `Cursor`, …).

use std::io::{self, Read};

use crate::dsha256;

pub const MAX_MESSAGE_SIZE: usize = 4 * 1024 * 1024;
/// A `block` may carry up to `MAX_SIZE` (32 MiB): v0.1's CheckBlock accepts blocks that large.
/// Mirrors netnode wire.max_payload (6 Oct 2026, test_fidelity_2009.py). Others keep 4 MiB.
pub const MAX_BLOCK_MESSAGE_SIZE: usize = crate::MAX_SIZE;

pub fn max_payload(command: &str) -> usize {
    if command == "block" {
        MAX_BLOCK_MESSAGE_SIZE
    } else {
        MAX_MESSAGE_SIZE
    }
}

fn checksum(payload: &[u8]) -> [u8; 4] {
    let h = dsha256(payload);
    [h[0], h[1], h[2], h[3]]
}

/// Build a framed message.
pub fn frame(command: &str, payload: &[u8], magic: &[u8; 4]) -> Vec<u8> {
    let mut cmd = [0u8; 12];
    let cb = command.as_bytes();
    let n = cb.len().min(12);
    cmd[..n].copy_from_slice(&cb[..n]);
    let mut out = Vec::with_capacity(24 + payload.len());
    out.extend_from_slice(magic);
    out.extend_from_slice(&cmd);
    out.extend_from_slice(&(payload.len() as u32).to_le_bytes());
    out.extend_from_slice(&checksum(payload));
    out.extend_from_slice(payload);
    out
}

/// Read one framed message. `Ok(None)` on a clean end-of-stream; `Err` on tamper / oversize / bad
/// magic.
pub fn read_message<R: Read>(r: &mut R, magic: &[u8; 4]) -> io::Result<Option<(String, Vec<u8>)>> {
    let mut hdr = [0u8; 24];
    match r.read_exact(&mut hdr) {
        Ok(()) => {}
        Err(e) if e.kind() == io::ErrorKind::UnexpectedEof => return Ok(None),
        Err(e) => return Err(e),
    }
    if &hdr[0..4] != magic {
        return Err(io::Error::new(io::ErrorKind::InvalidData, "bad magic"));
    }
    let command = String::from_utf8_lossy(&hdr[4..16]).trim_end_matches('\0').to_string();
    let len = u32::from_le_bytes(hdr[16..20].try_into().unwrap()) as usize;
    if len > max_payload(&command) {
        return Err(io::Error::new(io::ErrorKind::InvalidData, "message too large"));
    }
    let expect = [hdr[20], hdr[21], hdr[22], hdr[23]];
    let mut payload = vec![0u8; len];
    r.read_exact(&mut payload)?;
    if checksum(&payload) != expect {
        return Err(io::Error::new(io::ErrorKind::InvalidData, "bad checksum"));
    }
    Ok(Some((command, payload)))
}
