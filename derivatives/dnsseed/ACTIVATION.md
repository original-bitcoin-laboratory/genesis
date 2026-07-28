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

A crawling DNS seed runs as `obl-dnsseed.service` on **178.62.236.102 (Box 2)**, bound to the public
IP on **:53** (systemd-resolved keeps only the `127.0.0.53` stub, so the public `:53` is free). It
connects to each known node over the real netnode wire, does the `version` handshake — proving the
node is **reachable and on jan09x** — harvests the peers it gossips, and answers `A` queries for
`seed.bitcoin-lab.org` with the live **healthy** set. (Both anchors run both chains, so these IPs
serve NOV08-X bootstrap too; a dedicated nov08x seed can run on a second host/zone later.)

Verify it directly (works regardless of delegation — it queries the seed host itself):

```bash
dig  @178.62.236.102 seed.bitcoin-lab.org +short      # -> the live healthy node IPs
# Windows:
Resolve-DnsName -Server 178.62.236.102 seed.bitcoin-lab.org -Type A
```

Deploy/redeploy: [`../netnode/deploy/obl-dnsseed.service`](../netnode/deploy/obl-dnsseed.service)
(`ufw allow 53/udp` first).

## To activate crawling (delegate the zone) — Namecheap

When independent operators are running nodes, delegate the seed hostname to the crawler so the whole
internet's resolvers reach it. In **Namecheap → Domain → Advanced DNS**:

1. **Remove** the two `A` records for host `seed` (the current static anchors).
2. **Add** an `A` record — host `ns-seed`, value `178.62.236.102`  *(glue: the nameserver's address)*.
3. **Add** an `NS` record — host `seed`, value `ns-seed.bitcoin-lab.org.`  *(delegates the subdomain to the crawler)*.

Propagation is minutes-to-hours. After it takes effect, any resolver querying `seed.bitcoin-lab.org`
is answered by the live crawler, so `--connect seed.bitcoin-lab.org:18009` always dials a currently
reachable peer — no hardcoded IP.

**Redundancy (recommended before relying on delegation):** a single delegated nameserver is a single
point of failure — if Box 2 is down, `seed.bitcoin-lab.org` stops resolving. Before flipping, run a
second `obl-dnsseed` on Box 1 (`--listen 143.110.255.205:53`) and add a second glue `A`
(`ns-seed2 -> 143.110.255.205`) + `NS seed -> ns-seed2.bitcoin-lab.org.` so either host can answer.

## Why this is the honest call

Everything durable about the lab is reproducible from source; a live network's last mile is **other
people running nodes**. The seed is *offered infrastructure, never authority* — anyone can run their
own, or hardcode peers. Static-until-diverse keeps bootstrap dependable now; the crawler is stood up
and proven so activation is a two-record change, not a project. **Not money.**
