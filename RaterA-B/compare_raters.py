#!/usr/bin/env python3
"""
compare_raters.py — agreement between two rater files, plus detector precision.

Inputs (all keyed on rater_row_id):
  --a        rater_A_labels.csv   (Claude)
  --b        rater_B_labels.csv   (GPT, same columns)
  --map      rater_key_map.csv    (rater_row_id -> item_id, detector category)

Outputs:
  agreement_report.txt      kappa on verdict and on category, overall and per detector category
  disagreements.csv         rows where verdict OR category differ, for adjudication
  derived_precision.csv     per detector category: TP / FP_DETECTOR / FP / UNSURE from each rater

Derivation rule (per rater):
  TP           rater verdict == ISSUE and detector category in {issue_category} ∪ other_issues
  FP_DETECTOR  rater verdict == ISSUE but detector category not among the rater's categories
  FP           rater verdict in {NO_ISSUE, HANDLED}
  UNSURE       excluded from precision, reported separately

Usage:
  python compare_raters.py --a rater_A_labels.csv --b rater_B_labels.csv --map rater_key_map.csv
"""
import argparse
from collections import Counter, defaultdict
import pandas as pd


def cohen_kappa(x, y):
    x, y = list(x), list(y)
    n = len(x)
    if n == 0:
        return float("nan")
    po = sum(a == b for a, b in zip(x, y)) / n
    cx, cy = Counter(x), Counter(y)
    pe = sum(cx[k] * cy.get(k, 0) for k in cx) / (n * n)
    return float("nan") if pe == 1 else (po - pe) / (1 - pe)


def cats(row):
    s = set()
    if isinstance(row.get("issue_category"), str) and row["issue_category"] not in ("", "none"):
        s.add(row["issue_category"].strip())
    if isinstance(row.get("other_issues"), str):
        s |= {c.strip() for c in row["other_issues"].split(",") if c.strip()}
    return s


def derive(row, det):
    v = row["verdict"]
    if v == "UNSURE":
        return "UNSURE"
    if v in ("NO_ISSUE", "HANDLED"):
        return "FP"
    if v == "ISSUE":
        return "TP" if det in cats(row) else "FP_DETECTOR"
    return "INVALID"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--map", required=True)
    args = ap.parse_args()

    a = pd.read_csv(args.a).set_index("rater_row_id")
    b = pd.read_csv(args.b).set_index("rater_row_id")
    m = pd.read_csv(args.map).set_index("rater_row_id")

    ids = a.index.intersection(b.index).intersection(m.index)
    a, b, m = a.loc[ids], b.loc[ids], m.loc[ids]
    lines = [f"rows compared: {len(ids)}"]

    # ---- verdict agreement
    kv = cohen_kappa(a["verdict"], b["verdict"])
    pv = (a["verdict"] == b["verdict"]).mean()
    lines += ["", f"VERDICT   agreement={pv:.3f}  kappa={kv:.3f}"]

    # collapsed: defect vs no-defect (ISSUE vs NO_ISSUE/HANDLED), UNSURE dropped
    keep = (a["verdict"] != "UNSURE") & (b["verdict"] != "UNSURE")
    ca = a.loc[keep, "verdict"].map(lambda v: "ISSUE" if v == "ISSUE" else "NO")
    cb = b.loc[keep, "verdict"].map(lambda v: "ISSUE" if v == "ISSUE" else "NO")
    lines += [f"DEFECT?   agreement={(ca==cb).mean():.3f}  kappa={cohen_kappa(ca, cb):.3f}  (n={keep.sum()}, UNSURE dropped)"]

    # ---- category agreement (primary only, among rows both call ISSUE)
    both = (a["verdict"] == "ISSUE") & (b["verdict"] == "ISSUE")
    if both.sum():
        kc = cohen_kappa(a.loc[both, "issue_category"], b.loc[both, "issue_category"])
        pc = (a.loc[both, "issue_category"] == b.loc[both, "issue_category"]).mean()
        lines += [f"CATEGORY  agreement={pc:.3f}  kappa={kc:.3f}  (n={both.sum()}, primary category, both ISSUE)"]
        # lenient: any overlap between category sets
        overlap = [bool(cats(a.loc[i]) & cats(b.loc[i])) for i in a.index[both]]
        lines += [f"CATEGORY  any-overlap agreement={sum(overlap)/len(overlap):.3f}"]

    # ---- per detector category
    lines += ["", "PER DETECTOR CATEGORY (verdict kappa / n):"]
    for det, g in m.groupby("category"):
        idx = g.index
        k = cohen_kappa(a.loc[idx, "verdict"], b.loc[idx, "verdict"])
        p = (a.loc[idx, "verdict"] == b.loc[idx, "verdict"]).mean()
        lines += [f"  {det:32} agree={p:.2f}  kappa={k:6.3f}  n={len(idx)}"]

    # ---- derived precision per detector category
    rows = []
    for det, g in m.groupby("category"):
        da = Counter(derive(a.loc[i], det) for i in g.index)
        db = Counter(derive(b.loc[i], det) for i in g.index)
        def prec(c):
            tp, fpd, fp = c["TP"], c["FP_DETECTOR"], c["FP"]
            return tp / (tp + fpd + fp) if (tp + fpd + fp) else float("nan")
        rows.append({"detector_category": det, "n": len(g),
                     "A_TP": da["TP"], "A_FP_DETECTOR": da["FP_DETECTOR"], "A_FP": da["FP"], "A_UNSURE": da["UNSURE"], "A_precision": round(prec(da), 3),
                     "B_TP": db["TP"], "B_FP_DETECTOR": db["FP_DETECTOR"], "B_FP": db["FP"], "B_UNSURE": db["UNSURE"], "B_precision": round(prec(db), 3)})
    pd.DataFrame(rows).to_csv("derived_precision.csv", index=False)

    # ---- disagreements for adjudication
    dis = a.index[(a["verdict"] != b["verdict"]) | (a["issue_category"] != b["issue_category"])]
    out = pd.DataFrame({
        "rater_row_id": dis,
        "item_id": m.loc[dis, "item_id"].values,
        "detector_category": m.loc[dis, "category"].values,
        "A_verdict": a.loc[dis, "verdict"].values, "B_verdict": b.loc[dis, "verdict"].values,
        "A_category": a.loc[dis, "issue_category"].values, "B_category": b.loc[dis, "issue_category"].values,
        "A_notes": a.loc[dis, "notes"].values, "B_notes": b.loc[dis, "notes"].values,
        "adjudicated_verdict": "", "adjudicated_category": "", "adjudicator_notes": "",
    })
    out.to_csv("disagreements.csv", index=False)
    lines += ["", f"disagreements to adjudicate: {len(dis)}  -> disagreements.csv",
              "derived precision per category -> derived_precision.csv"]

    open("agreement_report.txt", "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
