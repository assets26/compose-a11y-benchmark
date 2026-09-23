#!/usr/bin/env python3
"""
reparse.py — re-parse `raw` in existing runs/*.jsonl with a stricter JSON
extractor. No model calls. Fixes the class of row where the model returned
perfectly good JSON inside a ```json fence (or with real newlines inside a
string) and the original greedy parser gave up.

What it does per row:
  - if `parsed` is already non-null and `--all` is not set, leave it alone
  - else re-run robust_parse(raw); if that succeeds, write it into `parsed`
  - never touches `raw`, `error`, `seconds`, `input_code`

Writes runs/<file>.bak before rewriting, and prints a before/after table.

Usage
  python reparse.py --runs runs                  # repair + detect + reflect
  python reparse.py --runs runs --tasks repair   # just repair
  python reparse.py --runs runs --dry-run        # report only, write nothing
"""
import argparse, json, re, shutil
from pathlib import Path

FENCE_RE = re.compile(r"```(?:json|JSON|kotlin)?\s*\n?(.*?)```", re.S)


def strip_fences(text):
    """Return candidate bodies: fence contents first, then the whole text."""
    out = []
    for m in FENCE_RE.finditer(text):
        body = m.group(1).strip()
        if body.startswith("{"):
            out.append(body)
    out.append(text.strip())
    return out


def brace_span(text):
    """First balanced {...} block, ignoring braces inside JSON strings.
    Much safer than re.search(r'\\{.*\\}', ...), which over-matches."""
    start = text.find("{")
    if start < 0:
        return None
    depth, in_str, esc = 0, False, False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def escape_control_in_strings(s):
    """Escape raw newlines/tabs that appear INSIDE JSON string literals.
    This is the correct version of the old blanket s.replace('\\n','\\\\n'),
    which also mangled the newlines between JSON members and destroyed
    already-escaped sequences."""
    out, in_str, esc = [], False, False
    for c in s:
        if in_str:
            if esc:
                out.append(c); esc = False; continue
            if c == "\\":
                out.append(c); esc = True; continue
            if c == '"':
                out.append(c); in_str = False; continue
            if c == "\n":
                out.append("\\n"); continue
            if c == "\r":
                out.append("\\r"); continue
            if c == "\t":
                out.append("\\t"); continue
            out.append(c); continue
        out.append(c)
        if c == '"':
            in_str = True
    return "".join(out)


def drop_trailing_commas(s):
    return re.sub(r",\s*([}\]])", r"\1", s)


VALID_ESCAPES = set('"\\/bfnrtu')


def fix_invalid_escapes(s):
    r"""Repair backslashes that are legal Kotlin but illegal JSON.

    Kotlin escapes a literal dollar as \$ (string templates), and regex
    fragments carry \d, \. and friends. JSON allows only \" \\ \/ \b \f \n
    \r \t and \uXXXX, so a model emitting correct Kotlin inside a JSON
    string produces 'Invalid \escape'. Doubling the offending backslash
    preserves the Kotlin source exactly while making the JSON parse.

    Only touches backslashes INSIDE string literals, and leaves valid
    escapes (including well-formed \uXXXX) untouched.
    """
    out, i, in_str = [], 0, False
    n = len(s)
    while i < n:
        c = s[i]
        if not in_str:
            out.append(c)
            if c == '"':
                in_str = True
            i += 1
            continue
        if c == "\\" and i + 1 < n:
            nxt = s[i + 1]
            if nxt == "u" and re.match(r"[0-9a-fA-F]{4}", s[i + 2:i + 6] or ""):
                out.append(s[i:i + 6]); i += 6; continue
            if nxt in VALID_ESCAPES and nxt != "u":
                out.append(s[i:i + 2]); i += 2; continue
            out.append("\\\\"); out.append(nxt); i += 2; continue   # \$ -> \\$
        if c == '"':
            in_str = False
        out.append(c); i += 1
    return "".join(out)


def robust_parse(text):
    """Try progressively more forgiving repairs. Returns dict or None."""
    if not text or not isinstance(text, str):
        return None
    for body in strip_fences(text):
        block = brace_span(body)
        if block is None:
            continue
        ctrl = escape_control_in_strings(block)
        for cand in (block,
                     ctrl,
                     fix_invalid_escapes(block),
                     fix_invalid_escapes(ctrl),
                     drop_trailing_commas(ctrl),
                     drop_trailing_commas(fix_invalid_escapes(ctrl))):
            try:
                obj = json.loads(cand)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                pass
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs")
    ap.add_argument("--tasks", nargs="*", default=["detect", "repair", "reflect"])
    ap.add_argument("--models", nargs="*", default=None,
                    help="ONLY these model names. Use this to stay off files a "
                         "running job still has open for appending.")
    ap.add_argument("--all", action="store_true",
                    help="re-parse every row, not just currently-null ones")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    files = []
    for t in a.tasks:
        files += sorted(Path(a.runs).glob(f"*__{t}.jsonl"))
    if a.models:
        files = [f for f in files if f.name.split("__")[0] in a.models]
    if not files:
        print(f"no run files under {a.runs}/ for tasks {a.tasks}")
        return

    print(f"{'file':40} {'rows':>5} {'was null':>9} {'recovered':>10} {'still null':>11}")
    print("-" * 80)
    grand = 0
    for f in files:
        rows = [json.loads(l) for l in f.open() if l.strip()]
        was_null = sum(1 for r in rows if not r.get("parsed"))
        recovered = 0
        for r in rows:
            if r.get("parsed") and not a.all:
                continue
            p = robust_parse(r.get("raw"))
            if p is not None and not r.get("parsed"):
                recovered += 1
            if p is not None:
                r["parsed"] = p
        still = sum(1 for r in rows if not r.get("parsed"))
        grand += recovered
        print(f"{f.name:40} {len(rows):5d} {was_null:9d} {recovered:10d} {still:11d}")
        if recovered and not a.dry_run:
            shutil.copy2(f, f.with_suffix(".jsonl.bak"))
            with f.open("w") as fh:
                for r in rows:
                    fh.write(json.dumps(r) + "\n")

    print("-" * 80)
    print(f"recovered {grand} rows" + ("  (dry run — nothing written)" if a.dry_run else "  (.bak written next to each file)"))


if __name__ == "__main__":
    main()
