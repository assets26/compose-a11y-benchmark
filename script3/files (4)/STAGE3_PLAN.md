# Stage 3 plan — from 6,053 candidates to a verifiable dataset

Your pre-screen found candidates in **all 15 categories**. Seeding is off the
table — good. The new problem is volume: 6,053 candidates is 100+ hours of
manual verification. The fix is a reproducible stratified sample, sized from
measured confirm rates rather than guessed.

## Step 1 — Pilot (do this first, ~4 hours)

```bash
python3 s3a_sample_for_verification.py --mode pilot --n 20
```

Draws 20 random candidates per category (fixed seed 20260911, max 3 per repo so
one big app cannot dominate). ~300 items with code snippets included.

Open `verify_pilot.csv`, fill the `verdict` column with
`TRUE_ISSUE` / `NOT_AN_ISSUE` / `UNSURE`. **Judge in context, not by pattern** —
same rule as study 1: an unlabeled icon inside an interactive button is a real
issue; a decorative icon beside a Text label is not.

Then compute the confirm rate per category (confirmed / rated) and write:

```json
{ "missing_content_description": 0.62,
  "pointerinput_no_semantics": 0.75,
  "missing_heading_semantics": 0.15 }
```
into `confirm_rates.json`.

## Step 2 — Decide what survives

Keep a category only if it clears BOTH bars:

| Bar | Threshold | Why |
|---|---|---|
| Confirm rate | >= ~30% | Below this the detector is mostly noise, and a reviewer will ask why you kept it |
| Confirmed instances available | enough to reach ~25 | A category with n=4 cannot support a per-category claim |

Expect to drop 3–6 categories. **That is a good outcome, not a failure.** Report
them as "screened but excluded, with the confirm rate that justified exclusion" —
it shows the screening was principled rather than convenient.

My predictions, to check against your data:
- `missing_heading_semantics` — very high raw count (537), lowest confirm rate.
  Likely drop, or cap hard.
- `pointerinput_no_semantics` — low count (52), high confirm rate. Keep; it is
  your most severe category (invisible to TalkBack entirely).
- `color_contrast` (127) — confirm rate probably low, since most hits will be
  hardcoded colors that are actually fine. Check before keeping.
- `missing_merge_descendants` (577) — high count, medium rate, needs judgment.

## Step 3 — Full sample

```bash
python3 s3a_sample_for_verification.py --mode full --target-confirmed 25 \
    --exclude missing_heading_semantics,color_contrast
```

Sizes each category automatically from its confirm rate — if a category confirms
at 40% and you want 25 confirmed, it samples ~68. Aim for **8–10 categories
x ~25 confirmed = 200–250 real issues**, roughly 9x study 1's 27, and all real.

## Step 4 — Dual rating, built in from the start

Every run already emits:
- `verify_<mode>_blind.csv` — shuffled, verdicts stripped → give to rater 2
- `verify_<mode>_answerkey.csv` — your verdicts → for `cohens_kappa.py`

Do this for the pilot too. If kappa is poor on the pilot, your criteria sheet
needs tightening **before** you spend time on the full sample — cheaper to find
out now than after 250 items.

**Do the same for repair ratings later.** That was the single criticism both
ASSETS reviewers raised, and it is the one thing text alone could not fix.

## Step 5 — Benchmark cost check

Before running models: count the composables in your final dataset.
Cost ~= composables x 7 models x 3 runs. 250 composables = ~5,250 calls.
Fine for cloud models at efficient tier; local models just take wall-clock time.

## Numbers to reconcile before writing

Stage 1 reported 157 repos / 2,993 files; Stage 2 reported 175 repos / 3,024
files. Settle on one set (re-run `s2` after mining is final) and use it
consistently in the Method — a reviewer comparing the two would flag it.
