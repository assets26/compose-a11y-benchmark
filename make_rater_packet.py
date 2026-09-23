#!/usr/bin/env python3
"""
make_rater_packet.py — cut rater files from verify_pilot_expanded.csv

Why this exists
---------------
verify_pilot_expanded.csv is the enriched MASTER (300 rows, resolved paths,
anchors, 53-line context, imports — about 2.5 MB). It is not what a rater should
open, for two reasons:

  1. It carries `category` and `evidence`, which state the expected answer.
     A rater who reads "clickable_icon_not_iconbutton" before reading the code
     is confirming a label, not detecting an issue.
  2. It is category-blocked, so 20 consecutive rows reveal the category even if
     the column were dropped.

This script produces:

  rater_<name>.csv      what each rater opens: code only, shuffled, blank
                        verdict / issue_category / notes columns
  rater_key_map.csv     rater_row_id -> item_id, so labels can be joined back
                        to the master after both raters are done
  batches/<cat>.csv     optional per-category cuts of the master, for reviewing
                        or adjudicating one category at a time

Blinding policy
---------------
Three categories are hard to judge with no prompt at all, because the code alone
does not tell you what question is being asked:

    color_contrast            needs to know contrast is at issue (and really
                              needs resolved theme colours, not source)
    text_truncation_scaling   needs to know scaling behaviour is at issue
    missing_merge_descendants needs to know grouping is at issue

For those, `category_hint` is populated. For the other 12 it is blank. Whatever
you choose, state it in the paper — partial blinding is defensible, undisclosed
blinding is not.

Usage
-----
    python make_rater_packet.py --master verify_pilot_expanded.csv --raters A B --seed 42
    python make_rater_packet.py --master verify_pilot_expanded.csv --raters A B --no-hints
    python make_rater_packet.py --master verify_pilot_expanded.csv --batches
"""

import argparse
from pathlib import Path

import pandas as pd

# categories where the code alone does not reveal the question being asked
HINTED = {
    "color_contrast",
    "text_truncation_scaling",
    "missing_merge_descendants",
}

# columns a rater sees — deliberately excludes category, evidence, snippet
RATER_COLS = [
    "rater_row_id",
    "repo",
    "decl_name",
    "anchor_line",
    "anchor_text",
    "context",
    "imports",
    "category_hint",
]

BLANK_COLS = ["verdict", "issue_category", "confidence", "notes"]

CODEBOOK = """\
verdict codebook
================
TP            Detector fired, and the code is genuinely an accessibility issue.
FP_DETECTOR   Pattern matched but the construct is not what the rule meant.
              e.g. .clickable sits on a ListItem container, not on the Icon.
FP_HANDLED    A real-looking pattern, but already mitigated: parent semantics{},
              clearAndSetSemantics, decorative-by-design with contentDescription=null.
UNSURE        Cannot be judged from source: needs runtime, theme resolution,
              device testing, or more surrounding code.
DUP           The same defect is already counted under another item_id.

issue_category
--------------
Name the category YOU think applies, from the 15-category scheme, or write
"none" if you judge there is no issue. Leave blank only if verdict is UNSURE.

confidence
----------
high / medium / low — your certainty in the verdict, not in the category.

notes
-----
One or two lines of justification. Required for every FP_* and UNSURE row.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--master", default="verify_pilot_expanded.csv")
    ap.add_argument("--raters", nargs="+", default=["A", "B"])
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no-hints", action="store_true",
                    help="fully blind: no category_hint for any row")
    ap.add_argument("--batches", action="store_true",
                    help="also write per-category cuts of the master")
    ap.add_argument("--outdir", default=".")
    args = ap.parse_args()

    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)

    d = pd.read_csv(args.master)
    print(f"master: {len(d)} rows, {len(d.columns)} columns")

    usable = d[d.get("file_found", True).astype(str) != "False"].copy()
    dropped = len(d) - len(usable)
    if dropped:
        print(f"  dropping {dropped} rows with file_found=False")

    # stable rater-facing id that leaks nothing about category or order
    usable = usable.sample(frac=1, random_state=args.seed).reset_index(drop=True)
    usable["rater_row_id"] = [f"r{i + 1:04d}" for i in range(len(usable))]

    if args.no_hints:
        usable["category_hint"] = ""
    else:
        usable["category_hint"] = usable["category"].where(
            usable["category"].isin(HINTED), ""
        )
    n_hinted = (usable["category_hint"] != "").sum()
    print(f"  category_hint populated for {n_hinted} rows "
          f"({', '.join(sorted(HINTED)) if not args.no_hints else 'none'})")

    # the map that lets you join labels back to the master afterwards
    usable[["rater_row_id", "item_id", "category", "repo", "file",
            "decl_name", "anchor_line"]].to_csv(
        out / "rater_key_map.csv", index=False)
    print(f"  wrote rater_key_map.csv")

    rater_view = usable[RATER_COLS].copy()
    for c in BLANK_COLS:
        rater_view[c] = ""

    for name in args.raters:
        p = out / f"rater_{name}.csv"
        rater_view.to_csv(p, index=False)
        size = p.stat().st_size / 1e6
        print(f"  wrote {p.name}  ({len(rater_view)} rows, {size:.1f} MB)")

    (out / "CODEBOOK.txt").write_text(CODEBOOK, encoding="utf-8")
    print("  wrote CODEBOOK.txt")

    if args.batches:
        bdir = out / "batches"
        bdir.mkdir(exist_ok=True)
        for cat, g in d.groupby("category"):
            g.to_csv(bdir / f"{cat}.csv", index=False)
        print(f"  wrote {d['category'].nunique()} per-category files to batches/")

    print("\nNext: each rater fills verdict / issue_category / confidence / notes")
    print("in their own copy, WITHOUT seeing the other's. Then join on")
    print("rater_row_id via rater_key_map.csv and compute Cohen's kappa.")


if __name__ == "__main__":
    main()
