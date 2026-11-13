#!/usr/bin/env python3
"""
make_handcheck_page.py -- turn results/repair_handcheck_sheet.csv into a readable page.

Run from the bench/ directory, after reviewer_stats.py:
    python3 make_handcheck_page.py
Writes:
    results/repair_handcheck_view.html     side-by-side original vs. repaired code, changes highlighted
    results/repair_handcheck_answers.csv   short sheet to fill in (one row per repair, no code)
"""
import csv, difflib, html, sys
from pathlib import Path

src = Path(sys.argv[1] if len(sys.argv) > 1 else "results/repair_handcheck_sheet.csv")
rows = list(csv.DictReader(src.open(newline="")))
differ = difflib.HtmlDiff(tabsize=4, wrapcolumn=78)
parts = []
for r in rows:
    table = differ.make_table(r["original_code"].splitlines(), r["repaired_code"].splitlines(),
                              "Original", "Repaired", context=True, numlines=6)
    parts.append(f"<section id='{r['check_id']}'><h2>{r['check_id']} &middot; {html.escape(r['category'])}</h2>"
                 f"<p class='sum'><b>Model's own summary:</b> {html.escape(r['model_summary'])}</p>{table}</section>")
nav = " ".join(f"<a href='#{r['check_id']}'>{r['check_id']}</a>" for r in rows)
page = f"""<!doctype html><meta charset='utf-8'><title>Repair hand-check</title>
<style>
body{{font:14px/1.45 -apple-system,Arial,sans-serif;margin:24px;color:#222;background:#fff}}
h2{{margin:36px 0 4px;border-top:2px solid #00853E;padding-top:12px}} .sum{{margin:4px 0 10px}}
nav{{position:sticky;top:0;background:#fff;padding:8px 0;border-bottom:1px solid #ccc;line-height:2}}
nav a{{margin-right:8px}} table.diff{{font:12px/1.35 Menlo,Consolas,monospace;border-collapse:collapse;width:100%}}
table.diff td{{padding:1px 6px;vertical-align:top;white-space:pre-wrap;word-break:break-word}}
.diff_header{{background:#eee;color:#666;text-align:right}} .diff_next{{display:none}}
.diff_add{{background:#c9f0c9}} .diff_chg{{background:#fff3a6}} .diff_sub{{background:#f7c5c5}}
</style>
<h1>Repair hand-check ({len(rows)} repairs)</h1>
<p>For each repair, ask: <b>does the repaired code fix the bug named in the heading, without breaking anything?</b>
Green = added, yellow = changed, red = removed. Only the changed lines and 6 lines around them are shown.
Record your answers in <code>repair_handcheck_answers.csv</code>.</p>
<nav>{nav}</nav>{''.join(parts)}"""
out = src.parent / "repair_handcheck_view.html"
out.write_text(page, encoding="utf-8")
ans = src.parent / "repair_handcheck_answers.csv"
with ans.open("w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["check_id", "category", "fixes_defect (yes/no/unsure)", "breaks_something (yes/no)", "notes"])
    for r in rows:
        w.writerow([r["check_id"], r["category"], "", "", ""])
print(f"wrote {out} and {ans} ({len(rows)} repairs)")
