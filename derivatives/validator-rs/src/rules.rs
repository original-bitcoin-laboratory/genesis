//! Chain rules the validator needs: subsidy schedule, the coinbase-value rule, and the PoW
//! encoding (mirrors `consensus.Rules` for the two X-chains). NOT money.

/// Proof-of-work target encoding.
#[derive(Clone, Copy, PartialEq)]
pub enum Pow {
    /// v0.1 / JAN09: compact `nBits` target.
    Compact,
    /// NOV08: the counterfactual "leading zero bits" encoding.
    LeadingZeroBits,
}

/// Consensus parameters. `strict` is the coinbase-value rule (NOV08 `==`, JAN09 `<=`); `min_pow` is
/// NOV08's `MINPROOFOFWORK` (the minimum leading-zero-bit count; unused for compact PoW).
#[derive(Clone)]
pub struct Rules {
    pub encoding: Pow,
    pub strict: bool,
    pub subsidy0: i64,
    pub halving: i64,
    pub min_pow: u32,
}

impl Rules {
    /// JAN09 (v0.1.0): compact PoW, `<=` coinbase rule, 50‑coin subsidy halving every 210 000.
    pub fn jan09() -> Self {
        Rules {
            encoding: Pow::Compact, strict: false,
            subsidy0: 50 * 100_000_000, halving: 210_000, min_pow: 0,
        }
    }

    /// NOV08 counterfactual: leading-zero-bits PoW (`MINPROOFOFWORK = 20`), `==` coinbase rule,
    /// 100‑coin subsidy (COIN = 1e6) halving every 100 000.
    pub fn nov08() -> Self {
        Rules {
            encoding: Pow::LeadingZeroBits, strict: true,
            subsidy0: 100 * 1_000_000, halving: 100_000, min_pow: 20,
        }
    }

    /// `GetBlockValue(height)` — the subsidy created by the block at `height`. `subsidy0 >> n` equals
    /// NOV08's explicit halving loop for `height >= 0`.
    pub fn subsidy(&self, height: i64) -> i64 {
        if height < 0 {
            return 0;
        }
        self.subsidy0 >> (height / self.halving)
    }

    /// Whether `raw`'s header meets its stated difficulty under this chain's PoW encoding —
    /// compact (`hash <= target`) for JAN09, leading-zero-bits (with the `min_pow` gate) for NOV08.
    pub fn pow_ok(&self, raw: &[u8], nbits: u32) -> bool {
        match self.encoding {
            Pow::Compact => crate::pow_ok(raw, nbits),
            Pow::LeadingZeroBits => crate::pow_ok_lzb(raw, nbits, self.min_pow),
        }
    }
}
