"""Python side of the port differential: run vectors through the MODEL, print the
same 'line => value' format as port.exe so the two can be diffed byte-for-byte."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "model"))
from evalscript_model import num, run  # noqa: E402


def parse(line: str) -> list:
    out = []
    for tok in line.split():
        if tok.startswith("n:"):
            out.append(num(int(tok[2:])))
        elif tok.startswith("x:"):
            out.append(bytes.fromhex(tok[2:]))
        else:
            out.append(tok)
    return out


def main(path: str) -> int:
    for line in open(path):
        line = line.rstrip("\n")
        if not line or line.startswith("#"):
            continue
        ok, stack = run(parse(line))
        if not ok:
            v = "FAIL"
        elif not stack:
            v = "(empty-stack)"
        else:
            top = stack[-1]
            v = "(empty)" if len(top) == 0 else top.hex()
        print(f"{line} => {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "vectors.txt"))
