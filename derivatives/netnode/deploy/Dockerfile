# An experimental X-chain node in a container.  NOT money.
#
# Build from the *genesis repo root* (so the whole derivatives tree is in context):
#   docker build -f derivatives/netnode/deploy/Dockerfile -t xnode .
# Run a listening jan09x node with a persistent volume + wallet + localhost RPC:
#   docker run -d --name xnode -p 18009:18009 -v xnode-data:/data xnode \
#       --chain jan09x --datadir /data --listen 0.0.0.0:18009 --advertise YOUR_PUBLIC_IP --mine --wallet
#
# NOT money: experimental, non-monetary, not production-secure. Read netnode/SECURITY.md.

FROM python:3.12-slim

# cryptography is required (the lab's faithful crypto); bitcoinx is OPTIONAL and only
# enables the ~7x libsecp256k1 verifier — the node falls back cleanly without it.
RUN pip install --no-cache-dir cryptography bitcoinx

WORKDIR /app
COPY derivatives /app/derivatives
WORKDIR /app/derivatives

# jan09x=18009, nov08x=18008. Publish whichever chain you run.
EXPOSE 18008 18009
VOLUME /data

ENTRYPOINT ["python", "-m", "netnode"]
CMD ["--chain", "jan09x", "--datadir", "/data", "--listen", "0.0.0.0:18009"]
