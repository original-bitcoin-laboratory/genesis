# R3 — plain-language runbook (run the real 2009 Bitcoin yourself)

This is the one step only a human can do: **run the unmodified January-2009
`bitcoin.exe`** (Satoshi's first release) and watch it build the genesis block and
mine coins. Everything else in this lab was proven headlessly; this is the live
witness. Written for a non-programmer — follow it top to bottom.

There are three options, easiest first. **Option 1 alone gives the core result**
(the historic program runs, makes the genesis block, and mines). Options 2 and 3 are
optional and give a cleaner room / the two-computer network story.

---

## What you're running (and why it's safe)

The file is `lab/genesis/r3-stage/bitcoin.exe` — the exact 2009 program, copied from
the hash-verified Nakamoto Institute archive. It's open-source (MIT), 6.4 MB, and we
verified its fingerprint (SHA-256 `fbcac071…`). You'll run it **offline**, so it can't
talk to the internet. Mined coins are lab coins on an isolated chain — not real money,
never the real Bitcoin ledger.

---

## Option 1 — Quickest: run it on your own PC, offline (~15 minutes)

### Step 1 — Check the file is genuine (optional but nice)
Open **PowerShell** (Start → type "PowerShell" → Enter), go to the folder holding the file, and
paste:
```powershell
cd "<the folder with bitcoin.exe in it>"
Get-FileHash .\bitcoin.exe -Algorithm SHA256
```
The `Hash` it prints must start with **`FBCAC071`**. If it does, the file is the real,
untampered 2009 binary.

### Step 2 — Go offline
Turn off Wi-Fi (or unplug the network cable). This keeps the old program fully
isolated. Leave it off until Step 7.

### Step 3 — Open the folder
In File Explorer, go to:
`…\original-bitcoin-laboratory\lab\genesis\r3-stage\`
You should see `bitcoin.exe`, `libeay32.dll`, `mingwm10.dll`, `readme.txt`,
`license.txt`. **Keep these five files together** — the exe needs the two `.dll`s
next to it.

### Step 4 — Run it
Double-click **`bitcoin.exe`**.
- If Windows shows a blue "Windows protected your PC" box: click **More info → Run
  anyway** (expected — it's an old, unsigned program).
- If Microsoft Defender quarantines/deletes it: that's Defender being cautious about a
  2009 crypto app. Either restore it from Defender's "Protection history" and add an
  exclusion for the `r3-stage` folder, **or** skip to Option 2 (a VM sidesteps this).

A small window titled **Bitcoin** opens.

### Step 5 — Start mining
In the menu bar: **Options → Generate Coins** (click so it's checked). Leave the
window open.
- Because you're isolated, the puzzle difficulty is the lowest possible, so your PC
  finds blocks in **seconds to a few minutes**.
- Watch the **block count** (shown in the window / status bar) climb: 1, 2, 3, …
- Note: the **coin balance stays 0 for a long time** — freshly mined coins only count
  after 100 more blocks (that's a real v0.1 rule). So watch the **block count**, not
  the balance. Letting it reach a few dozen blocks is plenty.

### Step 6 — Save the evidence
1. Let it mine for a few minutes, then take a **screenshot** of the window (press
   `Windows`+`Shift`+`S`, drag over the window, paste into Paint, save as PNG).
2. Close Bitcoin: **File → Exit**.
3. In File Explorer's address bar type `%APPDATA%\Bitcoin` and press Enter. This is the
   folder the program wrote to. Copy these files somewhere safe:
   `debug.log`, `blk0001.dat`, `blkindex.dat`, `wallet.dat`.
   - `debug.log` is the important one — it's the program's own diary of building the
     genesis block and mining.

### Step 7 — Back online
Turn Wi-Fi back on. Done — you've run the original Bitcoin and captured proof.

**What you just proved:** the unmodified 2009 binary boots, constructs the same
genesis block this lab reproduced by hand (if the genesis didn't match, the program
would refuse to start), and mines real blocks under its own rules.

---

## Option 2 — Cleaner: one Windows virtual machine (~1 hour)

Same result as Option 1 but inside a throwaway "computer-in-a-window", so nothing
touches your real PC. Best if Defender blocked the exe, or for a tidy official record.

1. Install **VirtualBox** (free, from virtualbox.org) on your PC.
2. Make a **Windows virtual machine**. Windows XP is Satoshi's stated target and most
   faithful; a Windows 10 VM also runs it if XP is hard to obtain. (Creating the VM =
   New → give it a name → attach a Windows install ISO → click through the installer.
   VirtualBox's docs walk you through it.)
3. Set the VM's network to **"Not attached"** (no internet) in the VM's Network
   settings.
4. Copy the whole `r3-stage` folder into the VM (drag-drop with Guest Additions, or a
   shared folder). Then do **Steps 4–6 of Option 1 inside the VM**.
5. Copy `debug.log` etc. out of the VM the same way you copied the folder in.

---

## Option 3 — Full story: two virtual machines that talk to each other (advanced)

This shows the **peer-to-peer network**: two nodes discover each other, sync blocks,
send a transaction, and (optionally) a chain reorg. It needs two VMs, a private
network, and a tiny discovery server that's already built in this repo
(`derivatives/r3/mini_ircd.py`). The exact commands are in
[`R3_MANUAL_RUNBOOK.md`](R3_MANUAL_RUNBOOK.md) — that runbook is the technical version
of this one. In plain terms the extra steps are:

- Make **two** VMs on a **private, internet-free network** using addresses
  `172.20.0.1` and `172.20.0.2` (the `172.20.x` range matters — the 2009 code hides its
  own address on the more common `192.168.x`/`10.x` ranges).
- On your host PC, run the bundled discovery server:
  `python derivatives/r3/mini_ircd.py --host 0.0.0.0 --port 6667` (host address
  `172.20.0.10`).
- In each VM, add one line to `C:\WINDOWS\system32\drivers\etc\hosts`:
  `172.20.0.10   chat.freenode.net` (this points the old program's built-in discovery
  at your local server instead of the long-dead real one).
- Start `bitcoin.exe` in both VMs with **Generate Coins** on; within a minute they find
  each other and sync. Then **Send Coins** from one to the other's address, mine one
  more block, and watch the balance move.

---

## How to hand the results back to me

Any one of these is enough — pick whatever's easiest:
- The `debug.log` file(s) and your screenshot(s); **or**
- Put the captured files under `lab/genesis/r3-evidence/<date-run>/` and run
  `python scripts/capture-evidence.py --run <date-run>` from `lab/genesis/`, then give
  me the generated `r3-findings/<date-run>/` folder; **or**
- Just tell me, in your own words, what happened at each step (did it start? did the
  block count climb? any error messages?).

I'll check it against what this lab predicted (the genesis hash, the mining, the
subsidy, the sync), write up any differences, and record the result — the top rung of
the evidence ladder, **JAN09-EXECUTED**.

## If something goes wrong
- **Won't start / "missing DLL":** make sure `bitcoin.exe`, `libeay32.dll`,
  `mingwm10.dll` are all in the same folder. If it still won't run on Windows 11, use
  Option 2 (a Windows XP VM is the most reliable).
- **Defender deletes it:** restore from Defender "Protection history" + add a folder
  exclusion, or use a VM.
- **Block count not moving:** confirm **Options → Generate Coins** is checked; give it a
  few minutes; the very first block can take longest.
- **(Option 3) the two nodes won't connect:** check both VMs can `ping 172.20.0.10`, the
  discovery server is running, the `hosts` line is exact, and the IPs are `172.20.x`.
