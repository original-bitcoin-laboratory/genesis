"""The replay harness end-to-end against the fake 2009 node (the from-spec validator behind the 2009 wire).

This proves the plumbing: handshake, chain sync, mining, block and tx submission, verdict reading,
resumable state, and grading. It says nothing about the real binary — that is the VM run.
"""
import json
import pathlib
import subprocess
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "replay"))

import recipes                     # noqa: E402
import verify_vectors as spec      # noqa: E402
import fake2009                    # noqa: E402  (replay/ is on sys.path; `replay` itself resolves to replay/replay.py)
import replay as rp                # noqa: E402

EASY = 0x207FFFFF


@pytest.fixture(scope="module")
def node(tmp_path_factory):
    d = tmp_path_factory.mktemp("fake")
    g = fake2009.easy_genesis(EASY)
    n = fake2009.Fake2009(g, EASY, d / "debug.log", port=0)
    # give the node a little history so sync has something to fetch
    for h in range(1, 4):
        cb = recipes.make_coinbase(h, [(50 * spec.COIN, recipes.OP_TRUE_SCRIPT)], b"history")
        raw = recipes.assemble_block(n.chain.tip, [cb], 1_700_000_000 + 600 * h, EASY, recipes.easy_mine)
        r = n.chain.process_block(raw)
        assert r["verdict"] == "accept"
        n.blocks[r["hash"]] = raw
    yield n, d
    n.close()


def test_replay_end_to_end_against_fake_node(node):
    n, d = node
    out = d / "run"
    args = ["--node", "127.0.0.1", "--port", str(n.port), "--out", str(out), "--genesis", n.chain.genesis_hash[::-1].hex(),
            "--pow-limit", f"{EASY:08x}", "--threads", "2"]
    # the native miner is used if built, else Python; at the easy target every block is instant either way
    rc = rp.main(args)
    assert rc == 0
    results = json.loads((out / "results.json").read_text())
    r = results["results"]
    assert len(r["evalscript"]) == 136 and len(r["checksig"]) >= 16 and len(r["blocks"]) == len(recipes.BLOCK_CASE_ORDER)
    # against the from-spec node every graded vector must agree, and the pending ones follow the strict rule
    for suite in ("evalscript", "blocks"):
        bad = [k for k, v in r[suite].items() if not v["agree"]]
        assert not bad, (suite, bad)
    for k, v in r["checksig"].items():
        assert v["accepted"] == v["expected_strict_der"], k
    # the grader reads it and finds every expected error string in the fake node's debug.log
    g = subprocess.run([sys.executable, str(HERE / "replay" / "grade_replay.py"), str(out / "results.json"),
                        "--log", str(d / "debug.log")], capture_output=True, text=True)
    assert g.returncode == 0, g.stdout + g.stderr
    assert "MISSING" not in g.stdout, g.stdout
    assert results["final_height"] == 3 + 1 + 100 + 3           # history + funding + maturity + 3 valid cases


def test_replay_is_resumable(node):
    n, d = node
    out = d / "run"
    state = json.loads((out / "state.json").read_text())
    assert state["mature"]["count"] == 100
    # a second run finds everything done and only re-syncs
    rc = rp.main(["--node", "127.0.0.1", "--port", str(n.port), "--out", str(out), "--genesis", n.chain.genesis_hash[::-1].hex(),
                  "--pow-limit", f"{EASY:08x}", "--threads", "2"])
    assert rc == 0
    assert json.loads((out / "state.json").read_text())["mature"]["count"] == 100
