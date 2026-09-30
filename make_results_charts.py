#!/usr/bin/env python3
"""
Render the four RESULT charts for the 140 x 90 cm landscape poster.

Each chart is saved at the exact physical size it will occupy in the Results
panel grid (52.0 x 14.2 cm, 300 dpi), so placement in the .pptx is exact and
text stays sharp in print.  Every number is read from results/ at render time:

  fig_ablation.png        F1 by five feature sets x three models, +95% CI bars
  fig_model_compare.png   precision / recall / F1 / AUC, three models (full set)
  fig_confusion.png       2x2 confusion matrix of the best model, FN called out
  fig_feature_importance.png  XGBoost feature gain, sentiment + linguistic cues

Usage (from the folder holding results/):
    python make_results_charts.py
"""
import os
import re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

RES = "results"
FIG = os.path.join(RES, "poster_figs")
os.makedirs(FIG, exist_ok=True)

FIGW, FIGH = 52.0, 16.5          # cm of each chart as placed on the poster
DPI = 300

INK = "#3B2B2E"          # near-black warm text
CRIMSON = "#B71C2A"      # rich red
ROSE = "#E5949D"         # soft red
DEEP = "#6A1320"         # deep maroon
GREEN = "#2E7D32"        # semantic (true positives)
MUT = "#7A666D"          # muted grey-red
SOFT = "#9A838A"

# aliases used throughout the chart code
NAVY = INK
BLUE = CRIMSON
LBLUE = ROSE
RED = DEEP
GREY = MUT
LGREY = SOFT

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 17,
    "axes.labelsize": 19,
    "axes.titlesize": 22,
    "xtick.labelsize": 16,
    "ytick.labelsize": 16,
    "legend.fontsize": 15,
    "axes.linewidth": 1.4,
    "axes.edgecolor": "#5A6B7A",
    "figure.facecolor": "white",
})

# ---------------------------------------------------------------- data load
metrics = pd.read_csv(os.path.join(RES, "metrics_all.csv"))
MODELS = ["Logistic Regression", "Random Forest", "XGBoost"]
ORDER = ["Sentiment only", "Linguistic only", "Sentiment + linguistic",
         "TF-IDF text only", "TF-IDF + sentiment + linguistic"]
SHORT = ["Sentiment", "Linguistic", "Sent + ling", "TF-IDF", "All features"]
MC = {"Logistic Regression": ROSE, "Random Forest": CRIMSON, "XGBoost": DEEP}

raw = open(os.path.join(RES, "confusion_matrix_best.txt")).read()
cm = {k: int(v) for k, v in re.findall(r"\b(TN|FP|FN|TP)=(\d+)", raw)}
cm_model = re.search(r"model=(\S+)", raw).group(1)
fnr = float(re.search(r"false negative rate\) = ([\d.]+)", raw).group(1))
fpr = float(re.search(r"false positive rate\)   = ([\d.]+)", raw).group(1))

fimp = pd.read_csv(os.path.join(RES, "feature_importance.csv"))


def newfig():
    return plt.figure(figsize=(FIGW / 2.54, FIGH / 2.54))


def save(fig, name):
    out = os.path.join(FIG, name)
    fig.savefig(out, dpi=DPI, facecolor="white")
    plt.close(fig)
    from PIL import Image
    with Image.open(out) as im:
        print(f"  {name:26s} {im.size[0]} x {im.size[1]} px   "
              f"{FIGW} x {FIGH} cm, {im.size[0] / (FIGW / 2.54):.0f} dpi")


# =================================================== A. ablation, with CI bars
fig = newfig()
ax = fig.add_axes([0.06, 0.20, 0.90, 0.66])
w = 0.27
for k, m in enumerate(MODELS):
    xs = np.arange(len(ORDER)) + (k - 1) * w
    vals = np.array([metrics[(metrics.feature_set == s) & (metrics.model == m)]
                     .f1.values[0] for s in ORDER])
    lo = np.array([metrics[(metrics.feature_set == s) & (metrics.model == m)]
                   .f1_ci_low.values[0] for s in ORDER])
    hi = np.array([metrics[(metrics.feature_set == s) & (metrics.model == m)]
                   .f1_ci_high.values[0] for s in ORDER])
    ax.bar(xs, vals, w, label=m, color=MC[m], yerr=[vals - lo, hi - vals],
           capsize=3.5, error_kw=dict(elinewidth=1.5, ecolor="#33414F"))
ax.set_xticks(np.arange(len(ORDER)))
ax.set_xticklabels(SHORT)
ax.set_ylabel("F1 score")
ax.set_ylim(0, 1.03)
ax.legend(frameon=False, ncol=3, loc="lower right", bbox_to_anchor=(1.0, 1.02),
          handlelength=1.1, columnspacing=1.2)
ax.set_title("A   Ablation - F1 across five feature sets and three models (95% CI error bars)",
             loc="left", fontsize=22, pad=12)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.tick_params(length=3)
save(fig, "fig_ablation.png")

# =================================================== B. model comparison (full set)
fig = newfig()
ax = fig.add_axes([0.06, 0.21, 0.90, 0.64])
full = metrics[metrics.feature_set == "TF-IDF + sentiment + linguistic"]
mets = ["precision", "recall", "f1", "auc"]
mlab = ["Precision", "Recall", "F1", "AUC"]
for j, met in enumerate(mets):
    for k, m in enumerate(MODELS):
        v = float(full[full.model == m].iloc[0][met])
        ax.bar(j + (k - 1) * w, v, w, color=MC[m], edgecolor="white", linewidth=0.5)
        ax.text(j + (k - 1) * w, v + 0.004, f"{v:.3f}", ha="center", va="bottom",
                fontsize=12.5, color=NAVY)
ax.set_xticks(range(len(mets)))
ax.set_xticklabels(mlab)
ax.set_ylabel("Score")
ax.set_ylim(0.82, 1.02)
ax.set_yticks(np.arange(0.85, 1.01, 0.05))
best = full.sort_values("f1").iloc[-1]
ax.set_title("B   Model comparison - full feature set (TF-IDF + sentiment + linguistic)",
             loc="left", fontsize=22, pad=12)
ax.text(0.995, 0.05, (f"Best: XGBoost  F1 {best.f1:.3f}  recall {best.recall:.3f}  "
                       f"AUC {best.auc:.3f}"),
        transform=ax.transAxes, ha="right", fontsize=14, color=GREY,
        bbox=dict(boxstyle="round,pad=0.35", fc="#FDF3F4", ec="#E3C2C8", lw=1))
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.tick_params(length=3)
save(fig, "fig_model_compare.png")

# =================================================== C. confusion matrix, FN out
TN, FP, FN, TP = cm["TN"], cm["FP"], cm["FN"], cm["TP"]
fig = newfig()
axm = fig.add_axes([0.10, 0.24, 0.52, 0.60])
cells = np.array([[[0xF3, 0xF7, 0xFB], [0xFB, 0xEC, 0xEB]],
                  [[0xF9, 0xDF, 0xDD], [0xE3, 0xF1, 0xE7]]], dtype=float) / 255.0
axm.imshow(cells, aspect="auto", interpolation="nearest")
axm.set_xticks([0, 1]); axm.set_xticklabels(["Predicted: not at-risk",
                                             "Predicted: at-risk"], fontsize=14)
axm.set_yticks([0, 1]); axm.set_yticklabels(["Actual: not at-risk",
                                             "Actual: at-risk"], fontsize=14)
axm.set_xticks(np.arange(-0.5, 2, 1), minor=True)
axm.set_yticks(np.arange(-0.5, 2, 1), minor=True)
axm.grid(which="minor", color="white", linewidth=2.5)
axm.tick_params(which="minor", length=0)
texts = [((0, 0), TN, f"{TN:,}", "#33414F", "TN"),
         ((1, 0), FP, f"{FP:,}", "#33414F", "FP"),
         ((0, 1), FN, f"{FN:,}", RED, "FN  -> MISSED"),
         ((1, 1), TP, f"{TP:,}", GREEN, "TP")]
for (r, c), val, lab, col, tag in texts:
    axm.text(c, r, lab, ha="center", va="center", fontsize=34, fontweight="bold", color=col)
    axm.text(c, r + 0.30, tag, ha="center", va="center", fontsize=13, color=col)
axm.set_title(f"C   Confusion matrix - best model ({cm_model}, all features)",
              loc="left", fontsize=22, pad=12)
for sp in axm.spines.values():
    sp.set_edgecolor("#5A6B7A"); sp.set_linewidth(1.4)
axr = fig.add_axes([0.69, 0.24, 0.27, 0.60])
axr.set_xticks([]); axr.set_yticks([])
for sp in axr.spines.values():
    sp.set_visible(False)
axr.text(0.0, 0.72, "False negatives called out", fontsize=17, fontweight="bold",
         color=RED, transform=axr.transAxes)
axr.text(0.0, 0.52, f"{FN} of {FN + TP:,} true at-risk posts were missed\n"
                    f"({fnr*100:.1f}% of the at-risk class).", fontsize=15.5, color=NAVY,
         transform=axr.transAxes, va="center")
axr.text(0.0, 0.18, f"False alarms: {FP} of {FP + TN:,} controls ({fpr*100:.1f}%).\n"
                    f"Recall {TP/(TP+FN):.3f}  precision {TP/(TP+FP):.3f}.",
         fontsize=15.5, color=GREY, transform=axr.transAxes, va="center")
save(fig, "fig_confusion.png")

# =================================================== D. feature importance
fig = newfig()
ax = fig.add_axes([0.13, 0.10, 0.80, 0.76])
f2 = fimp.sort_values("xgb_importance")
cols = [DEEP if x >= f2.xgb_importance.nlargest(3).min() else CRIMSON
        for x in f2.xgb_importance]
ax.barh(f2.feature, f2.xgb_importance, color=cols, height=0.62)
for i, (f, v) in enumerate(zip(f2.feature, f2.xgb_importance)):
    ax.text(v + 0.004, i, f"{v:.3f}", va="center", fontsize=13.5, color=GREY)
labels = {f: f.replace("_", " ").replace("vader neg", "negative sentiment (VADER)") for f in f2.feature}
ax.set_yticks(range(len(f2)))
ax.set_yticklabels([labels[f] for f in f2.feature], fontsize=15)
ax.set_xlabel("XGBoost feature gain")
ax.set_title("D   Which sentiment and linguistic indicators drive the flags?",
             loc="left", fontsize=22, pad=12)
ax.set_xlim(0, f2.xgb_importance.max() * 1.24)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.tick_params(length=3)
save(fig, "fig_feature_importance.png")

print("done")