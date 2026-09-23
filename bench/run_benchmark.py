#!/usr/bin/env python3
"""
run_benchmark.py — run Detect / Repair / Reflect for every model over the gold
set (+ negatives). Resumable: one JSONL per model+task; already-done items are
skipped, so you can Ctrl-C and restart.

Inputs
  verified_gold.csv           frozen gold (positives)
  negatives_labeled.csv       your labeled negatives (optional; rows with verdict
                              NO_ISSUE/HANDLED are used)
  models.json                 model list + settings
  --root ../mined_code        to extract the WHOLE composable (input unit).
                              Falls back to the context window if extraction fails.

Outputs  runs/<model>__<task>.jsonl   one line per item, raw + parsed

Usage
  python run_benchmark.py --root ../mined_code --tasks detect repair reflect
  python run_benchmark.py --root ../mined_code --tasks detect --models gemma3-1b phi3
  python run_benchmark.py --root ../mined_code --tasks detect --limit 10   # pilot
"""
import argparse, json, os, re, sys, time
from pathlib import Path
import pandas as pd
import requests
from prompts import SYSTEM, detect_prompt, repair_prompt, reflect_prompt

# ------------------------------------------------------------- code extraction
FUN_RE = re.compile(r"^\s*(?:@\w+[^\n]*\s+)?(?:private\s+|internal\s+|public\s+)*fun\s+(?:<[^>]+>\s+)?(?:(\w+)\.)?(\w+)\s*[(<]")
STR_RE = re.compile(r'"""(?:.|\n)*?"""|"(?:\\.|[^"\\])*"')

def whole_composable(root, rel_file, anchor_line, fallback):
    """Return (code, imports). Whole composable that CONTAINS anchor_line.
    Walks back from the anchor to the nearest `fun` declaration, then brace-counts
    forward. Falls back to the stored context window if anything is missing."""
    try:
        a = int(float(anchor_line)) - 1
    except (TypeError, ValueError):
        return fallback, ""
    if not root: return fallback, ""
    p = Path(root) / str(rel_file)
    if not p.is_file(): return fallback, ""
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    imports = "\n".join(l for l in lines[:150] if l.lstrip().startswith("import "))
    if a < 0 or a >= len(lines): return fallback, imports
    mask = [re.sub(r"//.*$", "", STR_RE.sub('""', l)) for l in lines]
    # find the enclosing fun: scan back for a `fun` line whose body spans the anchor
    def body_end(i):
        depth, started = 0, False
        for k in range(i, min(len(lines), i + 600)):
            for ch in mask[k]:
                if ch == "{": depth += 1; started = True
                elif ch == "}":
                    depth -= 1
                    if started and depth == 0: return k
        return None
    for i in range(a, -1, -1):
        if FUN_RE.match(lines[i]):
            e = body_end(i)
            if e is not None and e >= a:
                s = i
                while s > 0 and lines[s - 1].lstrip().startswith("@"): s -= 1
                return "\n".join(lines[s:e + 1]), imports
    return fallback, imports

def strip_numbers(context):
    return "\n".join(re.sub(r"^\s*\d+ \| ", "", l) for l in str(context).splitlines())

# ------------------------------------------------------------- backends
def headroom(cfg):
    """Extra budget for tokens the model spends but does not emit (reasoning /
    thinking). Added ONLY to backends that have such tokens, so that every
    model ends up with the SAME visible-output allowance, cfg['max_tokens'].
    Never multiply max_tokens per-backend: that silently handed reasoning
    models 3x the output budget of Claude and Ollama, which made the Repair
    results a measurement of the config rather than of the models."""
    return cfg["max_tokens"] + cfg.get("hidden_token_headroom", 3000)


def call_openai(model, system, user, cfg):
    body = {"model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {"type": "json_object"}}
    if model.startswith(("gpt-5", "o1", "o3", "o4")):
        # reasoning models: no custom temperature, new token field, reasoning eats budget
        body["max_completion_tokens"] = headroom(cfg)
    else:
        body["temperature"] = cfg["temperature"]; body["max_tokens"] = cfg["max_tokens"]
    r = requests.post("https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"}, json=body, timeout=cfg["timeout_s"])
    if r.status_code != 200: raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
    return r.json()["choices"][0]["message"]["content"]

def call_anthropic(model, system, user, cfg):
    r = requests.post("https://api.anthropic.com/v1/messages",
        headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"},
        json={"model": model, "max_tokens": cfg["max_tokens"], "temperature": cfg["temperature"],
              "system": system, "messages": [{"role": "user", "content": user}]},
        timeout=cfg["timeout_s"])
    r.raise_for_status(); return "".join(b.get("text", "") for b in r.json()["content"])

def call_gemini(model, system, user, cfg):
    r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        params={"key": os.environ["GEMINI_API_KEY"]},
        json={"systemInstruction": {"parts": [{"text": system}]},
              "contents": [{"parts": [{"text": user}]}],
              # Gemini 3.x charges THINKING tokens against maxOutputTokens, so a
              # single pool lets a long think starve the actual answer — that is
              # what truncated 42/47 repair rows. Cap thinking explicitly so the
              # visible-output allowance is genuinely cfg["max_tokens"].
              "generationConfig": {"temperature": cfg["temperature"],
                                   "maxOutputTokens": headroom(cfg),
                                   "thinkingConfig": {"thinkingBudget": cfg.get("hidden_token_headroom", 3000)},
                                   "responseMimeType": "application/json"}},
        timeout=cfg["timeout_s"])
    if r.status_code != 200: raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
    parts = r.json()["candidates"][0]["content"].get("parts", [])
    return "".join(p.get("text", "") for p in parts if not p.get("thought"))

def call_ollama(model, system, user, cfg):
    r = requests.post("http://localhost:11434/api/chat",
        json={"model": model, "stream": False, "format": "json",
              "options": {"temperature": cfg["temperature"], "num_predict": cfg["max_tokens"]},
              "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
        timeout=cfg["timeout_s"])
    r.raise_for_status(); return r.json()["message"]["content"]

BACKENDS = {"openai": call_openai, "anthropic": call_anthropic, "gemini": call_gemini, "ollama": call_ollama}

from reparse import robust_parse

def parse_json(text):
    """Pull the JSON object out of a model reply.

    Shared with reparse.py so that a live run and an offline re-parse of the
    stored `raw` field always agree. Handles ```json fences, braces inside
    string literals, raw newlines inside "fixed_code", and trailing commas.
    """
    return robust_parse(text)

def ask(backend, model, user, cfg, retries=2):
    """Retry malformed JSON, but never retry a timeout.

    A timeout means the model could not finish in the budget given. Asking
    again buys the same answer at the same price, so a 180 s timeout with
    retries=2 costs 9 minutes to record one failure. Bail on the first one.
    """
    err = None
    for attempt in range(retries + 1):
        try:
            t0 = time.time()
            raw = BACKENDS[backend](model, SYSTEM, user, cfg)
            parsed = parse_json(raw)
            if parsed is None and attempt < retries:
                user = user + "\n\nReturn ONLY the JSON object. No markdown, no explanation."
                continue
            return raw, parsed, time.time() - t0, None
        except requests.exceptions.Timeout as e:
            return None, None, None, f"TIMEOUT after {cfg['timeout_s']}s"
        except Exception as e:
            err = str(e)[:300]; time.sleep(2 + 3 * attempt)
    return None, None, None, err

# ------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", default="verified_gold.csv")
    ap.add_argument("--negatives", default="negatives_labeled.csv")
    ap.add_argument("--config", default="models.json")
    ap.add_argument("--root", default=None, help="mined_code root for whole-composable input")
    ap.add_argument("--tasks", nargs="+", default=["detect"], choices=["detect", "repair", "reflect"])
    ap.add_argument("--models", nargs="*", default=None, help="subset of model names")
    ap.add_argument("--limit", type=int, default=None, help="pilot: first N items")
    ap.add_argument("--sample", type=int, default=None,
                    help="stratified subsample of N items, balanced across gold_category. "
                         "Same --seed gives the same items to every model.")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--outdir", default="runs")
    a = ap.parse_args()

    cfg = json.load(open(a.config))
    models = [m for m in cfg["models"] if not a.models or m["name"] in a.models]
    Path(a.outdir).mkdir(exist_ok=True)

    gold = pd.read_csv(a.gold)
    items = []
    for _, r in gold.iterrows():
        code, imps = whole_composable(a.root, r["file"], r.get("anchor_line", 0), strip_numbers(r["context"]))
        # decl_line is not in gold; use anchor_line then walk back to the fun — good enough for a window
        items.append(dict(item_id=r["item_id"], kind="positive", gold_verdict=r["gold_verdict"],
                          gold_category=r["gold_category"], detector_category=r["detector_category"],
                          anchor_text=r.get("anchor_text", ""), code=code, imports=imps))
    if Path(a.negatives).is_file():
        neg = pd.read_csv(a.negatives)
        neg = neg[neg["verdict"].isin(["NO_ISSUE", "HANDLED"])]
        for _, r in neg.iterrows():
            items.append(dict(item_id=r["neg_id"], kind="negative", gold_verdict=r["verdict"],
                              gold_category="none", detector_category="none", anchor_text="",
                              code=strip_numbers(r["context"]), imports=r.get("imports", "")))
        print(f"negatives loaded: {len(neg)}")
    if a.limit: items = items[:a.limit]

    if a.sample:
        # Stratified subsample. ISSUE items are drawn balanced across
        # gold_category (these are what Repair consumes); non-ISSUE items are
        # kept at the same sampling fraction so Detect stays class-balanced.
        # Deterministic in --seed, so every model sees the identical subset.
        import random
        rng = random.Random(a.seed)
        pos = sorted([it for it in items if it["gold_verdict"] == "ISSUE"], key=lambda x: str(x["item_id"]))
        rest = sorted([it for it in items if it["gold_verdict"] != "ISSUE"], key=lambda x: str(x["item_id"]))
        buckets = {}
        for it in pos: buckets.setdefault(it["gold_category"], []).append(it)
        for b in buckets.values(): rng.shuffle(b)
        picked, order = [], sorted(buckets)
        while len(picked) < min(a.sample, len(pos)):           # round-robin across categories
            progressed = False
            for c in order:
                if buckets[c] and len(picked) < a.sample:
                    picked.append(buckets[c].pop()); progressed = True
            if not progressed: break
        frac = len(picked) / max(1, len(pos))
        rng.shuffle(rest)
        picked_rest = rest[:round(frac * len(rest))]
        items = sorted(picked + picked_rest, key=lambda x: str(x["item_id"]))
        tag = Path(a.outdir) / f"subset_n{a.sample}_seed{a.seed}.txt"
        Path(a.outdir).mkdir(exist_ok=True)
        tag.write_text("\n".join(str(it["item_id"]) for it in items) + "\n")
        print(f"stratified subset: {len(picked)} ISSUE + {len(picked_rest)} other "
              f"= {len(items)} items across {len(buckets)} categories -> {tag}")

    print(f"items: {len(items)}   models: {[m['name'] for m in models]}   tasks: {a.tasks}")

    for m in models:
        for task in a.tasks:
            out = Path(a.outdir) / f"{m['name']}__{task}.jsonl"
            done = set()
            if out.exists():
                done = {json.loads(l)["item_id"] for l in out.open() if l.strip()}
            # reflect needs the detect output
            prior = {}
            if task == "reflect":
                dp = Path(a.outdir) / f"{m['name']}__detect.jsonl"
                if not dp.exists(): print(f"  skip reflect for {m['name']}: no detect run"); continue
                prior = {json.loads(l)["item_id"]: json.loads(l).get("parsed") for l in dp.open() if l.strip()}
            todo = [it for it in items if it["item_id"] not in done]
            if task == "repair": todo = [it for it in todo if it["gold_verdict"] == "ISSUE"]
            print(f"\n{m['name']} / {task}: {len(todo)} to do ({len(done)} already)")
            with out.open("a") as fh:
                for n, it in enumerate(todo, 1):
                    if task == "detect":
                        user = detect_prompt(it["code"], it["imports"])
                    elif task == "repair":
                        user = repair_prompt(it["code"], it["imports"], it["gold_category"], it["anchor_text"])
                    else:
                        pj = json.dumps(prior.get(it["item_id"]) or {"note": "no prior analysis available"}, indent=1)
                        user = reflect_prompt(it["code"], it["imports"], pj)
                    # per-model overrides (timeout_s / max_tokens) win over globals
                    mcfg = {**cfg, **{k: m[k] for k in ("timeout_s", "max_tokens", "temperature") if k in m}}
                    raw, parsed, secs, err = ask(m["backend"], m["model"], user, mcfg)
                    rec = dict(item_id=it["item_id"], kind=it["kind"], model=m["name"], task=task,
                               gold_verdict=it["gold_verdict"], gold_category=it["gold_category"],
                               raw=raw, parsed=parsed, seconds=secs, error=err, input_code=it["code"])
                    fh.write(json.dumps(rec) + "\n"); fh.flush()
                    if n % 10 == 0 or err:
                        print(f"  {n}/{len(todo)}  {it['item_id']}  {'ERR ' + err if err else ('ok' if parsed else 'unparsed')}")

if __name__ == "__main__":
    main()
