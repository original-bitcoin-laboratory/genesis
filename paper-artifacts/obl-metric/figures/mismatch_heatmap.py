#!/usr/bin/env python3
"""Figure — axis-level protocol-profile comparison under the January 2009 (v0.1.0) reference.

Regenerated from the reproducible engine (`../obl_metric.py`), not hand-drawn. Each cell states whether a
chain's consensus rule on that axis **matches**, **mismatches**, or is **unspecified** relative to v0.1.0;
the bottom band reports the mismatch rate and coverage. Neutral, colour-blind-safe palette — a cell is
displacement from the reference, never a quality score. Reference-relative; see ../METHOD.md. NOT money.

    python mismatch_heatmap.py [--reference v0.1.0|nov08|whitepaper] [--no-plot]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import obl_metric as M  # noqa: E402

VERDICT_CODE = {"match": 0, "mismatch": 1, "unspecified": 2}


def main() -> int:
    ap = argparse.ArgumentParser(description="Axis-level mismatch heat map (NOT money).")
    ap.add_argument("--reference", default="v0.1.0", choices=M.REFERENCES)
    ap.add_argument("--no-plot", action="store_true")
    args = ap.parse_args()
    ref = args.reference

    axes = M.AXES
    chains = M.CHAINS
    grid = [[VERDICT_CODE[M.compare(ref, c, axes)["rows"][i]["verdict"]] for c in chains]
            for i in range(len(axes))]
    summary = {c: M.compare(ref, c, axes) for c in chains}

    print(f"reference = {ref}")
    for c in chains:
        s = summary[c]
        mr = "undef" if s["mismatch_rate"] is None else f"{s['mismatch_rate']:.2f}"
        print(f"  {c}: mismatch {mr}, coverage {s['coverage']:.2f} ({s['differing']}/{s['jointly_specified']})")
    if args.no_plot:
        return 0

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.colors import ListedColormap
        from matplotlib.patches import Patch
        import numpy as np
    except ImportError:
        print("matplotlib not installed — printed verdicts above are the figure content.")
        return 0

    # colour-blind-safe, non-evaluative: match=teal, mismatch=amber, unspecified=grey
    cmap = ListedColormap(["#3f6478", "#d9a34a", "#c9ccce"])
    arr = np.array(grid)
    fig, ax = plt.subplots(figsize=(6.4, 7.6))
    ax.imshow(arr, cmap=cmap, aspect="auto", vmin=0, vmax=2)

    ax.set_xticks(range(len(chains)))
    ax.set_xticklabels(chains)
    ax.set_yticks(range(len(axes)))
    ax.set_yticklabels([a["name"] for a in axes], fontsize=8)
    ax.set_xticks([x - 0.5 for x in range(1, len(chains))], minor=True)
    ax.set_yticks([y - 0.5 for y in range(1, len(axes))], minor=True)
    ax.grid(which="minor", color="white", linewidth=1.2)
    ax.tick_params(which="minor", length=0)

    # summary band under the map: mismatch rate + coverage
    lines = []
    for c in chains:
        s = summary[c]
        mr = "undef" if s["mismatch_rate"] is None else f"{s['mismatch_rate']:.2f}"
        # ⛔ FOUR ROUNDS OLD: this read f"{c}\n{mr}\ncov ..." and the chain name printed TWICE --
        #    once as the column tick label, once here. The axis already carries the name.
        lines.append(f"{mr}\ncov {s['coverage']:.2f}")
    for j, txt in enumerate(lines):
        ax.text(j, len(axes) + 0.15, txt, ha="center", va="top", fontsize=7.5, color="#555")

    # ⛔ ALSO FOUR ROUNDS OLD: pad=10 put the title straight through the disclaimer drawn at
    #    y=1.03. Two visual defects that no gate can see, reported in every round and fixed in
    #    none of them. ★ A defect no instrument checks survives exactly as long as nobody looks.
    ax.set_title(f"Consensus-profile comparison under the {ref} reference", fontsize=11, pad=24)
    ax.legend(handles=[Patch(color="#3f6478", label="matches reference"),
                       Patch(color="#d9a34a", label="mismatches reference"),
                       Patch(color="#c9ccce", label="unspecified")],
              loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3, frameon=False, fontsize=8)
    ax.text(0.0, 1.03, "Reference-relative displacement, not a metric or quality score; every cell is "
            "source-anchored (../METHOD.md). NOT money.", transform=ax.transAxes, fontsize=6.5, color="#7d7d7d")
    fig.tight_layout()
    out = Path(__file__).resolve().parent / f"mismatch_heatmap_{ref.replace('.', '')}.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    # ★ R5: the figure now records the dataset it depicts, so freshness is a CONTENT question
    #   rather than a filesystem-clock question. A clock check cannot tell a correct rebuild
    #   order from a stale artifact; a content check can.
    import json as _j
    _p = Path(__file__).resolve().parent / "figure_provenance.json"
    _p.write_text(_j.dumps({"n_axes": len(axes),
                            "rates": {c: ("%.4f" % summary[c]["mismatch_rate"])
                                      for c in chains if summary[c]["mismatch_rate"] is not None}},
                           indent=1), encoding="utf-8")
    print("wrote", out.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
