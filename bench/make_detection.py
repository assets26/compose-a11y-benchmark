#!/usr/bin/env python3
"""
make_detection.py -> fig_detection.pdf
Recall vs. specificity scatter. Colorblind-safe (Okabe-Ito), and identity is
carried by BOTH color and marker shape + a direct text label, never color
alone -- appropriate for an accessibility paper. Numbers are the frozen final
results (results/detect_composable_summary.csv); edit here if the CSV changes.
Phi-3-mini completed only 77 composables and is excluded (camera-ready).

    pip install matplotlib
    python make_detection.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
matplotlib.rcParams["pdf.fonttype"] = 42   # embed TrueType, not Type 3 (ACM camera-ready)
matplotlib.rcParams["font.family"] = "DejaVu Sans"

# Okabe-Ito colorblind-safe palette
BLUE = "#0072B2"   # closed / cloud
VERM = "#D55E00"   # open / local
GREY = "#999999"

# model: (specificity, recall, tier)   tier in {"closed","open"}
# composable-level detection scoring (matches score_composable.py)
DATA = {
    "Gemini 3.8 Flash":  (0.416, 0.912, "closed"),
    "GPT-5-mini":        (0.161, 0.978, "closed"),
    "Claude Sonnet 4.5": (0.134, 0.978, "closed"),
    "Gemma3-1B":         (0.662, 0.470, "open"),
    "Qwen2.5-Coder-7B":  (0.255, 0.821, "open"),
    "Mistral-7B":        (0.013, 0.993, "open"),
}
# per-label text offsets (points) to avoid collisions; ha per label
OFF = {
    "Gemini 3.8 Flash":  (9, 0, "left"),
    "GPT-5-mini":        (9, 0, "left"),
    "Claude Sonnet 4.5": (-2, -12, "left"),
    "Gemma3-1B":         (-9, -4, "right"),
    "Qwen2.5-Coder-7B":  (9, 0, "left"),
    "Mistral-7B":        (4, 10, "left"),
}

fig, ax = plt.subplots(figsize=(3.4, 2.1), dpi=200)

# chance diagonal: balanced accuracy = 0.5  ->  recall = 1 - specificity
ax.plot([0, 1], [1, 0], color=GREY, lw=1, ls="--", zorder=1)
ax.text(0.52, 0.52, "chance", color=GREY, fontsize=6.5, rotation=-38,
        rotation_mode="anchor", ha="center", va="bottom")

for name, (spec, rec, tier) in DATA.items():
    closed = tier == "closed"
    ax.scatter(spec, rec,
               marker="o" if closed else "s",
               s=46 if closed else 42,
               facecolor=(BLUE if closed else VERM),
               edgecolor="white", linewidth=0.8, zorder=3)
    dx, dy, ha = OFF[name]
    label = name + " (flags nearly everything)" if name == "Mistral-7B" else name
    ax.annotate(label, (spec, rec), textcoords="offset points", xytext=(dx, dy),
                fontsize=6.2, color="#222222", ha=ha, va="center")

ax.set_xlabel("Specificity (clean code left alone)", fontsize=8)
ax.set_ylabel("Recall (real issues found)", fontsize=8)
ax.set_xlim(-0.03, 0.78)
ax.set_ylim(0.40, 1.05)
ax.tick_params(labelsize=7)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(True, color="#EEEEEE", lw=0.6, zorder=0)
ax.set_axisbelow(True)

# legend by shape+color
from matplotlib.lines import Line2D
leg = [Line2D([0],[0], marker="o", color="w", markerfacecolor=BLUE,
              markeredgecolor="white", markersize=7, label="closed (cloud)"),
       Line2D([0],[0], marker="s", color="w", markerfacecolor=VERM,
              markeredgecolor="white", markersize=7, label="open (local)")]
ax.legend(handles=leg, fontsize=6.5, loc="lower left", frameon=False)

fig.tight_layout(pad=0.4)
fig.savefig("fig_detection.pdf", bbox_inches="tight")
print("wrote fig_detection.pdf")
