# R3 run findings — `2026-07-31-twonode-mined-block`

Evidence level: **JAN09-EXECUTED** (unmodified v0.1.0 `bitcoin.exe` in isolated VMs).
Raw artifacts are hashed in `EVIDENCE_MANIFEST.json` (bytes stay under the gitignored
`r3-evidence/2026-07-31-twonode-mined-block/`). **NOT money.**

This run closes the one rung the earlier runs (`run1`, `run2`) left open: **block production and relay
between two real 2009 nodes.** run1/run2 established boot, genesis validation, wallet-key generation, and
the original IRC discovery path for a single node; the released miner is *peer-gated* (`while(vNodes.empty())`,
`main.cpp`), so a lone node cannot mine. Here two nodes discover each other over an isolated network, one
mines, and the other receives and accepts the block.

## Environment

| Field | Value |
|---|---|
| Date / operator | 30–31 Jul 2026 (block mined 30 Jul, VM clock) |
| Hypervisor | Oracle VirtualBox 7.2.14 |
| Network | `172.20.0.0/24` VirtualBox **Internal Network** `obl-r3`, no gateway/DNS, firewall off |
| mini_ircd | on **node A** `172.20.0.1:6667`; both VMs' `hosts` → `chat.freenode.net = 172.20.0.1` |
| VM-A / VM-B IP | `172.20.0.1` (node A, receiver) / `172.20.0.2` (node B, miner) |
| `bitcoin.exe` sha256 | `fbcac071d92e26d82ec917214e334bd43850c0691f113bab1d4741c9bdd30d2d` (+ shipped `libeay32.dll`, `mingwm10.dll`) |
| Guest OS | Windows 10 (64-bit), two VMs (one installed, then full-cloned) |

## What executed (JAN09-EXECUTED)

Two unmodified 2009 `bitcoin.exe` nodes, air-gapped, discovered each other via the original IRC path
(a bare-`\r`-terminated line handshake against a minimal in-network IRC daemon — see *Divergences*),
formed a P2P connection on port 8333, and:

| # | Observation | Result | Evidence |
|---|---|:--:|---|
| 1 | Both nodes recognise the historical genesis `000000000019d668…0a8ce26f` (Chancellor coinbase) | ✓ | `*/blk0001.dat` block 0 |
| 2 | Node B connects to node A over the isolated net (address learned via IRC: `…ff ff ac 14 00 02` = `172.20.0.2`) | ✓ | `nodeA/debug-excerpt.txt` (`received: addr`) |
| 3 | Node B **mines** block 1 at real difficulty 1 (`proof-of-work found` → `ProcessBlock: ACCEPTED`) | ✓ | `nodeB/debug-excerpt.txt` |
| 4 | Node A **receives and accepts** node B's block (`inv` → `received: block (215 B)` → `ProcessBlock: ACCEPTED`) | ✓ | `nodeA/debug-excerpt.txt` |
| 5 | Both nodes end holding the **byte-identical** two-block chain | ✓ | `nodeA/blk0001.dat` == `nodeB/blk0001.dat` (sha256 `899c94d2…78c04c2`) |

### The block, verified from the raw `blk0001.dat` bytes

`verify_r3.py` (in the evidence dir) decodes both nodes' `blk0001.dat` and confirms:

- **Block 0** = the historical genesis: hash `000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f`,
  prev = all-zero, version 1, time 1231006505, bits `1d00ffff`, nonce 2083236893, coinbase
  *"The Times 03/Jan/2009 Chancellor on brink of second bailout for banks"*. The run started from
  Satoshi's real genesis, not a lab one.
- **Block 1** (mined by node B): hash `000000005bdcfb220b87ef15367ae329af0eee8f84d4db5830631e112b16370a`,
  **prev = the genesis**, version 1, time 1785431155, bits `1d00ffff`, nonce 899943534, and its hash is a
  **valid proof-of-work below the difficulty-1 target**. This hash matches node B's `getdata for: block
  000000005bdcfb` and node A's received block.

Both nodes' 516-byte `blk0001.dat` hash identically (`899c94d2…`), so the two independent nodes agree, byte
for byte, that node B produced this block and node A accepted it.

## Divergences / surprises

- **The released client terminates IRC lines with a bare `\r`** (`irc.cpp`: `Send("NICK %s\r")`), not
  CRLF. The lab's `mini_ircd` originally read line-by-line on `\n` and so never parsed the real client's
  `NICK`/`USER`, never sent the `004` numeric, and discovery stalled before `JOIN`/`WHO`. Fixed by reading
  `readuntil(b"\r")` (commit in `derivatives/r3/`), with a regression test that now defaults to the bare-`\r`
  protocol. This is a *test-tooling* fix; the 2009 binary was unmodified.
- `GetMyExternalIP()` fails (harmless): it dials a public IP-echo host, unreachable in isolation.
- The peer-gated miner behaves exactly as the source reads: mining only began once the second node
  connected; with both miners running the VMs saturate CPU, which starves the P2P threads — turning the
  miners off is what let the already-found block relay to node A.

## Conclusion

At **JAN09-EXECUTED** level this run supports **block production and relay by the unmodified 2009 client**:
two real v0.1.0 nodes, isolated, discovered each other over the original IRC path, one mined a valid block
at real difficulty 1 on top of the historical genesis, and the other received, validated, and accepted it,
leaving both with the identical two-block chain — verified from the raw block bytes, not just the GUI. This
lifts block production and relay from **MODEL/PORT** (the headless C++ port and the Python/Rust networks)
to **JAN09-EXECUTED** for the released binary. Sustained multi-block mining and transaction relay between
the two nodes remain to be captured in a future run; the block-production-and-relay claim is now witnessed.
