# Study 2 — Runbook (no-seeding redesign)

Goal: rebuild the benchmark on **naturally occurring** accessibility issues so
the seeded/real confound disappears, while keeping every fix already made for
the ASSETS reviewer comments.

## What changed vs. study 1

| | Study 1 | Study 2 |
|---|---|---|
| Repos | ~30, top-starred | 150–250, **star-banded** incl. mid-tier + F-Droid |
| Why | popularity bias → more accessible than average | mid-tier apps carry more real defects |
| Sparse categories | seeded (36 injected) | mine wider; seed only as last resort |
| Provenance | partial | `repos_manifest.csv` for every repo |
| Funnel numbers | qualitative | `stage1_report.txt` — exact counts for the Method |

## Order of operations

```bash
export GITHUB_TOKEN=ghp_xxx      # github.com/settings/tokens, public_repo scope

# 1a. Build a wide candidate pool (F-Droid + GitHub star bands)
python3 s1a_build_repo_list.py --target 400
#     -> repos_candidates.csv

# 1b. Filter (license / maintained / really uses Compose) and download
python3 s1b_filter_and_fetch.py --limit 200
#     -> mined_code/, repos_manifest.csv, stage1_report.txt

# 2. Pre-screen + PER-CATEGORY YIELD  <-- DECISION CHECKPOINT
python3 s2_prescreen_yield.py --indir mined_code
#     -> composables.csv, candidates.csv, stage2_yield.txt
```

**Stop at stage2_yield.txt and read the verdict before doing anything else.**
This is the whole point of the redesign: you learn in ~a day, for the cost of
API calls only, whether real code supplies all six categories. Study 1 only
discovered the gap after mining was finished and it was too late to change plan.

If categories are thin: re-run 1b with a bigger `--limit` (cheapest), or drop
to a clean 4-category study on 100% real data (strongest paper), or seed only
the thin ones and say so plainly (acceptable, weaker).

## After the checkpoint — reuse study 1 scripts

Stages 3–6 are unchanged in design; point the existing scripts at the new
`candidates.csv`:

3. **Ground truth** — `ground_truth_analyzer_v2.py`, `verify_ground_truth.py`,
   then blind second rater: `prepare_second_rater.py` → `rate_blind.py` →
   `cohens_kappa.py` → `reconcile_disagreements.py` → `apply_reconciliation.py`
4. *(seeding — skip entirely if the checkpoint says OK)*
5. **Benchmark** — `run_llm_benchmark_v3.py` (7 models × 3 runs)
6. **Score + rate** — `label_detections.py`, `score_benchmark_6cat.py`,
   `rate_repairs.py`, `combine_final.py`

## Do this time what you didn't last time

- **Second rater on REPAIR ratings too**, not just detection. Build a blind
  copy of `repair_ratings.csv` (fix + composable, rating column blank), have a
  second person rate ~45 of them, run `cohens_kappa.py`. This answers the one
  criticism both ASSETS reviewers raised.
- **Keep `repos_manifest.csv` and `stage1_report.txt`** — they are the exact
  numbers R2 asked for ("why were those 30 projects selected").
- **Record the mining date** — it is in the manifest; cite it in the Method.

## Scanner notes (be honest about these in the paper)

- The pre-screen is deliberately **over-inclusive**: output is candidates for
  humans to judge, never verdicts. Same rule as study 1 — no LLM decides
  candidates or ground truth.
- `color_contrast` can only be flagged from **hardcoded `Color(0xFF…)` literals**.
  Modern Compose reads colors from `MaterialTheme.colorScheme`, which a static
  scanner cannot resolve. If this category stays near zero, that is itself a
  finding about the limits of source-level analysis — report it.
- `missing_state_description` is noisy: many components legitimately don't need
  one. Expect a low confirm rate at verification.

---

# Extended category set (study 2)

`detectors_v2.py` adds eight modern-Compose categories on top of the seven
carried from study 1. They exist because several study-1 categories are
structurally rare in real source (contrast, stateDescription), and these have
much higher natural yield — which is what lets you drop seeding.

| Category | The actual user harm | WCAG / Android anchor |
|---|---|---|
| `pointerinput_no_semantics` | `detectTapGestures` creates a tap target with **no role, no click action, not focusable** — TalkBack cannot reach it at all | WCAG 4.1.2 Name/Role/Value |
| `textfield_no_label` | Placeholder disappears on focus; screen reader announces an unlabeled field | WCAG 3.3.2 Labels or Instructions |
| `text_truncation_scaling` | `maxLines=1` + ellipsis clips content when a low-vision user raises font scale | WCAG 1.4.4 Resize Text |
| `missing_heading_semantics` | Screen-reader users navigate by heading; Compose requires explicit `heading()` | WCAG 1.3.1 Info and Relationships |
| `missing_merge_descendants` | A clickable card with 4 Texts is announced as 4 fragments instead of one item | WCAG 1.3.1 / Android semantics merging |
| `progress_no_semantics` | Progress value never announced | WCAG 4.1.2 |
| `error_state_no_semantics` | `isError=true` colors the field red but announces nothing — color-only signal | WCAG 1.4.1 Use of Color, 3.3.1 Error Identification |
| `clickable_icon_not_iconbutton` | Bypasses `IconButton`'s 48dp minimum and its Role | WCAG 2.5.8 Target Size, 4.1.2 |

## Precision notes — read before verification

Honest expectations, so you plan rater time correctly:

- **Low false-positive risk** (verify quickly): `pointerinput_no_semantics`,
  `textfield_no_label`, `progress_no_semantics`, `error_state_no_semantics`.
  These are close to binary.
- **Judgment required** (budget rater time): `missing_heading_semantics` —
  whether a given Text *should* be a heading is contextual, and flagging every
  `headlineMedium` will over-fire. `missing_merge_descendants` — merging is
  sometimes deliberately avoided. `text_truncation_scaling` — single-line
  truncation is occasionally an intentional design choice with a tooltip.
- Expect `missing_heading_semantics` to have the **highest raw count and the
  lowest confirm rate**. Do not let it dominate the dataset; consider capping
  how many you carry into ground truth, and say so in the Method.

## Two categories I deliberately did NOT implement

- **Hardcoded strings** (`Text("Submit")` instead of `stringResource`). Enormous
  yield and it was a category in Aljedaani et al., but it is a *localization*
  defect, not an accessibility one — a screen reader reads a hardcoded string
  perfectly well. Including it would invite a reviewer to say the construct is
  loose. Add it only if you frame it explicitly as localization.
- **Color-only information** (red text = error, no icon/label). A real WCAG 1.4.1
  issue, but reliable static detection needs semantic understanding of intent.
  `error_state_no_semantics` captures the tractable slice of it.

## Suggested plan

Run the checkpoint with all 15 enabled. Then keep the categories that clear
both bars — enough confirmed instances **and** a defensible confirm rate — and
report the rest as "screened but too sparse/noisy to evaluate." A 6–8 category
study on 100% real code is a much stronger paper than a 6-category study where
4 categories are synthetic.
