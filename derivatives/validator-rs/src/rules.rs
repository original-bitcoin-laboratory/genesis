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

/// Consensus parameters. `strict` is the coinbase-value rule (NOV08 `==`, JAN09 `<=`).
#[derive(Clone)]
pub struct Rules {
    pub encoding: Pow,
    pub strict: bool,
    pub subsidy0: i64,
    pub halving: i64,
}

impl Rules {
    /// JAN09 (v0.1.0): compact PoW, `<=` coinbase rule, 50‑coin subsidy halving every 210 000.
    pub fn jan09() -> Self {
        Rules { encoding: Pow::Compact, strict: false, subsidy0: 50 * 100_000_000, halving: 210_000 }
    }

    /// NOV08 counterfactual: leading-zero-bits PoW, `==` coinbase rule, 100‑coin subsidy
    /// (COIN = 1e6) halving every 100 000.
    pub fn nov08() -> Self {
        Rules { encoding: Pow::LeadingZeroBits, strict: true, subsidy0: 100 * 1_000_000, halving: 100_000 }
    }

    /// `GetBlockValue(height)` — the subsidy created by the block at `height`.
    pub fn subsidy(&self, height: i64) -> i64 {
        if height < 0 {
            return 0;
        }
        self.subsidy0 >> (height / self.halving)
    }
}
