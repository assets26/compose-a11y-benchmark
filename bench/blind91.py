#!/usr/bin/env python3
"""
blind91.py -- second blind human check of the answer key (review 213A, comment 1).

The 286-item answer key has 106 items where both LLM raters agreed. Only 15 of
those were in the first 40-item human check. This script covers the other 91,
so that every item in the answer key has been judged by a human.

Run from the bench/ directory:
    python3 blind91.py make     # writes the page and the empty answer sheet
    python3 blind91.py score    # after you fill in the answers: agreement + kappa

Files (all in results/):
    blind91_view.html      the 91 code windows, flagged line highlighted, NO labels shown
    blind91_answers.csv    fill in: verdict, issue_category, notes
    blind91_key.csv        the answer-key labels. Do not open before you finish.
"""
import csv, html, random, re, sys
from pathlib import Path

RATERS, OUT, SEED = Path("../RaterA-B"), Path("results"), 91
VERDICTS = ["ISSUE", "NO_ISSUE", "HANDLED", "UNSURE"]


def kappa(pairs):
    n = len(pairs); labels = {x for p in pairs for x in p}
    po = sum(a == b for a, b in pairs) / n
    pe = sum((sum(a == l for a, _ in pairs) / n) * (sum(b == l for _, b in pairs) / n) for l in labels)
    return po, pe, (po - pe) / (1 - pe) if pe < 1 else float("nan")


def boot(pairs, B=10_000):
    rng, n, vals = random.Random(42), len(pairs), []
    for _ in range(B):
        k = kappa([pairs[rng.randrange(n)] for _ in range(n)])[2]
        if k == k:
            vals.append(k)
    vals.sort()
    return vals[int(.025 * len(vals))], vals[int(.975 * len(vals)) - 1]


def make():
    gold = list(csv.DictReader(open(RATERS / "verified_gold.csv", newline="")))
    seen = {r["rater_row_id"] for r in csv.DictReader(open(RATERS / "rater_human_40.csv", newline=""))}
    items = [r for r in gold if r["gold_source"] == "agreed" and r["rater_row_id"] not in seen]
    items.sort(key=lambda r: r["rater_row_id"])
    random.Random(SEED).shuffle(items)                     # fixed order, unrelated to the labels
    OUT.mkdir(exist_ok=True)
    old = OUT / "blind91_answers.csv"
    if old.exists() and any(r.get("notes") or any(v for k, v in r.items() if k.startswith("verdict"))
                            for r in csv.DictReader(old.open(newline=""))):
        sys.exit("results/blind91_answers.csv already has answers in it. Not overwriting. Rename it first if you really want a fresh sheet.")
    parts = []
    with open(OUT / "blind91_answers.csv", "w", newline="") as fa, open(OUT / "blind91_key.csv", "w", newline="") as fk:
        wa, wk = csv.writer(fa), csv.writer(fk)
        wa.writerow(["blind_id", "decl_name", "anchor_line", "verdict (ISSUE/NO_ISSUE/HANDLED/UNSURE)", "issue_category", "notes"])
        wk.writerow(["blind_id", "rater_row_id", "item_id", "gold_verdict", "gold_category"])
        for i, r in enumerate(items, 1):
            bid = f"b{i:02d}"
            wa.writerow([bid, r["decl_name"], str(r["anchor_line"]).split(".")[0], "", "", ""])
            wk.writerow([bid, r["rater_row_id"], r["item_id"], r["gold_verdict"], r["gold_category"]])
            anchor = str(r["anchor_line"]).split(".")[0]
            lines = []
            for ln in r["context"].splitlines():
                m = re.match(r"\s*(\d+) \|", ln)
                cls = " class='hit'" if m and m.group(1) == anchor else ""
                lines.append(f"<span{cls}>{html.escape(ln)}</span>")
            parts.append(f"<section id='{bid}'><h2>{bid} &middot; {html.escape(r['decl_name'])} &middot; line {anchor}</h2>"
                         f"<p>Flagged construct: <code>{html.escape(r['anchor_text'])}</code></p><pre>{''.join(lines)}</pre></section>")
    nav = " ".join(f"<a href='#b{i:02d}'>b{i:02d}</a>" for i in range(1, len(items) + 1))
    (OUT / "blind91_view.html").write_text(f"""<!doctype html><meta charset='utf-8'><title>Blind check (91 items)</title>
<style>body{{font:14px/1.45 -apple-system,Arial,sans-serif;margin:24px;color:#222;background:#fff}}
h2{{margin:36px 0 4px;border-top:2px solid #00853E;padding-top:12px}}
nav{{position:sticky;top:0;background:#fff;padding:8px 0;border-bottom:1px solid #ccc;line-height:2}} nav a{{margin-right:8px}}
pre{{font:12px/1.4 Menlo,Consolas,monospace;background:#f6f6f6;padding:10px;white-space:pre-wrap}}
pre span{{display:block}} .hit{{background:#fff3a6;font-weight:bold}}</style>
<h1>Blind check of the answer key ({len(items)} items)</h1>
<p>Judge <b>only the highlighted line</b>, using the code around it and <code>CODEBOOK.txt</code>.
Verdicts: <b>ISSUE</b> (real defect), <b>NO_ISSUE</b> (fine), <b>HANDLED</b> (framework or code already covers it),
<b>UNSURE</b> (cannot tell from source). If ISSUE, give one of the 15 category names.
Write answers in <code>blind91_answers.csv</code>. Do not open <code>blind91_key.csv</code> until you finish.</p>
<nav>{nav}</nav>{''.join(parts)}""", encoding="utf-8")
    print(f"wrote {OUT}/blind91_view.html, blind91_answers.csv, blind91_key.csv ({len(items)} items)")


def score():
    key = {r["blind_id"]: r for r in csv.DictReader(open(OUT / "blind91_key.csv", newline=""))}
    ans = list(csv.DictReader(open(OUT / "blind91_answers.csv", newline="")))
    vcol = next(c for c in ans[0] if c.startswith("verdict"))
    done = [a for a in ans if a[vcol].strip()]
    bad = [a["blind_id"] for a in done if a[vcol].strip().upper() not in VERDICTS]
    if bad:
        sys.exit(f"Fix these verdicts (must be one of {VERDICTS}): {bad}")
    pairs = [(a[vcol].strip().upper(), key[a["blind_id"]]["gold_verdict"]) for a in done]
    out = [f"judged {len(done)} of {len(ans)} items"]
    po, pe, k = kappa(pairs); lo, hi = boot(pairs)
    out.append(f"NEW 91-item check, human vs answer key:  agree {sum(a == b for a, b in pairs)}/{len(pairs)} = {po:.2f}  kappa = {k:.2f} [{lo:.2f}, {hi:.2f}]")
    both = [(a, key[a["blind_id"]]) for a in done if a[vcol].strip().upper() == "ISSUE" and key[a["blind_id"]]["gold_verdict"] == "ISSUE"]
    if both:
        same = sum(a["issue_category"].strip() == g["gold_category"] for a, g in both)
        out.append(f"category, where both say ISSUE: same category on {same}/{len(both)}")
    dis = [f"{a['blind_id']}: {a[vcol].strip().upper()} vs {key[a['blind_id']]['gold_verdict']}"
           for a in done if a[vcol].strip().upper() != key[a["blind_id"]]["gold_verdict"]]
    out.append("disagreements (blind_id: yours vs key): " + (", ".join(dis) or "none"))
    # pooled with the first check: the 40 items, human vs the final answer key (4 of the 40 were removed as duplicates or are absent)
    gold = {r["rater_row_id"]: r["gold_verdict"] for r in csv.DictReader(open(RATERS / "verified_gold.csv", newline=""))}
    h40 = [(r["verdict"], gold[r["rater_row_id"]]) for r in csv.DictReader(open(RATERS / "rater_human_40.csv", newline="")) if r["rater_row_id"] in gold]
    po, pe, k = kappa(h40); lo, hi = boot(h40)
    out.append(f"first check vs answer key (n={len(h40)}):       agree {po:.2f}  kappa = {k:.2f} [{lo:.2f}, {hi:.2f}]   (note: you also adjudicated some of these)")
    allp = pairs + h40; po, pe, k = kappa(allp); lo, hi = boot(allp)
    out.append(f"both checks pooled (n={len(allp)}):              agree {po:.2f}  kappa = {k:.2f} [{lo:.2f}, {hi:.2f}]")
    print("\n".join(out)); (OUT / "blind91_result.txt").write_text("\n".join(out) + "\n")


if __name__ == "__main__":
    {"make": make, "score": score}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
