"""
prompts.py — the three task prompts. Identical for every model.

Output is forced JSON so scoring is mechanical. Small models will still break
format sometimes; run_benchmark.py retries once with a "JSON only" nudge and
score_benchmark.py counts unparseable outputs as a separate column.
"""

CATEGORIES = [
    "clickable_icon_not_iconbutton", "color_contrast", "decorative_mislabeled",
    "error_state_no_semantics", "missing_content_description", "missing_heading_semantics",
    "missing_interaction_semantics", "missing_merge_descendants", "missing_semantics_role",
    "missing_state_description", "pointerinput_no_semantics", "progress_no_semantics",
    "text_truncation_scaling", "textfield_no_label", "touch_target_size",
]
CAT_LIST = "\n".join(f"- {c}" for c in CATEGORIES)

SYSTEM = (
    "You are an expert Android accessibility reviewer for Jetpack Compose. "
    "You know how TalkBack reads Compose semantics and what Material 3 components "
    "provide by default. Answer only in the JSON schema requested. No prose outside the JSON."
)

# ---------------------------------------------------------------- DETECT
DETECT = """Review this Jetpack Compose composable for accessibility defects.

Consider only what is in the code shown. Material 3 components (Switch, Checkbox,
RadioButton, IconButton, TextField with label, determinate progress indicators)
supply role, state, minimum touch target, and error semantics by default; do not
report those as missing unless the code overrides them.

Categories (use these exact strings):
{cats}

Imports:
{imports}

Composable:
{code}

Respond with exactly this JSON:
{{
  "has_issue": true | false,
  "issues": [
    {{"category": "<one of the categories>", "line_hint": "<short quote of the offending line>", "why": "<one sentence>"}}
  ],
  "confidence": <integer 0-100>,
  "abstain": true | false
}}
If has_issue is false, "issues" must be []. Set "abstain": true only if you
genuinely cannot judge from the code shown (e.g. theme-resolved colors)."""

# ---------------------------------------------------------------- REPAIR
REPAIR = """This Jetpack Compose composable has the following accessibility defect:

  category: {category}
  location: {anchor}

Imports:
{imports}

Composable:
{code}

Fix ONLY this defect. Preserve every other line exactly. Use real Jetpack Compose
and Material 3 APIs only; do not invent parameters or modifiers.

Respond with exactly this JSON:
{{
  "fixed_code": "<the complete composable with the fix applied, as a single string>",
  "change_summary": "<one sentence: what you changed and which API you used>",
  "confidence": <integer 0-100>
}}"""

# ---------------------------------------------------------------- REFLECT
REFLECT = """You previously reviewed a composable and produced this analysis:

{prior_json}

Here is the composable again:

Imports:
{imports}

Composable:
{code}

Re-examine your analysis critically. Consider whether Material 3 defaults already
handle what you flagged, whether you missed a defect, and whether the code shown
is sufficient to decide.

Respond with exactly this JSON:
{{
  "revised_has_issue": true | false,
  "revised_issues": [ {{"category": "<category>", "why": "<one sentence>"}} ],
  "changed_mind": true | false,
  "confidence": <integer 0-100>,
  "abstain": true | false,
  "uncertainty_reason": "<one sentence, or empty string>"
}}"""


def detect_prompt(code, imports):
    return DETECT.format(cats=CAT_LIST, imports=imports or "(none)", code=code)

def repair_prompt(code, imports, category, anchor):
    return REPAIR.format(imports=imports or "(none)", code=code, category=category, anchor=anchor)

def reflect_prompt(code, imports, prior_json):
    return REFLECT.format(imports=imports or "(none)", code=code, prior_json=prior_json)
