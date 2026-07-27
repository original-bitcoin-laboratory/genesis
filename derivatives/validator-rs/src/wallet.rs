//! An experimental wallet for the standalone node — mirrors `netnode/nodewallet.py`. NOT money.
//!
//! Keys are secp256k1 secrets derived deterministically from a seed (so no RNG dependency). An
//! "address" is a bare-P2PK public key. The wallet discovers owned, mature coins in the node's UTXO,
//! reports a balance, and builds + signs payments. **Not** a secure store — experimental keys for a
//! valueless chain.

use std::collections::HashMap;

use k256::ecdsa::SigningKey;

use crate::chainstate::{Coin, Outpoint};
use crate::script::{pubkey_sec, sign_input};
use crate::{serialize_tx, sha256, Tx, TxIn, TxOut};

fn p2pk(pubkey: &[u8]) -> Vec<u8> {
    let mut s = vec![pubkey.len() as u8];
    s.extend_from_slice(pubkey);
    s.push(0xac); // OP_CHECKSIG
    s
}

fn p2pk_pubkey(spk: &[u8]) -> Option<&[u8]> {
    if spk.len() >= 2 && *spk.last().unwrap() == 0xac {
        let plen = spk[0] as usize;
        if plen > 0 && plen <= 75 && spk.len() == 1 + plen + 1 {
            return Some(&spk[1..1 + plen]);
        }
    }
    None
}

fn push(data: &[u8]) -> Vec<u8> {
    let mut s = vec![data.len() as u8];
    s.extend_from_slice(data);
    s
}

pub struct Wallet {
    seed: [u8; 32],
    keys: Vec<[u8; 32]>,
}

impl Wallet {
    pub fn new(seed: [u8; 32]) -> Self {
        let mut w = Wallet { seed, keys: Vec::new() };
        w.new_address();
        w
    }

    fn derive(&self, i: u32) -> [u8; 32] {
        let mut ctr = 0u32;
        loop {
            let mut buf = self.seed.to_vec();
            buf.extend_from_slice(&i.to_le_bytes());
            buf.extend_from_slice(&ctr.to_le_bytes());
            let k = sha256(&buf);
            if SigningKey::from_slice(&k).is_ok() {
                return k;
            }
            ctr += 1; // a hash that isn't a valid scalar is astronomically rare
        }
    }

    /// Generate a fresh receive address (returns the SEC public key).
    pub fn new_address(&mut self) -> Vec<u8> {
        let k = self.derive(self.keys.len() as u32);
        self.keys.push(k);
        pubkey_sec(&k)
    }

    /// A coinbase/payout scriptPubKey paying our primary key (bare P2PK).
    pub fn receive_spk(&self) -> Vec<u8> {
        p2pk(&pubkey_sec(&self.keys[0]))
    }

    fn key_for(&self, pubkey: &[u8]) -> Option<[u8; 32]> {
        self.keys.iter().find(|k| pubkey_sec(k) == pubkey).copied()
    }

    fn owned_key(&self, spk: &[u8]) -> Option<[u8; 32]> {
        p2pk_pubkey(spk).and_then(|pk| self.key_for(pk))
    }

    fn spendable(&self, coin: &Coin, height: i64, maturity: i64) -> bool {
        self.owned_key(&coin.spk).is_some()
            && !(coin.coinbase && coin.height >= 0 && height - coin.height < maturity)
    }

    pub fn balance(&self, utxo: &HashMap<Outpoint, Coin>, height: i64, maturity: i64) -> i64 {
        utxo.values().filter(|c| self.spendable(c, height, maturity)).map(|c| c.value).sum()
    }

    /// Build + sign a payment of `amount` (+`fee`) to `to_pubkey`, change back to self. Returns raw
    /// tx bytes, or an error if the spendable balance is short.
    pub fn create_payment(
        &self,
        utxo: &HashMap<Outpoint, Coin>,
        height: i64,
        maturity: i64,
        to_pubkey: &[u8],
        amount: i64,
        fee: i64,
    ) -> Result<Vec<u8>, &'static str> {
        if amount < 0 || fee < 0 {
            return Err("negative amount/fee");
        }
        let mut coins: Vec<(Outpoint, i64, [u8; 32], Vec<u8>)> = Vec::new();
        for (op, c) in utxo {
            if let Some(k) = self.owned_key(&c.spk) {
                if !(c.coinbase && c.height >= 0 && height - c.height < maturity) {
                    coins.push((*op, c.value, k, c.spk.clone()));
                }
            }
        }
        coins.sort_by_key(|c| std::cmp::Reverse(c.1)); // largest-first coin selection
        let target = amount + fee;
        let mut selected = Vec::new();
        let mut sum = 0i64;
        for c in coins {
            if sum >= target {
                break;
            }
            sum += c.1;
            selected.push(c);
        }
        if sum < target {
            return Err("insufficient funds");
        }
        let mut vout = vec![TxOut { value: amount, script: p2pk(to_pubkey) }];
        let change = sum - target;
        if change > 0 {
            vout.push(TxOut { value: change, script: self.receive_spk() });
        }
        let vin: Vec<TxIn> = selected
            .iter()
            .map(|c| TxIn { prevhash: c.0 .0, n: c.0 .1, script: vec![], seq: 0xffff_ffff })
            .collect();
        let mut tx = Tx { version: 1, vin, vout, locktime: 0 };
        for (i, c) in selected.iter().enumerate() {
            let sig = sign_input(&c.2, &tx, i, &c.3, 1); // SIGHASH_ALL clears other inputs' scripts
            tx.vin[i].script = push(&sig);
        }
        Ok(serialize_tx(&tx))
    }
}
