# R3 — Historical node in an isolated VM (JAN09-EXECUTED)

The top rung of the evidence ladder: run the **unmodified** `BITCOIN.EXE` from the
hash-verified v0.1.0 archive and observe original behaviour directly. This can only
happen **inside an isolated virtual machine** (never on the host, never on the
internet). This doc is the plan + evidence checklist to drive it; nothing here runs
the binary automatically.

Everything below is grounded in the extracted, hash-verified source
(`manifests/SOURCE_MANIFEST.json`): the CLI is Windows-style (`/gen`, via
`mapArgs`, `ui.cpp:3024`), peer discovery is IRC-only
(`gethostbyname("chat.freenode.net")` :6667, `JOIN #bitcoin`, `irc.cpp:148-180`) —
there is **no `-connect`/`-addnode`** — and mining is `fGenerateBitcoins`
(`main.cpp:2191`). The genesis it must recognise is
`000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f` (`main.cpp:24`).

## Safety posture (non-negotiable, from the charter)

- Isolated VM only; **host-only network**, no NAT, no internet.
- Disposable virtual disk; take a snapshot before every run.
- No real private keys, no real `wallet.dat`, no valuable funds — ever.
- No shared folders / clipboard once running; copy artifacts in beforehand.
- The binary is 2009 **alpha** software (Satoshi's own warning): treat as untrusted.

## Binary provenance

`bitcoin.exe` (6,440,960 B) + `libeay32.dll` (OpenSSL) + `mingwm10.dll` are already
in the verified tree at `extracted/bitcoin/` (the `.rar` and `.tgz` are byte-
identical, 48/48). `scripts/stage-jan09-binary.sh` copies them into a gitignored
`r3-stage/` and writes their SHA-256s, so you carry hash-anchored bytes into the VM.

## VM

- Guest that runs 2009 Win32 GUI apps (Windows XP/7-era). VirtualBox or Hyper-V.
- Build **VM-A**, then clone to **VM-B**. Attach both to one **host-only** network
  (e.g. `192.168.56.0/24`); confirm no default route / no DNS to the internet.
- Copy `r3-stage/` into each VM (into its own folder). Snapshot both as "clean".

## Two-node private network (IRC discovery, faithfully)

v0.1 finds peers only via IRC, so stand up a **local IRC daemon** on the host-only
net and make the VMs resolve the hardcoded hostname to it:

1. Run a tiny ircd (e.g. on the host or a third small guest) reachable at, say,
   `192.168.56.10:6667`.
2. In **each** VM's `hosts` file add: `192.168.56.10   chat.freenode.net`.
3. Start `BITCOIN.EXE` on both. Each joins `#bitcoin`, `WHO #bitcoin` returns the
   other's encoded address, and they connect on port **8333**.

(Fallback if IRC is fussy: pre-seed `addr.dat`; but the IRC + hosts-override path
is the faithful mechanism and preferred.)

## Run + mine

- Start with the GUI, or `BITCOIN.EXE /gen` to mine (Options → *Generate Coins*
  toggles `fGenerateBitcoins`). On a fresh isolated chain from the hardcoded
  genesis, early blocks mine at the minimum difficulty and are CPU-mineable.

## Evidence to capture — each result tagged **JAN09-EXECUTED**

| # | Observation | Capture |
|---|---|---|
| 1 | Node starts and recognises the genesis hash `…19d668…a8ce26f` | `debug.log`, screenshot |
| 2 | `/gen` mining produces blocks; coinbase matures (100) | `debug.log`, block height |
| 3 | VM-B connects to VM-A over the host-only net (via IRC) | both `debug.log`s, peer count |
| 4 | A block relays A→B and validates on B | `blk*.dat` present on B |
| 5 | Send a transaction A→B (Send Coins), it relays and confirms | tx id, screenshots |
| 6 | Balances / UTXO change as expected | wallet balances, `debug.log` |
| 7 | (opt.) Reorg: mine competing blocks on each side, reconnect | `debug.log` reorg lines |

For each, record: SHA-256 of `blkindex.dat`/`blk0001.dat`, the `debug.log`
excerpt, and a screenshot. Store under `derivatives/r3-evidence/<date>/` (gitignored
bytes; commit only a manifest + written findings).

## Important framing

Because v0.1 **hardcodes Bitcoin's genesis**, an isolated chain mined here begins
from that same genesis — these are **laboratory coins on an isolated branch**, with
no relationship to and no value on the historical Bitcoin network. This environment
proves *what the released binary does*; it is **not** a Bitcoin fork or continuation.
(The separate, new-genesis *experimental* networks are a later, clearly-labelled
phase — see the roadmap.)
