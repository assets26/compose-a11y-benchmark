#!/usr/bin/env python3
"""
patch_scorer.py — add specificity / balanced_acc / substantive to an existing
score_benchmark.py, in place. Idempotent: running it twice changes nothing.

Run from the bench/ directory:
    python patch_scorer.py
"""
import re, shutil, sys
from pathlib import Path

P = Path("score_benchmark.py")
if not P.is_file():
    sys.exit("score_benchmark.py not found — run this from the bench/ directory")

src = P.read_text()
orig = src
applied, skipped = [], []

# ---- 1. compute specificity + balanced accuracy -----------------------------
old1 = '        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0\n'
new1 = ('        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0\n'
        '        # specificity = share of genuinely clean code the model clears.\n'
        '        # Precision hides this when positives dominate; specificity states it\n'
        '        # directly and is the number that decides whether a tool can gate a build.\n'
        '        spec = tn / (tn + fp) if tn + fp else 0\n'
        '        bal_acc = (rec + spec) / 2\n')
if 'spec = tn / (tn + fp)' in src:
    skipped.append("specificity calculation")
elif old1 in src:
    src = src.replace(old1, new1, 1); applied.append("specificity calculation")
else:
    skipped.append("specificity calculation (anchor not found)")

# ---- 2. report them in the detect summary -----------------------------------
old2 = '                             precision=round(prec, 3), recall=round(rec, 3), f1=round(f1, 3),\n'
new2 = ('                             precision=round(prec, 3), recall=round(rec, 3), f1=round(f1, 3),\n'
        '                             specificity=round(spec, 3), balanced_acc=round(bal_acc, 3),\n')
if 'specificity=round(spec' in src:
    skipped.append("specificity column")
elif old2 in src:
    src = src.replace(old2, new2, 1); applied.append("specificity column")
else:
    skipped.append("specificity column (anchor not found)")

# ---- 3. substantive gate in repair_scores -----------------------------------
old3 = re.compile(
    r"    return dict\(parsed=True, syntactic_ok=balanced\(fixed\), api_valid=not halluc,\n"
    r"                hallucinations=\",\"\.join\(halluc\), addresses_defect=addressed,\n"
    r"                similarity=round\(ratio, 3\), lines_dropped=dropped, "
    r"lines_dropped_frac=round\(dropped / max\(1, len\(o_lines\)\), 3\)\)\n")
new3 = ('    drop_frac = dropped / max(1, len(o_lines))\n'
        '    # A model that returns a fragment instead of the composable scores a free\n'
        '    # api_valid=True (no code -> no hallucinated API to match) and a free\n'
        '    # syntactic_ok. Gate both on the reply actually being the composable back.\n'
        '    substantive = ratio >= 0.5 and drop_frac <= 0.5\n'
        '    return dict(parsed=True, substantive=substantive,\n'
        '                syntactic_ok=balanced(fixed), api_valid=not halluc,\n'
        '                hallucinations=",".join(halluc), addresses_defect=addressed,\n'
        '                similarity=round(ratio, 3), lines_dropped=dropped, '
        'lines_dropped_frac=round(drop_frac, 3))\n')
if 'substantive=substantive' in src:
    skipped.append("substantive gate")
elif old3.search(src):
    src = old3.sub(new3, src, count=1); applied.append("substantive gate")
else:
    skipped.append("substantive gate (anchor not found)")

# ---- 4. include it in the repair summary + fully_correct --------------------
old4 = ('                             fully_correct=round((ok.syntactic_ok & ok.api_valid '
        '& ok.addresses_defect).mean(), 3) if len(ok) else None,\n')
new4 = ('                             substantive=round(ok.substantive.mean(), 3) if len(ok) else None,\n'
        '                             fully_correct=round((ok.substantive & ok.syntactic_ok & ok.api_valid '
        '& ok.addresses_defect).mean(), 3) if len(ok) else None,\n')
if 'substantive=round(ok.substantive' in src:
    skipped.append("substantive column")
elif old4 in src:
    src = src.replace(old4, new4, 1); applied.append("substantive column")
else:
    skipped.append("substantive column (anchor not found)")

if src != orig:
    shutil.copy2(P, P.with_suffix(".py.bak"))
    P.write_text(src)

print("applied :", ", ".join(applied) or "nothing")
print("skipped :", ", ".join(skipped) or "nothing")
print("\nverify:")
print("  grep -c specificity score_benchmark.py   (expect 2)")
print("  grep -c substantive  score_benchmark.py   (expect 4)")
if any("anchor not found" in s for s in skipped):
    print("\nSome anchors did not match — your file differs from the expected version.")
    print("Paste the output of:  grep -n 'f1 = 2 \\* prec' score_benchmark.py")
