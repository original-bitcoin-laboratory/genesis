#!/usr/bin/env bash
# provision.sh -- stand up a public Bitcoin (Aug 2026) node on a fresh Ubuntu 24.04 droplet.
#
# Run as root on the droplet:
#     ssh root@168.144.27.117
#     curl -fsSL https://raw.githubusercontent.com/original-bitcoin-laboratory/genesis/main/derivatives/bitcoin/deploy/provision.sh | bash -s -- 168.144.27.117
# or, if the repo is not pushed yet, scp this file over and:
#     bash provision.sh 168.144.27.117
#
# Idempotent: safe to re-run. Everything it does is listed here; nothing is hidden.
#   - unprivileged service account (systemd DynamicUser), node state in /var/lib/bitcoin-node
#   - ufw: SSH + 18026/tcp only
#   - the node listens on 18026 with magic f00ba726 -- NOT mainnet's 8333/f9beb4d9
#
# NOT money. Experimental research chain.
set -euo pipefail

ADVERTISE_IP="${1:-}"
REPO="${REPO:-https://github.com/original-bitcoin-laboratory/genesis.git}"
BRANCH="${BRANCH:-main}"
PREFIX=/opt/obl
PORT=18026

if [[ -z "$ADVERTISE_IP" ]]; then
    echo "usage: bash provision.sh <PUBLIC_IPV4>    # the address peers will dial back" >&2
    exit 2
fi
if [[ $EUID -ne 0 ]]; then echo "run as root" >&2; exit 2; fi

echo "==> packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 python3-venv git ufw build-essential ca-certificates >/dev/null

echo "==> source at $PREFIX"
if [[ -d "$PREFIX/.git" ]]; then
    git -C "$PREFIX" fetch --quiet origin "$BRANCH"
    git -C "$PREFIX" reset --hard --quiet "origin/$BRANCH"
else
    rm -rf "$PREFIX"
    git clone --quiet --depth 1 --branch "$BRANCH" "$REPO" "$PREFIX"
fi

# the derivatives tree is what the node runs
DERIV="$PREFIX/lab/genesis/derivatives"
[[ -d "$DERIV/bitcoin" ]] || { echo "ERROR: $DERIV/bitcoin missing -- is the chain pushed to $BRANCH?" >&2; exit 1; }

echo "==> verifying the genesis this node will serve"
python3 "$DERIV/bitcoin/net.py"

echo "==> firewall"
ufw allow OpenSSH             >/dev/null
ufw allow ${PORT}/tcp         >/dev/null
ufw --force enable            >/dev/null
ufw status numbered | sed 's/^/    /'

echo "==> systemd unit"
cat >/etc/systemd/system/bitcoin-node.service <<UNIT
# Bitcoin (Aug 2026) -- public node. NOT money.
# genesis 00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a
[Unit]
Description=Bitcoin (Aug 2026) node -- experimental, NOT money
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=${DERIV}
Environment=ADVERTISE_IP=${ADVERTISE_IP}
ExecStart=/usr/bin/python3 -m netnode --chain bitcoin --datadir /var/lib/bitcoin-node \\
          --listen 0.0.0.0:${PORT} --advertise \${ADVERTISE_IP}
Restart=on-failure
RestartSec=5
DynamicUser=yes
StateDirectory=bitcoin-node
ProtectSystem=strict
ProtectHome=yes
NoNewPrivileges=yes
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now bitcoin-node >/dev/null
sleep 3

echo
echo "==> status"
systemctl is-active bitcoin-node | sed 's/^/    service: /'
ss -lntp 2>/dev/null | grep ":${PORT}" | sed 's/^/    /' || echo "    (not listening yet -- check: journalctl -u bitcoin-node -n 50)"
echo
echo "Bitcoin (Aug 2026) node is up."
echo "  advertise : ${ADVERTISE_IP}:${PORT}"
echo "  magic     : f00ba726   (mainnet is f9beb4d9 -- this is a separate network)"
echo "  genesis   : 00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a"
echo "  logs      : journalctl -u bitcoin-node -f"
echo
echo "Anyone can now join with:"
echo "  python3 -m netnode --chain bitcoin --datadir ./data --connect ${ADVERTISE_IP}:${PORT}"
