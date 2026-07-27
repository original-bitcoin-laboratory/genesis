//! Script verification for the scripts the X-chains actually use — bare **P2PK** and the
//! anyone-can-spend `OP_1` coinbase output — with real ECDSA (k256). NOT money.
//!
//! **Byte-faithful to v0.1's lenient (pre-BIP66) OpenSSL semantics:** the signature is normalized
//! to low-S before verifying, so a high-S (malleated) signature verifies the same as its canonical
//! form — exactly as OpenSSL accepts both. (Strict-DER edge cases that OpenSSL would leniently
//! accept are the one documented residual; the chains' real signatures are canonical.)
//!
//! Arbitrary scripts (a full `EvalScript` port) and P2PKH (needs RIPEMD-160) are **not** here — a
//! non-template script returns `Err("unsupported script")`; those are the remaining native-node
//! slice. The chains' transactions are bare P2PK, which this verifies.

use k256::ecdsa::signature::hazmat::PrehashVerifier;
use k256::ecdsa::{Signature, VerifyingKey};

use crate::sighash::signature_hash;
use crate::Tx;

/// Verify a DER signature over `digest`, lenient like v0.1's OpenSSL (accepts high-S).
pub fn ecdsa_verify(pubkey_sec: &[u8], der: &[u8], digest: &[u8; 32]) -> bool {
    let vk = match VerifyingKey::from_sec1_bytes(pubkey_sec) {
        Ok(v) => v,
        Err(_) => return false,
    };
    let sig = match Signature::from_der(der) {
        Ok(s) => s,
        Err(_) => return false,
    };
    let sig = sig.normalize_s().unwrap_or(sig); // low-S normalize -> OpenSSL-lenient equivalence
    vk.verify_prehash(&digest[..], &sig).is_ok()
}

/// Split a scriptSig into its data pushes, or `None` if it contains a non-push opcode.
fn parse_pushes(script: &[u8]) -> Option<Vec<Vec<u8>>> {
    let mut i = 0;
    let mut out = Vec::new();
    while i < script.len() {
        let op = script[i];
        i += 1;
        let n = if op == 0 {
            0usize
        } else if op <= 75 {
            op as usize
        } else if op == 0x4c {
            // OP_PUSHDATA1
            if i >= script.len() {
                return None;
            }
            let n = script[i] as usize;
            i += 1;
            n
        } else {
            return None; // an opcode in the scriptSig — not a simple push
        };
        if i + n > script.len() {
            return None;
        }
        out.push(script[i..i + n].to_vec());
        i += n;
    }
    Some(out)
}

/// The pubkey of a bare-P2PK scriptPubKey (`<push pubkey> OP_CHECKSIG`), else `None`.
fn p2pk_pubkey(spk: &[u8]) -> Option<Vec<u8>> {
    if spk.len() >= 2 && *spk.last().unwrap() == 0xac {
        let plen = spk[0] as usize;
        if plen > 0 && plen <= 75 && spk.len() == 1 + plen + 1 {
            return Some(spk[1..1 + plen].to_vec());
        }
    }
    None
}

/// True iff `script_sig` satisfies `spk` for input `n_in` of `tx`. Handles the templates the
/// X-chains use; any other script is `Err("unsupported script")`.
pub fn verify_spend(script_sig: &[u8], spk: &[u8], tx: &Tx, n_in: usize) -> Result<bool, &'static str> {
    if spk.len() == 1 && spk[0] == 0x51 {
        return Ok(true); // OP_1 anyone-can-spend (empty scriptSig)
    }
    if let Some(pubkey) = p2pk_pubkey(spk) {
        let pushes = match parse_pushes(script_sig) {
            Some(p) => p,
            None => return Ok(false),
        };
        if pushes.len() != 1 || pushes[0].is_empty() {
            return Ok(false);
        }
        let sig = &pushes[0];
        let (der, ht) = sig.split_at(sig.len() - 1); // last byte is the hash type
        let digest = signature_hash(spk, tx, n_in, ht[0]); // scriptCode = the P2PK scriptPubKey
        return Ok(ecdsa_verify(&pubkey, der, &digest));
    }
    Err("unsupported script")
}
