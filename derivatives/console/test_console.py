"""The full-stack console drives a complete session on both X-chains: mine, pay, a
full-vocabulary OP_CAT contract created + spent, a signed marketplace listing with
reputation, and a deterministic evidence bundle. This is NOV08-Full's executable form
(and its JAN09-X twin). Evidence: MODEL."""

import json
import pathlib
import sys

import pytest

_HERE = pathlib.Path(__file__).resolve().parent
for sub in ("model", "wallet", "nov08x", "ledger", "market", "studio"):
    sys.path.insert(0, str(_HERE.parent / sub))
sys.path.insert(0, str(_HERE))

from console import XConsole, describe_spk, run_session
from consensus import Rules

PROFILES = [("nov08", "NOV08-X"), ("jan09", "JAN09-X")]


@pytest.mark.parametrize("profile,name", PROFILES)
def test_full_session_runs_on_both_chains(profile, name):
    c = run_session(Rules.load(profile), name)
    assert c.led.height >= 6
    assert c.balance() > 0
    assert len(c.led.utxos) > 0
    # a signed product listed and a review raised the seller's reputation
    assert c.products and c.products[0].verify()
    assert c.market.user(c.products[0].user_hash()).atom_count() >= 1
    # the OP_CAT hash-lock contract was created and then spent (an event trail)
    assert any("hash-lock" in e for e in c.events)
    assert any("spent the hash-lock" in e for e in c.events)


@pytest.mark.parametrize("profile,name", PROFILES)
def test_evidence_bundle_exports(profile, name, tmp_path):
    path = tmp_path / "bundle.json"
    c = run_session(Rules.load(profile), name, export_path=path)
    bundle = json.loads(path.read_text())
    assert bundle["profile"] == profile.upper() if profile == "nov08" else "JAN09"
    assert bundle["constitution"]["COIN"] == c.rules.COIN
    assert bundle["height"] == c.led.height
    assert bundle["utxo_count"] == len(c.led.utxos)
    assert any(u["coinbase"] for u in bundle["utxos"])       # unspent coinbases remain
    assert bundle["products"][0]["verified"] is True


def test_hashlock_is_a_btc_disabled_contract():
    # the console's contract uses OP_CAT — describe_spk labels it as BTC-disabled
    c = XConsole(Rules.load("jan09"), "JAN09-X")
    c.mine_until_mature(); c.mine()
    (op, halves) = c.create_hashlock(b"abcdEFGH", c.rules.get_block_value(-1) // 5)
    kind = describe_spk(c.led.utxos[op].spk)
    assert "OP_CAT" in kind and "BTC-disabled" in kind
    c.mine()
    from wallet import Wallet, p2pk
    c.spend_hashlock(op, halves, p2pk(Wallet().new_key()))
    assert op not in c.led.utxos                       # the locked coin was spent


def test_the_two_constitutions_differ_in_the_bundle():
    nov = run_session(Rules.load("nov08"), "NOV08-X")
    jan = run_session(Rules.load("jan09"), "JAN09-X")
    assert nov.rules.COIN == 1_000_000 and jan.rules.COIN == 100_000_000
    assert nov.rules.subsidy_base // nov.rules.COIN == 100          # November's 100-coin reward
    assert jan.rules.subsidy_base // jan.rules.COIN == 50           # January's 50
    assert nov.rules.coinbase_rule == "equal" and jan.rules.coinbase_rule == "le"
