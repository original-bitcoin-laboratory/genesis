# R3 tooling — isolated two-node network

Helpers to drive the JAN09-EXECUTED run (see `../../docs/R3_HISTORICAL_NODE.md`
for the full plan, safety posture, and evidence checklist). Evidence level:
DERIVATIVE (test infrastructure — not original code).

- `mini_ircd.py` — a minimal IRC daemon implementing exactly the handshake v0.1
  needs for peer discovery (hostname notice → 001–004 → JOIN/WHO relaying the
  address-carrying nicks). No external ircd required.
- `test_mini_ircd.py` — verifies two clients discover each other via `WHO`
  (`python -m pytest`), so the discovery path is proven before any VM run.

## Network (why `172.20.x`, not `192.168.x`)

v0.1 advertises its address over IRC only when the local IP `IsRoutable()`, and
that excludes **only `10.x` and `192.168.x`** (net.h:265). Put the isolated network
on **`172.20.0.0/24`** — RFC1918 (safely air-gapped) yet routable to v0.1.

```
172.20.0.10   host / mini_ircd   (also: chat.freenode.net in each VM's hosts file)
172.20.0.1    VM-A (bitcoin node)
172.20.0.2    VM-B (bitcoin node)
```

### VirtualBox (host-only, no internet)

```sh
VBoxManage hostonlyif create                       # e.g. creates vboxnet0
VBoxManage hostonlyif ipconfig vboxnet0 --ip 172.20.0.10 --netmask 255.255.255.0
VBoxManage dhcpserver remove --ifname vboxnet0     # static IPs; ignore if none
VBoxManage modifyvm VM-A --nic1 hostonly --hostonlyadapter1 vboxnet0   # only NIC -> no NAT
VBoxManage modifyvm VM-B --nic1 hostonly --hostonlyadapter1 vboxnet0
```
In each guest set a static IP (`172.20.0.1` / `172.20.0.2`), **blank gateway/DNS**.

### Hyper-V (internal switch, no internet)

```powershell
New-VMSwitch -Name "OBL-Isolated" -SwitchType Internal
New-NetIPAddress -InterfaceAlias "vEthernet (OBL-Isolated)" -IPAddress 172.20.0.10 -PrefixLength 24
Add-VMNetworkAdapter -VMName VM-A -SwitchName "OBL-Isolated"   # and remove any External adapter
Add-VMNetworkAdapter -VMName VM-B -SwitchName "OBL-Isolated"
```
In each guest set a static IP, **blank gateway/DNS**.

## Bring-up

1. Host: `python mini_ircd.py --host 0.0.0.0 --port 6667` (listens on 172.20.0.10).
2. Each VM `hosts` (`C:\Windows\System32\drivers\etc\hosts`): `172.20.0.10  chat.freenode.net`.
3. Stage the binary (host): `bash ../../scripts/stage-jan09-binary.sh`; copy
   `../../r3-stage/` into each VM.
4. In each VM, run `BITCOIN.EXE` (add `/gen` to mine). They JOIN `#bitcoin`,
   discover via `WHO`, connect on 8333, and relay blocks/transactions.
5. Capture evidence per the checklist in `../../docs/R3_HISTORICAL_NODE.md`.

Reminder: mined coins here are laboratory coins on an isolated branch from the
hardcoded genesis — never the historical Bitcoin ledger, never online.
