#!/usr/bin/env python3
"""Replay the corpus against a running v0.1 bitcoin.exe, over its own wire protocol.

    python replay.py --chain 2026 --target release-v0.1.3-openssl-1.0.2u --node CLONE_IP --out results/<date>-release
    python replay.py --chain 2009 --target 2009-fbcac071-openssl-0.9.8  --node A_IP --witness B_IP --out results/<date>-2009
        [--miner PATH] [--threads N] [--phase all|sync|fund|mature|scripts|checksig|blocks]
        [--port N] [--magic hex] [--genesis preset|<hash>] [--pow-limit 1d00ffff]

--chain selects magic, port and genesis (identification is by genesis, never by version number). ONLY ever
point this at an ISOLATED node: it mines ~112 blocks, pays their coinbases to OP_TRUE and spends test
outputs, which must never reach the public 2026 chain (see RUNBOOK.md).

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
import copy
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

# The two chains the same v0.1 code runs on. Identification is by the coinbase of block 0, never by the
# version number (derivatives/bitcoin/00-PROVENANCE.txt); here by genesis hash, magic and port.
CHAINS = {
    "2009": {"magic": "f9beb4d9", "port": 8333,
             "genesis": "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f",
             "note": "Satoshi's chain; the frozen 2009 bitcoin.exe (OpenSSL 0.9.8) in the R4 appliance"},
    "2026": {"magic": "f00ba726", "port": 18026,
             "genesis": "00000000ad12f3ecd9b14e4276ac98936fb0d658f05dce95ad35d18fceee208a",
             "note": "this lab's Bitcoin (2026); the release client (OpenSSL 1.0.2u) — replay on an ISOLATED clone only"},
}


def load(name: str) -> dict:
    return json.loads((CORPUS / name).read_text(encoding="ascii"))


class Replay:
    def __init__(self, a):
        self.a = a
        self.out = pathlib.Path(a.out)
        self.out.mkdir(parents=True, exist_ok=True)
        self.state_path = self.out / "state.json"
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {}
        preset = CHAINS[a.chain]
        self.genesis = bytes.fromhex(preset["genesis"] if a.genesis == "preset" else a.genesis)[::-1]
        self.magic = bytes.fromhex(a.magic or preset["magic"])
        self.port = a.port or preset["port"]
        self.target = a.target
        self.pow_limit = int(a.pow_limit, 16)
        self.chain = spec.Chain2009(self.pow_limit, self.genesis)
        self.raw_blocks: dict[bytes, bytes] = {}
        if a.redo:
            for suite in a.redo.split(","):
                self.state.get("results", {}).pop(suite, None)
        try:                                       # grade full-vocabulary spends locally too, when the model is here
            from fake2009 import model_spend_verifier
            self.chain.spend_verifier = model_spend_verifier()
        except Exception:                          # noqa: BLE001
            pass
        self.mine = minerlib.make_miner(a.miner, a.threads, self.log)
        self.peer = Peer(a.node, self.port, self.magic)
        self.witness = Peer(a.witness, self.port, self.magic) if a.witness else None
        self.key, self.wrong, self.kb = (recipes.key_from_label(x) for x in ("checksig-a", "checksig-wrong", "checksig-b"))
        self.bkey, self.bwrong = recipes.key_from_label("blocks-a"), recipes.key_from_label("blocks-wrong")
        self.evalscript = load("evalscript.json")["vectors"]
        self.variants = recipes.build_sig_variants(self.key, self.wrong, self.kb)
        self.blocks_expect = {v["label"]: v for v in load("blocks.json")["vectors"]}
        self.log(f"target '{self.target}': chain {a.chain} magic {self.magic.hex()} node {a.node}:{self.port} "
                 f"version {self.peer.their_version}; miner: {self.mine.backend}")
        self.state.setdefault("target", self.target)
        if self.state["target"] != self.target:
            raise RuntimeError(f"state.json belongs to target '{self.state['target']}', not '{self.target}' — use another --out")

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

    def refresh_tip(self) -> int:
        """Adopt any block the node's main chain has beyond our local tip — its own mined blocks, if its
        miner is on. Returns how many were adopted. The node is the authority on what its tip is."""
        adopted = 0
        while True:
            after = self.peer.main_chain_after(self.chain.tip, timeout=2.0)
            new = [h for h in after if h not in self.chain.index]
            if not new:
                return adopted
            for h in new:
                raw = self.peer.getdata(MSG_BLOCK, h, timeout=10.0)
                if raw is None:
                    raise RuntimeError(f"node lists {h[::-1].hex()[:16]} on its chain but did not serve it")
                r = self.chain.process_block(raw)
                if r["verdict"] != "accept":
                    raise RuntimeError(f"the node's own block {h[::-1].hex()[:16]} fails the local validator: {r}")
                self.raw_blocks[h] = raw
                adopted += 1
                self.log(f"  adopted a block the NODE added itself: {h[::-1].hex()[:16]} (height {self.chain.height}) — its miner is on")

    def tip_coinbase(self) -> dict:
        blk = spec.parse_block(self.raw_blocks[self.chain.tip])
        cb = blk["txs"][0]
        return {"txid": spec.txid(cb), "value": spec.value_out(cb), "script": cb["vout"][0]["script"]}

    def unspent_p2pk_funding(self) -> list[dict]:
        f = self.state["funding"]
        fid = bytes.fromhex(f["txid"])[::-1]
        outs = []
        for i in range(6):
            n = f["index"][f"p2pk:{i}"]
            if (fid, n) in self.chain.utxo:
                outs.append({"txid": fid, "n": n, "value": f["values"][f"p2pk:{i}"]})
        return outs

    def submit_block(self, raw: bytes, expect_accept: bool = True) -> dict:
        """Send a block; read both signals. Also feed the local validator and compare."""
        h = spec.dsha256(raw[:80])
        prev_tip = self.chain.tip
        locator = list(reversed(self.chain.main[-12:]))      # newest first; survives a reorganisation on the node
        self.peer.send("block", raw)
        served = self.peer.probe(MSG_BLOCK, h, self.genesis)
        in_main = False
        for _try in range(4):                     # the node answers getblocks on its SendMessages tick; be patient
            after = self.peer.main_chain_after(locator, timeout=2.0)
            if after:
                in_main = h in after
                break
            time.sleep(1.0)
        # The local validator is a WITNESS, not the authority: it is run on the block for its own verdict,
        # but the local tip follows the NODE. If the two disagree, the local state is rolled back to what
        # the node holds, so one divergence cannot orphan every later case on the node's side.
        snapshot = copy.deepcopy(self.chain)
        try:
            local = self.chain.process_block(raw, now=self.now())
        except spec.Unsupported as e:
            local = {"verdict": None, "stage": None, "reason": f"unsupported locally: {e}"}
        local_extended = self.chain.tip == h
        local_verdict_side = local.get("verdict") == "side"
        node_side = served and not in_main
        if local_extended != in_main and not (local_verdict_side and node_side):
            self.chain = snapshot                       # follow the node
            self.chain.spend_verifier = snapshot.spend_verifier
            self.log(f"  local validator {'accepted' if local_extended else 'rejected'} {h[::-1].hex()[:16]} but the node "
                     f"{'connected' if in_main else 'did not connect'} it — local state reset to the node's; "
                     f"local reason: {local['reason']}")
        obs = {"hash": h[::-1].hex(), "in_index": served, "in_main": in_main,
               "local": {"verdict": local["verdict"], "stage": local["stage"], "reason": local["reason"]},
               "local_followed_node": local_extended == in_main or (local_verdict_side and node_side)}
        if served:
            self.raw_blocks[h] = raw
        foreign = [x for x in after if x not in self.chain.index]
        if foreign:
            obs["node_added_own_blocks"] = self.refresh_tip()
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
        self.refresh_tip()                        # never build on a tip the node has already moved past
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
            self.raw_blocks[r["hash"]] = raw
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
        hashes: dict[str, bytes] = {k: bytes.fromhex(v["hash"])[::-1] for k, v in res.items()}
        for name in recipes.BLOCK_CASE_ORDER:
            if name in res:
                continue
            exp = self.blocks_expect[name]
            self.refresh_tip()
            funding = self.unspent_p2pk_funding()        # whatever the node still holds unspent, in order
            if len(funding) < recipes.FUNDING_OUTPUTS_CONSUMED:
                raise RuntimeError(f"fewer than {recipes.FUNDING_OUTPUTS_CONSUMED} unspent P2PK funding outputs remain; "
                                   "mine a new funding block (--redo fund)")
            last_cb = self.tip_coinbase()                # the newest coinbase is the immature one
            h = self.chain.height + 1
            nbits = self.chain.index[self.chain.tip]["bits"]
            ctx = {"prev": self.chain.tip, "height": h, "mtp": self.chain.median_time_past(self.chain.tip),
                   "ntime": self.ntime_for_next(), "now": self.now(), "nbits": nbits, "pow_limit_nbits": self.pow_limit,
                   "subsidy": self.chain.subsidy(self.chain.height), "subsidy_prev": self.chain.subsidy(self.chain.height - 1),
                   "parent_of_tip": self.chain.index[self.chain.tip]["prev"], "hashes": hashes,
                   "key": self.bkey, "wrong_key": self.bwrong,
                   "funding": funding, "last_cb": last_cb, "mine": self.mine}
            self.log(f"blocks: {name} (expect {exp['expect']} at {exp['stage']}){' — mining' if exp.get('needs_pow', True) else ''}")
            case = recipes.build_block_case(name, ctx)
            obs = self.submit_block(case["raw"], expect_accept=False)
            hashes[name] = bytes.fromhex(obs["hash"])[::-1]
            # v0.1 AddToBlockIndex (main.cpp:1107-1113) ERASES a block whose ConnectBlock fails, from disk and
            # from mapBlockIndex, so every rejection — whatever its stage — leaves the same two signals as an
            # orphan: not served, not on the main chain. A 'side' block (not higher than the best) is indexed
            # and served but not on the main chain. Only those three patterns are visible from outside.
            pred = {"accept": (True, True), "orphan": (False, False), "reject": (False, False), "side": (True, False)}[exp["expect"]]
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
        results = {"target": self.target, "chain": self.a.chain, "magic": self.magic.hex(), "port": self.port,
                   "node": self.a.node, "genesis": self.genesis[::-1].hex(), "finished": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "miner": self.mine.backend, "results": self.state.get("results", {}), "funding": self.state.get("funding"),
                   "final_height": self.chain.height}
        (self.out / "results.json").write_text(json.dumps(results, indent=1, sort_keys=True))
        self.log(f"results written to {self.out / 'results.json'}; run grade_replay.py on it")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--node", required=True)
    ap.add_argument("--witness")
    ap.add_argument("--chain", choices=sorted(CHAINS), default="2009",
                    help="which chain the node runs: sets magic, port and genesis (2009 = Satoshi's; 2026 = this lab's)")
    ap.add_argument("--target", default="unlabelled",
                    help="label for the binary under test, e.g. '2009-fbcac071-openssl-0.9.8' or 'release-v0.1.3-openssl-1.0.2u'")
    ap.add_argument("--port", type=int, help="override the chain preset's port")
    ap.add_argument("--magic", help="override the chain preset's 4-byte magic (hex)")
    ap.add_argument("--out", default="results/latest")
    ap.add_argument("--miner", help="path to the native miner (default: replay/miner-rs/target/release/miner[.exe] if built)")
    ap.add_argument("--threads", type=int)
    ap.add_argument("--phase", default="all")
    ap.add_argument("--genesis", default="preset", help="'preset' or a genesis hash (display order); test chains only")
    ap.add_argument("--redo", help="comma-separated result suites to discard and run again, e.g. 'blocks' or 'checksig,blocks'")
    ap.add_argument("--pow-limit", default="1d00ffff")
    a = ap.parse_args(argv)
    r = Replay(a)
    r.run(a.phase)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
