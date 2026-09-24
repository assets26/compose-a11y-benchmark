# Detect, Repair, Reflect — Replication Package

Benchmarking LLM accessibility analysis in Android Jetpack Compose.

This package contains the dataset, model outputs, prompts, scoring scripts, and
supporting analysis used in the paper. The reported results can be reproduced
offline from the released model outputs; re-running the LLMs themselves requires
the corresponding API access or local Ollama models.

## Pipeline stages and where they live

### Stage 1–2 — Mine and pre-screen repositories

Files are in `script-1-2/`.

- `s1a_build_repo_list.py` — builds the repository candidate list
- `s1b_filter_and_fetch.py` — filters and fetches repositories
- `s2_prescreen_yield.py` — runs the deterministic accessibility pre-screen
- `detectors_v2.py` — rule-based candidate detectors
- `RUNBOOK.md` — stage-specific execution notes
- `repos_manifest.csv` at the repository root — provenance for the mined repositories

The deterministic scanner is intentionally over-inclusive. Its output identifies
candidates for later labeling; scanner output itself is not treated as ground truth.

### Stage 3 — Sample and expand context

Files are in `script3/`.

- `s3a_sample_for_verification.py` — creates the stratified 300-candidate sample
- `expand_context_v3.py` — extracts source context around candidate anchors
- `make_rater_packet.py` — creates the blind rater packets
- `STAGE3_PLAN.md` — stage-specific notes

### Ground-truth construction

Files are in `RaterA-B/`.

- `build_gold.py` — constructs the frozen verified ground-truth dataset
- `apply_rulings.py` — applies adjudication decisions
- `compare_raters.py` — computes inter-rater agreement
- `rater_A_labels.csv` — first independent LLM rater
- `rater_B_labels.csv` — second independent LLM rater
- `rater_human_40.csv` — blind human-labeled 40-item reliability subset
- `disagreements_adjudicated.csv` — human adjudication of rater disagreements
- `agreement_report.txt` — agreement statistics
- `CODEBOOK.txt` — labeling codebook, also available at the repository root

The frozen screened ground truth contains 286 items before the additional clean
controls used by the benchmark.

## Benchmark and scoring

Benchmark files are in `bench/`.

- `run_benchmark.py` — Detect / Repair / Reflect benchmark runner
- `prompts.py` — exact prompts supplied to the evaluated models
- `models.json` — exact model IDs and inference settings
- `reparse.py` — robust JSON re-parsing of raw model responses
- `verified_gold.csv` — frozen ground truth used by the benchmark
- `negatives_labeled.csv` — additional clean controls
- `runs/` — released raw model outputs, one JSONL file per model and task

### Reported RQ1 and RQ3 scorer

`score_composable.py` is the **authoritative scorer for the RQ1 detection and
RQ3 reflection results reported in the revised paper**.

For RQ1, the Detect prompt presents the complete composable. Therefore, rows
that received identical composable input are merged before scoring. A composable
is positive if any constituent anchor is a confirmed `ISSUE`; it is negative if
all constituent anchors are `NO_ISSUE` or `HANDLED`. Composables containing only
undecidable (`UNSURE`) ground truth are excluded.

For RQ3, `UNSURE` items are excluded before evaluating whether reflection moves
a verdict toward or away from the ground truth.

Running `score_composable.py` writes:

- `results/detect_composable_summary.csv` — **authoritative Table 2 / RQ1 results**
- `results/reflect_decidable_summary.csv` — **authoritative Figure 3 / RQ3 results**

The complete detection runs contain 285 scored composables after exclusion of
UNSURE-only composables. Phi-3-mini completed only a partial set and is reported
separately as such.

### Repair scoring

- `score_repair_subset.py` — repair scoring on the common 60-issue subset used
  for the like-for-like comparison reported in Table 3
- `patch_scorer.py` — mechanical repair checks
- `cat_robustness.py` — category-label normalization robustness analysis
- `sample_negatives.py` — matched-negative sampling

### Intermediate and legacy scoring outputs

`score_benchmark.py` is retained for provenance and intermediate analysis. It
contains the original anchor/item-level detection and reflection scoring as well
as repair-related analysis.

Accordingly, some files in `bench/results/` are also retained as intermediate
outputs. In particular:

- `detect_summary.csv` — original anchor/item-level detection summary
- `reflect_summary.csv` — original reflection summary before the revised
  decidable-only analysis
- `detect_items.csv` — item-level detection diagnostics
- `detect_recall_by_category.csv` — item-level category diagnostics

These files are preserved for transparency and provenance. **They are not the
authoritative RQ1/RQ3 results reported in the revised paper.**

For the final reported results, use:

- `detect_composable_summary.csv` for RQ1 / Table 2
- `reflect_decidable_summary.csv` for RQ3 / Figure 3
- `score_repair_subset.py` and its corresponding repair outputs for RQ2 / Table 3

## Reproduce the reported results

From the repository root:

```bash
cd bench
pip install pandas requests matplotlib
```

Re-parse the released raw model outputs:

```bash
python reparse.py --runs runs
```

The following command reproduces the original/intermediate scoring retained for
provenance:

```bash
python score_benchmark.py \
  --runs runs \
  --gold verified_gold.csv \
  --out results
```

Run the authoritative scorer for the revised RQ1 and RQ3 results:

```bash
python score_composable.py \
  --runs runs \
  --out results
```

This writes:

```text
results/detect_composable_summary.csv
results/reflect_decidable_summary.csv
```

Run the common-subset repair scoring used for Table 3:

```bash
python score_repair_subset.py
```

Run the category-label robustness analysis:

```bash
python cat_robustness.py
```

## Re-running the models

The released `runs/*.jsonl` files contain each benchmark item's exact model
input together with the raw model response, so the reported scoring can be
reproduced without querying the models again.

Re-running the models with `run_benchmark.py` additionally requires:

- the corresponding cloud API credentials for cloud models,
- the specified local models through Ollama,
- the source corpus under `mined_code/`.

See `bench/models.json` for the exact model identifiers and inference settings
used in the benchmark.

## Corpus

`mined_code/` contains the mined Jetpack Compose source used by the benchmark.
The corpus was drawn from permissively licensed open-source repositories.

## Result-file quick reference

| Paper result | Authoritative artifact |
| --- | --- |
| RQ1 / Table 2 — Detection | `bench/results/detect_composable_summary.csv` |
| RQ2 / Table 3 — Repair | `bench/score_repair_subset.py` and repair outputs |
| RQ3 / Figure 3 — Reflection | `bench/results/reflect_decidable_summary.csv` |

The older `detect_summary.csv` and `reflect_summary.csv` files remain in the
repository only to preserve the analysis history and should not be used as the
final RQ1/RQ3 results.