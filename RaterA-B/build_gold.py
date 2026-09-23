#!/usr/bin/env python3
"""
build_gold.py — assemble verified_gold.csv from raters + adjudication.

Inputs (same folder):
  rater_A_labels.csv           Claude, 300 rows
  rater_B_labels.csv           GPT,    300 rows
  disagreements_adjudicated.csv  192 rows with adjudicated_* filled (your file)
  rater_key_map.csv            rater_row_id -> item_id, detector category, file, anchor_line
  verify_pilot_expanded.csv    for file / anchor_line (dedup key) and context

Logic
  agreed rows (A == B on verdict AND category)  -> take A
  disagreed rows                                 -> take adjudicated_*
  gold_source column records which
  detector_result derived per row:
      TP           gold ISSUE and detector category == gold category
      TP_OTHER     gold ISSUE, different primary category, detector's in other_issues (either rater)
      FP_DETECTOR  gold ISSUE, detector category not supported
      FP           gold NO_ISSUE or HANDLED
      UNSURE       excluded from precision
  dedup on (file, anchor_line): keep the row whose detector category == gold category
  if any, else the first; duplicates listed in gold_duplicates_removed.csv

Usage
  python build_gold.py
"""
import pandas as pd

A = pd.read_csv("rater_A_labels.csv").set_index("rater_row_id")
B = pd.read_csv("rater_B_labels.csv").set_index("rater_row_id")
ADJ = pd.read_csv("disagreements_adjudicated.csv").set_index("rater_row_id")
MAP = pd.read_csv("rater_key_map.csv").set_index("rater_row_id")
EXP = pd.read_csv("verify_pilot_expanded.csv").set_index("item_id")

for df in (A, B, ADJ):
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].fillna("").astype(str).str.strip()

rows = []
for rid in A.index:
    a, b = A.loc[rid], B.loc[rid]
    if rid in ADJ.index:
        adj = ADJ.loc[rid]
        verdict, cat, src = adj["adjudicated_verdict"], adj["adjudicated_category"], "adjudicated"
        note = adj.get("adjudicator_notes", "")
    else:
        verdict, cat, src = a["verdict"], a["issue_category"], "agreed"
        note = ""
    if verdict != "ISSUE":
        cat = "none"
    det = MAP.loc[rid, "category"]
    others = set()
    for r in (a, b):
        others |= {c.strip() for c in str(r.get("other_issues", "")).split(",") if c.strip()}
    if verdict == "UNSURE":
        res = "UNSURE"
    elif verdict in ("NO_ISSUE", "HANDLED"):
        res = "FP"
    elif det == cat:
        res = "TP"
    elif det in others:
        res = "TP_OTHER"
    else:
        res = "FP_DETECTOR"
    item = MAP.loc[rid, "item_id"]
    rows.append({
        "item_id": item, "rater_row_id": rid,
        "repo": MAP.loc[rid, "repo"], "file": MAP.loc[rid, "file"],
        "anchor_line": MAP.loc[rid, "anchor_line"], "decl_name": MAP.loc[rid, "decl_name"],
        "detector_category": det,
        "gold_verdict": verdict, "gold_category": cat, "gold_source": src,
        "detector_result": res,
        "rater_A_verdict": a["verdict"], "rater_A_category": a["issue_category"],
        "rater_B_verdict": b["verdict"], "rater_B_category": b["issue_category"],
        "other_issues": ",".join(sorted(others)),
        "adjudicator_notes": note,
        "anchor_text": EXP.loc[item, "anchor_text"] if item in EXP.index else "",
        "context": EXP.loc[item, "context"] if item in EXP.index else "",
    })

g = pd.DataFrame(rows)

# ---- dedup on (file, anchor_line)
g["_match"] = (g.detector_category == g.gold_category).astype(int)
g = g.sort_values(["file", "anchor_line", "_match"], ascending=[True, True, False])
dup_mask = g.duplicated(subset=["file", "anchor_line"], keep="first")
removed = g[dup_mask].drop(columns="_match")
gold = g[~dup_mask].drop(columns="_match").sort_values("item_id").reset_index(drop=True)

gold.to_csv("verified_gold.csv", index=False)
removed.to_csv("gold_duplicates_removed.csv", index=False)
g.drop(columns="_match").sort_values("item_id").to_csv("verified_gold_with_duplicates.csv", index=False)

# ---- summary
print(f"items in: {len(g)}   duplicates removed: {len(removed)}   gold items: {len(gold)}")
print("\ngold_verdict:"); print(gold.gold_verdict.value_counts().to_string())
print("\ngold_source:"); print(gold.gold_source.value_counts().to_string())
print("\ndetector_result:"); print(gold.detector_result.value_counts().to_string())
print("\ngold ISSUE by category:"); print(gold[gold.gold_verdict == "ISSUE"].gold_category.value_counts().to_string())

prec = (gold[gold.detector_result != "UNSURE"]
        .groupby("detector_category").detector_result
        .value_counts().unstack(fill_value=0))
for c in ["TP", "TP_OTHER", "FP_DETECTOR", "FP"]:
    if c not in prec: prec[c] = 0
prec["n"] = prec[["TP", "TP_OTHER", "FP_DETECTOR", "FP"]].sum(axis=1)
prec["precision_strict"] = (prec.TP / prec.n).round(3)
prec["precision_lenient"] = ((prec.TP + prec.TP_OTHER) / prec.n).round(3)
prec = prec[["n", "TP", "TP_OTHER", "FP_DETECTOR", "FP", "precision_strict", "precision_lenient"]]
prec.to_csv("detector_precision.csv")
print("\nDETECTOR PRECISION (post-dedup, UNSURE excluded):")
print(prec.to_string())
