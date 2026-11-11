#!/usr/bin/env python3
"""
reviewer_stats.py -- extra numbers for the ISEC camera-ready (reviews 213A/213B).
Offline: reads the released outputs only. No model is re-run.

Run from the bench/ directory of the replication repo:
    cp reviewer_stats.py <repo>/bench/ && cd <repo>/bench
    python reviewer_stats.py

What it prints, and which review comment it answers:
  [A1] Cohen's kappa of the 40-item human check, with a 95% bootstrap CI
  [A2] how the controls were sampled; specificity split: controls vs. screened negatives
  [A3] 95% bootstrap CIs for detection and repair; exact McNemar tests (detect, repair, reflect)
  [A4] a sample sheet of Pass repairs to check by hand  -> results/repair_handcheck_sheet.csv
  [A7] unparsed-output counts per model
Everything is also written to results/reviewer_stats.txt.

Method notes
  * Detection is scored per composable, exactly as in score_composable.py.
  * Bootstrap: resample composables (or issues) with replacement, 10,000 times,
    seed 42; the CI is the 2.5th-97.5th percentile.
  * McNemar (exact): for two paired yes/no outcomes, look only at the items where
    they differ; under "no real difference" each direction is a fair coin flip,
    so the p-value is a two-sided binomial test on those counts.
"""
import argparse, csv, glob, json, random, sys
from collections import defaultdict
from math import comb
from pathlib import Path

try:
    from score_benchmark import repair_scores          # same repair checks as the paper
except Exception as e:
    sys.exit(f"Run this from the bench/ directory (needs score_benchmark.py): {e}")

B, SEED = 10_000, 42
OUT_LINES = []


def say(s=""):
    print(s); OUT_LINES.append(s)


def load(path):
    return [json.loads(l) for l in open(path) if l.strip()]


def mcnemar_exact(b, c):
    """Two-sided exact McNemar p-value from the two discordant counts."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def boot_ci(items, stat, rng):
    """95% percentile bootstrap CI of stat(list_of_items)."""
    n, vals = len(items), []
    for _ in range(B):
        v = stat([items[rng.randrange(n)] for _ in range(n)])
        if v is not None:
            vals.append(v)
    vals.sort()
    return vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1]


def kappa(pairs):
    """Cohen's kappa for a list of (label_1, label_2)."""
    n = len(pairs)
    labels = {x for p in pairs for x in p}
    po = sum(a == b for a, b in pairs) / n
    pe = sum((sum(a == l for a, _ in pairs) / n) * (sum(b == l for _, b in pairs) / n) for l in labels)
    return (po - pe) / (1 - pe) if pe < 1 else None


# ------------------------------------------------------------------ detection
def detect_composables(path):
    """One record per composable: gold label, prediction, group (control/screened)."""
    groups = defaultdict(list)
    for r in load(path):
        groups[r.get("input_code", r["item_id"])].append(r)
    out, excl, unparsed = {}, 0, 0
    for code, grp in groups.items():
        verds = {r["gold_verdict"] for r in grp}
        if "ISSUE" in verds:
            pos, gold_cats = True, {r["gold_category"] for r in grp if r["gold_verdict"] == "ISSUE"}
        elif verds <= {"NO_ISSUE", "HANDLED"}:
            pos, gold_cats = False, set()
        else:
            excl += 1; continue                         # UNSURE-only: not scored
        p = next((r["parsed"] for r in grp if r.get("parsed")), None)
        if p is None:
            unparsed += 1; continue                     # unparsable: excluded, counted
        cats = [str(i.get("category", "")) for i in p.get("issues", []) if isinstance(i, dict)]
        key = min(r["item_id"] for r in grp)            # stable id shared across models
        out[key] = dict(pos=pos, pred=bool(p.get("has_issue")),
                        cat_ok=bool(cats and cats[0] in gold_cats),
                        control=all(r.get("kind") == "negative" for r in grp),
                        handled=(not pos) and "HANDLED" in verds)
    return out, excl, unparsed


def rate(xs):
    return sum(xs) / len(xs) if xs else None


def recall(d):  return rate([x["pred"] for x in d if x["pos"]])
def spec(d):    return rate([not x["pred"] for x in d if not x["pos"]])
def catacc(d):  return rate([x["cat_ok"] for x in d if x["pos"]])
def balacc(d):
    r, s = recall(d), spec(d)
    return None if r is None or s is None else (r + s) / 2


def fmt(v, ci):
    return f"{v:.2f} [{ci[0]:.2f}, {ci[1]:.2f}]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs")
    ap.add_argument("--out", default="results")
    ap.add_argument("--raters", default="../RaterA-B")
    a = ap.parse_args()
    rng = random.Random(SEED)
    Path(a.out).mkdir(exist_ok=True)

    # ---------------- [A3] detection CIs, [A2] specificity split, [A7] unparsed
    det = {}
    say("=== [A3] DETECTION, composable level, 95% bootstrap CI ===")
    say(f"{'model':15}{'n':>5}  {'recall':20}{'specificity':20}{'balanced acc':20}{'category acc':20}")
    for f in sorted(glob.glob(f"{a.runs}/*__detect.jsonl")):
        m = Path(f).name.split("__")[0]
        d, excl, unp = detect_composables(f)
        det[m] = (d, unp)
        v = list(d.values())
        say(f"{m:15}{len(v):>5}  " + "".join(f"{fmt(s(v), boot_ci(v, s, rng)):20}" for s in (recall, spec, balacc, catacc)))

    say("\n=== [A7] UNPARSED detect outputs (excluded from scoring, after one retry + tolerant parse) ===")
    for m, (d, unp) in det.items():
        say(f"{m:15} unparsed composables: {unp}")

    say("\n=== [A2] SPECIFICITY SPLIT: controls (not scanner-flagged) vs. screened negatives (scanner-flagged) ===")
    say(f"{'model':15}{'controls':>22}{'screened negatives':>24}{'  of which HANDLED':>22}")
    for m, (d, _) in det.items():
        neg = [x for x in d.values() if not x["pos"]]
        ctl = [x for x in neg if x["control"]]; scr = [x for x in neg if not x["control"]]
        hd = [x for x in scr if x["handled"]]
        cell = lambda g: f"{spec(g):.2f} ({sum(not x['pred'] for x in g)}/{len(g)})" if g else "n/a"
        say(f"{m:15}{cell(ctl):>22}{cell(scr):>24}{cell(hd):>22}")

    say("\n=== [A3] DETECTION, exact McNemar on correct/incorrect (paired, same composables) ===")
    full = [m for m in det if len(det[m][0]) > 200]      # skips the partial Phi-3 run
    for i, m1 in enumerate(full):
        for m2 in full[i + 1:]:
            common = det[m1][0].keys() & det[m2][0].keys()
            ok = lambda m, k: det[m][0][k]["pred"] == det[m][0][k]["pos"]
            b = sum(ok(m1, k) and not ok(m2, k) for k in common)
            c = sum(ok(m2, k) and not ok(m1, k) for k in common)
            say(f"{m1:15} vs {m2:15} only-first-correct={b:>3} only-second-correct={c:>3}  p={mcnemar_exact(b, c):.4f}")

    # ---------------- [A3] reflection
    say("\n=== [A3] REFLECTION, exact McNemar on verdict changes (UNSURE excluded) ===")
    for f in sorted(glob.glob(f"{a.runs}/*__reflect.jsonl")):
        m = Path(f).name.split("__")[0]
        d0 = {r["item_id"]: r.get("parsed") for r in load(f"{a.runs}/{m}__detect.jsonl")}
        n = toward = away = 0
        for r in load(f):
            p, d = r.get("parsed"), d0.get(r["item_id"])
            if r.get("gold_verdict") == "UNSURE" or not p or not d:
                continue
            n += 1
            pos, before, after = r["gold_verdict"] == "ISSUE", bool(d.get("has_issue")), bool(p.get("revised_has_issue"))
            if before != after:
                toward += after == pos; away += after != pos
        say(f"{m:15} n={n:>3} toward={toward:>2} away={away:>2} net={toward - away:+d}  p={mcnemar_exact(toward, away):.3f}")

    # ---------------- [A3] repair CIs + McNemar, [A4] hand-check sheet
    subset = {l.strip() for l in open(f"{a.runs}/subset_n60_seed42.txt") if l.strip()}
    rep, sheet = {}, []
    tier = {"claude-sonnet": "cloud", "gpt-mini": "cloud", "gemini-flash": "cloud",
            "qwen-coder": "local", "mistral": "local", "gemma3-1b": "local"}
    say("\n=== [A3] REPAIR on the common 60-issue subset, Pass with 95% bootstrap CI ===")
    for m in tier:
        f = Path(a.runs) / f"{m}__repair.jsonl"
        if not f.is_file():
            continue
        res = {}
        for r in load(f):
            if r.get("item_id") not in subset or r.get("gold_verdict") != "ISSUE":
                continue
            fixed = (r.get("parsed") or {}).get("fixed_code")
            s = repair_scores(r.get("input_code", ""), fixed, r.get("gold_category", ""))
            if not s.get("parsed"):
                continue                                  # same rule as score_repair_subset.py
            ok = bool(s["substantive"] and s["syntactic_ok"] and s["api_valid"] and s["addresses_defect"])
            res[r["item_id"]] = ok
            if ok:
                sheet.append(dict(tier=tier[m], model=m, item_id=r["item_id"], category=r["gold_category"],
                                  original_code=r.get("input_code", ""), repaired_code=fixed,
                                  model_summary=(r.get("parsed") or {}).get("change_summary", "")))
        rep[m] = res
        v = list(res.values())
        say(f"{m:15} n={len(v):>3} Pass={fmt(rate(v), boot_ci(v, rate, rng))}")
    say("\nRepair, exact McNemar on Pass (paired, same issues):")
    ms = list(rep)
    for i, m1 in enumerate(ms):
        for m2 in ms[i + 1:]:
            common = rep[m1].keys() & rep[m2].keys()
            b = sum(rep[m1][k] and not rep[m2][k] for k in common)
            c = sum(rep[m2][k] and not rep[m1][k] for k in common)
            say(f"{m1:15} vs {m2:15} n={len(common):>2} only-first={b:>2} only-second={c:>2}  p={mcnemar_exact(b, c):.4f}")

    # hand-check sheet: up to 30 Pass repairs per tier, seed-fixed, model name hidden in a key file
    pick = []
    for t in ("cloud", "local"):
        pool = sorted((s for s in sheet if s["tier"] == t), key=lambda s: (s["model"], s["item_id"]))
        random.Random(SEED).shuffle(pool)
        pick += pool[:30]
        say(f"\n[A4] hand-check sheet: {min(30, len(pool))} of {len(pool)} Pass repairs from the {t} tier")
    random.Random(SEED + 1).shuffle(pick)
    with open(Path(a.out) / "repair_handcheck_sheet.csv", "w", newline="") as fh, \
         open(Path(a.out) / "repair_handcheck_key.csv", "w", newline="") as kh:
        w = csv.writer(fh); k = csv.writer(kh)
        w.writerow(["check_id", "category", "original_code", "repaired_code", "model_summary",
                    "fixes_defect (yes/no/unsure)", "breaks_something (yes/no)", "notes"])
        k.writerow(["check_id", "tier", "model", "item_id"])
        for i, s in enumerate(pick, 1):
            w.writerow([f"h{i:02d}", s["category"], s["original_code"], s["repaired_code"], s["model_summary"], "", "", ""])
            k.writerow([f"h{i:02d}", s["tier"], s["model"], s["item_id"]])
    say(f"-> wrote {a.out}/repair_handcheck_sheet.csv (judge this one) and {a.out}/repair_handcheck_key.csv (open only after judging)")

    # ---------------- [A1] kappa of the 40-item human check
    say("\n=== [A1] 40-item human check: Cohen's kappa on verdict, 95% bootstrap CI ===")
    rd = Path(a.raters)
    human = {r["rater_row_id"]: r["verdict"] for r in csv.DictReader(open(rd / "rater_human_40.csv"))}
    for name in ("rater_A_labels.csv", "rater_B_labels.csv"):
        lab = {r["rater_row_id"]: r["verdict"] for r in csv.DictReader(open(rd / name))}
        pairs = [(human[k], lab[k]) for k in human if k in lab]
        lo, hi = boot_ci(pairs, kappa, rng)
        say(f"human vs {name:20} n={len(pairs)} kappa={kappa(pairs):.2f} [{lo:.2f}, {hi:.2f}]")

    # ---------------- [A2] what the scanner missed among sampled unflagged composables
    neg = list(csv.DictReader(open("negatives_labeled.csv")))
    counts = defaultdict(int)
    for r in neg:
        counts[r["verdict"]] += 1
    say("\n=== [A2] Unflagged composables sampled as control candidates (sample_negatives.py, seed 7) ===")
    say(f"sampled={len(neg)}  " + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    say("ISSUE rows are real defects the rule scanner did not flag; NO_ISSUE + HANDLED rows are the controls.")

    Path(a.out, "reviewer_stats.txt").write_text("\n".join(OUT_LINES) + "\n")
    print(f"\n-> wrote {a.out}/reviewer_stats.txt")


if __name__ == "__main__":
    main()
