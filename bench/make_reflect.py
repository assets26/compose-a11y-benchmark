#!/usr/bin/env python3
"""
make_reflect.py -> fig_reflect.pdf
Diverging bars: verdict changes toward vs. away from ground truth under
self-reflection. Diverging = two hues + neutral, per dataviz rules; identity
is also labeled directly so it is never color-alone. Numbers are the frozen
final results (results/reflect_summary.csv).

    python make_reflect.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
matplotlib.rcParams["pdf.fonttype"] = 42   # embed TrueType, not Type 3 (ACM camera-ready)
matplotlib.rcParams["font.family"] = "DejaVu Sans"

GREEN = "#009E73"   # toward ground truth (Okabe-Ito bluish green)
VERM  = "#D55E00"   # away from ground truth (Okabe-Ito vermillion)

# model: (toward_gold, away_from_gold, tier)
# reflection on 129 decidable items (UNSURE excluded)
DATA = [
    ("Gemini 3.8 Flash",  7,  1, "closed"),
    ("GPT-5-mini",        8,  5, "closed"),
    ("Claude Sonnet 4.5", 8,  5, "closed"),
    ("Qwen2.5-Coder-7B", 19, 23, "open"),
    ("Mistral-7B",        8,  3, "open"),
    ("Gemma3-1B",        15, 21, "open"),
]

labels = [d[0] for d in DATA]
toward = [d[1] for d in DATA]
away   = [-d[2] for d in DATA]
y = list(range(len(DATA)))[::-1]   # first model on top

fig, ax = plt.subplots(figsize=(3.4, 2.25), dpi=200)

ax.barh(y, toward, color=GREEN, height=0.62, zorder=3, label="toward ground truth")
ax.barh(y, away,   color=VERM,  height=0.62, zorder=3, label="away from ground truth")
ax.axvline(0, color="#333333", lw=0.9, zorder=4)

# value labels at bar ends
for yi, t, a in zip(y, toward, away):
    if t:
        ax.text(t + 0.6, yi, str(t), va="center", ha="left", fontsize=6.3, color="#222")
    if a:
        ax.text(a - 0.6, yi, str(-a), va="center", ha="right", fontsize=6.3, color="#222")
    net = t + a
    ax.text(30.5, yi, f"net {net:+d}", va="center", ha="right", fontsize=6.0, color="#555")

ax.set_yticks(y)
ax.set_yticklabels(labels, fontsize=7)
ax.set_xlabel("Verdicts changed under reflection (count)", fontsize=8)
ax.set_xlim(-28, 31)
ax.set_xticks([-20, -10, 0, 10, 20])
ax.tick_params(axis="x", labelsize=7)
ax.tick_params(axis="y", length=0)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.grid(True, axis="x", color="#EEEEEE", lw=0.6, zorder=0)
ax.set_axisbelow(True)
ax.legend(fontsize=6.3, loc="lower center", bbox_to_anchor=(0.42, 1.0), frameon=False, ncol=2,
          handlelength=1.2, columnspacing=1.2)

fig.tight_layout(pad=0.4)
fig.savefig("fig_reflect.pdf", bbox_inches="tight")
print("wrote fig_reflect.pdf")
