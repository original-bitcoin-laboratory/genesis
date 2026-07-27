//! Spend verification: run the **real v0.1 interpreter** over `scriptSig · OP_CODESEPARATOR ·
//! scriptPubKey` (exactly as `VerifySignature` does), with a signature checker that computes the
//! v0.1 sighash and verifies ECDSA. Any script the chains use — bare P2PK, P2PKH, multisig, or an
//! arbitrary script — goes through the full engine, not a template. NOT money.
//!
//! **Byte-faithful to v0.1's lenient (pre-BIP66) OpenSSL semantics:** the signature is normalized to
//! low-S before verifying, so a high-S (malleated) signature verifies the same, exactly as OpenSSL
//! accepts both.

use k256::ecdsa::signature::hazmat::{PrehashSigner, PrehashVerifier};
use k256::ecdsa::{Signature, SigningKey, VerifyingKey};

use crate::eval::{valid, SigCheck};
use crate::sighash::signature_hash;
use crate::Tx;

const OP_CODESEPARATOR: u8 = 0xab;

/// The uncompressed SEC public key (65 bytes) for a 32-byte secret — an "address" for bare P2PK.
pub fn pubkey_sec(priv_bytes: &[u8; 32]) -> Vec<u8> {
    let sk = SigningKey::from_slice(priv_bytes).expect("valid secret");
    sk.verifying_key().to_encoded_point(false).as_bytes().to_vec()
}

/// Sign input `n_in` of `tx` with `priv_bytes` over `script_code` — returns the DER signature with
/// the appended hash-type byte (the scriptSig payload for a bare-P2PK spend). Low-S canonical, so
/// it verifies under both the faithful OpenSSL path and libsecp256k1.
pub fn sign_input(priv_bytes: &[u8; 32], tx: &Tx, n_in: usize, script_code: &[u8], hash_type: u8) -> Vec<u8> {
    let sk = SigningKey::from_slice(priv_bytes).expect("valid secret");
    let digest = signature_hash(script_code, tx, n_in, hash_type);
    let sig: Signature = sk.sign_prehash(&digest).expect("sign");
    let sig = sig.normalize_s().unwrap_or(sig);
    let mut out = sig.to_der().as_bytes().to_vec();
    out.push(hash_type);
    out
}

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
