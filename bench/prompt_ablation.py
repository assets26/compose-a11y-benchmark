"""
prompt_ablation.py -- scores the prompt-definition test reported in RQ1.

What it compares
  runs/<model>__detect.jsonl                 original Detect prompt (category names only)
  runs_defs_prompt/<model>__detect.jsonl     same prompt, one-line definition after each name
                                             (made by run_benchmark_defs.py + category_definitions.json)

Both are scored on the same 135 items in runs/subset_n60_seed42.txt, item by item.

Metrics (per model, per prompt)
  category  = ISSUE items where the first reported issue has the gold category   (out of all ISSUE items)
  caught    = ISSUE items the model flagged (has_issue true)                       (out of all ISSUE items)
  clean_ok  = clean items (NO_ISSUE / HANDLED) the model left alone               (out of all clean items)
              -> this is the "specificity" in the paper
  UNSURE items are skipped. Unparsable output counts as wrong.

Tests
  exact McNemar (two-sided binomial on the discordant pairs) per model and metric,
  then Benjamini-Hochberg over all tests (6 models x 3 metrics = 18 in the paper).

Run from bench/:
  python prompt_ablation.py
  -> prints a table and writes results/prompt_ablation_summary.csv
"""
import csv, json, sys
from math import comb
from pathlib import Path

RUNS, DEFS, OUT = Path("runs"), Path("runs_defs_prompt"), Path("results")
SUBSET = RUNS / "subset_n60_seed42.txt"
CLEAN = {"NO_ISSUE", "HANDLED"}


def load(path):
    rows = {}
    for line in path.open():
        if line.strip():
            r = json.loads(line)
            rows[r["item_id"]] = r
    return rows


def first_category(parsed):
    issues = (parsed or {}).get("issues") or []
    if issues and isinstance(issues[0], dict):
        return issues[0].get("category")
    return None


def flags(r):
    """Return (category_ok, caught, clean_ok) for one record; None where it does not apply."""
    p = r.get("parsed")
    ok = isinstance(p, dict)
    gold = r.get("gold_verdict")
    if gold == "ISSUE":
        return (ok and first_category(p) == r.get("gold_category"), ok and bool(p.get("has_issue")), None)
    if gold in CLEAN:
        return (None, None, ok and not p.get("has_issue"))
    return (None, None, None)


def mcnemar_exact(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def bh(pvals):
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj = [0.0] * m
    prev = 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        prev = min(prev, pvals[i] * m / rank)
        adj[i] = prev
    return adj


def main():
    if not SUBSET.exists() or not DEFS.is_dir():
        sys.exit("Run from bench/. Needs runs/subset_n60_seed42.txt and the runs_defs_prompt/ folder.")
    ids = [l.strip() for l in SUBSET.open() if l.strip()]
    rows = []
    for f in sorted(DEFS.glob("*__detect.jsonl")):
        model = f.name.split("__")[0]
        base_f = RUNS / f.name
        if not base_f.exists():
            print(f"skip {model}: no {base_f}")
            continue
        base, new = load(base_f), load(f)
        shared = [i for i in ids if i in base and i in new]
        if len(shared) < len(ids):
            print(f"warning {model}: only {len(shared)} of {len(ids)} subset items in both runs")
        for k, name in enumerate(("category", "caught", "clean_ok")):
            pairs = []
            for i in shared:
                a, b = flags(base[i])[k], flags(new[i])[k]
                if a is not None:
                    pairs.append((bool(a), bool(b)))
            n = len(pairs)
            before = sum(a for a, _ in pairs)
            after = sum(b for _, b in pairs)
            gained = sum((not a) and b for a, b in pairs)   # wrong before, right after
            lost = sum(a and (not b) for a, b in pairs)     # right before, wrong after
            rows.append(dict(model=model, metric=name, n=n,
                             before=round(before / n, 2) if n else None,
                             after=round(after / n, 2) if n else None,
                             gained=gained, lost=lost,
                             p_mcnemar=round(mcnemar_exact(gained, lost), 4)))
    if not rows:
        sys.exit("No model files found in runs_defs_prompt/.")
    for r, q in zip(rows, bh([r["p_mcnemar"] for r in rows])):
        r["p_bh"] = round(q, 4)
        r["significant_bh_05"] = q < 0.05
    OUT.mkdir(exist_ok=True)
    with open(OUT / "prompt_ablation_summary.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{'model':<15}{'metric':<10}{'n':>4}{'before':>8}{'after':>7}{'+':>4}{'-':>4}{'p':>8}{'p_BH':>8}")
    for r in rows:
        print(f"{r['model']:<15}{r['metric']:<10}{r['n']:>4}{r['before']:>8}{r['after']:>7}"
              f"{r['gained']:>4}{r['lost']:>4}{r['p_mcnemar']:>8}{r['p_bh']:>8}{'  *' if r['significant_bh_05'] else ''}")
    print(f"\n{len(rows)} tests, BH-corrected. -> wrote {OUT}/prompt_ablation_summary.csv")


if __name__ == "__main__":
    main()
