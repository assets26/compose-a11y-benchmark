#!/usr/bin/env python3
"""
expand_context_v3.py — re-extract code context for verify_pilot.csv

Fixes the bug that produced `anchor_file 110` in the v2 run.

THE BUG
-------
v1/v2 located the composable by searching the file for the first line of the
stored snippet that was longer than 8 characters. But 289 of the 300 snippets
begin with a generic annotation:

    @Composable                                  222 rows
    @OptIn(ExperimentalMaterial3Api::class)       47 rows
    other @OptIn variants                        ~11 rows
    an actual fun signature                        1 row

So for most rows the matcher searched for the literal string "@Composable" and
locked onto the FIRST composable in the file. In a screen file with a dozen
composables that is almost always the wrong function, which is why the detector
pattern was not found in the body and the whole-file fallback kicked in.

THE FIX
-------
v3 does not trust a single probe line. It:

  1. Enumerates every `fun` declaration in the file (handles receivers, so
     `fun RowScope.DialButton(` is recorded under BOTH "RowScope.DialButton"
     and "DialButton").
  2. Builds a fingerprint from the snippet: strip annotations, blank lines and
     lines under 12 chars, keep up to 8 distinctive lines (parameter
     declarations, modifier chains, widget calls).
  3. Scores every candidate declaration by how many fingerprint lines appear in
     the ~60 lines beneath it.
  4. Breaks ties with: name matches the `composable` column, then whether the
     body contains the category's detector pattern, then proximity to the top.
  5. Records `decl_confidence` (fraction of fingerprint lines matched) so you
     can filter low-confidence rows during labeling.

Rows where the best score is 0 are reported as `declaration_ambiguous` rather
than silently given a window from the wrong function.

Usage (ONE line)
----------------
    python expand_context_v3.py --csv verify_pilot.csv --root ~/compose_mining/repos --out verify_pilot_expanded.csv --before 12 --after 40 --report
"""

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

CATEGORY_PATTERNS = {
    "clickable_icon_not_iconbutton": [r"\.clickable\s*[({]", r"\bIcon\s*\("],
    "color_contrast":               [r"Color\s*\(\s*0x", r"contentColor\s*=", r"\bcolor\s*="],
    "decorative_mislabeled":        [r"contentDescription\s*="],
    "error_state_no_semantics":     [r"\bisError\b", r"supportingText\s*=", r"\berror\b"],
    "missing_content_description":  [r"\bIcon\s*\(", r"\bImage\s*\("],
    "missing_heading_semantics":    [r"headlineLarge|headlineMedium|headlineSmall|titleLarge",
                                     r"\bText\s*\("],
    "missing_interaction_semantics":[r"\.clickable\s*[({]", r"\.combinedClickable\s*\(", r"onClick\s*="],
    "missing_merge_descendants":    [r"ListItem\s*\(", r"\bCard\s*\(", r"\bColumn\s*\(", r"\bRow\s*\("],
    "missing_semantics_role":       [r"\.clickable\s*[({]", r"\.toggleable\s*\(", r"\.selectable\s*\("],
    "missing_state_description":    [r"\.toggleable\s*\(", r"\bSwitch\s*\(", r"\bCheckbox\s*\(",
                                     r"\bRadioButton\s*\(", r"\.selectable\s*\(", r"\bselected\s*="],
    "pointerinput_no_semantics":    [r"detectTapGestures", r"detectDragGestures",
                                     r"detectTransformGestures", r"\.pointerInput\s*\("],
    "progress_no_semantics":        [r"ProgressIndicator", r"\bprogress\s*="],
    "text_truncation_scaling":      [r"\boverflow\s*=", r"maxLines\s*=", r"fontSize\s*=\s*\d+\.?\d*\.sp"],
    "textfield_no_label":           [r"OutlinedTextField\s*\(", r"BasicTextField\s*\(", r"\bTextField\s*\("],
    "touch_target_size":            [r"\.size\s*\(\s*\d+\.?\d*\.dp", r"\.height\s*\(\s*\d+\.?\d*\.dp",
                                     r"\.width\s*\(\s*\d+\.?\d*\.dp", r"\.requiredSize\s*\("],
}

IMPORT_RE = re.compile(r"^\s*import\s+")
ANNOTATION_RE = re.compile(r"^\s*@\w+")
FUN_RE = re.compile(r"^\s*(?:@\w+[^\n]*\s+)?(?:private\s+|internal\s+|public\s+|inline\s+|suspend\s+)*"
                    r"fun\s+(?:<[^>]+>\s+)?(?:(\w+)\.)?(\w+)\s*[(<]")
SUFFIX_DEPTH = 4
FINGERPRINT_LOOKAHEAD = 60


# ---------------------------------------------------------------- file index
def build_index(root: Path):
    by_relpath, by_suffix, by_repo_name = {}, defaultdict(list), defaultdict(list)
    n = 0
    for p in root.rglob("*.kt"):
        if not p.is_file():
            continue
        n += 1
        parts = [s.lower() for s in p.relative_to(root).parts]
        by_relpath.setdefault("/".join(parts), p)
        by_suffix["/".join(parts[-SUFFIX_DEPTH:])].append(p)
        if parts:
            by_repo_name[(parts[0], parts[-1])].append(p)
    return by_relpath, by_suffix, by_repo_name, n


def resolve(root, rel, repo, idx):
    by_relpath, by_suffix, by_repo_name, _ = idx
    if not rel:
        return None, "no_file_column"
    p = root / rel
    if p.is_file():
        return p, "exact"
    parts = [s.lower() for s in Path(rel).parts]
    hit = by_relpath.get("/".join(parts))
    if hit:
        return hit, "case_insensitive"
    cands = by_suffix.get("/".join(parts[-SUFFIX_DEPTH:]), [])
    if len(cands) == 1:
        return cands[0], "suffix"
    if len(cands) > 1 and repo:
        same = [c for c in cands if c.relative_to(root).parts[0].lower() == repo.lower()]
        if len(same) == 1:
            return same[0], "suffix_repo_scoped"
    if repo:
        cands = by_repo_name.get((repo.lower(), parts[-1]), [])
        if len(cands) == 1:
            return cands[0], "basename_in_repo"
        if len(cands) > 1:
            return None, f"ambiguous_basename_{len(cands)}_matches"
    if repo and not (root / repo).is_dir():
        return None, "repo_folder_absent"
    return None, "path_not_found"


# ------------------------------------------------------------- source helpers
def read_lines(path: Path):
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None


STR_RE = re.compile(r'"""(?:.|\n)*?"""|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')
LINE_COMMENT_RE = re.compile(r"//.*$")


def masked(lines):
    out, in_block = [], False
    for line in lines:
        s = line
        if in_block:
            if "*/" in s:
                s, in_block = s.split("*/", 1)[1], False
            else:
                out.append("")
                continue
        if "/*" in s:
            head, _, tail = s.partition("/*")
            if "*/" in tail:
                s = head + tail.split("*/", 1)[1]
            else:
                s, in_block = head, True
        out.append(LINE_COMMENT_RE.sub("", STR_RE.sub('""', s)))
    return out


def fingerprint(snippet):
    """Distinctive lines from the stored snippet — annotations dropped."""
    fp = []
    for raw in str(snippet or "").splitlines():
        s = raw.strip()
        if not s or len(s) < 12:
            continue
        if ANNOTATION_RE.match(s):          # <- the v2 bug: these were used as probes
            continue
        fp.append(s)
        if len(fp) >= 8:
            break
    return fp


def candidate_declarations(lines):
    """Every fun declaration: list of (line_idx, simple_name, qualified_name)."""
    out = []
    for i, line in enumerate(lines):
        m = FUN_RE.match(line)
        if m:
            recv, name = m.group(1), m.group(2)
            out.append((i, name, f"{recv}.{name}" if recv else name))
    return out


def body_range(mask, decl_idx, max_scan=600):
    depth, started = 0, False
    end = min(len(mask) - 1, decl_idx + max_scan)
    for i in range(decl_idx, end + 1):
        for ch in mask[i]:
            if ch == "{":
                depth += 1
                started = True
            elif ch == "}":
                depth -= 1
                if started and depth == 0:
                    return decl_idx, i
    return decl_idx, end


def body_has_pattern(lines, start, end, category):
    for pat in CATEGORY_PATTERNS.get(category, []):
        rx = re.compile(pat)
        for i in range(start, min(end, len(lines) - 1) + 1):
            if rx.search(lines[i]):
                return True
    return False


def pick_declaration(lines, mask, snippet, composable, category):
    """Score every fun declaration against the snippet fingerprint."""
    cands = candidate_declarations(lines)
    if not cands:
        return None, 0.0
    fp = fingerprint(snippet)
    want = (composable or "").strip()

    best, best_key = None, None
    for idx, name, qual in cands:
        window = lines[idx: min(len(lines), idx + FINGERPRINT_LOOKAHEAD)]
        joined = "\n".join(window)
        matched = sum(1 for f in fp if f in joined)
        score = matched / len(fp) if fp else 0.0

        name_hit = int(want != "" and want in (name, qual, qual.split(".")[0]))
        start, end = body_range(mask, idx)
        pat_hit = int(body_has_pattern(lines, start, end, category))

        key = (score, name_hit, pat_hit, -idx)
        if best_key is None or key > best_key:
            best, best_key = idx, key

    return best, (best_key[0] if best_key else 0.0)


def find_anchor(lines, category, start, end, decl):
    pats = CATEGORY_PATTERNS.get(category, [])
    for pat in pats:
        rx = re.compile(pat)
        for i in range(start, min(end, len(lines) - 1) + 1):
            if rx.search(lines[i]):
                return i, pat, "body"
    best = None
    for pat in pats:
        rx = re.compile(pat)
        for i, line in enumerate(lines):
            if rx.search(line):
                d = abs(i - decl)
                if best is None or d < best[0]:
                    best = (d, i, pat)
    if best:
        return best[1], best[2], "file"
    return None, None, "none"


def numbered(lines, lo, hi):
    return "\n".join(f"{n + 1:>5} | {lines[n]}" for n in range(lo, hi + 1))


# ------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", default="verify_pilot_expanded.csv")
    ap.add_argument("--before", type=int, default=12)
    ap.add_argument("--after", type=int, default=40)
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        sys.exit(f"--root is not a directory: {root}")

    with open(args.csv, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    print(f"indexing .kt files under {root} ...")
    idx = build_index(root)
    print(f"  indexed {idx[3]} Kotlin files")

    out_fields = list(rows[0].keys()) + [
        "abs_path", "resolve_method", "file_found", "decl_line", "decl_name",
        "decl_confidence", "anchor_line", "anchor_pattern", "anchor_scope",
        "anchor_text", "anchor_found", "context", "imports",
    ]

    stats, fail_reasons, unresolved = defaultdict(int), defaultdict(int), []

    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=out_fields)
        w.writeheader()

        for r in rows:
            rel, repo = (r.get("file") or "").strip(), (r.get("repo") or "").strip()
            path, method = resolve(root, rel, repo, idx)

            if path is None:
                stats["file_missing"] += 1
                fail_reasons[method] += 1
                unresolved.append({"item_id": r.get("item_id"), "repo": repo,
                                   "file": rel, "reason": method})
                w.writerow({**r, "file_found": False, "resolve_method": method,
                            "anchor_found": False, "anchor_scope": "none"})
                continue

            lines = read_lines(path)
            if lines is None:
                stats["file_missing"] += 1
                fail_reasons["unreadable"] += 1
                w.writerow({**r, "abs_path": str(path), "file_found": False,
                            "resolve_method": method, "anchor_found": False,
                            "anchor_scope": "none"})
                continue

            stats[f"resolved_{method}"] += 1
            imports = "\n".join(l for l in lines[:150] if IMPORT_RE.match(l))
            mask = masked(lines)
            decl, conf = pick_declaration(lines, mask, r.get("snippet", ""),
                                          r.get("composable", ""), r.get("category", ""))

            if decl is None:
                stats["decl_missing"] += 1
                unresolved.append({"item_id": r.get("item_id"), "repo": repo,
                                   "file": rel, "reason": "no_fun_declarations"})
                w.writerow({**r, "abs_path": str(path), "resolve_method": method,
                            "file_found": True, "anchor_found": False,
                            "anchor_scope": "none", "imports": imports})
                continue

            if conf == 0.0:
                stats["decl_confidence_zero"] += 1
                unresolved.append({"item_id": r.get("item_id"), "repo": repo,
                                   "file": rel, "reason": "declaration_ambiguous"})
            elif conf >= 0.6:
                stats["decl_confidence_high"] += 1
            else:
                stats["decl_confidence_low"] += 1

            m = FUN_RE.match(lines[decl])
            decl_name = (f"{m.group(1)}.{m.group(2)}" if m and m.group(1)
                         else (m.group(2) if m else ""))

            start, end = body_range(mask, decl)
            anchor, pat, scope = find_anchor(lines, r.get("category", ""), start, end, decl)
            stats[f"anchor_{scope}"] += 1

            if anchor is None:
                lo, hi = decl, min(len(lines) - 1, decl + args.after + args.before)
            else:
                lo = max(0, anchor - args.before)
                hi = min(len(lines) - 1, anchor + args.after)
                if decl < lo and lo - decl <= 25:
                    lo = decl

            w.writerow({
                **r,
                "abs_path": str(path),
                "resolve_method": method,
                "file_found": True,
                "decl_line": decl + 1,
                "decl_name": decl_name,
                "decl_confidence": f"{conf:.2f}",
                "anchor_line": (anchor + 1) if anchor is not None else "",
                "anchor_pattern": pat or "",
                "anchor_scope": scope,
                "anchor_text": lines[anchor].strip() if anchor is not None else "",
                "anchor_found": anchor is not None,
                "context": numbered(lines, lo, hi),
                "imports": imports,
            })

    print(f"\nwrote {args.out}")
    for k in sorted(stats):
        print(f"  {k:26} {stats[k]}")
    if fail_reasons:
        print("\nunresolved file reasons:")
        for k, v in sorted(fail_reasons.items(), key=lambda kv: -kv[1]):
            print(f"  {k:30} {v}")
    if args.report and unresolved:
        with open("unresolved_rows.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["item_id", "repo", "file", "reason"])
            w.writeheader()
            w.writerows(unresolved)
        print(f"\nwrote unresolved_rows.csv ({len(unresolved)} rows)")


if __name__ == "__main__":
    main()
