#!/usr/bin/env python3
"""Replay the corpus against a running January 2009 bitcoin.exe, over its own wire protocol.

    python replay.py --node 192.168.56.101 [--witness 192.168.56.102] [--out results/2026-09-20]
                     [--miner PATH] [--threads N] [--phase all|sync|fund|mature|scripts|checksig|blocks]
                     [--genesis 2009|<hash>] [--pow-limit 1d00ffff] [--port 8333]

What it does, in order (each phase resumes from --out/state.json):
  sync     fetch the node's whole main chain with getblocks/getdata and validate it locally with the
           from-spec validator (a side-check: every block the node accepted, we accept for the same reasons);
  fund     mine ONE block whose coinbase carries an output per corpus vector (each evalscript script and each
           checksig scriptPubKey as an output script; six P2PK outputs for the block cases);
  mature   mine 100 more blocks so those outputs become spendable (ConnectInputs' coinbase-maturity walk);
  scripts  for every evalscript vector, send a transaction spending its output with an EMPTY scriptSig,
           and record whether the node accepted it (served back by getdata from its relay pool);
  checksig same, with the signature variants rebuilt against the real prevout;
  blocks   rebuild each block case on the live tip (mined at difficulty 1 where the case needs real work),
           submit it, and read two signals: is it in the node's index (getdata), and did the main chain
           advance to it (getblocks from the previous tip).

Every verdict is read from the node itself; debug.log is a second witness that grade_replay.py checks
against the exact main.cpp strings. Mining cost: ~112 difficulty-1 blocks. NOT money.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import verify_vectors as spec                                  # noqa: E402
import recipes                                                 # noqa: E402
import miner as minerlib                                       # noqa: E402
from wire01 import MSG_BLOCK, MSG_TX, Peer                     # noqa: E402

GENESIS_2009 = bytes.fromhex("000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f")[::-1]
CORPUS = HERE.parent
OUT_VALUE = 1000


def load(name: str) -> dict:
    return json.loads((CORPUS / name).read_text(encoding="ascii"))


class Replay:
    def __init__(self, a):
        self.a = a
        self.out = pathlib.Path(a.out)
        self.out.mkdir(parents=True, exist_ok=True)
        self.state_path = self.out / "state.json"
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {}
        self.genesis = GENESIS_2009 if a.genesis == "2009" else bytes.fromhex(a.genesis)[::-1]
        self.pow_limit = int(a.pow_limit, 16)
        self.chain = spec.Chain2009(self.pow_limit, self.genesis)
        try:                                       # grade full-vocabulary spends locally too, when the model is here
            from fake2009 import model_spend_verifier
            self.chain.spend_verifier = model_spend_verifier()
        except Exception:                          # noqa: BLE001
            pass
        self.mine = minerlib.make_miner(a.miner, a.threads, self.log)
        self.peer = Peer(a.node, a.port)
        self.witness = Peer(a.witness, a.port) if a.witness else None
        self.key, self.wrong, self.kb = (recipes.key_from_label(x) for x in ("checksig-a", "checksig-wrong", "checksig-b"))
        self.bkey, self.bwrong = recipes.key_from_label("blocks-a"), recipes.key_from_label("blocks-wrong")
        self.evalscript = load("evalscript.json")["vectors"]
        self.variants = recipes.build_sig_variants(self.key, self.wrong, self.kb)
        self.blocks_expect = {v["label"]: v for v in load("blocks.json")["vectors"]}
        self.log(f"node {a.node}:{a.port} version {self.peer.their_version}; miner: {self.mine.backend}")

    # ---- plumbing ------------------------------------------------------------------------------
    def log(self, msg: str) -> None:
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        print(line, flush=True)
        with open(self.out / "replay.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def save(self) -> None:
        self.state_path.write_text(json.dumps(self.state, indent=1, sort_keys=True))

    def now(self) -> int:
        return self.peer.node_now()

    def ntime_for_next(self) -> int:
        return max(self.chain.median_time_past(self.chain.tip) + 1, self.now())

    def submit_block(self, raw: bytes, expect_accept: bool = True) -> dict:
        """Send a block; read both signals. Also feed the local validator and compare."""
        h = spec.dsha256(raw[:80])
        prev_tip = self.chain.tip
        self.peer.send("block", raw)
        served = self.peer.probe(MSG_BLOCK, h, self.genesis)
        after = self.peer.main_chain_after(prev_tip, timeout=2.0)
        in_main = h in after
        try:
            local = self.chain.process_block(raw)
        except spec.Unsupported as e:
            local = {"verdict": None, "stage": None, "reason": f"unsupported locally: {e}"}
        obs = {"hash": h[::-1].hex(), "in_index": served, "in_main": in_main,
               "local": {"verdict": local["verdict"], "stage": local["stage"], "reason": local["reason"]}}
        if expect_accept and not in_main:
            raise RuntimeError(f"block {h[::-1].hex()[:16]} was expected to extend the chain but did not: {obs}")
        return obs

    def submit_tx(self, raw: bytes) -> dict:
        h = spec.dsha256(raw)
        if self.witness:
            self.witness.drain(0.2)
            self.witness.seen_inv.clear()
        self.peer.send("tx", raw)
        served = self.peer.probe(MSG_TX, h, self.genesis)
        obs = {"txid": h[::-1].hex(), "accepted": served}
        if self.witness:
            self.witness.drain(1.0)
            obs["witness_inv"] = any(t == MSG_TX and hh == h for t, hh in self.witness.seen_inv)
        try:
            local_ok, local_reason = self.chain.accept_tx(raw)
        except spec.Unsupported as e:
            local_ok, local_reason = None, f"unsupported locally: {e}"
        obs["local"] = {"accepted": local_ok, "reason": local_reason}
        return obs

    def mine_block(self, txs: list[dict], nbits: int | None = None, ntime: int | None = None) -> bytes:
        nbits = nbits or self.chain.index[self.chain.tip]["bits"]
        ntime = ntime or self.ntime_for_next()
        t0 = time.time()
        raw = recipes.assemble_block(self.chain.tip, txs, ntime, nbits, self.mine)
        self.log(f"  mined {spec.dsha256(raw[:80])[::-1].hex()[:16]} in {time.time() - t0:.0f}s")
        return raw

    # ---- phases -------------------------------------------------------------------------------
    def phase_sync(self) -> None:
        self.log("sync: fetching the node's chain")
        count = [0]

        def on_block(raw: bytes) -> None:
            r = self.chain.process_block(raw)
            if r["verdict"] != "accept":
                raise RuntimeError(f"the node's block {r['hash'][::-1].hex()[:16]} fails the from-spec validator: {r}")
            count[0] += 1
        if self.chain.tip is None:
            # the genesis itself: the node serves it by hash
            g = self.peer.getdata(MSG_BLOCK, self.genesis, timeout=10.0)
            if g is None:
                raise RuntimeError("node did not serve the genesis block")
            on_block(g)
        self.peer.sync_chain(self.chain.tip, on_block=on_block)
        self.log(f"sync: height {self.chain.height}, {count[0]} blocks validated locally, tip {self.chain.tip[::-1].hex()[:16]}")
        self.state.setdefault("sync", {})["height"] = self.chain.height
        self.save()

    def funding_outputs(self) -> list[tuple[str, int, bytes]]:
        outs = []
        for v in self.evalscript:
            outs.append((f"script:{v['label']}", OUT_VALUE, bytes.fromhex(v["script_hex"])))
        for v in self.variants:
            outs.append((f"checksig:{v['label']}", OUT_VALUE, v["script_pubkey"]))
        for i in range(6):
            outs.append((f"p2pk:{i}", 8 * spec.COIN, recipes.p2pk(self.bkey["sec"])))
        return outs

    def phase_fund(self) -> None:
        if "funding" in self.state:
            self.log("fund: already done")
            return
        outs = self.funding_outputs()
        h = self.chain.height + 1
        cb = recipes.make_coinbase(h, [(v, s) for _l, v, s in outs], b"obl-vectors funding")
        assert spec.value_out(cb) <= self.chain.subsidy(self.chain.height)
        self.log(f"fund: mining the funding block at height {h} with {len(outs)} outputs")
        raw = self.mine_block([cb])
        obs = self.submit_block(raw)
        self.state["funding"] = {"block": obs["hash"], "height": h, "txid": spec.txid(cb)[::-1].hex(),
                                 "index": {l: i for i, (l, _v, _s) in enumerate(outs)},
                                 "values": {l: v for (l, v, _s) in outs}}
        self.save()

    def phase_mature(self) -> None:
        done = self.state.setdefault("mature", {"count": 0, "blocks": []})
        need = spec.COINBASE_MATURITY
        while done["count"] < need:
            h = self.chain.height + 1
            cb = recipes.make_coinbase(h, [(self.chain.subsidy(self.chain.height), recipes.OP_TRUE_SCRIPT)], b"obl-vectors mature")
            self.log(f"mature: block {done['count'] + 1}/{need} at height {h}")
            raw = self.mine_block([cb])
            obs = self.submit_block(raw)
            done["count"] += 1
            done["blocks"].append(obs["hash"])
            done["last_cb"] = {"txid": spec.txid(cb)[::-1].hex(), "value": spec.value_out(cb)}
            self.save()
        self.log("mature: done")

    def _funding_prevout(self, label: str) -> tuple[bytes, int, int]:
        f = self.state["funding"]
        return bytes.fromhex(f["txid"])[::-1], f["index"][label], f["values"][label]

    def phase_scripts(self) -> None:
        res = self.state.setdefault("results", {}).setdefault("evalscript", {})
        for v in self.evalscript:
            if v["label"] in res:
                continue
            prev, n, val = self._funding_prevout(f"script:{v['label']}")
            tx = recipes.spend(prev, n, val, recipes.OP_TRUE_SCRIPT)
            obs = self.submit_tx(spec.ser_tx(tx))
            obs["expected_valid"] = v["valid"]
            obs["agree"] = obs["accepted"] == v["valid"]
            res[v["label"]] = obs
            self.log(f"scripts: {v['label']:34s} expected {str(v['valid']):5s} node {str(obs['accepted']):5s} {'ok' if obs['agree'] else 'DISAGREE'}")
            self.save()

    def phase_checksig(self) -> None:
        res = self.state.setdefault("results", {}).setdefault("checksig", {})
        for v in self.variants:
            if v["label"] in res:
                continue
            prev, n, val = self._funding_prevout(f"checksig:{v['label']}")
            tx = recipes.spend(prev, n, val, recipes.OP_TRUE_SCRIPT)
            ss = v["scriptsig"](tx, 0)
            if ss is None:
                continue
            tx["vin"][0]["script"] = ss
            obs = self.submit_tx(spec.ser_tx(tx))
            obs.update(expected_strict_der=v["expected_strict_der"], expected_binary=v["expected_binary"])
            obs["agree"] = None if v["expected_binary"] is None else obs["accepted"] == v["expected_binary"]
            res[v["label"]] = obs
            tag = "recorded" if obs["agree"] is None else ("ok" if obs["agree"] else "DISAGREE")
            self.log(f"checksig: {v['label']:30s} node {str(obs['accepted']):5s} strict {str(v['expected_strict_der']):5s} {tag}")
            self.save()

    def phase_blocks(self) -> None:
        res = self.state.setdefault("results", {}).setdefault("blocks", {})
        f = self.state["funding"]
        funding = [{"txid": bytes.fromhex(f["txid"])[::-1], "n": f["index"][f"p2pk:{i}"], "value": f["values"][f"p2pk:{i}"]}
                   for i in range(6)]
        lc = self.state["mature"]["last_cb"]
        last_cb = {"txid": bytes.fromhex(lc["txid"])[::-1], "value": lc["value"]}
        for name in recipes.BLOCK_CASE_ORDER:
            if name in res:
                continue
            exp = self.blocks_expect[name]
            h = self.chain.height + 1
            nbits = self.chain.index[self.chain.tip]["bits"]
            ctx = {"prev": self.chain.tip, "height": h, "mtp": self.chain.median_time_past(self.chain.tip),
                   "ntime": self.ntime_for_next(), "nbits": nbits, "pow_limit_nbits": self.pow_limit,
                   "subsidy": self.chain.subsidy(self.chain.height), "key": self.bkey, "wrong_key": self.bwrong,
                   "funding": funding, "last_cb": last_cb, "mine": self.mine}
            self.log(f"blocks: {name} (expect {exp['expect']} at {exp['stage']}){' — mining' if exp.get('needs_pow', True) else ''}")
            case = recipes.build_block_case(name, ctx)
            obs = self.submit_block(case["raw"], expect_accept=False)
            pred = {"accept": (True, True), "orphan": (False, False),
                    "reject": (exp["stage"] == "ConnectBlock", False)}[exp["expect"]]
            obs.update(expected=exp["expect"], expected_stage=exp["stage"], expected_reason=exp["reason"],
                       predicted_signals={"in_index": pred[0], "in_main": pred[1]})
            obs["agree"] = (obs["in_index"], obs["in_main"]) == pred
            res[name] = obs
            self.log(f"  in_index {obs['in_index']} in_main {obs['in_main']} -> {'ok' if obs['agree'] else 'DISAGREE'}")
            self.save()

    def run(self, phase: str) -> None:
        """Run sync, then every phase up to and including `phase` ('all' = everything)."""
        order = ["fund", "mature", "scripts", "checksig", "blocks"]
        self.phase_sync()
        if phase != "sync":
            upto = order.index(phase) if phase in order else len(order) - 1
            for p in order[:upto + 1]:
                getattr(self, f"phase_{p}")()
        self.finish()

    def finish(self) -> None:
        results = {"node": self.a.node, "genesis": self.genesis[::-1].hex(), "finished": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "miner": self.mine.backend, "results": self.state.get("results", {}), "funding": self.state.get("funding"),
                   "final_height": self.chain.height}
        (self.out / "results.json").write_text(json.dumps(results, indent=1, sort_keys=True))
        self.log(f"results written to {self.out / 'results.json'}; run grade_replay.py on it")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--node", required=True)
    ap.add_argument("--witness")
    ap.add_argument("--port", type=int, default=8333)
    ap.add_argument("--out", default="results/latest")
    ap.add_argument("--miner", help="path to the native miner (default: replay/miner-rs/target/release/miner[.exe] if built)")
    ap.add_argument("--threads", type=int)
    ap.add_argument("--phase", default="all")
    ap.add_argument("--genesis", default="2009", help="'2009' or a genesis hash (display order)")
    ap.add_argument("--pow-limit", default="1d00ffff")
    a = ap.parse_args(argv)
    r = Replay(a)
    r.run(a.phase)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
