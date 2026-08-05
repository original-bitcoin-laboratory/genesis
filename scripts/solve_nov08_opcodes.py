#!/usr/bin/env python3
"""Recover the November 2008 opcode values from the genesis merkle root.

`script.h` is not in the November 2008 archive -- it is a four-file fragment (main.cpp, main.h,
node.cpp, node.h) -- so the numeric values of OP_CODESEPARATOR and OP_CHECKSIG cannot be read from
it. They can, however, be *solved for*, because Satoshi published the genesis merkle root in a debug
comment and everything else in the hash preimage is specified by main.h, which is present.

Two unknown bytes, 65,536 possibilities, one 256-bit target. Exactly one pair matches.

Result: November had OP_CODESEPARATOR = 0xa9 and OP_CHECKSIG = 0xaa, two slots below January's
0xab / 0xac -- the two slots January gives to OP_HASH160 and OP_HASH256. Those opcodes did not exist
in November, which is why there was no address format: P2PKH is
`OP_DUP OP_HASH160 <hash> OP_EQUALVERIFY OP_CHECKSIG` and it cannot be written without OP_HASH160.

Exit 0 iff the unique solution is found and equals (0xa9, 0xaa).

    python3 scripts/solve_nov08_opcodes.py

NOT money. Reads nothing from the network; the inputs are literals from the archived source.
"""
import hashlib
import sys

# --- constants, all quoted from the November 2008 main.cpp genesis block -----------------------
#   txNew.vin[0].scriptSig     = CScript() << 247422313;
#   txNew.vout[0].nValue       = 10000;
#   txNew.vout[0].scriptPubKey = CScript() << OP_CODESEPARATOR << CBigNum("0x31D1...D404") << OP_CHECKSIG;
#   block.nTime = 1221069728;  block.nBits = 20;  block.nNonce = 141755;
MERKLE_ROOT = "769a5e93fac273fd825da42d39ead975b5d712b2d50953f35a4fdebdec8083e3"
SCRIPTSIG_INT = 247422313
NVALUE = 10000
PUBKEY_LITERAL = ("31D18A083F381B4BDE37B649AACF8CD0AFD88C53A3587ECDB7FAF23D449C800A"
                  "F1CE516199390BFE42991F10E7F5340F2A63449F0B639A7115C667E5D7B051D404")

# January 2009 values, for the comparison only -- never used as an input to the search.
JAN_CODESEPARATOR, JAN_CHECKSIG = 0xAB, 0xAC


def dsha(b: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


def coinbase_txid(op_codeseparator: int, op_checksig: int) -> tuple[bytes, bytes]:
    """Serialize the November genesis coinbase and return (txid, scriptPubKey).

    Serialization is taken from the archived main.h, not from January:
      CTxIn        : prevout (FLATDATA: 32-byte hash + 4-byte n), then scriptSig
                     -- note there is NO nSequence on CTxIn in November
      CTxOut       : nValue, nSequence, scriptPubKey, and posNext only when (nType & SER_DISK)
                     -- nSequence lives HERE in November, and posNext is disk-only
      CTransaction : nVersion only when !(nType & SER_GETHASH), then vin, vout, nLockTime
                     -- so the hash preimage carries no nVersion
    """
    # CBigNum literals serialize little-endian, so the written value is byte-reversed.
    pubkey = bytes.fromhex(PUBKEY_LITERAL)[::-1]
    assert pubkey[0] == 0x04 and len(pubkey) == 65, "not an uncompressed pubkey after reversal"

    script_sig = bytes([0x04]) + SCRIPTSIG_INT.to_bytes(4, "little")   # debug: coinbase 04695dbf0e
    spk = bytes([op_codeseparator]) + bytes([0x41]) + pubkey + bytes([op_checksig])

    tx = bytearray()
    tx += bytes([1])                                        # vin count
    tx += b"\x00" * 32 + (0xFFFFFFFF).to_bytes(4, "little")  # prevout: null hash, n = -1
    tx += bytes([len(script_sig)]) + script_sig
    tx += bytes([1])                                        # vout count
    tx += NVALUE.to_bytes(8, "little")
    tx += (0xFFFFFFFF).to_bytes(4, "little")                 # nSequence, on CTxOut
    tx += bytes([len(spk)]) + spk
    tx += (0).to_bytes(4, "little")                          # nLockTime
    return dsha(bytes(tx)), spk


def main() -> int:
    print(f"target merkle root : {MERKLE_ROOT}")
    print("unknowns           : OP_CODESEPARATOR, OP_CHECKSIG  (script.h absent from the archive)")
    print("search space       : 65,536 pairs\n")

    solutions = []
    for a in range(256):
        for b in range(256):
            txid, _ = coinbase_txid(a, b)
            if txid[::-1].hex() == MERKLE_ROOT or txid.hex() == MERKLE_ROOT:
                solutions.append((a, b))

    for a, b in solutions:
        print(f"  SOLVED  OP_CODESEPARATOR = 0x{a:02x}   OP_CHECKSIG = 0x{b:02x}")
    print(f"\n  solutions found: {len(solutions)}  (a chance match is ~65536 / 2**256)")

    if len(solutions) != 1:
        print("  FAIL: expected exactly one solution")
        return 1

    a, b = solutions[0]
    if (a, b) != (0xA9, 0xAA):
        print(f"  FAIL: expected (0xa9, 0xaa), got (0x{a:02x}, 0x{b:02x})")
        return 1

    # corroboration: Satoshi's debug line prints scriptPubKey[4], scriptPubKey[5] as "51b0"
    _, spk = coinbase_txid(a, b)
    print(f"\n  debug-print check: scriptPubKey[4],[5] = {spk[4]:02x}{spk[5]:02x}   "
          f"(source comment says 51b0)  {'OK' if (spk[4], spk[5]) == (0x51, 0xB0) else 'MISMATCH'}")
    if (spk[4], spk[5]) != (0x51, 0xB0):
        return 1

    shift = JAN_CODESEPARATOR - a
    print(f"\n  January: OP_CODESEPARATOR = 0x{JAN_CODESEPARATOR:02x}, OP_CHECKSIG = 0x{JAN_CHECKSIG:02x}")
    print(f"  shift November -> January: +{shift}")
    print(f"  the {shift} inserted slots are January's OP_HASH160 (0xa9) and OP_HASH256 (0xaa)")
    print("\n  => neither existed in November 2008, so no P2PKH and no address format:")
    print("     OP_DUP OP_HASH160 <hash> OP_EQUALVERIFY OP_CHECKSIG cannot be written without it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
