# An experimental X-chain node in a container.  NOT money.
#
# Pull the prebuilt image and JOIN the live network in one command (no Python/venv to set up):
#   docker run --rm -v xnode-data:/data ghcr.io/original-bitcoin-laboratory/xnode
#     -> joins JAN09-X, dials seed.bitcoin-lab.org, syncs + re-validates every block.
#   NOV08-X:  docker run --rm -v xnode-data:/data ghcr.io/original-bitcoin-laboratory/xnode \
#                 --chain nov08x --datadir /data --connect seed.bitcoin-lab.org:18008
#
# Run a reachable ANCHOR (listens, mines, wallet + localhost RPC):
#   docker run -d --name xnode -p 18009:18009 -v xnode-data:/data \
#       ghcr.io/original-bitcoin-laboratory/xnode \
#       --chain jan09x --datadir /data --listen 0.0.0.0:18009 --advertise YOUR_PUBLIC_IP --mine --wallet
#
# Build locally instead (from the *genesis repo root*):
#   docker build -f derivatives/netnode/deploy/Dockerfile -t xnode .
#
# NOT money: experimental, non-monetary, not production-secure. Read netnode/SECURITY.md.

FROM python:3.12-slim

# cryptography is required (the lab's faithful crypto). bitcoinx is OPTIONAL — it only enables the
# ~7x libsecp256k1 verifier and needs a C toolchain to build, so we try it but never fail the image:
# the node falls back to the faithful verifier automatically, with identical results.
RUN pip install --no-cache-dir cryptography && \
    (pip install --no-cache-dir bitcoinx || echo "bitcoinx unavailable — using the faithful verifier")

WORKDIR /app
COPY derivatives /app/derivatives
WORKDIR /app/derivatives

# jan09x=18009, nov08x=18008. Publish whichever chain you run as an anchor.
EXPOSE 18008 18009
VOLUME /data

ENTRYPOINT ["python", "-m", "netnode"]
# default: a one-command JOIN — dial the public seed and sync JAN09-X (override args to run an anchor)
CMD ["--chain", "jan09x", "--datadir", "/data", "--connect", "seed.bitcoin-lab.org:18009"]
