# Contributing

Thanks for your interest in the Original Bitcoin Laboratory. This is an **experimental research and
teaching artifact — not money** (see [`derivatives/netnode/SECURITY.md`](derivatives/netnode/SECURITY.md)).
Contributions that improve fidelity, reproducibility, tests, or documentation are welcome.

## Reporting issues and asking questions

Open an issue on the repository: <https://github.com/original-bitcoin-laboratory/genesis/issues>.
For anything that looks like a correctness or robustness problem, please include the exact command,
the chain (`nov08x` / `jan09x`), and enough detail to reproduce. Because nothing of value is at stake,
disclosure can be public.

## Development setup and tests

- **Python node:** Python 3.10+ with `cryptography` (optional `bitcoinx` enables the accelerated
  verifier). From `derivatives/`: `python -m pytest netnode/ p2p/`.
- **Rust node:** `cd derivatives/validator-rs && cargo test`.
- **Whole lab:** `python scripts/reproduce.py` re-derives both genesis blocks from source and runs
  every suite. A change should keep `reproduce.py` and `cargo test` green.

## Pull requests

1. Branch from `main` and keep changes focused.
2. Add or update tests for any behavior change; a **fidelity** change must cite a `file:line` witness
   in the primary source or the conformance documentation.
3. Do not add the 2010-era guardrails (overflow/size/script limits): the point is the undrifted
   origin, kept safe by being valueless. Fidelity fixes, tests, docs, and tooling are in scope.
4. Ensure `reproduce.py` (21/21) and `cargo test` pass, then open the PR describing what changed and
   the evidence for it.

## Scope

This project reconstructs the earliest Bitcoin as a runnable, verifiable artifact. It is not a
currency, a wallet for anything of value, or a production node, and contributions should preserve that
framing.
