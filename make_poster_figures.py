#!/usr/bin/env python3
"""
Re-render the study figures at A0-poster print resolution.

Same data and same visual language as experiments.py, but sized and weighted for
print: 300 DPI, fonts scaled up for reading at 1-3 m, thicker lines, no tiny
tick labels.  Column-width figures are matched to COL_W_CM so they land at
~300 DPI at their final physical size on the poster.

Usage (run from the folder holding results/):
    python make_poster_figures.py
"""
import os
import re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RES = "results"
FIG = os.path.join(RES, "poster_figs")
os.makedirs(FIG, exist_ok=True)

COL_W_CM = 23.0          # physical width a column-width figure occupies on A0
DPI = 300
CM = 1 / 2.54

res = pd.read_csv(os.path.join(RES, "metrics_all.csv"))
tiers = pd.read_csv(os.path.join(RES, "proposed_risk_tiers.csv"))
fimp = pd.read_csv(os.path.join(RES, "feature_importance.csv"))

MODELS = ["Logistic Regression", "Random Forest", "XGBoost"]
ORDER = ["Sentiment only", "Linguistic only", "Sentiment + linguistic",
         "TF-IDF text only", "TF-IDF + sentiment + linguistic"]
FULL = "TF-IDF + sentiment + linguistic"
COLORS = ["#7FB3E6", "#0070C0", "#0B2A4A"]
ACCENT = "#C0392B"
GREY = "#5A5A5A"

plt.rcParams.update({
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 13.5,
    "xtick.labelsize": 10.5,
    "ytick.labelsize": 10.5,
    "legend.fontsize": 10.5,
    "axes.linewidth": 1.1,
    "lines.linewidth": 2.2,
    "savefig.bbox": "tight",
    "savefig.facecolor": "white",
    "figure.facecolor": "white",
})


def finish(fig, name, width_cm=COL_W_CM):
    """Save at fixed physical width and true 300 DPI."""
    w_in = width_cm * CM
    h_in = w_in * fig.get_figheight() / fig.get_figwidth()
    fig.set_size_inches(w_in, h_in)
    out = os.path.join(FIG, name)
    fig.savefig(out, dpi=DPI, facecolor="white")
    plt.close(fig)
    px = int(round(w_in * DPI))
    print(f"  {name:34s} {px:5d} px wide  @ {DPI} dpi  ({width_cm:.0f} cm)")


def clean(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=3, width=1.0)


print("Rendering poster figures at 300 dpi ...")

# ---------------------------------------------------------------- ablation (F1)
fig, ax = plt.subplots(figsize=(10, 5.2))
w = 0.26
for k, m in enumerate(MODELS):
    v = [res[(res.feature_set == s) & (res.model == m)].f1.values[0] for s in ORDER]
    ax.bar(np.arange(len(ORDER)) + (k - 1) * w, v, w, label=m, color=COLORS[k])
ax.set_xticks(range(len(ORDER)))
ax.set_xticklabels(["Sentiment\nonly", "Linguistic\nonly", "Sentiment +\nlinguistic",
                    "TF-IDF\nonly", "TF-IDF +\nsent + ling"], fontsize=10.5)
ax.set_ylabel("F1 score (at-risk class)")
ax.set_ylim(0, 1.0)
ax.legend(frameon=False, ncol=3, loc="upper left")
ax.set_title("Ablation: which feature groups identify at-risk posts?", pad=10)
clean(ax)
finish(fig, "ablation_f1.png")

# ---------------------------------------------------------------- model comparison
fig, ax = plt.subplots(figsize=(10, 5.2))
mets = ["recall", "precision", "f1", "auc"]
w = 0.2
for k, mt in enumerate(mets):
    v = [res[(res.feature_set == FULL) & (res.model == m)][mt].values[0] for m in MODELS]
    lbl = "AUC" if mt == "auc" else mt.capitalize()
    ax.bar(np.arange(3) + (k - 1.5) * w, v, w, label=lbl,
           color=["#0B2A4A", "#0070C0", "#7FB3E6", "#F5A623"][k])
    for x, val in zip(np.arange(3) + (k - 1.5) * w, v):
        ax.text(x, val + 0.018, f"{val:.2f}", ha="center", fontsize=8.5, color=GREY)
ax.set_xticks(range(3))
ax.set_xticklabels(["Logistic\nRegression", "Random\nForest", "XGBoost"])
ax.set_ylim(0, 1.12)
ax.legend(frameon=False, ncol=4, loc="upper right")
ax.set_title("Model comparison on the full feature set", pad=10)
clean(ax)
finish(fig, "model_comparison.png")

# ---------------------------------------------------------------- feature importance
f2 = fimp.sort_values("xgb_importance")
fig, ax = plt.subplots(figsize=(10, 6.4))
cols = [ACCENT if f == "distress_term_rate" else "#0070C0" for f in f2.feature]
ax.barh(f2.feature, f2.xgb_importance, color=cols)
ax.set_xlabel("XGBoost feature importance (gain)")
ax.set_title("Which indicators carry the signal?", pad=10)
for i, (f, v) in enumerate(zip(f2.feature, f2.xgb_importance)):
    ax.text(v + 0.004, i, f"{v:.3f}", va="center", fontsize=9, color=GREY)
ax.set_xlim(0, f2.xgb_importance.max() * 1.16)
clean(ax)
finish(fig, "feature_importance.png")

# ---------------------------------------------------------------- claim test
cl = pd.read_csv(os.path.join(RES, "claim_test_combined_vs_single.csv"))
q1 = cl[cl.combined == "Sentiment + linguistic"].copy()
q2 = cl[cl.combined == FULL].copy()
# stacked (2 rows x 1 col) so it fits a single poster column at 300 dpi
fig, axes = plt.subplots(2, 1, figsize=(10, 8.4))

for ax, d, title, note in [
    (axes[0], q1, "A.  Do sentiment + linguistic beat either group alone?",
     "all 6 comparisons favour combining  (6/6 CIs exclude zero)"),
    (axes[1], q2, "B.  Do they add anything on top of TF-IDF?",
     "sign flips across models  ->  claim does NOT hold"),
]:
    ypos = np.arange(len(MODELS))[::-1]
    for y, (_, r) in zip(ypos, d.iterrows()):
        sig = bool(r.ci_excludes_zero)
        col = "#2E7D32" if (sig and r.delta_f1 > 0) else (ACCENT if sig else GREY)
        ax.plot([r.ci_low, r.ci_high], [y, y], color=col, lw=4.5, solid_capstyle="round")
        ax.plot(r.delta_f1, y, "o", color=col, ms=12,
                zorder=3, markeredgecolor="white", markeredgewidth=1.6)
    ax.axvline(0, color="black", lw=1.3, ls="--")
    ax.set_yticks(ypos)
    ax.set_yticklabels([m.replace(" ", "\n", 0) for m in MODELS], fontsize=10)
    ax.set_xlabel(r"$\Delta$F1  (combined $-$ baseline),  95% bootstrap CI")
    ax.set_title(title, fontsize=12, pad=8, loc="left")
    ax.text(0.0, -0.42, note, transform=ax.transAxes, ha="left",
            fontsize=10, color=GREY, style="italic")
    ax.set_ylim(-0.75, len(MODELS) - 0.25)
    clean(ax)

axes[0].set_xlim(-0.022, 0.115)
axes[1].set_xlim(-0.055, 0.065)
fig.suptitle("Does combining features help?  Paired bootstrap, 1000 resamples",
             fontsize=13, y=0.995)
fig.tight_layout(rect=[0, 0, 1, 0.97])
finish(fig, "claim_test.png")


# ---------------------------------------------------------------- risk tiers
fig, ax = plt.subplots(figsize=(10, 4.4))
bands = tiers.band.tolist()
rates = (tiers.observed_at_risk_rate * 100).tolist()
posts = tiers.posts.tolist()
bc = ["#2E7D32", "#F5A623", ACCENT]
b = ax.bar(bands, rates, 0.55, color=bc)
for r, rate, n in zip(b, rates, posts):
    ax.text(r.get_x() + r.get_width() / 2, rate + 2.5,
            f"{rate:.1f}%\n(n={n:,})", ha="center", fontsize=10, color=GREY)
ax.axhline(tiers.actual_at_risk.sum() / tiers.posts.sum() * 100, color="black",
           ls="--", lw=1.3)
ax.text(2.42, tiers.actual_at_risk.sum() / tiers.posts.sum() * 100 + 1.5,
        f"base rate {tiers.actual_at_risk.sum()/tiers.posts.sum()*100:.0f}%",
        ha="right", fontsize=9.5, color="black")
ax.set_ylabel("Observed at-risk rate in band (%)")
ax.set_ylim(0, 112)
ax.set_xlabel("Predicted probability band  (PROPOSED - not clinically validated)")
ax.set_title("Proposed risk tiers: the score is ordinally informative", pad=10)
clean(ax)
finish(fig, "risk_tiers.png")

# ---------------------------------------------------------------- confusion matrix
cm_txt = open(os.path.join(RES, "confusion_matrix_best.txt")).read()
cell = dict(re.findall(r"\b(TN|FP|FN|TP)=(\d+)", cm_txt))
tn, fp, fn, tp = (int(cell[k]) for k in ("TN", "FP", "FN", "TP"))
cm = np.array([[tn, fp], [fn, tp]])
fig, ax = plt.subplots(figsize=(7.4, 6.4))
ax.imshow(cm, cmap="Blues")
for i in range(2):
    for j in range(2):
        ax.text(j, i, f"{cm[i, j]:,}", ha="center", va="center", fontsize=26,
                color="white" if cm[i, j] > cm.max() / 2 else "black", weight="bold")
ax.set_xticks([0, 1]); ax.set_yticks([0, 1])
ax.set_xticklabels(["Not at risk", "At risk"], fontsize=12)
ax.set_yticklabels(["Not at risk", "At risk"], fontsize=12)
ax.set_xlabel("Predicted", fontsize=12); ax.set_ylabel("Actual", fontsize=12)
ax.set_title("XGBoost, full features  (n = 2,838)", fontsize=12.5, pad=10)
for s in ax.spines.values():
    s.set_visible(False)
ax.text(0.5, -0.20, f"missed {fn/(fn+tp)*100:.1f}% of at-risk posts   |   "
                    f"false alarms {fp/(fp+tn)*100:.1f}%",
        transform=ax.transAxes, ha="center", fontsize=11, color=ACCENT, weight="bold")
finish(fig, "confusion_matrix.png", width_cm=COL_W_CM * 0.80)

# ROC deliberately omitted: experiments.py does not persist test-set
# probabilities, and the AUC values are already reported in the model
# comparison chart.  Regenerate from the saved metrics if a panel asks.
print(f"\nDone. {len(os.listdir(FIG))} figures in ./{FIG}/ at {DPI} dpi.")
print("No ROC panel: experiments.py does not persist test probabilities, and the")
print("AUC values are already shown in model_comparison.png.")
