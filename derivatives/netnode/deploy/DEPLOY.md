# Deploying an X‑chain node / seed (operator templates)

**Evidence: NEW‑EXP. Not money.** These are **templates** to make running a node or a bootstrap DNS
seed a copy‑paste job — the "operators" rung of
[`../../../docs/PUBLIC_TESTNET_SCOPE.md`](../../../docs/PUBLIC_TESTNET_SCOPE.md). A chain is only
"eternal" once independent people keep nodes up; nothing here changes that — it just lowers the bar
to *become* one of those people. Read [`../SECURITY.md`](../SECURITY.md) first.

> These files are deployment templates verified against the CLI, not run in CI — adjust the IPs,
> ports, and paths for your host before using them.

## Docker — one-command join (prebuilt image)

CI ([`.github/workflows/docker.yml`](../../../.github/workflows/docker.yml)) publishes a prebuilt
image to GHCR, so joining needs no Python/venv:

```bash
# JOIN the live network — dial the public seed and sync JAN09-X:
docker run --rm -v xnode-data:/data ghcr.io/original-bitcoin-laboratory/xnode
# NOV08-X:
docker run --rm -v xnode-data:/data ghcr.io/original-bitcoin-laboratory/xnode \
    --chain nov08x --datadir /data --connect seed.bitcoin-lab.org:18008

# run a reachable ANCHOR (listens, mines, wallet + localhost RPC):
docker run -d --name xnode -p 18009:18009 -v xnode-data:/data \
    ghcr.io/original-bitcoin-laboratory/xnode \
    --chain jan09x --datadir /data --listen 0.0.0.0:18009 --advertise YOUR_PUBLIC_IP --mine --wallet
```

Or build it yourself from the genesis repo root:

```bash
docker build -f derivatives/netnode/deploy/Dockerfile -t xnode .
docker run --rm -v xnode-data:/data xnode
```

`cryptography` is required; `bitcoinx` (the ~7× libsecp256k1 verifier) is attempted but optional — the
node falls back to the faithful verifier with identical results. Swap `jan09x`↔`nov08x` (port `18008`).

> **Maintainer, one-time:** GHCR packages start **private**. After the first CI publish, set the
> `xnode` package to **public** (GitHub → org → Packages → `xnode` → Package settings → Change
> visibility) so `docker pull` needs no login, and make sure **Actions is enabled** for the repo.

## systemd

- **[`xnode.service`](xnode.service)** — a persistent node. Copy the `derivatives/` tree to
  `/opt/obl/derivatives`, set `ADVERTISE_IP` to your reachable IP, `systemctl enable --now xnode`.
  Add `--mine --wallet` to earn/keep coins and `--rpc 127.0.0.1:18332` for local control.
- **[`obl-dnsseed.service`](obl-dnsseed.service)** — the concrete **crawling DNS seed** as deployed
  (bind the public IP on `:53`; `ufw allow 53/udp`). See [`../../dnsseed/ACTIVATION.md`](../../dnsseed/ACTIVATION.md)
  for the delegation records. **[`xseed.service`](xseed.service)** is the generic template.

## The honest part

Templates and a seed don't make a network — **people do**. If you want NOV08‑X / JAN09‑X to have the
same open accessibility as any coin, the remaining work isn't code: stand up a node with a stable
address, run a seed, publish the zone, and invite others to do the same. It can be *offered*; it
can't be *engineered*. **Not money.**
