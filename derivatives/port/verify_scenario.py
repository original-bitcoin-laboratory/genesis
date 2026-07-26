"""Cross-language check: verify the C++ port's signed scenarios (scenario.txt)
by running the Python MODEL interpreter's OP_CHECKSIG / OP_CHECKMULTISIG over the
same fixed transaction. The C++ side SIGNED; Python independently VERIFIES."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "model"))
from evalscript_model import valid            # noqa: E402
from tx_sighash import SigChecker, demo_tx     # noqa: E402


def main(path: str) -> int:
    tx, spk0 = demo_tx()
    checker = SigChecker(tx, 0, spk0)
    npass = nfail = 0
    for line in open(path):
        p = line.split()
        if not p:
            continue
        if p[0] == "CHECKSIG":
            pub = bytes.fromhex(p[1]); sig = bytes.fromhex(p[2]); exp = p[3] == "1"
            got = valid([sig, pub, "OP_CHECKSIG"], checker)
        elif p[0] == "CHECKMULTISIG":
            m, n = int(p[1]), int(p[2]); rest = p[3:]
            keys = [bytes.fromhex(x) for x in rest[:n]]
            sigs = [bytes.fromhex(x) for x in rest[n:n + m]]
            exp = rest[n + m] == "1"
            script = ["OP_0"] + sigs + [f"OP_{m}"] + keys + [f"OP_{n}"] + ["OP_CHECKMULTISIG"]
            got = valid(script, checker)
        else:
            continue
        ok = got == exp
        print(f"  [{'PASS' if ok else 'FAIL'}] {p[0]} got={got} want={exp}")
        npass += ok
        nfail += not ok
    print(f"Python verify of C++-signed scenarios: {npass} PASS, {nfail} FAIL")
    return 0 if nfail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "scenario.txt"))
