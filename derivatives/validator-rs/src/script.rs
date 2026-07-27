//! Spend verification: run the **real v0.1 interpreter** over `scriptSig · OP_CODESEPARATOR ·
//! scriptPubKey` (exactly as `VerifySignature` does), with a signature checker that computes the
//! v0.1 sighash and verifies ECDSA. Any script the chains use — bare P2PK, P2PKH, multisig, or an
//! arbitrary script — goes through the full engine, not a template. NOT money.
//!
//! **Byte-faithful to v0.1's lenient (pre-BIP66) OpenSSL semantics:** the signature is normalized to
//! low-S before verifying, so a high-S (malleated) signature verifies the same, exactly as OpenSSL
//! accepts both.

use k256::ecdsa::signature::hazmat::PrehashVerifier;
use k256::ecdsa::{Signature, VerifyingKey};

use crate::eval::{valid, SigCheck};
use crate::sighash::signature_hash;
use crate::Tx;

const OP_CODESEPARATOR: u8 = 0xab;

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

/// The interpreter's signature hook for a specific input of a specific transaction.
struct TxChecker<'a> {
    tx: &'a Tx,
    n_in: usize,
}

impl<'a> SigCheck for TxChecker<'a> {
    fn check_sig(&self, sig: &[u8], pubkey: &[u8], subscript: &[u8]) -> bool {
        if sig.is_empty() {
            return false;
        }
        let (der, ht) = sig.split_at(sig.len() - 1); // last byte is the hash type
        let digest = signature_hash(subscript, self.tx, self.n_in, ht[0]);
        ecdsa_verify(pubkey, der, &digest)
    }
}

/// True iff `script_sig` satisfies `spk` for input `n_in` of `tx` — by running the full v0.1
/// interpreter over `scriptSig · OP_CODESEPARATOR · scriptPubKey`.
pub fn verify_spend(script_sig: &[u8], spk: &[u8], tx: &Tx, n_in: usize) -> bool {
    let mut combined = Vec::with_capacity(script_sig.len() + 1 + spk.len());
    combined.extend_from_slice(script_sig);
    combined.push(OP_CODESEPARATOR);
    combined.extend_from_slice(spk);
    valid(&combined, Some(&TxChecker { tx, n_in }))
}
