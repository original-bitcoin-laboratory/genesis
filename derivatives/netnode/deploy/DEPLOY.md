# Deploying an X‑chain node / seed (operator templates)

**Evidence: NEW‑EXP. Not money.** These are **templates** to make running a node or a bootstrap DNS
seed a copy‑paste job — the "operators" rung of
[`../../../docs/PUBLIC_TESTNET_SCOPE.md`](../../../docs/PUBLIC_TESTNET_SCOPE.md). A chain is only
"eternal" once independent people keep nodes up; nothing here changes that — it just lowers the bar
to *become* one of those people. Read [`../SECURITY.md`](../SECURITY.md) first.

> These files are deployment templates verified against the CLI, not run in CI — adjust the IPs,
> ports, and paths for your host before using them.

## Docker

```bash
# from the genesis repo root (the whole derivatives/ tree must be in the build context)
docker build -f derivatives/netnode/deploy/Dockerfile -t xnode .
docker run -d --name xnode -p 18009:18009 -v xnode-data:/data xnode \
    --chain jan09x --datadir /data --listen 0.0.0.0:18009 --advertise YOUR_PUBLIC_IP
```

`cryptography` is required; `bitcoinx` is installed too so the **libsecp256k1 fast verifier** is
active (the node runs fine without it — it just falls back to the faithful path). Swap `jan09x`↔
`nov08x` (port `18008`) for the November chain.

## systemd

- **[`xnode.service`](xnode.service)** — a persistent node. Copy the `derivatives/` tree to
  `/opt/obl/derivatives`, set `ADVERTISE_IP` to your reachable IP, `systemctl enable --now xnode`.
  Add `--mine --wallet` to earn/keep coins and `--rpc 127.0.0.1:18332` for local control.
- **[`xseed.service`](xseed.service)** — a bootstrap [DNS seed](../../dnsseed/). Delegate your seed
  hostname to the host with an `NS` record, set `ZONE` + a `KNOWN_NODE`, `systemctl enable --now
  xseed`.

## The honest part

Templates and a seed don't make a network — **people do**. If you want NOV08‑X / JAN09‑X to have the
same open accessibility as any coin, the remaining work isn't code: stand up a node with a stable
address, run a seed, publish the zone, and invite others to do the same. It can be *offered*; it
can't be *engineered*. **Not money.**
