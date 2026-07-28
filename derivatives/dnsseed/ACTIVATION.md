# DNS seed — the decision, the live deployment, and how to activate crawling

**NOT money.** This records how `seed.bitcoin-lab.org` bootstraps new nodes today, and the one
registrar change that flips it to a fully dynamic crawling seed when the network grows.

## The decision (today: static A; crawler live and ready)

`seed.bitcoin-lab.org` currently resolves — via ordinary **static A records at the registrar** — to
**both** always-on anchors:

```
seed.bitcoin-lab.org  ->  143.110.255.205 , 178.62.236.102   (round-robin)
```

This is deliberately the robust choice **while the only nodes are operator-run**: the name is served
by the registrar's redundant nameservers, so it keeps resolving even if a box is down, and it already
hands out both anchors — exactly what a crawler would return when every known node is one of ours.

A crawling seed only *adds* information once there are **independent** nodes it can discover that a
static record can't know about. So the crawler is **built, deployed, and running now**, verified, and
one NS delegation away from taking over the moment that's true.

## The live crawler (deployed, verified)

Crawling DNS seeds run as `obl-dnsseed.service` on **both anchors** — `143.110.255.205` (Box 1) and
`178.62.236.102` (Box 2) — each bound to its public IP on **:53** (systemd-resolved keeps only the
`127.0.0.53` stub, so the public `:53` is free). Each connects to every known node over the real
netnode wire, does the `version` handshake — proving the node is **reachable and on jan09x** — harvests
the peers it gossips, and answers `A` queries for `seed.bitcoin-lab.org` with the live **healthy** set.
**Two nameservers means the delegation has no single point of failure.** (Both anchors run both chains,
so these IPs serve NOV08-X bootstrap too.)

Verify either directly (works regardless of delegation — it queries the seed host itself):

```bash
dig @143.110.255.205 seed.bitcoin-lab.org +short      # or @178.62.236.102 -> the live healthy IPs
# Windows:
Resolve-DnsName -Server 178.62.236.102 seed.bitcoin-lab.org -Type A
```

Deploy/redeploy: [`../netnode/deploy/obl-dnsseed.service`](../netnode/deploy/obl-dnsseed.service)
(`ufw allow 53/udp` first).

## To activate crawling (delegate the zone) — Namecheap

Both nameservers are live and **redundant**, so the delegation is ready to flip whenever you want a
fully dynamic seed. In **Namecheap → Domain List → bitcoin-lab.org → Manage → Advanced DNS**:

1. **Remove** the two `A` records for host `seed` (the current static anchors).
2. **Add** two `A` records — the nameservers' own addresses (glue):
   - host `ns1`, value `143.110.255.205`
   - host `ns2`, value `178.62.236.102`
3. **Add** two `NS` records — delegate the subdomain to both nameservers:
   - host `seed`, value `ns1.bitcoin-lab.org.`
   - host `seed`, value `ns2.bitcoin-lab.org.`

Propagation is minutes-to-hours. After it takes effect, any resolver querying `seed.bitcoin-lab.org`
is answered by the live crawlers (either nameserver), so `--connect seed.bitcoin-lab.org:18009` always
dials a currently reachable peer — no hardcoded IP. **To revert:** delete the `NS` + `ns1`/`ns2` records
and re-add the static `A` records for `seed`.

## Why this is the honest call

Everything durable about the lab is reproducible from source; a live network's last mile is **other
people running nodes**. The seed is *offered infrastructure, never authority* — anyone can run their
own, or hardcode peers. Static-until-diverse keeps bootstrap dependable now; two redundant crawlers are
stood up and proven, so activation is a handful of registrar records, not a project. **Not money.**
