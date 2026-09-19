"""Probes for the rules JAN09-B installs that the 317-vector corpus does not
exercise.  Each one is my own construction, not a corpus vector."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jan09b as V

PB, P1 = V.Params(V.JAN09B), V.Params(V.JAN09)
rows = []


def row(rule, probe, jb, j1, note=""):
    rows.append((rule, probe, jb, j1, note))


def mktx(outs, ins=None, locktime=0, seq=0xffffffff):
    ins = ins or [V.TxIn(b"\x11" * 32, 0, b"", seq)]
    return V.Tx(1, ins, [V.TxOut(v, s) for v, s in outs], locktime)


# 1. MoneyRange and the output-sum bound (OBL-C-0003), block-74638 amounts
AMT = 9_223_372_036_854_277_039          # 92,233,720,368.54277039 BTC
tx = mktx([(AMT, b"\x51"), (AMT, b"\x51")])
jb = V.check_transaction(tx, PB)
j1 = V.check_transaction(tx, P1)
row("MoneyRange / output-sum (OBL-C-0003)",
    "two outputs of 9223372036854277039 sat (block 74638)",
    "reject: %s" % jb[1], "accept" if j1[0] else "reject",
    "wrapped int64 sum = %d sat" % tx.value_out(wrap=True))

# single output just over MAX_MONEY
tx2 = mktx([(PB.MAX_MONEY + 1, b"\x51")])
row("MoneyRange bound", "one output of MAX_MONEY+1",
    "reject: %s" % V.check_transaction(tx2, PB)[1],
    "accept" if V.check_transaction(tx2, P1)[0] else "reject")
tx3 = mktx([(PB.MAX_MONEY, b"\x51")])
row("MoneyRange bound", "one output of exactly MAX_MONEY",
    "accept" if V.check_transaction(tx3, PB)[0] else "reject",
    "accept" if V.check_transaction(tx3, P1)[0] else "reject")

# 2. Script caps (OBL-C-0002): 520-byte element, 10,000-byte script, 1,000 stack
big = b"\x4d" + (521).to_bytes(2, "little") + b"\x00" * 521      # PUSHDATA2 521 bytes
for name, script in (("element 521 bytes", big + b"\x51"),
                     ("element 520 bytes",
                      b"\x4d" + (520).to_bytes(2, "little") + b"\x00" * 520 + b"\x51"),
                     ("script 10,001 bytes (OP_1 + NOPs)",
                      b"\x51" + b"\x61" * 10000),
                     ("script 10,000 bytes (OP_1 + NOPs)",
                      b"\x51" + b"\x61" * 9999),
                     ("stack depth 1,001", b"\x51" * 1001),
                     ("stack depth 1,000", b"\x51" * 1000)):
    a, b = [], []
    ra = V.eval_script(script, a, PB)
    rb = V.eval_script(script, b, P1)
    row("script caps (OBL-C-0002)", name,
        "complete" if ra else "fail", "complete" if rb else "fail")

# numeric operand cap (4 bytes)
for name, script in (("5-byte numeric operand to OP_ADD",
                      b"\x05\x01\x00\x00\x00\x00\x51\x93"),
                     ("4-byte numeric operand to OP_ADD",
                      b"\x04\x01\x00\x00\x00\x51\x93")):
    a, b = [], []
    row("numeric operand cap (OBL-C-0012)", name,
        "complete" if V.eval_script(script, a, PB) else "fail",
        "complete" if V.eval_script(script, b, P1) else "fail")

# 3. Block ceiling (OBL-C-0006 / OBL-C-0001): 32 MiB kept, no 1 MB rule
def sized_block(payload_len):
    cb = V.Tx(1, [V.TxIn(b"\x00" * 32, 0xffffffff, b"\x00\x00", 0xffffffff)],
              [V.TxOut(0, b"\x00" * payload_len)], 0)
    root = V.merkle_root([cb.txid()])
    body = V.ser_varint(1) + cb.ser()
    hdr = (1).to_bytes(4, "little") + b"\x00" * 32 + root + \
          (0).to_bytes(4, "little") + (0x207fffff).to_bytes(4, "little") + \
          (0).to_bytes(4, "little")
    return V.Block.from_hex((hdr + body).hex())

for name, n in (("block of 1,000,001 bytes", 1_000_001),
                ("block of 32 MiB + 1 byte", 0x02000000 + 1)):
    blk = sized_block(n)
    a = V.check_block(blk, PB, pow_limit_nbits=0x207fffff)
    b = V.check_block(blk, P1, pow_limit_nbits=0x207fffff)
    def verdict(res):
        if res[0]:
            return "passes CheckBlock"
        if "size limits" in res[1]:
            return "reject: size limits failed"
        return "size clause PASSED (stopped later at: %s)" % res[1].split(": ")[-1]
    row("block ceiling (OBL-C-0001/0006)", "%s (%d bytes)" % (name, blk.size()),
        verdict(a), verdict(b))

# 4. Sigop ceiling (OBL-C-0004): MAX_SIZE/50 = 671,088
cap = PB.MAX_BLOCK_SIGOPS
for name, n in (("%d OP_CHECKSIG (cap)" % cap, cap),
                ("%d OP_CHECKSIG (cap+1)" % (cap + 1), cap + 1)):
    cb = V.Tx(1, [V.TxIn(b"\x00" * 32, 0xffffffff, b"\x00\x00", 0xffffffff)],
              [V.TxOut(0, b"\xac" * n)], 0)
    got = V.tx_sigops(cb)
    over_b = PB.MAX_BLOCK_SIGOPS is not None and got > PB.MAX_BLOCK_SIGOPS
    over_1 = P1.MAX_BLOCK_SIGOPS is not None and got > P1.MAX_BLOCK_SIGOPS
    row("sigop ceiling (OBL-C-0004)", "%s -> counted %d" % (name, got),
        "reject" if over_b else "accept", "no rule" if P1.MAX_BLOCK_SIGOPS is None else "n/a")

# 5. time-based nLockTime (OBL-C-0007)
T = 1_700_000_000
for name, lt, h, t in (("nLockTime 1,700,000,000 at block time 1,699,999,999",
                        T, 200, T - 1),
                       ("nLockTime 1,700,000,000 at block time 1,700,000,001",
                        T, 200, T + 1),
                       ("nLockTime 150 at height 200", 150, 200, T),
                       ("nLockTime 150 at height 100", 150, 100, T)):
    tx = mktx([(1, b"\x51")], locktime=lt, seq=0)
    row("time-based nLockTime (OBL-C-0007)", name,
        "final" if V.is_final(tx, h, t, PB) else "non-final",
        "final" if V.is_final(tx, h, t, P1) else "non-final")

# 6. chain selection by cumulative work (OBL-C-0008), OBL-F-0001's shape
class FakeIdx:
    def __init__(self, height, work):
        self.height, self.work = height, work

cand = FakeIdx(122, 262)     # fewer blocks, more work
tip = FakeIdx(125, 250)      # more blocks, less work
cb = V.Chain(PB); cb.tip = tip
c1 = V.Chain(P1); c1.tip = tip
row("chain selection (OBL-C-0008)", "height 122/work 262 against tip height 125/work 250",
    "reorganise to the heavier branch" if cb.better(cand, tip) else "keep the longer branch",
    "reorganise to the heavier branch" if c1.better(cand, tip) else "keep the longer branch",
    "OBL-F-0001's exhibited failure")

# 7. strict DER (OBL-C-0014) at the encoding level
probes = {
    "canonical 71-byte sig": bytes.fromhex(
        "304402204a8277828b15acab46a86ab4aa7fd733e8eb48d3fc79583ac8ee77764937b191"
        "0220075139151d7b2b5d4ad4c7b6d042dbda33fdfb7bcc962cf742450d45319e8f1301"),
}
import json
cs = json.load(open("/home/claude/genesis/derivatives/vectors/checksig.json"))
for v in cs["vectors"]:
    if v["label"].startswith("der_"):
        probes[v["label"]] = bytes.fromhex(v["script_sig_hex"])[1:]
for name, sig in probes.items():
    row("strict DER (OBL-C-0014)", name,
        "valid encoding" if V.is_valid_signature_encoding(sig) else "rejected",
        "parsed" if V.der_parse_tolerant(sig[:-1]) else "rejected")

print("%-38s %-52s %-34s %s" % ("rule", "probe", "JAN09-B", "JAN09 (v0.1)"))
print("-" * 160)
for r in rows:
    print("%-38s %-52s %-34s %s%s" % (r[0], r[1][:52], r[2], r[3],
                                      ("   [%s]" % r[4]) if r[4] else ""))
