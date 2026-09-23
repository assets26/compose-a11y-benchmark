#!/usr/bin/env python3
"""
score_benchmark.py — turn runs/*.jsonl into result tables.

DETECT  per model: precision / recall / F1 on has_issue (positives = gold ISSUE,
        negatives = gold NO_ISSUE/HANDLED + labeled negatives); category accuracy
        (strict = primary match, lenient = gold category anywhere in issues);
        unparsed rate; abstain rate; Brier score on confidence; split by
        gold_source (agreed vs adjudicated) if present in gold.
REPAIR  per model: parse rate; brace/paren balance; API-validity (hallucination
        patterns); addresses-defect heuristic; preservation ratio.
REFLECT per model: how often it changed its mind, and whether changes moved
        toward or away from gold; calibration after reflection.

Usage
  python score_benchmark.py --runs runs --gold verified_gold.csv --out results
"""
import argparse, difflib, json, re
from pathlib import Path
import pandas as pd

# --------------------------------------------------------------- repair checks
# invented / misplaced API patterns (the stateDescription-as-parameter class)
HALLUCINATION_PATTERNS = {
    "stateDescription_as_param":   r"\b(toggleable|clickable|selectable|Switch|Checkbox|RadioButton|Row|Column|Box|Text|Icon)\s*\([^)]*\bstateDescription\s*=",
    "contentDescription_on_layout": r"\b(Row|Column|Box|Text|Surface|Card|ListItem)\s*\([^)]*\bcontentDescription\s*=",
    "role_on_component":           r"\b(ListItem|Row|Column|Box|Text|Icon|Card|Surface)\s*\([^)]*\brole\s*=",
    "heading_as_param":            r"\b(Text|Row|Column)\s*\([^)]*\bheading\s*=",
    "invented_modifier":           r"Modifier\.(accessible|accessibilityLabel|accessibilityRole|contentDescription|talkback|a11y)\s*\(",
    "invented_semantics_key":      r"semantics\s*\{[^}]*\b(accessibilityLabel|label|hint|accessibilityRole|isButton|announce)\s*=",
    "onClickLabel_outside_click":  r"^(?!.*\.(clickable|combinedClickable)).*\bonClickLabel\s*=",
    "min_size_wrong_name":         r"minimumTouchTargetSize|minTouchTarget|minimumInteractiveSize\b",
}
VALID_FIX_PATTERNS = {
    "missing_semantics_role":        r"role\s*=\s*Role\.\w+",
    "missing_content_description":   r"contentDescription\s*=\s*(?!null)",
    "decorative_mislabeled":         r"contentDescription\s*=\s*null",
    "missing_heading_semantics":     r"semantics\s*\{[^}]*heading\(\)",
    "missing_state_description":     r"(stateDescription\s*=|toggleable\(|selectable\()",
    "missing_merge_descendants":     r"(mergeDescendants\s*=\s*true|toggleable\(|selectable\(|semantics\(\s*mergeDescendants)",
    "textfield_no_label":            r"label\s*=\s*\{",
    "progress_no_semantics":         r"(progressSemantics|contentDescription\s*=|stateDescription\s*=)",
    "pointerinput_no_semantics":     r"(semantics\s*\{|\.clickable|customActions|onClick\s*\()",
    "touch_target_size":             r"(48\.dp|minimumInteractiveComponentSize|sizeIn\(|defaultMinSize\()",
    "clickable_icon_not_iconbutton": r"\bIconButton\s*\(",
    "missing_interaction_semantics": r"onClickLabel\s*=",
    "error_state_no_semantics":      r"(supportingText\s*=|semantics\s*\{[^}]*error\()",
    "text_truncation_scaling":       r"(maxLines\s*=\s*[2-9]|softWrap\s*=\s*true|\.sp\b.*fontScale|nonScaledSp)",
    "color_contrast":                r"(MaterialTheme\.colorScheme|contentColorFor|Color\(0x)",
}

def balanced(code):
    return code.count("{") == code.count("}") and code.count("(") == code.count(")")


def looks_truncated(raw):
    """True if generation stopped mid-output rather than the model emitting
    bad JSON. Repair asks the model to re-emit the whole composable, so long
    inputs can exhaust max_tokens. That is a budget limit shared by every
    model, not a competence difference, and must not be reported as a
    malformed-output rate. Cap-agnostic test: a completed reply ends on the
    closing brace (optionally inside a fence)."""
    if not raw or not isinstance(raw, str):
        return False
    t = raw.strip().rstrip("`").strip()
    return not t.endswith("}") and len(t) > 400

def repair_scores(orig, fixed, category):
    if not fixed or not isinstance(fixed, str):
        return dict(parsed=False)
    halluc = [k for k, rx in HALLUCINATION_PATTERNS.items() if re.search(rx, fixed, re.M)]
    addressed = bool(re.search(VALID_FIX_PATTERNS.get(category, r"$^"), fixed))
    ratio = difflib.SequenceMatcher(None, orig.split(), fixed.split()).ratio()
    o_lines = [l.strip() for l in orig.splitlines() if l.strip()]
    f_lines = set(l.strip() for l in fixed.splitlines() if l.strip())
    dropped = sum(1 for l in o_lines if l not in f_lines)
    drop_frac = dropped / max(1, len(o_lines))
    # A model that returns a fragment instead of the composable scores a free
    # api_valid=True (no code -> no hallucinated API to match) and a free
    # syntactic_ok. Gate both on the reply actually being the composable back.
    substantive = ratio >= 0.5 and drop_frac <= 0.5
    return dict(parsed=True, substantive=substantive,
                syntactic_ok=balanced(fixed), api_valid=not halluc,
                hallucinations=",".join(halluc), addresses_defect=addressed,
                similarity=round(ratio, 3), lines_dropped=dropped, lines_dropped_frac=round(drop_frac, 3))

# --------------------------------------------------------------- helpers
def load(path):
    return [json.loads(l) for l in Path(path).open() if l.strip()]

def cats_from(parsed):
    if not parsed: return []
    return [i.get("category", "") for i in parsed.get("issues", []) if isinstance(i, dict)]

def brier(rows):
    v = [((r["conf"] / 100.0) - (1.0 if r["correct"] else 0.0)) ** 2 for r in rows if r["conf"] is not None]
    return round(sum(v) / len(v), 3) if v else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs")
    ap.add_argument("--gold", default="verified_gold.csv")
    ap.add_argument("--out", default="results")
    a = ap.parse_args()
    Path(a.out).mkdir(exist_ok=True)
    gold = pd.read_csv(a.gold).set_index("item_id")
    src = gold["gold_source"].to_dict() if "gold_source" in gold else {}
    others = gold["other_issues"].fillna("").to_dict() if "other_issues" in gold else {}

    det_rows, cat_rows, rep_rows, ref_rows, item_rows = [], [], [], [], []
    for f in sorted(Path(a.runs).glob("*__detect.jsonl")):
        model = f.name.split("__")[0]
        recs = load(f)
        tp = fp = tn = fn = 0; unparsed = abst = 0; cal = []; strict = lenient = n_issue = 0
        excluded = 0
        by_src = {"agreed": [0, 0], "adjudicated": [0, 0]}
        for r in recs:
            # UNSURE gold items are not ground truth in either direction:
            # the adjudicators could not decide, so scoring a model against
            # them would charge it for our own uncertainty. Excluded, counted.
            if r["gold_verdict"] == "UNSURE":
                excluded += 1; continue
            p = r["parsed"]; is_pos = r["gold_verdict"] == "ISSUE"
            if not p: unparsed += 1; item_rows.append(dict(model=model, item_id=r["item_id"], pred=None, gold=is_pos)); continue
            pred = bool(p.get("has_issue")); ab = bool(p.get("abstain")); conf = p.get("confidence")
            if ab: abst += 1
            if pred and is_pos: tp += 1
            elif pred and not is_pos: fp += 1
            elif not pred and is_pos: fn += 1
            else: tn += 1
            correct = pred == is_pos
            cal.append(dict(conf=conf if isinstance(conf, (int, float)) else None, correct=correct))
            s = src.get(r["item_id"])
            if s in by_src: by_src[s][0] += correct; by_src[s][1] += 1
            if is_pos:
                n_issue += 1
                cs = cats_from(p); g = r["gold_category"]
                oth = {c for c in str(others.get(r["item_id"], "")).split(",") if c}
                if cs and cs[0] == g: strict += 1
                if g in cs or (oth & set(cs)): lenient += 1
            item_rows.append(dict(model=model, item_id=r["item_id"], pred=pred, gold=is_pos, correct=correct, conf=conf))
        prec = tp / (tp + fp) if tp + fp else 0; rec = tp / (tp + fn) if tp + fn else 0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0
        # specificity = share of genuinely clean code the model clears.
        # Precision hides this when positives dominate; specificity states it
        # directly and is the number that decides whether a tool can gate a build.
        spec = tn / (tn + fp) if tn + fp else 0
        bal_acc = (rec + spec) / 2
        det_rows.append(dict(model=model, n=len(recs) - excluded, n_unsure_excluded=excluded,
                             tp=tp, fp=fp, tn=tn, fn=fn,
                             precision=round(prec, 3), recall=round(rec, 3), f1=round(f1, 3),
                             specificity=round(spec, 3), balanced_acc=round(bal_acc, 3),
                             unparsed=unparsed, abstain=abst, brier=brier(cal),
                             cat_acc_strict=round(strict / n_issue, 3) if n_issue else None,
                             cat_acc_lenient=round(lenient / n_issue, 3) if n_issue else None,
                             acc_agreed=round(by_src["agreed"][0] / by_src["agreed"][1], 3) if by_src["agreed"][1] else None,
                             acc_adjudicated=round(by_src["adjudicated"][0] / by_src["adjudicated"][1], 3) if by_src["adjudicated"][1] else None))
        # per-category recall
        for g, grp in pd.DataFrame([r for r in recs if r["gold_verdict"] == "ISSUE"]).groupby("gold_category"):
            hit = sum(1 for _, r in grp.iterrows() if r["parsed"] and r["parsed"].get("has_issue"))
            cat_rows.append(dict(model=model, gold_category=g, n=len(grp), recall=round(hit / len(grp), 3)))

    for f in sorted(Path(a.runs).glob("*__repair.jsonl")):
        model = f.name.split("__")[0]
        recs = load(f); sc = []
        for r in recs:
            p = r["parsed"] or {}
            s = repair_scores(r["input_code"], p.get("fixed_code"), r["gold_category"])
            s.update(model=model, item_id=r["item_id"], category=r["gold_category"],
                     truncated=looks_truncated(r.get("raw")),
                     errored=bool(r.get("error")))
            sc.append(s)
        d = pd.DataFrame(sc); d.to_csv(Path(a.out) / f"repair_items__{model}.csv", index=False)
        ok = d[d.parsed]
        rep_rows.append(dict(model=model, n=len(d),
                             parse_rate=round(d.parsed.mean(), 3),
                             truncated_rate=round(d.truncated.mean(), 3),
                             error_rate=round(d.errored.mean(), 3),
                             syntactic_ok=round(ok.syntactic_ok.mean(), 3) if len(ok) else None,
                             api_valid=round(ok.api_valid.mean(), 3) if len(ok) else None,
                             addresses_defect=round(ok.addresses_defect.mean(), 3) if len(ok) else None,
                             substantive=round(ok.substantive.mean(), 3) if len(ok) else None,
                             fully_correct=round((ok.substantive & ok.syntactic_ok & ok.api_valid & ok.addresses_defect).mean(), 3) if len(ok) else None,
                             mean_similarity=round(ok.similarity.mean(), 3) if len(ok) else None,
                             mean_lines_dropped_frac=round(ok.lines_dropped_frac.mean(), 3) if len(ok) else None,
                             top_hallucinations=ok.hallucinations[ok.hallucinations != ""].str.split(",").explode().value_counts().head(3).to_dict() if len(ok) else {}))

    for f in sorted(Path(a.runs).glob("*__reflect.jsonl")):
        model = f.name.split("__")[0]
        recs = load(f)
        det = {r["item_id"]: r["parsed"] for r in load(Path(a.runs) / f"{model}__detect.jsonl")}
        changed = toward = away = 0; cal = []; n = 0
        for r in recs:
            p = r["parsed"]; d0 = det.get(r["item_id"])
            if not p or not d0: continue
            n += 1; is_pos = r["gold_verdict"] == "ISSUE"
            before = bool(d0.get("has_issue")); after = bool(p.get("revised_has_issue"))
            if before != after:
                changed += 1
                if after == is_pos: toward += 1
                else: away += 1
            cal.append(dict(conf=p.get("confidence") if isinstance(p.get("confidence"), (int, float)) else None, correct=after == is_pos))
        ref_rows.append(dict(model=model, n=n, changed_mind=changed, toward_gold=toward, away_from_gold=away,
                             abstain=sum(1 for r in recs if r["parsed"] and r["parsed"].get("abstain")),
                             brier_after=brier(cal)))

    pd.DataFrame(det_rows).to_csv(Path(a.out) / "detect_summary.csv", index=False)
    pd.DataFrame(cat_rows).pivot(index="gold_category", columns="model", values="recall").to_csv(Path(a.out) / "detect_recall_by_category.csv")
    pd.DataFrame(item_rows).to_csv(Path(a.out) / "detect_items.csv", index=False)
    pd.DataFrame(rep_rows).to_csv(Path(a.out) / "repair_summary.csv", index=False)
    pd.DataFrame(ref_rows).to_csv(Path(a.out) / "reflect_summary.csv", index=False)
    pd.set_option("display.width", 200)
    print("DETECT\n", pd.DataFrame(det_rows).to_string(index=False))
    print("\nREPAIR\n", pd.DataFrame(rep_rows).drop(columns="top_hallucinations", errors="ignore").to_string(index=False))
    print("\nREFLECT\n", pd.DataFrame(ref_rows).to_string(index=False))

if __name__ == "__main__":
    main()
