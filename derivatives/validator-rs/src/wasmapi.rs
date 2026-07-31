//! Browser-verifier FFI (`wasm32` only). Raw `extern "C"` exports marshalled by a tiny JS shim — no
//! wasm-bindgen — so the **same** validation core runs client-side. Strings cross the boundary through
//! `__alloc`/`__dealloc` and length-prefixed result buffers. Every entry point catches panics, so
//! malformed input returns a clean error object instead of trapping the instance. NOT money.

use std::panic;
use std::slice;

use serde_json::{json, Value};

// k256 pulls `getrandom` transitively, but the verifier never signs (verification and the crate's
// deterministic RFC6979 signing never draw randomness). Register a stub so nothing links wasm-bindgen
// via `getrandom/js`; if a signing path were ever reached it would error loudly, never silently
// producing weak randomness. NOT money.
getrandom::register_custom_getrandom!(no_randomness);
fn no_randomness(_buf: &mut [u8]) -> Result<(), getrandom::Error> {
    Err(getrandom::Error::UNSUPPORTED)
}

use crate::eval;
use crate::script;
use crate::{
    block_hash, is_coinbase, merkle_root, parse_block_txs, parse_tx, pow_ok, sum_outputs,
    target_from_bits, validate_context_free,
};

// ---- memory marshaling ------------------------------------------------------------

/// Allocate `len` bytes (exact capacity) for the JS side to fill; returns a pointer into wasm memory.
#[no_mangle]
pub extern "C" fn __alloc(len: usize) -> *mut u8 {
    let boxed = vec![0u8; len].into_boxed_slice(); // capacity == len, so __dealloc is sound
    let ptr = boxed.as_ptr() as *mut u8;
    std::mem::forget(boxed);
    ptr
}

/// Free a buffer from `__alloc`, or a result buffer (pass its exact total length).
///
/// # Safety
/// `ptr`/`len` must name a buffer previously produced by `__alloc` or `pack` and not yet freed.
#[no_mangle]
pub unsafe extern "C" fn __dealloc(ptr: *mut u8, len: usize) {
    if !ptr.is_null() && len != 0 {
        drop(Box::from_raw(slice::from_raw_parts_mut(ptr, len)));
    }
}

/// Pack a result string as `[u32 LE len][utf8]`; returns its pointer. JS reads the length, copies the
/// JSON, then calls `__dealloc(ptr, 4 + len)`.
fn pack(s: String) -> *mut u8 {
    let bytes = s.into_bytes();
    let mut buf = Vec::with_capacity(4 + bytes.len());
    buf.extend_from_slice(&(bytes.len() as u32).to_le_bytes());
    buf.extend_from_slice(&bytes);
    let boxed = buf.into_boxed_slice();
    let ptr = boxed.as_ptr() as *mut u8;
    std::mem::forget(boxed);
    ptr
}

fn input(ptr: *const u8, len: usize) -> String {
    let s = unsafe { slice::from_raw_parts(ptr, len) };
    String::from_utf8_lossy(s).into_owned()
}

fn hex_decode(s: &str) -> Result<Vec<u8>, String> {
    let cleaned: String = s.chars().filter(|c| !c.is_whitespace()).collect();
    let cleaned = cleaned.strip_prefix("0x").unwrap_or(&cleaned);
    if cleaned.len() % 2 != 0 {
        return Err("hex has an odd number of digits".into());
    }
    (0..cleaned.len())
        .step_by(2)
        .map(|i| u8::from_str_radix(&cleaned[i..i + 2], 16).map_err(|_| "invalid hex digit".to_string()))
        .collect()
}

fn hex_encode(b: &[u8]) -> String {
    let mut s = String::with_capacity(b.len() * 2);
    for &x in b {
        s.push_str(&format!("{:02x}", x));
    }
    s
}

/// Internal little-endian hash bytes -> conventional big-endian display hex.
fn rev_hex(b: &[u8]) -> String {
    let mut v = b.to_vec();
    v.reverse();
    hex_encode(&v)
}

fn err(msg: &str) -> String {
    json!({ "ok": false, "error": msg, "not_money": true }).to_string()
}

/// Run `f`, turning any panic (e.g. a truncated byte stream) into a clean error object.
fn guard<F: FnOnce() -> String + panic::UnwindSafe>(f: F) -> String {
    panic::catch_unwind(f).unwrap_or_else(|_| err("malformed input (could not parse the bytes)"))
}

// ---- exported verifiers -----------------------------------------------------------

/// Verify a raw block (hex): recompute the block hash and merkle root, check the merkle commitment,
/// the coinbase placement, and the proof-of-work, and summarise every transaction.
#[no_mangle]
pub extern "C" fn verify_block(ptr: *const u8, len: usize) -> *mut u8 {
    let hexs = input(ptr, len);
    pack(guard(move || {
        let raw = match hex_decode(&hexs) {
            Ok(r) => r,
            Err(e) => return err(&e),
        };
        if raw.len() < 80 {
            return err("shorter than an 80-byte block header");
        }
        let bits = u32::from_le_bytes(raw[72..76].try_into().unwrap());
        let header = json!({
            "version": u32::from_le_bytes(raw[0..4].try_into().unwrap()),
            "prev": rev_hex(&raw[4..36]),
            "merkle_root": rev_hex(&raw[36..68]),
            "time": u32::from_le_bytes(raw[68..72].try_into().unwrap()),
            "bits": format!("{:#010x}", bits),
            "nonce": u32::from_le_bytes(raw[76..80].try_into().unwrap()),
        });
        let bh = rev_hex(&block_hash(&raw));
        let pow = pow_ok(&raw, bits);
        let target = hex_encode(&target_from_bits(bits));
        if raw.len() < 81 {
            return json!({
                "ok": false, "not_money": true, "block_hash": bh, "header": header,
                "pow_ok": pow, "target": target,
                "error": "header only — no transactions in this input",
            })
            .to_string();
        }
        match validate_context_free(&raw) {
            Ok(sum) => {
                let txs: Vec<Value> = parse_block_txs(&raw)
                    .iter()
                    .map(|(tx, txid)| {
                        json!({
                            "txid": rev_hex(txid),
                            "coinbase": is_coinbase(tx),
                            "vin": tx.vin.len(),
                            "vout": tx.vout.len(),
                            "out_total": sum_outputs(tx),
                        })
                    })
                    .collect();
                json!({
                    "ok": true, "not_money": true, "block_hash": bh, "header": header,
                    "merkle_recomputed": rev_hex(&sum.merkle_root), "merkle_ok": true,
                    "pow_ok": sum.pow_ok, "target": target, "ntx": sum.ntx, "txs": txs,
                })
                .to_string()
            }
            Err(e) => {
                // Structural/merkle failure: still show the recomputed root so the mismatch is visible.
                let mr = rev_hex(&merkle_root(&raw));
                json!({
                    "ok": false, "not_money": true, "block_hash": bh, "header": header,
                    "merkle_recomputed": mr, "merkle_ok": mr == rev_hex(&raw[36..68]),
                    "pow_ok": pow, "target": target, "error": e,
                })
                .to_string()
            }
        }
    }))
}

/// Execute a single script (hex) with no signature checker: the v0.1 interpreter runs it and reports
/// success and the final stack. For scripts WITHOUT `OP_CHECKSIG`/`OP_CHECKMULTISIG` (arithmetic,
/// hashing, flow control) — signature checks need a transaction context (see `verify_spend`).
#[no_mangle]
pub extern "C" fn run_script(ptr: *const u8, len: usize) -> *mut u8 {
    let hexs = input(ptr, len);
    pack(guard(move || {
        let script = match hex_decode(&hexs) {
            Ok(s) => s,
            Err(e) => return err(&e),
        };
        let (executed, stack) = eval::run(&script, None);
        // "success" is the v0.1 CScript::valid semantics: it executed AND left a truthy value on top.
        let ok = executed && stack.last().map(|t| eval::cast_to_bool(t)).unwrap_or(false);
        json!({
            "ok": ok, "executed": executed, "not_money": true,
            "stack": stack.iter().map(|x| hex_encode(x)).collect::<Vec<_>>(),
        })
        .to_string()
    }))
}

/// Verify a spend: `{"script_sig", "script_pubkey", "tx", "n_in"}` (hex fields). Runs scriptSig then
/// scriptPubKey with a real signature checker bound to the given transaction and input index — the
/// full P2PK / P2PKH / multisig / hash-lock / conditional predicate path.
#[no_mangle]
pub extern "C" fn verify_spend(ptr: *const u8, len: usize) -> *mut u8 {
    let s = input(ptr, len);
    pack(guard(move || {
        let v: Value = match serde_json::from_str(&s) {
            Ok(v) => v,
            Err(e) => return err(&format!("input must be a JSON object: {e}")),
        };
        let field = |k: &str| v.get(k).and_then(|x| x.as_str()).unwrap_or("");
        let sig = match hex_decode(field("script_sig")) {
            Ok(x) => x,
            Err(e) => return err(&format!("script_sig: {e}")),
        };
        let spk = match hex_decode(field("script_pubkey")) {
            Ok(x) => x,
            Err(e) => return err(&format!("script_pubkey: {e}")),
        };
        let txbytes = match hex_decode(field("tx")) {
            Ok(x) => x,
            Err(e) => return err(&format!("tx: {e}")),
        };
        let n_in = v.get("n_in").and_then(|x| x.as_u64()).unwrap_or(0) as usize;
        let (tx, _) = parse_tx(&txbytes, 0);
        if n_in >= tx.vin.len() {
            return err("n_in is out of range for this transaction");
        }
        json!({ "ok": script::verify_spend(&sig, &spk, &tx, n_in), "not_money": true }).to_string()
    }))
}

/// Identify the validator core backing the page.
#[no_mangle]
pub extern "C" fn version() -> *mut u8 {
    pack(json!({ "crate": "obl-validator", "version": env!("CARGO_PKG_VERSION"), "not_money": true }).to_string())
}
