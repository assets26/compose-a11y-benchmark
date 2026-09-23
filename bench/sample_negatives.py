#!/usr/bin/env python3
"""
sample_negatives.py — matched negatives for the Detect task.

For each construct type the detectors target, find composables in mined_code
that CONTAIN that construct but were NOT flagged (not in verify_pilot_expanded),
and sample N of them. These are "matched" negatives: same constructs, so a
model has to tell correct from defective rather than spot a Spacer.

Output: negatives_to_label.csv — same shape as rater_A.csv (context, imports,
anchor). You label verdict/category by hand; rows you mark NO_ISSUE or HANDLED
become the negative set. Rows you mark ISSUE are real misses and go in a
"detector recall" side table.

Usage:
  python sample_negatives.py --root ../mined_code --gold verified_gold.csv \
      --expanded verify_pilot_expanded.csv --per-construct 6 --seed 7
"""
import argparse, random, re
from pathlib import Path
import pandas as pd

CONSTRUCTS = {                       # construct -> regex that must appear in the body
    "switch_checkbox":  r"\b(Switch|Checkbox|RadioButton)\s*\(",
    "clickable":        r"\.clickable\s*[({]",
    "icon_image":       r"\b(Icon|Image|AsyncImage)\s*\(",
    "textfield":        r"\b(Outlined)?TextField\s*\(",
    "progress":         r"ProgressIndicator\s*\(",
    "heading_style":    r"typography\.(headline|title)(Large|Medium|Small)",
    "pointer_input":    r"\.pointerInput\s*\(",
    "maxlines":         r"maxLines\s*=\s*1",
    "sized_box":        r"\.size\s*\(\s*\d+\.?\d*\.dp",
    "color_literal":    r"Color\s*\(\s*0x",
}
FUN_RE = re.compile(r"^\s*(?:@\w+[^\n]*\s+)?(?:private\s+|internal\s+|public\s+)*fun\s+(?:<[^>]+>\s+)?(?:(\w+)\.)?(\w+)\s*[(<]")
STR_RE = re.compile(r'"""(?:.|\n)*?"""|"(?:\\.|[^"\\])*"')

def masked(lines):
    return [re.sub(r"//.*$", "", STR_RE.sub('""', l)) for l in lines]

def body_end(mask, start, max_scan=400):
    depth, started = 0, False
    for i in range(start, min(len(mask), start + max_scan)):
        for ch in mask[i]:
            if ch == "{": depth += 1; started = True
            elif ch == "}":
                depth -= 1
                if started and depth == 0: return i
    return min(len(mask) - 1, start + max_scan)

def composables(path, root):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    mask = masked(lines)
    imports = "\n".join(l for l in lines[:150] if l.lstrip().startswith("import "))
    out = []
    for i, l in enumerate(lines):
        m = FUN_RE.match(l)
        if not m: continue
        # must be preceded by @Composable within 3 lines
        if not any("@Composable" in lines[j] for j in range(max(0, i - 3), i + 1)): continue
        e = body_end(mask, i)
        body = "\n".join(lines[i:e + 1])
        out.append(dict(file=str(path.relative_to(root)), decl_name=m.group(2),
                        decl_line=i + 1, end_line=e + 1, body=body, imports=imports,
                        context="\n".join(f"{n+1:>5} | {lines[n]}" for n in range(i, e + 1))))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--gold", default="verified_gold.csv")
    ap.add_argument("--expanded", default="verify_pilot_expanded.csv")
    ap.add_argument("--per-construct", type=int, default=6)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--max-lines", type=int, default=80, help="skip composables longer than this")
    ap.add_argument("--out", default="negatives_to_label.csv")
    a = ap.parse_args()
    random.seed(a.seed)
    root = Path(a.root).expanduser().resolve()

    flagged = pd.read_csv(a.expanded)
    flagged_keys = set(zip(flagged["file"], flagged["decl_name"]))
    flagged_files = set(flagged["file"])

    pool = {k: [] for k in CONSTRUCTS}
    n_files = 0
    for p in root.rglob("*.kt"):
        rel = str(p.relative_to(root))
        if rel not in flagged_files:           # prefer files the detector looked at but did not flag here
            pass
        try: comps = composables(p, root)
        except Exception: continue
        n_files += 1
        for c in comps:
            if (c["file"], c["decl_name"]) in flagged_keys: continue
            if c["end_line"] - c["decl_line"] > a.max_lines: continue
            for k, rx in CONSTRUCTS.items():
                if re.search(rx, c["body"]):
                    pool[k].append(dict(c, construct=k))
    print(f"scanned {n_files} files")
    rows = []
    for k, items in pool.items():
        random.shuffle(items)
        take = items[:a.per_construct]
        print(f"  {k:16} pool={len(items):5}  sampled={len(take)}")
        rows += take
    df = pd.DataFrame(rows)
    df.insert(0, "neg_id", [f"n{i+1:04d}" for i in range(len(df))])
    df["anchor_line"] = df["decl_line"]; df["anchor_text"] = df["decl_name"]
    for c in ["verdict", "issue_category", "confidence", "notes"]: df[c] = ""
    df = df.sample(frac=1, random_state=a.seed).reset_index(drop=True)
    df[["neg_id", "construct", "file", "decl_name", "anchor_line", "anchor_text",
        "context", "imports", "verdict", "issue_category", "confidence", "notes"]].to_csv(a.out, index=False)
    print(f"\nwrote {a.out} ({len(df)} rows). Label verdict/issue_category by hand.")

if __name__ == "__main__":
    main()
