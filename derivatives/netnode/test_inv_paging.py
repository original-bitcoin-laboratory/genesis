"""`getblocks` must be answered in PAGES, and the pages must reach the tip.

⛔ WHY THIS TEST EXISTS. Until 28 August 2026 `ChainState.blocks_after` returned the entire
remainder of the chain in a single `inv`, unbounded. At 36 bytes per entry that is 3.1 MB for a
90,246-block chain against a 4 MiB `MAX_MESSAGE_SIZE`, so jan09x was roughly nine days from the
point where `getblocks` from genesis could not be served AT ALL -- no new peer could sync it, and
the status probe already could not read it: it timed out and published `height: 0` for a chain at
90,246, reporting a month of mining as nothing.

The two properties below are what make that impossible to reintroduce:

  1. a single answer is bounded -- it can never approach the wire cap; and
  2. paging is COMPLETE -- walking page by page from genesis still reaches the tip, so bounding
     the answer costs no reachability.

Property 2 is the one that matters. A cap alone would be a silent truncation.
"""
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
for _p in ("model", "p2p", "nov08x", "wallet", "profiles"):
    sys.path.insert(0, str(_HERE.parent / _p))
sys.path.insert(0, str(_HERE))

from chainstate import ChainState                          # noqa: E402


class _FakeChain:
    """Only what blocks_after touches: an ordered active list of block hashes."""

    def __init__(self, n):
        # UNIQUE hashes. A first draft used bytes([i % 251]) * 32, which repeats every 251
        # blocks; blocks_after builds a hash->index map, so duplicates collapse and the
        # walk reads nonsense. The test failed and the code was right -- the data was wrong.
        self.hashes = [i.to_bytes(32, "big") for i in range(n)]


def _state(n):
    st = ChainState.__new__(ChainState)          # bypass __init__: blocks_after reads .active only
    st.active = _FakeChain(n).hashes
    return st


def test_a_single_answer_is_bounded():
    """However long the chain, one inv never exceeds the cap -- 2000 x 36 B is far under 4 MiB."""
    st = _state(ChainState.MAX_INV_BLOCKS * 3)
    page = st.blocks_after([st.active[0]], b"\x00" * 32)
    assert len(page) == ChainState.MAX_INV_BLOCKS, "answer must be capped at one page"
    assert len(page) * 36 < 4 * 1024 * 1024, "a page must stay well under MAX_MESSAGE_SIZE"


def test_paging_still_reaches_the_tip():
    """Bounding the answer must not cost reachability: page by page still arrives at the tip.

    This is the property the cap could silently break. Walking from genesis exactly as a peer
    does -- locator = the last hash of the previous page -- must enumerate every block after
    genesis, in order, with nothing dropped and nothing repeated.
    """
    n = ChainState.MAX_INV_BLOCKS * 2 + 137      # deliberately not a whole number of pages
    st = _state(n)
    seen, locator, pages = [], [st.active[0]], 0
    while True:
        page = st.blocks_after(locator, b"\x00" * 32)
        if not page:
            break
        seen += page
        locator = [page[-1]]
        pages += 1
        assert pages < 100, "walk did not terminate"
    assert pages > 1, "the test chain must be long enough to actually page"
    assert seen == st.active[1:], "paging must enumerate the whole chain after genesis, in order"
    assert len(seen) == len(set(seen)), "no block may be served twice"


def test_short_chain_is_answered_in_one_page():
    """A chain shorter than the cap is still answered whole -- paging costs nothing at small n."""
    st = _state(10)
    page = st.blocks_after([st.active[0]], b"\x00" * 32)
    assert page == st.active[1:]


def test_the_real_chain_sizes_now_fit_the_wire():
    """The heights that provoked this: jan09x 90,246 and nov08x 67,347 on 28 Aug 2026."""
    for height in (90_246, 67_347, 116_508, 1_000_000):
        st = _state(height)
        page = st.blocks_after([st.active[0]], b"\x00" * 32)
        assert len(page) * 36 < 4 * 1024 * 1024, f"height {height} would still overflow the wire"
