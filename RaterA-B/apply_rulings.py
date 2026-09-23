#!/usr/bin/env python3
"""
apply_rulings.py — pre-fill disagreements.csv with the codebook rulings R1–R5.

Fills adjudicated_verdict / adjudicated_category / adjudicator_notes ONLY for
rows that a ruling covers. Everything else stays blank for manual adjudication.
Raw A_/B_ columns are never modified.

Usage:
    python apply_rulings.py --in disagreements.csv --out disagreements_prefilled.csv
Then open disagreements_prefilled.csv, review the pre-filled rows (they are
tagged "R1".."R5" in adjudicator_notes), and fill the blanks.
"""
import argparse
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--in", dest="inp", default="disagreements.csv")
ap.add_argument("--out", default="disagreements_prefilled.csv")
args = ap.parse_args()

d = pd.read_csv(args.inp)
for c in ["adjudicated_verdict", "adjudicated_category", "adjudicator_notes"]:
    if c not in d.columns:
        d[c] = ""
    d[c] = d[c].fillna("").astype(str)

def setrow(mask, verdict, category, tag):
    m = mask & (d["adjudicated_verdict"] == "")
    d.loc[m, "adjudicated_verdict"] = verdict
    d.loc[m, "adjudicated_category"] = category
    d.loc[m, "adjudicator_notes"] = tag
    return int(m.sum())

det = d["detector_category"]
A, B = d["A_verdict"], d["B_verdict"]
An = d["A_notes"].fillna("").str.lower()
Bn = d["B_notes"].fillna("").str.lower()

# R1 indeterminate progress: A=ISSUE, B=NO_ISSUE on progress_no_semantics
n1 = setrow((det == "progress_no_semantics") & (A == "ISSUE") & (B == "NO_ISSUE"),
            "HANDLED", "none", "R1 framework supplies progress role; no label -> other_issues")

# R2 clickable container without role: A says role issue, B says NO_ISSUE
n2 = setrow((A == "ISSUE") & (B == "NO_ISSUE") &
            (d["A_category"] == "missing_semantics_role"),
            "ISSUE", "missing_semantics_role", "R2 missing Role.Button on clickable container")

# R3 clickable Icon with a name: A=ISSUE clickable_icon, B=NO_ISSUE
#    default to ISSUE (raw .clickable never adds a role); flag for size check
n3 = setrow((A == "ISSUE") & (B == "NO_ISSUE") &
            (d["A_category"] == "clickable_icon_not_iconbutton"),
            "ISSUE", "clickable_icon_not_iconbutton",
            "R3 named but roleless raw .clickable; confirm <48dp if downgrading")

# R4 truncation: A=NO_ISSUE, B=ISSUE on text_truncation_scaling -> manual,
#    because the unique-content test needs a human read. Tag only.
m4 = (det == "text_truncation_scaling") & (A == "NO_ISSUE") & (B == "ISSUE") & (d["adjudicated_verdict"] == "")
d.loc[m4, "adjudicator_notes"] = "R4 MANUAL: unique content? ISSUE(low) : NO_ISSUE"
n4 = int(m4.sum())

# R5 hardcoded strings: B=ISSUE with category none, notes mention hard-coded
m5 = (B == "ISSUE") & (d["B_category"].fillna("none") == "none") & Bn.str.contains("hard-coded|hardcoded|localiz")
# gold falls back to A's label (A judged the construct, not the string)
d.loc[m5 & (d["adjudicated_verdict"] == ""), "adjudicated_verdict"] = d.loc[m5, "A_verdict"]
d.loc[m5 & (d["adjudicated_category"] == ""), "adjudicated_category"] = d.loc[m5, "A_category"]
d.loc[m5 & (d["adjudicator_notes"] == ""), "adjudicator_notes"] = "R5 localization is out of scope; A label stands"
n5 = int(m5.sum())

# same-verdict, different-category rows: tag for quick manual pick
m6 = (A == B) & (d["adjudicated_verdict"] == "")
d.loc[m6, "adjudicator_notes"] = "CATEGORY ONLY: both agree on verdict; pick category"
n6 = int(m6.sum())

d.to_csv(args.out, index=False)
left = int((d["adjudicated_verdict"] == "").sum())
print(f"R1 progress             {n1}")
print(f"R2 role on container    {n2}")
print(f"R3 named clickable icon {n3}")
print(f"R4 truncation (manual)  {n4}")
print(f"R5 hardcoded strings    {n5}")
print(f"category-only rows      {n6}")
print(f"\nstill blank for manual adjudication: {left}  -> {args.out}")
