| # | Axis | v0.1.0 | BTC | BCH | BSV | XEC | BTG |
|--:|:--|:--|:--|:--|:--|:--|:--|
| 1 | Best-chain selection | height | most-work | most-work | most-work | most-work+avalanche | most-work |
| 2 | Block-size consensus rule | no-dedicated-cap | 1mb+weight | abla-dynamic | no-consensus-cap | 32mb | 1mb+weight |
| 3 | Script opcode vocabulary | broad | restricted | partial-restore | broad | partial-restore | restricted |
| 4 | Script-number operand width | unbounded-openssl | 4-byte | large-bigint | 32mb-limit | 8-byte | 4-byte |
| 5 | Script element-size limit | none | 520-byte | 10000-byte | none | 520-byte | 520-byte |
| 6 | Signature encoding | lenient-openssl | strict-der | strict-der | strict-der | strict-der | strict-der |
| 7 | Output-value range check | none | moneyrange | moneyrange | moneyrange | moneyrange | moneyrange |
| 8 | Signature scheme | ecdsa-only | ecdsa+schnorr | ecdsa+schnorr | ecdsa-only | ecdsa+schnorr | ecdsa-only |
| 9 | Pay-to-Script-Hash (P2SH) | none | p2sh | p2sh | none | p2sh | p2sh |
| 10 | Segregated witness | none | segwit | none | none | none | segwit |
| 11 | Taproot output type | none | taproot | none | none | none | none |
| 12 | Timelock opcodes | nops | cltv+csv | cltv+csv | nops | cltv+csv | cltv+csv |
| 13 | Difficulty-adjustment algorithm | 2016-block-retarget | 2016-block-retarget | asert | daa-cw144 | asert+rtt | lwma |
| 14 | Replay protection | none | none | forkid | forkid | forkid | forkid |
| 15 | Transaction ordering in a block | topological | topological | ctor | topological | ctor | topological |
| 16 | Initial block subsidy | 50 | 50 | 50 | 50 | 50 | 50 |
| 17 | Target block spacing | 10-min | 10-min | 10-min | 10-min | 10-min | 10-min |
| 18 | Coinbase height commitment | not-required | required | required | required | required | required |
| 19 | Proof-of-work function | sha256d | sha256d | sha256d | sha256d | sha256d | equihash-btg |
