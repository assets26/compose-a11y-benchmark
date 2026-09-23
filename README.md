# Detect, Repair, Reflect — Replication Package

Benchmarking LLM accessibility analysis in Android Jetpack Compose.
This package reproduces the tables and figures in the paper from the released
model outputs and scoring scripts.

## Pipeline stages and where they live

**Stage 1–2 — mine and pre-screen repositories** (`script-1-2/`)
- `s1a_build_repo_list.py`, `s1b_filter_and_fetch.py` — build the repo list and fetch
- `s2_prescreen_yield.py`, `detectors_v2.py` — deterministic candidate scanner (no LLM)
- `RUNBOOK.md` — step-by-step notes
- `repos_manifest.csv` (root) — the mined repositories to re-fetch

**Stage 3 — sample and expand context** (`script3/`)
- `s3a_sample_for_verification.py` — stratified 300-item sample
- `expand_context_v3.py` — anchor-centered code extraction
- `make_rater_packet.py` — build the blind rater packets
- `STAGE3_PLAN.md`

**Ground-truth construction** (`RaterA-B/`)
- `build_gold.py` — produces `verified_gold.csv` (286 items)
- `apply_rulings.py`, `compare_raters.py`
- `rater_A_labels.csv`, `rater_B_labels.csv` — the two LLM raters
- `rater_human_40.csv` — the author's blind 40-item check
- `disagreements_adjudicated.csv`, `agreement_report.txt`
- `CODEBOOK.txt` — the labeling codebook (also at root)

**Benchmark and scoring** (`bench/`)
- `run_benchmark.py`, `prompts.py`, `models.json` — Detect/Repair/Reflect runner
- `score_benchmark.py` — detection, repair, and reflect tables
- `reparse.py` — robust JSON re-parse of raw model output
- `score_repair_subset.py` — repair on the common 60-issue subset
- `cat_robustness.py` — category-accuracy robustness check
- `sample_negatives.py` — matched-negative sampling
- `verified_gold.csv`, `negatives_labeled.csv` — frozen ground truth + controls
- `runs/` — raw model outputs, one JSONL per model+task (each row keeps the
  exact input code and the model's raw reply)
- `results/` — scored tables (CSV)

**Corpus** (`mined_code/`) — the mined Compose source, all permissively licensed.

## Reproduce the results

```bash
cd bench
pip install pandas requests matplotlib
python reparse.py --runs runs
python score_benchmark.py --runs runs --gold verified_gold.csv --out results
python score_repair_subset.py
python cat_robustness.py
```

The `runs/*.jsonl` files embed each item's input code and the model's raw
reply, so every table reproduces from this package alone. Re-running the models
(`run_benchmark.py`) additionally needs the corpus in `mined_code/` and API
keys set as environment variables (see `models.json` for exact model IDs and
inference settings).
