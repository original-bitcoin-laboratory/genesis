"""The committed corpus reproduces from the model, and replays from the rules alone."""
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent


def _run(*args):
    return subprocess.run([sys.executable, *args], cwd=HERE, capture_output=True, text=True)


def test_committed_corpus_matches_regeneration():
    r = _run("export_vectors.py", "--check")
    assert r.returncode == 0, r.stdout + r.stderr


def test_corpus_replays_from_first_principles_without_the_model():
    r = _run("verify_vectors.py", "--no-model")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "0 failures" in r.stdout


def test_corpus_replays_through_the_model():
    r = _run("verify_vectors.py")
    assert r.returncode == 0, r.stdout + r.stderr


def test_manifest_covers_every_json_file():
    names = {ln.split("  ", 1)[1] for ln in (HERE / "MANIFEST.sha256").read_text().splitlines()}
    assert names == {p.name for p in HERE.glob("*.json")}


def test_oracle_value_sums_wrap_as_int64():
    """The from-spec oracle sums values as v0.1 does (int64, main.h:492, main.cpp:844-853), so the
    Aug 2010 overflow transaction (block 74638: two outputs of 92,233,720,368.54277039) wraps to a
    small negative total rather than an unbounded one. Checked here, not as a corpus vector, so the
    pinned corpus and its replay record against the release client are unchanged."""
    sys.path.insert(0, str(HERE))
    import verify_vectors as vv
    each = 9223372036854277039
    assert vv.value_out({"vout": [{"value": each}, {"value": each}]}) == -997538
    assert vv.i64(2**63) == -(2**63) and vv.i64(2**63 - 1) == 2**63 - 1
