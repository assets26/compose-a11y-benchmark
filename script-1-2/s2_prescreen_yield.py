#!/usr/bin/env python3
"""
Stage 2 - Rule-based pre-screen (NO LLM) + PER-CATEGORY YIELD REPORT.

This is the decision checkpoint of the whole redesign. It tells you, BEFORE
you spend money on model runs or weeks on manual verification, whether real
code actually supplies all six categories - i.e. whether you can drop seeding.

Splits each file into individual composables, then flags candidates per
category. Output is CANDIDATES for humans to judge, not verdicts:
the scanner is intentionally over-inclusive.

Writes:
  composables.csv        one row per composable (the analysis unit)
  candidates.csv         one row per flagged candidate
  stage2_yield.txt       per-category counts + GO/NO-GO verdict

Usage:
    python3 s2_prescreen_yield.py --indir mined_code
"""
import argparse, csv, re, sys
from pathlib import Path
from collections import Counter, defaultdict

# ---------------------------------------------------------------- categories
# Core set (carried from study 1)
CORE_CATEGORIES = [
    "missing_content_description",
    "missing_semantics_role",
    "missing_interaction_semantics",
    "touch_target_size",
    "missing_state_description",
    "decorative_mislabeled",
    "color_contrast",
]

# Extended set (study 2) - modern Compose APIs, higher natural yield.
# Enable/disable individually; each is over-inclusive by design.
EXTENDED_CATEGORIES = [
    "pointerinput_no_semantics",
    "textfield_no_label",
    "text_truncation_scaling",
    "missing_heading_semantics",
    "missing_merge_descendants",
    "progress_no_semantics",
    "error_state_no_semantics",
    "clickable_icon_not_iconbutton",
]

CATEGORIES = CORE_CATEGORIES + EXTENDED_CATEGORIES

COMPOSABLE_RE = re.compile(r"@Composable\s*(?:@\w+(?:\([^)]*\))?\s*)*"
                           r"(?:private|internal|public)?\s*fun\s+(\w+)")


def split_composables(text):
    """Yield (name, body) per composable using brace matching."""
    out = []
    for m in COMPOSABLE_RE.finditer(text):
        name = m.group(1)
        i = text.find("{", m.end())
        if i == -1:
            continue
        depth, j = 0, i
        while j < len(text):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        out.append((name, text[m.start():min(j + 1, len(text))]))
    return out


def flag(body):
    """Return list of (category, evidence) candidates for one composable."""
    hits = []

    # 1. null / absent contentDescription on an Icon or Image
    for m in re.finditer(r"\b(Icon|Image)\s*\(", body):
        seg = body[m.start():m.start() + 400]
        if re.search(r"contentDescription\s*=\s*null", seg):
            hits.append(("missing_content_description", "contentDescription = null"))
        elif "contentDescription" not in seg:
            hits.append(("missing_content_description", f"{m.group(1)}() without contentDescription"))

    # 2. clickable Modifier without Role  -> screen reader announces no role
    for m in re.finditer(r"\.clickable\s*[({]", body):
        seg = body[max(0, m.start() - 200):m.start() + 300]
        if "Role." not in seg and "role" not in seg:
            hits.append(("missing_semantics_role", ".clickable without Role"))

    # 3. clickable without onClickLabel -> no action description
    for m in re.finditer(r"\.clickable\s*[({]", body):
        seg = body[m.start():m.start() + 300]
        if "onClickLabel" not in seg:
            hits.append(("missing_interaction_semantics", ".clickable without onClickLabel"))

    # 4. interactive element sized under 48dp
    for m in re.finditer(r"\.size\s*\(\s*(\d+)\s*\.dp", body):
        if int(m.group(1)) < 48:
            seg = body[max(0, m.start() - 300):m.start() + 300]
            if ".clickable" in seg or "IconButton" not in seg and "onClick" in seg:
                hits.append(("touch_target_size", f"size({m.group(1)}.dp) on interactive element"))

    # 5. toggleable/selectable without stateDescription
    for m in re.finditer(r"\b(Switch|Checkbox|RadioButton|\.toggleable|\.selectable)\b", body):
        seg = body[max(0, m.start() - 300):m.start() + 400]
        if "stateDescription" not in seg:
            hits.append(("missing_state_description", f"{m.group(1)} without stateDescription"))

    # 6. decorative element given a description (the inverse error)
    for m in re.finditer(r"contentDescription\s*=\s*[\"']([^\"']{1,60})[\"']", body):
        seg = body[max(0, m.start() - 300):m.start() + 200]
        if re.search(r"\b(Divider|Spacer|decorat|background|Gradient)\b", seg, re.I):
            hits.append(("decorative_mislabeled", f'decorative with description "{m.group(1)}"'))

    # 7. HARDCODED colors -> the only statically-checkable contrast signal.
    #    Theme colors (MaterialTheme.colorScheme.*) cannot be resolved statically.
    lits = re.findall(r"Color\(\s*0x([0-9A-Fa-f]{8})\s*\)", body)
    if len(lits) >= 2 and re.search(r"\bText\s*\(", body):
        hits.append(("color_contrast", f"{len(lits)} hardcoded Color literals with Text"))

    # --- extended (study 2) detectors ---
    try:
        from detectors_v2 import flag_extended
        hits += flag_extended(body)
    except ImportError:
        pass

    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indir", default="mined_code")
    args = ap.parse_args()

    files = list(Path(args.indir).rglob("*.kt"))
    if not files:
        sys.exit(f"No .kt files under {args.indir}. Run Stage 1 first.")

    comp_rows, cand_rows = [], []
    per_cat = Counter()
    per_cat_repos = defaultdict(set)

    for fp in files:
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        parts = fp.relative_to(args.indir).parts
        repo = parts[0] if parts else "?"
        for name, body in split_composables(text):
            cid = f"{repo}::{fp.name}::{name}"
            comp_rows.append({
                "composable_id": cid, "repo": repo,
                "file": str(fp.relative_to(args.indir)),
                "composable": name, "loc": body.count("\n") + 1,
            })
            for cat, ev in flag(body):
                cand_rows.append({
                    "composable_id": cid, "repo": repo,
                    "file": str(fp.relative_to(args.indir)),
                    "composable": name, "category": cat, "evidence": ev,
                    "verdict": "", "rater": "", "notes": "",
                })
                per_cat[cat] += 1
                per_cat_repos[cat].add(repo)

    for path, rows in (("composables.csv", comp_rows), ("candidates.csv", cand_rows)):
        if rows:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                w.writeheader(); w.writerows(rows)

    repos = len({r["repo"] for r in comp_rows})
    lines = [
        "STAGE 2 - PRE-SCREEN YIELD  (no LLM involved)",
        "=" * 62,
        f"Repos           : {repos}",
        f"Files           : {len(files)}",
        f"Composables     : {len(comp_rows)}",
        f"Candidates      : {len(cand_rows)}",
        "",
        f"{'CATEGORY':<32}{'CANDS':>7}{'REPOS':>7}  STATUS",
        "-" * 62,
    ]
    # Target: enough candidates that ~a third survive verification and still
    # give a usable per-category n. 30 candidates -> plausibly ~10 confirmed.
    TARGET = 30
    weak = []
    for c in CATEGORIES:
        if c == EXTENDED_CATEGORIES[0]:
            lines.append("-" * 62)
            lines.append("EXTENDED (study 2) " + "-" * 43)
        n, nr = per_cat[c], len(per_cat_repos[c])
        if n >= TARGET:
            status = "OK"
        elif n >= TARGET // 3:
            status = "THIN - verify first"
        else:
            status = "TOO FEW"
            weak.append(c)
        lines.append(f"{c:<32}{n:>7}{nr:>7}  {status}")

    lines += ["", "VERDICT", "-" * 62]
    if not weak:
        lines += [
            "All six categories have natural candidates. Proceed to Stage 3",
            "(manual verification). NO SEEDING NEEDED -> the confound that",
            "weakened study 1 disappears.",
        ]
    else:
        lines += [
            "Thin/absent categories: " + ", ".join(weak),
            "",
            "Options, in order of preference:",
            "  (a) Re-run Stage 1 with a larger --limit / more candidate repos,",
            "      then re-run this script. Cheapest fix if you are near target.",
            "  (b) DROP the weak categories and run a clean N-category study on",
            "      100% real data. Strongest paper: no seeding, no confound.",
            "  (c) Keep them and seed ONLY those, stating plainly that N",
            "      categories are real and M are synthetic, and never comparing",
            "      the two groups as if origin were the only difference.",
            "",
            "Note: color_contrast is structurally hard to find statically because",
            "modern Compose pulls colors from MaterialTheme.colorScheme rather than",
            "literals, so a source-level scanner cannot resolve the actual pair.",
            "If it stays near zero after more mining, that is a FINDING about the",
            "limits of static analysis - report it, do not paper over it.",
        ]
    out = "\n".join(lines)
    Path("stage2_yield.txt").write_text(out, encoding="utf-8")
    print(out)
    print("\nWrote composables.csv, candidates.csv, stage2_yield.txt")


if __name__ == "__main__":
    main()
