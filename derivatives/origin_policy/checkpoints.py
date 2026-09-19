"""Hard-coded checkpoints, executed -- MODEL.

The January 2009 client accepts any block whose proof of work and ancestry are valid; nothing in it
names a block hash other than the genesis constant. Commit ae922a36a (17 July 2010, version 0.3.2,
message "security safeguards, limited addr messages") adds to `AcceptBlock` three hard-coded
pairs of height and hash, and rejects a block at one of those heights whose hash differs:

    // Check that the block chain matches the known block chain up to a checkpoint
    if (pindexPrev->nHeight+1 == 11111 && hash != uint256("0x0000000069e2...7c1d"))
        return error("AcceptBlock() : rejected by checkpoint lockin at 11111");

Further checkpoints followed: 70567 in 813505cc1 (27 July 2010, a message about Crypto++ and SHA-256
speed) and 74000 in 4bd188c43 (15 August 2010, "misc changes", the day of the overflow incident; the
author's post of that evening calls it "the most recent security lockin"). Constitution row
OBL-C-0016.

This module ports the rule as it stood at 4bd188c43 (five checkpoints, one combined test) beside the
January client, which has none, and exhibits a block at height 11111 with a hash other than the
checkpointed one: January accepts it (proof of work and ancestry being taken as valid here), the
July 2010 rule rejects it. Evidence level: MODEL; the block is a stand-in whose hash is the input
under test, and the checkpoint hashes are the ones in the commit. NOT money.
"""
from __future__ import annotations

# height -> block hash, as written into AcceptBlock by 4bd188c43 (the hashes as the source spells them)
CHECKPOINTS_20100815 = {
    11111: "0000000069e244f73d78e8fd29ba2fd2ed618bd6fa2ee92559f542fdb26e7c1d",
    33333: "000000002dd5588a74784eaa7ab0507a18ad16a236e7b1ce69f00d7ddfb5d0a6",
    68555: "00000000001e1b4903550a0b96e9a9405c8a95f387162e4944e8d9fbe501cd6a",
    70567: "00000000006a49b14bcf27462068f1264c961f11fa2e0eddd2be0791e1d4124a",
    74000: "0000000000573993a3c9e41ce34471c079dcf5f52a0e824a81e7f953b8661a20",
}
CHECKPOINTS_20100717 = {h: CHECKPOINTS_20100815[h] for h in (11111, 33333, 68555)}


def accept_block_v01(height: int, block_hash: str):
    """v0.1 AcceptBlock has no checkpoint clause: for the decision under test, every block passes."""
    return True, "ok"


def accept_block_checkpointed(height: int, block_hash: str, checkpoints: dict = CHECKPOINTS_20100815):
    """The clause added by ae922a36a and extended through 4bd188c43: `nHeight == H && hash != KNOWN` rejects."""
    for h, known in checkpoints.items():
        if height == h and block_hash.lower() != known:
            return False, "rejected by checkpoint lockin" + (f" at {h}" if checkpoints is CHECKPOINTS_20100717 else "")
    return True, "ok"


def report() -> None:
    other = "00000000004a3b7e5f6c9d2a1b0e8f7d6c5b4a39281706f5e4d3c2b1a0f9e8d7"
    print("HARD-CODED CHECKPOINTS -- executed side by side (MODEL)")
    for height, h in ((11111, other), (11111, CHECKPOINTS_20100815[11111]), (11112, other), (74000, other)):
        print(f"  height {height:>6} hash {h[:12]}..  v0.1 {accept_block_v01(height, h)}   0.3.2+ {accept_block_checkpointed(height, h)}")
    print("  => from 17 July 2010 a chain must pass through named blocks at named heights; the January client")
    print("     has no such rule and follows proof of work alone. NOT money.")


if __name__ == "__main__":
    report()
