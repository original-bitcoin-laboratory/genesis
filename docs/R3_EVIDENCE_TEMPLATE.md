# R3 run findings — `<RUN>`

Evidence level: **JAN09-EXECUTED** (unmodified v0.1.0 `bitcoin.exe` in an isolated
VM). Raw artifacts are hashed in `EVIDENCE_MANIFEST.json` (bytes stay under the
gitignored `r3-evidence/<RUN>/`). Fill this in from the observed run; cite the
`sha256` of each supporting artifact from the manifest.

## Environment

| Field | Value |
|---|---|
| Date / operator | |
| Hypervisor | VirtualBox / Hyper-V (version) |
| Network | `172.20.0.0/24` host-only/internal, no gateway/DNS |
| mini_ircd | `172.20.0.10:6667`, hosts → `chat.freenode.net` |
| VM-A / VM-B IP | `172.20.0.1` / `172.20.0.2` |
| `bitcoin.exe` sha256 | `fbcac071d92e26d82ec917214e334bd43850c0691f113bab1d4741c9bdd30d2d` |
| Guest OS | |

## Checklist results

| # | Observation | Result (pass/fail) | Evidence file(s) → sha256 | Notes |
|---|---|:--:|---|---|
| 1 | Node starts; recognises genesis `…19d668…a8ce26f` | | `A/debug.log` → | |
| 2 | `/gen` mining produces blocks; coinbase matures (100) | | `A/debug.log`, block height | |
| 3 | VM-B connects to VM-A over the isolated net (via IRC) | | `A/debug.log`, `B/debug.log` | peer count |
| 4 | A block relays A→B and validates on B | | `B/blk0001.dat`, `B/blkindex.dat` → | |
| 5 | Transaction A→B relays and confirms | | tx id, `A/debug.log`, screenshot → | |
| 6 | Balances / UTXO change as expected | | screenshots → | |
| 7 | (opt.) Reorg on reconnect resolves to one chain | | `debug.log` reorg lines | |

## Divergences / surprises

- Record anything the released binary did that differs from the source reading
  (tag `JAN09-EXECUTED` vs the `JAN09-SOURCE` expectation), e.g. networking quirks,
  difficulty behaviour, wallet handling.

## Conclusion

One paragraph: which claims are now supported at `JAN09-EXECUTED` level, and which
remain at `MODEL`/`PORT`/`JAN09-SOURCE`.
