#!/usr/bin/env python3
"""
score_repair_subset.py — recompute REPAIR metrics for the closed (API) models
on EXACTLY the same 60-issue subset the local models were run on, so the
closed-vs-local repair comparison uses one common test set.

Run from the bench/ directory (where runs/ and score_benchmark.py live):
    cp score_repair_subset.py <your bench dir>/
    cd <your bench dir>
    python score_repair_subset.py

It reads runs/subset_n60_seed42.txt for the item IDs, filters each model's
runs/<model>__repair.jsonl to the ISSUE items in that subset, and reuses
repair_scores() from score_benchmark.py so the numbers match your pipeline.
Paste the printed table back and the paper's Table 3 gets the common-subset row.
"""
import json, sys
from pathlib import Path

# reuse the exact scoring logic already in the repo
try:
    from score_benchmark import repair_scores
except Exception as e:
    sys.exit(f"Run this from the bench/ directory (needs score_benchmark.py): {e}")

SUBSET = Path("runs/subset_n60_seed42.txt")
if not SUBSET.is_file():
    sys.exit("runs/subset_n60_seed42.txt not found — it was written by the "
             "--sample 60 local runs; regenerate with one of those if missing.")
subset_ids = {l.strip() for l in SUBSET.open() if l.strip()}

MODELS = ["claude-sonnet", "gpt-mini", "gemini-flash",
          "qwen-coder", "mistral", "gemma3-1b"]

def frac(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 3) if xs else None

print(f"subset items: {len(subset_ids)}")
print(f"{'model':16}{'n':>4}{'Subst':>8}{'Synt':>8}{'API':>8}{'Addr':>8}{'Pass':>8}")
print("-" * 60)
for m in MODELS:
    f = Path(f"runs/{m}__repair.jsonl")
    if not f.is_file():
        print(f"{m:16}  (no repair file)"); continue
    rows = [json.loads(l) for l in f.open() if l.strip()]
    # ISSUE items that are in the common subset
    rows = [r for r in rows
            if r.get("item_id") in subset_ids and r.get("gold_verdict") == "ISSUE"]
    if not rows:
        print(f"{m:16}  (no overlapping ISSUE items)"); continue
    sc = [repair_scores(r.get("input_code", ""), (r.get("parsed") or {}).get("fixed_code"),
                        r.get("gold_category", "")) for r in rows]
    ok = [s for s in sc if s.get("parsed")]
    subst = frac([s.get("substantive") for s in ok])
    synt  = frac([s.get("syntactic_ok") for s in ok])
    api   = frac([s.get("api_valid") for s in ok])
    addr  = frac([s.get("addresses_defect") for s in ok])
    pw    = frac([bool(s.get("substantive") and s.get("syntactic_ok")
                       and s.get("api_valid") and s.get("addresses_defect")) for s in ok])
    print(f"{m:16}{len(rows):>4}{str(subst):>8}{str(synt):>8}{str(api):>8}{str(addr):>8}{str(pw):>8}")
