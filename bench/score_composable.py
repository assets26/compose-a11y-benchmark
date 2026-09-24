#!/usr/bin/env python3
"""
score_composable.py — address reviewer issues #1 and #2, offline, no re-runs.

#1  Detection is rescored at the COMPOSABLE level. The Detect prompt shows the
    whole composable, so we group detection rows by the exact input code sent,
    merge the anchor-level gold into one composable label (a composable is
    positive if ANY of its anchors is ISSUE; negative if all are
    NO_ISSUE/HANDLED; excluded if it has UNSURE and no ISSUE), and score once
    per composable. This removes the contradictory case where the same code was
    a true positive for one anchor and a false positive for another.

#2  Reflection is rescored EXCLUDING the UNSURE items (matching detection).

Run from the bench/ directory:
    cp score_composable.py <bench dir>/ && cd <bench dir>
    python score_composable.py
Paste the two printed tables back.
"""
import json, glob
from collections import defaultdict
from pathlib import Path


def cats_of(parsed):
    if not parsed:
        return []
    return [str(i.get("category", "")) for i in parsed.get("issues", []) if isinstance(i, dict)]


def rep_parsed(rows):
    """Representative prediction for a composable: first row that parsed."""
    for r in rows:
        if r.get("parsed"):
            return r["parsed"]
    return None


print("=== #1  DETECTION, composable-level ===")
print(f"{'model':16}{'nComp':>6}{'P':>7}{'R':>7}{'Spec':>7}{'Bal':>7}{'CatS':>7}{'CatL':>7}{'Brier':>7}{'excl':>6}")
print("-" * 86)
for f in sorted(glob.glob("runs/*__detect.jsonl")):
    model = Path(f).name.split("__")[0]
    rows = [json.loads(l) for l in open(f) if l.strip()]
    groups = defaultdict(list)
    for r in rows:
        groups[r.get("input_code", r["item_id"])].append(r)   # group by exact code sent

    tp = fp = tn = fn = 0
    strict = lenient = npos = 0
    excl = unparsed = 0
    cal = []
    for _, grp in groups.items():
        verds = {r["gold_verdict"] for r in grp}
        if "ISSUE" in verds:
            is_pos = True
            gold_cats = {r["gold_category"] for r in grp if r["gold_verdict"] == "ISSUE"}
        elif verds <= {"NO_ISSUE", "HANDLED"}:
            is_pos = False; gold_cats = set()
        else:
            excl += 1; continue                                # UNSURE with no ISSUE

        p = rep_parsed(grp)
        if p is None:
            unparsed += 1
            continue
        pred = bool(p.get("has_issue"))
        conf = p.get("confidence")
        if pred and is_pos: tp += 1
        elif pred and not is_pos: fp += 1
        elif not pred and is_pos: fn += 1
        else: tn += 1
        cal.append((conf if isinstance(conf, (int, float)) else None, pred == is_pos))
        if is_pos:
            npos += 1
            cs = cats_of(p)
            if cs and cs[0] in gold_cats: strict += 1
            if set(cs) & gold_cats: lenient += 1

    prec = tp / (tp + fp) if tp + fp else 0
    rec = tp / (tp + fn) if tp + fn else 0
    spec = tn / (tn + fp) if tn + fp else 0
    bal = (rec + spec) / 2
    br = [((c / 100.0) - (1.0 if ok else 0.0)) ** 2 for c, ok in cal if c is not None]
    brier = sum(br) / len(br) if br else None
    print(f"{model:16}{len(groups):>6}{prec:>7.3f}{rec:>7.3f}{spec:>7.3f}{bal:>7.3f}"
          f"{(strict/npos if npos else 0):>7.3f}{(lenient/npos if npos else 0):>7.3f}"
          f"{(round(brier,3) if brier is not None else 0):>7}{excl:>6}")

print("\n=== #2  REFLECTION, UNSURE excluded ===")
print(f"{'model':16}{'n':>5}{'changed':>9}{'toward':>8}{'away':>7}{'net':>6}")
print("-" * 52)
for f in sorted(glob.glob("runs/*__reflect.jsonl")):
    model = Path(f).name.split("__")[0]
    dp = Path("runs") / f"{model}__detect.jsonl"
    det = {json.loads(l)["item_id"]: json.loads(l).get("parsed")
           for l in dp.open() if l.strip()} if dp.exists() else {}
    rows = [json.loads(l) for l in open(f) if l.strip()]
    n = changed = toward = away = 0
    for r in rows:
        if r.get("gold_verdict") == "UNSURE":       # <-- the fix
            continue
        p = r.get("parsed"); d0 = det.get(r["item_id"])
        if not p or not d0:
            continue
        n += 1
        is_pos = r["gold_verdict"] == "ISSUE"
        before = bool(d0.get("has_issue"))
        after = bool(p.get("revised_has_issue"))
        if before != after:
            changed += 1
            if after == is_pos: toward += 1
            else: away += 1
    print(f"{model:16}{n:>5}{changed:>9}{toward:>8}{away:>7}{toward-away:>+6}")
