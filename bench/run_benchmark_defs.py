#!/usr/bin/env python3
"""
run_benchmark_defs.py -- side test: the same benchmark runner, but the Detect
prompt lists each category WITH a one-line definition.

It changes no existing file. prompts.py and run_benchmark.py are used as they
are; this script only swaps the category list in memory before the run starts.
Definitions come from category_definitions.json (same folder).

Run from the bench/ directory, with the same options as run_benchmark.py.
Always give a separate --outdir so the paper's runs/ folder is never touched:

    python3 run_benchmark_defs.py --root ../mined_code --tasks detect \
        --models qwen-coder --sample 60 --seed 42 --outdir runs_defs
"""
import json, sys
from pathlib import Path

import prompts                      # the unchanged paper prompts

defs = json.loads((Path(__file__).parent / "category_definitions.json").read_text())
missing = [c for c in prompts.CATEGORIES if not str(defs.get(c, "")).strip()]
if missing:
    sys.exit(f"category_definitions.json has no definition for: {missing}")
prompts.CAT_LIST = "\n".join(f"- {c}: {defs[c].strip()}" for c in prompts.CATEGORIES)

args = sys.argv[1:]
outdir = args[args.index("--outdir") + 1] if "--outdir" in args and args.index("--outdir") + 1 < len(args) else "runs"
if Path(outdir).resolve() == (Path(__file__).parent / "runs").resolve():
    sys.exit("Refusing to write into runs/ (the paper's results). Add e.g.  --outdir runs_defs")

print("Detect prompt now lists categories WITH definitions, e.g.:")
print("  " + prompts.CAT_LIST.splitlines()[0])

import run_benchmark                # imported after the swap; uses the same prompts module
run_benchmark.main()
