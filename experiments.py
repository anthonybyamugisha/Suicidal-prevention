#!/usr/bin/env python3
"""
AI and data-driven identification of suicide-risk signals: proof-of-concept experiments.

Usage (from the folder that holds your dataset):
    python run_experiments.py --data yourfile.csv
Optional:
    --text-col NAME  --label-col NAME     (if auto-detection picks the wrong columns)
    --pos-label "suicide" --neg-label "non-suicide"   (exact label values, if auto-mapping is wrong)
    --max-rows 40000   (stratified sample cap; keeps the laptop responsive)
    --seed 42

Everything the poster needs is written to ./results/ . Only report numbers this script prints.
"""
import argparse, json, os, re, sys, time, warnings
import numpy as np
import pandas as pd
import scipy.sparse as sp
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, roc_auc_score, confusion_matrix, roc_curve)
from xgboost import XGBClassifier
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

warnings.filterwarnings("ignore")
OUT = "results"
os.makedirs(OUT, exist_ok=True)

# ----------------------------------------------------------------------------- args
ap = argparse.ArgumentParser()
ap.add_argument("--data", required=True)
ap.add_argument("--text-col")
ap.add_argument("--label-col")
ap.add_argument("--pos-label")
ap.add_argument("--neg-label")
ap.add_argument("--max-rows", type=int, default=40000)
ap.add_argument("--seed", type=int, default=42)
args = ap.parse_args()
SEED = args.seed
t0 = time.time()


def log(msg):
    print(f"[{time.time()-t0:6.0f}s] {msg}", flush=True)


# ----------------------------------------------------------------------------- load
path = args.data
if path.lower().endswith((".xlsx", ".xls")):
    df = pd.read_excel(path)
else:
    try:
        df = pd.read_csv(path)
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="latin-1")
log(f"Loaded {path}: {df.shape[0]} rows, columns = {list(df.columns)}")

# ----------------------------------------------------------------------------- column detection
text_col = args.text_col
if not text_col:
    obj = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])]
    if not obj:
        sys.exit("No text column found. Use --text-col.")
    text_col = max(obj, key=lambda c: df[c].astype(str).str.len().mean())

label_col = args.label_col
if not label_col:
    cands = [c for c in df.columns if c != text_col and 2 <= df[c].nunique() <= 10]
    pref = [c for c in cands if re.search(r"class|label|target|status|category", str(c).lower())]
    pool = pref or cands
    if not pool:
        sys.exit("No label column found. Use --label-col.")
    label_col = pool[0]
log(f"Text column = '{text_col}' | label column = '{label_col}'")

df = df[[text_col, label_col]].rename(columns={text_col: "text", label_col: "label_raw"})
df = df.dropna()
df["text"] = df["text"].astype(str).str.strip()
n_raw = len(df)

# ----------------------------------------------------------------------------- label mapping (binary)
raw_counts = df["label_raw"].value_counts().to_dict()
log(f"Raw label counts: {raw_counts}")
lab = df["label_raw"].astype(str).str.strip().str.lower()

if args.pos_label is not None and args.neg_label is not None:
    keep = lab.isin([args.pos_label.lower(), args.neg_label.lower()])
    df = df[keep].copy()
    df["y"] = (lab[keep] == args.pos_label.lower()).astype(int)
elif set(lab.unique()) <= {"0", "1", "0.0", "1.0"}:
    df["y"] = lab.astype(float).astype(int)
else:
    neg_pat = r"non|not|normal|no[ _-]?suicid|control|healthy"
    is_pos = lab.str.contains("suicid") & ~lab.str.contains(neg_pat)
    is_neg = lab.str.contains(neg_pat)
    keep = is_pos | is_neg
    if is_pos.sum() == 0 or is_neg.sum() == 0:
        sys.exit(f"Could not map labels automatically: {raw_counts}. "
                 f"Re-run with --pos-label and --neg-label using exact values.")
    df = df[keep].copy()
    df["y"] = is_pos[keep].astype(int)
    dropped = int((~keep).sum())
    if dropped:
        log(f"Dropped {dropped} rows from other classes (kept suicidal vs non-suicidal/normal only)")
pos_names = sorted(df.loc[df.y == 1, "label_raw"].astype(str).unique())
neg_names = sorted(df.loc[df.y == 0, "label_raw"].astype(str).unique())
log(f"Label mapping: at-risk (1) = {pos_names} | not at-risk (0) = {neg_names}")

# ----------------------------------------------------------------------------- clean
df = df[df["text"].str.len() >= 10]
n_before_dup = len(df)
df = df.drop_duplicates(subset="text")
n_dups = n_before_dup - len(df)
if len(df) > args.max_rows:
    df, _ = train_test_split(df, train_size=args.max_rows, stratify=df["y"], random_state=SEED)
    log(f"Stratified sample of {args.max_rows} rows used (--max-rows)")
df = df.reset_index(drop=True)
log(f"After cleaning: {len(df)} posts | at-risk = {int(df.y.sum())} ({df.y.mean():.1%})")

# ----------------------------------------------------------------------------- split
train_idx, test_idx = train_test_split(np.arange(len(df)), test_size=0.2,
                                       stratify=df["y"], random_state=SEED)
y = df["y"].values
ytr, yte = y[train_idx], y[test_idx]
log(f"Train = {len(train_idx)} | Test = {len(test_idx)}")

# ----------------------------------------------------------------------------- features
vader = SentimentIntensityAnalyzer()
FIRST = {"i", "me", "my", "myself", "mine", "i'm", "im", "i've", "ive", "i'd", "i'll"}
ABSOL = {"absolute", "absolutely", "all", "always", "complete", "completely", "constant",
         "constantly", "definitely", "entire", "ever", "every", "everyone", "everything",
         "full", "must", "never", "nothing", "totally", "whole"}
NEGW = {"no", "not", "never", "none", "nothing", "nobody", "neither", "nor", "cannot"}
DISTRESS = {"hopeless", "worthless", "pointless", "empty", "alone", "lonely", "tired",
            "burden", "useless", "numb", "trapped", "exhausted", "hate", "cry", "crying",
            "pain", "hurt", "failure", "sad", "depressed", "anxious", "scared"}
tok_re = re.compile(r"[a-z']+")

SENT_NAMES = ["vader_neg", "vader_neu", "vader_pos", "vader_compound"]
LING_NAMES = ["log_word_count", "avg_word_length", "first_person_rate", "absolutist_rate",
              "negation_rate", "distress_term_rate", "question_rate", "exclamation_rate",
              "uppercase_ratio"]


def sent_feats(t):
    s = vader.polarity_scores(t[:5000])
    return [s["neg"], s["neu"], s["pos"], s["compound"]]


def ling_feats(t):
    t = t[:5000]
    toks = tok_re.findall(t.lower())
    n = max(len(toks), 1)
    neg = sum(1 for w in toks if w in NEGW or w.endswith("n't"))
    letters = [c for c in t if c.isalpha()]
    up = sum(1 for c in letters if c.isupper()) / max(len(letters), 1)
    return [np.log1p(len(toks)),
            np.mean([len(w) for w in toks]) if toks else 0.0,
            sum(w in FIRST for w in toks) / n,
            sum(w in ABSOL for w in toks) / n,
            neg / n,
            sum(w in DISTRESS for w in toks) / n,
            t.count("?") / n,
            t.count("!") / n,
            up]


log("Computing sentiment (VADER) and linguistic features ...")
texts = df["text"].tolist()
S = np.array([sent_feats(t) for t in texts])
L = np.array([ling_feats(t) for t in texts])
log("Features done.")

sc_S = StandardScaler().fit(S[train_idx]); S_ = sc_S.transform(S)
sc_L = StandardScaler().fit(L[train_idx]); L_ = sc_L.transform(L)
tfidf = TfidfVectorizer(max_features=10000, ngram_range=(1, 2), min_df=3,
                        sublinear_tf=True, stop_words="english")
T = tfidf.fit(np.array(texts, dtype=object)[train_idx]).transform(texts)

SETS = {
    "Sentiment only": (lambda: sp.csr_matrix(S_), SENT_NAMES),
    "Linguistic only": (lambda: sp.csr_matrix(L_), LING_NAMES),
    "Sentiment + linguistic": (lambda: sp.csr_matrix(np.hstack([S_, L_])), SENT_NAMES + LING_NAMES),
    "TF-IDF text only": (lambda: T.tocsr(), None),
    "TF-IDF + sentiment + linguistic": (lambda: sp.hstack([T, sp.csr_matrix(np.hstack([S_, L_]))]).tocsr(), None),
}
spw = (ytr == 0).sum() / max((ytr == 1).sum(), 1)


def make_models():
    return {
        "Logistic Regression": LogisticRegression(max_iter=2000, C=1.0, class_weight="balanced",
                                                  solver="liblinear", random_state=SEED),
        "Random Forest": RandomForestClassifier(n_estimators=200, min_samples_leaf=2, n_jobs=-1,
                                                class_weight="balanced_subsample", random_state=SEED),
        "XGBoost": XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.1, subsample=0.8,
                                 colsample_bytree=0.6, tree_method="hist", n_jobs=-1,
                                 eval_metric="logloss", scale_pos_weight=spw, random_state=SEED),
    }


rng = np.random.default_rng(SEED)
BOOT = 1000


def boot_ci(yt, yp, fn):
    n = len(yt); vals = []
    for _ in range(BOOT):
        i = rng.integers(0, n, n)
        vals.append(fn(yt[i], yp[i]))
    return np.percentile(vals, [2.5, 97.5])


rows, preds, probs, fitted = [], {}, {}, {}
for sname, (build, _) in SETS.items():
    X = build()
    Xtr, Xte = X[train_idx], X[test_idx]
    for mname, model in make_models().items():
        ts = time.time()
        model.fit(Xtr, ytr)
        p = model.predict_proba(Xte)[:, 1]
        yp = (p >= 0.5).astype(int)
        r_lo, r_hi = boot_ci(yte, yp, lambda a, b: recall_score(a, b, zero_division=0))
        f_lo, f_hi = boot_ci(yte, yp, lambda a, b: f1_score(a, b, zero_division=0))
        rows.append(dict(feature_set=sname, model=mname,
                         accuracy=accuracy_score(yte, yp),
                         precision=precision_score(yte, yp, zero_division=0),
                         recall=recall_score(yte, yp, zero_division=0),
                         recall_ci_low=r_lo, recall_ci_high=r_hi,
                         f1=f1_score(yte, yp, zero_division=0),
                         f1_ci_low=f_lo, f1_ci_high=f_hi,
                         auc=roc_auc_score(yte, p)))
        preds[(sname, mname)] = yp; probs[(sname, mname)] = p; fitted[(sname, mname)] = model
        log(f"{sname:34s} | {mname:19s} | F1={rows[-1]['f1']:.3f} recall={rows[-1]['recall']:.3f} "
            f"AUC={rows[-1]['auc']:.3f}  ({time.time()-ts:.0f}s)")

res = pd.DataFrame(rows)
res.round(4).to_csv(f"{OUT}/metrics_all.csv", index=False)

# ----------------------------------------------------------------------------- test of the abstract's claim
FULL = "TF-IDF + sentiment + linguistic"
claim = []


def paired_delta(ya, pa, pb):
    n = len(ya); d = []
    for _ in range(BOOT):
        i = rng.integers(0, n, n)
        d.append(f1_score(ya[i], pa[i], zero_division=0) - f1_score(ya[i], pb[i], zero_division=0))
    return np.percentile(d, [2.5, 97.5])


for m in ["Logistic Regression", "Random Forest", "XGBoost"]:
    for base, comb in [("Sentiment only", "Sentiment + linguistic"),
                       ("Linguistic only", "Sentiment + linguistic"),
                       ("TF-IDF text only", FULL)]:
        pa, pb = preds[(comb, m)], preds[(base, m)]
        d = f1_score(yte, pa) - f1_score(yte, pb)
        lo, hi = paired_delta(yte, pa, pb)
        claim.append(dict(model=m, combined=comb, baseline=base, delta_f1=d,
                          ci_low=lo, ci_high=hi, ci_excludes_zero=bool(lo > 0 or hi < 0)))
pd.DataFrame(claim).round(4).to_csv(f"{OUT}/claim_test_combined_vs_single.csv", index=False)

# ----------------------------------------------------------------------------- charts
def savefig(name):
    plt.tight_layout(); plt.savefig(f"{OUT}/{name}", dpi=200); plt.close()


order = list(SETS.keys())
models = ["Logistic Regression", "Random Forest", "XGBoost"]
colors = ["#7FB3E6", "#0070C0", "#0B2A4A"]

# ablation (F1)
fig, ax = plt.subplots(figsize=(11, 5))
w = 0.26
for k, m in enumerate(models):
    v = [res[(res.feature_set == s) & (res.model == m)].f1.values[0] for s in order]
    ax.bar(np.arange(len(order)) + (k - 1) * w, v, w, label=m, color=colors[k])
ax.set_xticks(range(len(order))); ax.set_xticklabels([o.replace(" + ", "\n+ ") for o in order], fontsize=9)
ax.set_ylabel("F1 (at-risk class)"); ax.set_ylim(0, 1); ax.legend(frameon=False)
ax.set_title("Ablation: which feature groups identify at-risk posts?")
for sp_ in ("top", "right"): ax.spines[sp_].set_visible(False)
savefig("ablation_f1.png")

# model comparison on full feature set
fig, ax = plt.subplots(figsize=(10, 5))
mets = ["recall", "precision", "f1", "auc"]
w = 0.2
for k, mt in enumerate(mets):
    v = [res[(res.feature_set == FULL) & (res.model == m)][mt].values[0] for m in models]
    ax.bar(np.arange(3) + (k - 1.5) * w, v, w, label=mt.upper() if mt == "auc" else mt.capitalize(),
           color=["#0B2A4A", "#0070C0", "#7FB3E6", "#F5A623"][k])
ax.set_xticks(range(3)); ax.set_xticklabels(models); ax.set_ylim(0, 1.05); ax.legend(frameon=False, ncol=4)
ax.set_title("Model comparison (all features)")
for sp_ in ("top", "right"): ax.spines[sp_].set_visible(False)
savefig("model_comparison.png")

# best model overall on full set (by F1)
best_m = res[res.feature_set == FULL].sort_values("f1", ascending=False).iloc[0]["model"]
log(f"Best model on full feature set (by F1): {best_m}")

# confusion matrix
cm = confusion_matrix(yte, preds[(FULL, best_m)])
fig, ax = plt.subplots(figsize=(4.6, 4.2))
ax.imshow(cm, cmap="Blues")
for i in range(2):
    for j in range(2):
        ax.text(j, i, f"{cm[i, j]:,}", ha="center", va="center", fontsize=15,
                color="white" if cm[i, j] > cm.max() / 2 else "black")
ax.set_xticks([0, 1]); ax.set_yticks([0, 1])
ax.set_xticklabels(["Not at risk", "At risk"]); ax.set_yticklabels(["Not at risk", "At risk"])
ax.set_xlabel("Predicted"); ax.set_ylabel("Actual"); ax.set_title(f"{best_m}: confusion matrix")
savefig("confusion_matrix_best.png")
tn, fp, fn, tp = cm.ravel()
with open(f"{OUT}/confusion_matrix_best.txt", "w") as f:
    f.write(f"model={best_m} feature_set={FULL}\nTN={tn} FP={fp} FN={fn} TP={tp}\n"
            f"missed at-risk (false negative rate) = {fn/(fn+tp):.3f}\n"
            f"false alarms (false positive rate)   = {fp/(fp+tn):.3f}\n")

# ROC
fig, ax = plt.subplots(figsize=(5.2, 4.6))
for k, m in enumerate(models):
    fpr, tpr, _ = roc_curve(yte, probs[(FULL, m)])
    ax.plot(fpr, tpr, color=colors[k], lw=2, label=f"{m} (AUC {res[(res.feature_set==FULL)&(res.model==m)].auc.values[0]:.2f})")
ax.plot([0, 1], [0, 1], "--", color="grey", lw=1)
ax.set_xlabel("False positive rate"); ax.set_ylabel("True positive rate (recall)")
ax.legend(frameon=False, fontsize=8, loc="lower right"); ax.set_title("ROC curves (all features)")
for sp_ in ("top", "right"): ax.spines[sp_].set_visible(False)
savefig("roc_curves.png")

# interpretable feature importance: XGBoost + LR on sentiment + linguistic
SL = "Sentiment + linguistic"
xgb_sl = fitted[(SL, "XGBoost")]
names = SENT_NAMES + LING_NAMES
imp = pd.Series(xgb_sl.feature_importances_, index=names).sort_values()
fig, ax = plt.subplots(figsize=(6.5, 5.2))
ax.barh(imp.index, imp.values, color="#0070C0")
ax.set_xlabel("XGBoost importance (gain)"); ax.set_title("Which indicators matter most?")
for sp_ in ("top", "right"): ax.spines[sp_].set_visible(False)
savefig("feature_importance.png")
lr_sl = fitted[(SL, "Logistic Regression")]
pd.DataFrame({"feature": names, "lr_standardised_coef": lr_sl.coef_[0],
              "xgb_importance": xgb_sl.feature_importances_}).round(4) \
    .sort_values("xgb_importance", ascending=False).to_csv(f"{OUT}/feature_importance.csv", index=False)

# top terms (CSV only; do not print method-related terms on the poster)
lr_full = fitted[(FULL, "Logistic Regression")]
vocab = np.array(tfidf.get_feature_names_out())
coefs = lr_full.coef_[0][:len(vocab)]
top = np.argsort(coefs)[::-1][:30]
pd.DataFrame({"term": vocab[top], "coef": coefs[top]}).round(3).to_csv(f"{OUT}/top_terms_CSV_ONLY.csv", index=False)

# ----------------------------------------------------------------------------- proposed risk tiers
pb = probs[(FULL, best_m)]
bands = pd.cut(pb, [0, 0.33, 0.67, 1.0], labels=["Low (<0.33)", "Moderate (0.33-0.67)", "High (>0.67)"],
               include_lowest=True)
tier = pd.DataFrame({"band": bands, "actual": yte}).groupby("band", observed=False).agg(
    posts=("actual", "size"), actual_at_risk=("actual", "sum"))
tier["share_of_test_posts"] = (tier.posts / tier.posts.sum()).round(3)
tier["observed_at_risk_rate"] = (tier.actual_at_risk / tier.posts.replace(0, np.nan)).round(3)
tier.to_csv(f"{OUT}/proposed_risk_tiers.csv")

# ----------------------------------------------------------------------------- data-at-a-glance
summary = dict(
    source_file=os.path.basename(path), text_column=text_col, label_column=label_col,
    at_risk_labels=pos_names, not_at_risk_labels=neg_names,
    rows_read=int(n_raw), duplicates_removed=int(n_dups), posts_used=int(len(df)),
    at_risk_share=round(float(df.y.mean()), 4), train_size=int(len(train_idx)),
    test_size=int(len(test_idx)), split="stratified 80/20", seed=SEED,
    tfidf="1-2 grams, 10,000 features, English stop words removed",
    bootstrap_resamples=BOOT, best_model_full_features=best_m,
)
with open(f"{OUT}/data_at_a_glance.json", "w") as f:
    json.dump(summary, f, indent=2)

# ----------------------------------------------------------------------------- final printout
pd.set_option("display.width", 200)
print("\n" + "=" * 90)
print("DATA AT A GLANCE\n" + json.dumps(summary, indent=2))
print("\nABLATION + MODEL COMPARISON (test set)")
print(res[["feature_set", "model", "recall", "precision", "f1", "auc"]].round(3).to_string(index=False))
print("\nDOES COMBINING HELP? (F1 difference, 95% bootstrap CI)")
print(pd.DataFrame(claim).round(3).to_string(index=False))
print("\n" + open(f"{OUT}/confusion_matrix_best.txt").read())
print("PROPOSED RISK TIERS (best model)\n" + tier.to_string())
print(f"\nDone in {time.time()-t0:.0f}s. Files are in ./{OUT}/ . Send me metrics_all.csv, "
      f"claim_test_combined_vs_single.csv, data_at_a_glance.json, proposed_risk_tiers.csv, "
      f"confusion_matrix_best.txt and the PNGs.")
