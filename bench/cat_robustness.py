#!/usr/bin/env python3
"""
cat_robustness.py — recompute category accuracy after mechanically normalizing
near-miss category strings, as a robustness check.

The question a reviewer will ask: is the local models' low category accuracy an
artifact of string formatting? This answers it by being deliberately GENEROUS to
the models -- lowercasing, converting spaces/hyphens to underscores, stripping
redundant "missing_"/"no_" prefixes, and then accepting any close fuzzy match to
the controlled vocabulary. If accuracy still does not move, the gap is real.

Run from bench/:
    python cat_robustness.py
"""
import difflib, json, glob, re

VOCAB = ["clickable_icon_not_iconbutton", "color_contrast", "decorative_mislabeled",
         "error_state_no_semantics", "missing_content_description", "missing_heading_semantics",
         "missing_interaction_semantics", "missing_merge_descendants", "missing_semantics_role",
         "missing_state_description", "pointerinput_no_semantics", "progress_no_semantics",
         "text_truncation_scaling", "textfield_no_label", "touch_target_size"]
VSET = set(VOCAB)

# suffix/stem index so "missing_touch_target_size" -> "touch_target_size"
STEMS = {}
for v in VOCAB:
    STEMS[v] = v
    STEMS[re.sub(r"^(missing_|no_)", "", v)] = v


def normalize(raw):
    """Return (canonical_or_None, how)."""
    s = str(raw or "").strip().lower()
    if not s:
        return None, "empty"
    s = re.sub(r"[\s\-/]+", "_", s)
    s = re.sub(r"[^a-z0-9_]", "", s)
    s = re.sub(r"_+", "_", s).strip("_")
    if s in VSET:
        return s, "exact"
    if s in STEMS:
        return STEMS[s], "stem"
    stripped = re.sub(r"^(missing_|no_)", "", s)
    if stripped in STEMS:
        return STEMS[stripped], "prefix"
    close = difflib.get_close_matches(s, VOCAB, n=1, cutoff=0.80)
    if close:
        return close[0], "fuzzy"
    close = difflib.get_close_matches(stripped, list(STEMS), n=1, cutoff=0.80)
    if close:
        return STEMS[close[0]], "fuzzy"
    return None, "unmapped"


def main():
    print(f"{'model':16} {'n_issue':>8} {'strict':>8} {'normalized':>11} {'delta':>7} "
          f"{'remapped':>9} {'unmapped':>9}")
    print("-" * 78)
    for f in sorted(glob.glob("runs/*__detect.jsonl")):
        model = f.split("/")[-1].split("__")[0]
        n = strict = norm = remapped = unmapped = 0
        for line in open(f):
            r = json.loads(line)
            if r.get("gold_verdict") != "ISSUE":
                continue
            p = r.get("parsed") or {}
            issues = [i for i in (p.get("issues") or []) if isinstance(i, dict)]
            if not issues:
                continue
            n += 1
            gold = r.get("gold_category")
            first = issues[0].get("category")
            if first == gold:
                strict += 1
            canon, how = normalize(first)
            if how in ("stem", "prefix", "fuzzy"):
                remapped += 1
            if how == "unmapped":
                unmapped += 1
            if canon == gold:
                norm += 1
        if not n:
            continue
        s, v = strict / n, norm / n
        print(f"{model:16} {n:8d} {s:8.3f} {v:11.3f} {v - s:+7.3f} {remapped:9d} {unmapped:9d}")

    print("\nnormalized = accuracy after lowercasing, separator cleanup, prefix")
    print("stripping and fuzzy matching (cutoff 0.80) -- deliberately generous.")
    print("A delta near zero means the category gap is not a formatting artifact.")


if __name__ == "__main__":
    main()
