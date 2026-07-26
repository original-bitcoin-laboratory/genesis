# R3 manual runbook (the steps only you can do)

Everything off-VM is built and tested (staged binary, `mini_ircd`, network recipe,
capture tooling). This is the exact, ordered checklist for the isolated-VM run that
produces the top-rung **JAN09-EXECUTED** evidence. Read
`R3_HISTORICAL_NODE.md` for the *why*; this is the *do*.

Grounded in the archive: OS target is **Windows NT/2000/XP** (`readme.txt`); run is
"unpack + run `bitcoin.exe`", mine via **Options → Generate Coins** (or `/gen`); the
node writes to **`%APPDATA%\Bitcoin\`** (`main.cpp:1353`). On an isolated chain from
the hardcoded genesis, difficulty is 1 → blocks are CPU-mineable in seconds/minutes.

> Safety: isolated network only, **no internet**, disposable disks, snapshots, no
> real keys/funds. Mined coins are laboratory coins on an isolated branch — never
> the historical ledger.

---

## Phase 0 — Host prep (you have Python + this repo)

1. `git pull` in the repo, then from `lab/genesis/`:
   ```bash
   bash scripts/stage-jan09-binary.sh        # -> r3-stage/  (bitcoin.exe + DLLs, hashed)
   python -m pytest derivatives/r3/test_mini_ircd.py -q   # optional: confirm ircd handshake
   ```
2. Start the discovery server (leave it running in its own terminal):
   ```bash
   python derivatives/r3/mini_ircd.py --host 0.0.0.0 --port 6667
   ```
   Make sure your host's isolated-network adapter is **172.20.0.10** (see Phase 1).

## Phase 1 — Create the isolated network + two VMs

- Guest OS: **Windows XP** (Satoshi's stated target; most reliable for the 2009 exe).
- Network: **`172.20.0.0/24`, host-only / internal, NO gateway, NO DNS, NO internet.**
  Not `10.x`/`192.168.x` (v0.1 would then hide its address — `IsRoutable`, net.h:265).
  - **VirtualBox:**
    ```sh
    VBoxManage hostonlyif create
    VBoxManage hostonlyif ipconfig vboxnet0 --ip 172.20.0.10 --netmask 255.255.255.0
    VBoxManage dhcpserver remove --ifname vboxnet0
    VBoxManage modifyvm VM-A --nic1 hostonly --hostonlyadapter1 vboxnet0
    VBoxManage modifyvm VM-B --nic1 hostonly --hostonlyadapter1 vboxnet0
    ```
  - **Hyper-V:**
    ```powershell
    New-VMSwitch -Name "OBL-Isolated" -SwitchType Internal
    New-NetIPAddress -InterfaceAlias "vEthernet (OBL-Isolated)" -IPAddress 172.20.0.10 -PrefixLength 24
    Add-VMNetworkAdapter -VMName VM-A -SwitchName "OBL-Isolated"
    Add-VMNetworkAdapter -VMName VM-B -SwitchName "OBL-Isolated"
    ```
- In each guest, set a **static IP** (VM-A `172.20.0.1`, VM-B `172.20.0.2`),
  subnet `255.255.255.0`, **blank gateway and DNS**. Snapshot both as "clean".

## Phase 2 — Configure each VM

3. Copy the host's `r3-stage/` folder into each VM (e.g. `C:\bitcoin\`).
4. Edit `C:\WINDOWS\system32\drivers\etc\hosts` in each VM, add:
   ```
   172.20.0.10   chat.freenode.net
   ```
5. Allow port **8333** through the guest firewall (or disable the XP firewall on
   the isolated adapter — safe, it's air-gapped).
6. Sanity: from each VM, `ping 172.20.0.10` (host/ircd) and the other VM should reply.

## Phase 3 — Run

7. **VM-A:** run `C:\bitcoin\bitcoin.exe`. In the window: **Options → Generate
   Coins**. Watch it mine blocks (difficulty 1 → quick).
8. **VM-B:** run `bitcoin.exe`. Within a minute or so the two should find each other
   via the ircd (you'll see IRC/connection lines) and B will sync A's blocks.
9. Let A mine a handful of blocks; confirm B's block count matches.
10. **Send a transaction:** on VM-B copy a receiving address (*Your Address* /
    address book). On VM-A, *Send Coins* → paste B's address → send. Then mine one
    more block (A) so it confirms. Confirm B's balance increases.
11. (optional) Reorg test: pause B, mine a couple blocks on each side, reconnect,
    watch the shorter branch get reorganised out.

## Phase 4 — Capture (what to collect)

From **each** VM's data dir `%APPDATA%\Bitcoin\`
(XP: `C:\Documents and Settings\<user>\Application Data\Bitcoin\`), collect:
`debug.log`, `blk0001.dat`, `blkindex.dat`, `addr.dat`, and `wallet.dat`
(test-only). Also take **screenshots** of: the main window with block count/balance,
the transaction, and any IRC/connection log lines.

To get files out safely: **stop bitcoin.exe first**, then use a hypervisor shared
folder / Guest-Additions drag-drop *for the copy only* (still no internet). Put them
on the host under:
```
lab/genesis/r3-evidence/<run>/A/…       # from VM-A   (e.g. run = 2026-07-27-run1)
lab/genesis/r3-evidence/<run>/B/…       # from VM-B
```
(`r3-evidence/` is gitignored — the bytes never get committed.)

## Phase 5 — Turn it into committed findings, then hand back

12. On the host, from `lab/genesis/`:
    ```bash
    python scripts/capture-evidence.py --run <run>
    ```
    This writes `r3-findings/<run>/EVIDENCE_MANIFEST.json` + `SHA256SUMS` +
    `FINDINGS.md` (skeleton).
13. Fill in `r3-findings/<run>/FINDINGS.md` (the 7-row checklist: pass/fail + which
    file/screenshot supports each), and note anything surprising.

### Hand back to me
Give me any of these and I'll take it from there:
- the generated `r3-findings/<run>/` (manifest + your filled `FINDINGS.md`), **and/or**
- the two `debug.log` files (or excerpts) + your screenshots, **and/or**
- just a plain description of what happened at each of the 11 steps.

I'll verify the manifest, reconcile what the **released binary actually did**
against our `JAN09-SOURCE`/`MODEL`/`PORT` expectations, flag any divergences, write
the conclusion, and commit the results with the same provenance discipline.

## If something snags
- **exe won't start / missing DLL:** use a Windows XP guest; keep `bitcoin.exe` next
  to `libeay32.dll` + `mingwm10.dll` (all in `r3-stage/`). Check `readme.txt`.
- **nodes don't connect:** confirm both can ping `172.20.0.10`; `mini_ircd` is
  running; the `hosts` line is exact; IPs are `172.20.x` (not `192.168.x`); firewall
  allows 8333. Capture both `debug.log`s and send them — the IRC lines tell us why.
- **mining seems stuck:** it shouldn't at difficulty 1; give it a few minutes on one
  node, confirm *Generate Coins* is checked.
