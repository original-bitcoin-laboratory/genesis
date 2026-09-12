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
