#!/usr/bin/env python3
"""
Stage 3a - Stratified sampling for manual verification.

Why: the pre-screen produced thousands of candidates. Verifying all of them by
hand is infeasible, and verifying a convenience subset is indefensible. This
draws a REPRODUCIBLE stratified random sample (fixed seed), so the Method can
state exactly how items were chosen.

Two modes:
  --mode pilot   small sample per category, to MEASURE the confirm rate
                 (do this first; it tells you which categories are worth keeping)
  --mode full    larger sample, sized per category from the pilot's confirm rate

Also emits the BLIND second-rater files up front, so dual rating is built into
the process from the start rather than bolted on afterwards.

Outputs:
  verify_<mode>.csv            <- you rate this (verdict column)
  verify_<mode>_blind.csv      <- give to rater 2 (no verdicts, shuffled)
  verify_<mode>_answerkey.csv  <- your ratings, for cohens_kappa.py
  sampling_report.txt          <- numbers for the Method section

Usage:
    python3 s3a_sample_for_verification.py --mode pilot --n 20
    # ...verify, measure confirm rates, then:
    python3 s3a_sample_for_verification.py --mode full --target-confirmed 25
"""
import argparse, csv, json, random
from pathlib import Path
from collections import Counter, defaultdict

SEED = 20260911  # fixed -> sample is reproducible; state this in the paper


def load(path):
    return list(csv.DictReader(open(path, encoding="utf-8")))


def snippet_for(row, indir, ctx=14):
    """Pull a few lines around the composable so the rater sees real context."""
    fp = Path(indir) / row["file"]
    if not fp.exists():
        return ""
    try:
        text = fp.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    name = row["composable"]
    i = text.find(f"fun {name}")
    if i == -1:
        return ""
    lines = text[:i].count("\n")
    all_lines = text.split("\n")
    start = max(0, lines - 2)
    end = min(len(all_lines), lines + ctx)
    return "\n".join(all_lines[start:end])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", default="candidates.csv")
    ap.add_argument("--indir", default="mined_code")
    ap.add_argument("--mode", choices=["pilot", "full"], default="pilot")
    ap.add_argument("--n", type=int, default=20,
                    help="pilot: candidates to sample per category")
    ap.add_argument("--target-confirmed", type=int, default=25,
                    help="full: confirmed issues wanted per category")
    ap.add_argument("--rates", default="confirm_rates.json",
                    help="full: {category: confirm_rate} measured in the pilot")
    ap.add_argument("--max-per-repo", type=int, default=3,
                    help="cap per repo per category, so one big app cannot dominate")
    ap.add_argument("--exclude", default="",
                    help="comma-separated categories to skip entirely")
    args = ap.parse_args()

    rows = load(args.candidates)
    skip = {c.strip() for c in args.exclude.split(",") if c.strip()}
    by_cat = defaultdict(list)
    for r in rows:
        if r["category"] not in skip:
            by_cat[r["category"]].append(r)

    rates = {}
    if args.mode == "full":
        p = Path(args.rates)
        if not p.exists():
            raise SystemExit(
                f"Missing {args.rates}. Run the pilot first, then create it, e.g.\n"
                '  {"missing_content_description": 0.62, "missing_heading_semantics": 0.18}')
        rates = json.loads(p.read_text())

    rng = random.Random(SEED)
    sample, report = [], []

    for cat in sorted(by_cat):
        pool = by_cat[cat][:]
        rng.shuffle(pool)

        # cap per repo so a single large app cannot dominate a category
        per_repo, capped = Counter(), []
        for r in pool:
            if per_repo[r["repo"]] < args.max_per_repo:
                capped.append(r)
                per_repo[r["repo"]] += 1

        if args.mode == "pilot":
            want = args.n
        else:
            rate = rates.get(cat)
            if rate is None:
                report.append(f"{cat:<32} SKIPPED (no confirm rate in {args.rates})")
                continue
            if rate <= 0:
                report.append(f"{cat:<32} DROPPED (confirm rate 0 in pilot)")
                continue
            want = min(len(capped), int(args.target_confirmed / rate) + 5)

        take = capped[:want]
        for r in take:
            r = dict(r)
            r["snippet"] = snippet_for(r, args.indir)
            r["verdict"] = ""      # TRUE_ISSUE / NOT_AN_ISSUE / UNSURE
            r["notes"] = ""
            sample.append(r)
        report.append(
            f"{cat:<32} pool={len(by_cat[cat]):>5}  after_repo_cap={len(capped):>5}  "
            f"sampled={len(take):>4}" + ("" if args.mode == "pilot"
                                         else f"  (rate={rates.get(cat):.2f})"))

    # stable ids so the answer key and blind file can be joined later
    for i, r in enumerate(sample, 1):
        r["item_id"] = f"{args.mode}-{i:04d}"

    cols = ["item_id", "category", "repo", "file", "composable", "evidence",
            "snippet", "verdict", "notes"]
    out = f"verify_{args.mode}.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader(); w.writerows(sample)

    # blind copy for rater 2: verdicts stripped, order shuffled so category
    # blocks do not cue the rater
    blind = [dict(r) for r in sample]
    rng.shuffle(blind)
    for r in blind:
        r["verdict"] = ""
        r["notes"] = ""
    with open(f"verify_{args.mode}_blind.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader(); w.writerows(blind)

    with open(f"verify_{args.mode}_answerkey.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["item_id", "category", "verdict"],
                           extrasaction="ignore")
        w.writeheader(); w.writerows(sample)

    txt = "\n".join([
        f"STAGE 3a SAMPLING ({args.mode})",
        "=" * 70,
        f"Random seed (reproducible)   : {SEED}",
        f"Max candidates per repo/cat  : {args.max_per_repo}",
        f"Total candidates available   : {len(rows)}",
        f"Total sampled for verification: {len(sample)}",
        "",
        *report,
        "",
        "NEXT",
        f"  1. Open {out} and fill the verdict column:",
        "       TRUE_ISSUE / NOT_AN_ISSUE / UNSURE",
        "     Judge in CONTEXT, not by pattern (see criteria sheet).",
        "  2. Copy your verdicts into the answerkey file.",
        f"  3. Give verify_{args.mode}_blind.csv to a second rater (no verdicts).",
        "  4. Run cohens_kappa.py on the two, then reconcile disagreements.",
    ])
    Path("sampling_report.txt").write_text(txt, encoding="utf-8")
    print(txt)


if __name__ == "__main__":
    main()
