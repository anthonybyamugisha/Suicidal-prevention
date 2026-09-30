# Suidal Prevention — proof-of-concept study

**AI and data-driven identification of suicide-risk signals from text.**

A single-file study that tests whether cheap, transparent, language-light text
features (sentiment + linguistic markers) can identify suicide-risk signals in
social-media posts — and, just as importantly, whether combining them actually
helps.

> **Status: proof of concept. Not a validated clinical tool.** The labels come
> from Reddit communities, not clinicians. The data is not Ugandan. The risk
> tiers are proposed, not validated. Do not use this for triage or screening
> decisions.

---

## The finding

The claim test in `results/claim_test_combined_vs_single.csv` gives a **split
verdict**, and the two halves disagree. That is the honest result, and it is
what the poster reports.

**1. Sentiment and linguistic features do combine with each other — decisively.**
All 6 paired-bootstrap comparisons favour combining, every CI clear of zero.

| Feature set | Best model | F1 | Recall | AUC |
|---|---|---|---|---|
| Sentiment only | XGBoost | 0.788 | 0.790 | 0.869 |
| Linguistic only | Random Forest | 0.784 | 0.787 | 0.872 |
| **Sentiment + linguistic** | **XGBoost** | **0.847** | **0.846** | **0.932** |
| TF-IDF text only | Logistic Regression | 0.920 | 0.894 | 0.977 |
| All features | XGBoost | 0.917 | 0.909 | 0.978 |

**2. Those features add nothing reliable on top of TF-IDF — the sign flips.**

| Model | ΔF1 (all features − TF-IDF only) | 95% CI | Verdict |
|---|---|---|---|
| Logistic Regression | −0.012 | [−0.021, −0.003] | significantly **worse** |
| Random Forest | −0.001 | [−0.012, +0.011] | null (CI spans zero) |
| XGBoost | +0.024 | [+0.013, +0.034] | better, but small |

So the poster claims the first result with numbers, and reports the second
honestly as a negative.

**Headline:** combining sentiment and linguistic features reliably beats either
alone (F1 0.847 vs 0.788 / 0.784; 6/6 bootstrap CIs exclude zero) — but adds
little on top of raw text.

On the strongest configuration (XGBoost, all features, held-out test set
n = 2,838): precision 0.925, recall 0.909 [0.893, 0.925], F1 0.917
[0.906, 0.928], AUC 0.978. Confusion matrix TN 1,384 / FP 100 / FN 123 /
TP 1,231 — that is a **9.1% false-negative rate** (share of at-risk posts
missed) against a **6.7% false-positive rate**. Uncertainty throughout is a
1000-resample bootstrap.

Note that "best model" is a **tie, not a win**: XGBoost on all features scores
F1 0.917 [0.906, 0.928], while TF-IDF-only Logistic Regression scores
**0.920** [0.909, 0.930]. The CIs overlap almost completely. The claim test
compares same-model pairs (the correct design), but nobody tested
XGBoost-full against LR-TFIDF-only, and on that comparison the full pipeline
does not come out ahead.

---

## Data

| | |
|---|---|
| Source | Mendeley Data — *Suicidal Ideation Detection Reddit Dataset* (Version 2) |
| DOI | [10.17632/z8s6w86tr3.2](https://doi.org/10.17632/z8s6w86tr3.2) |
| Authors | Mafi, M. M. H., & Alam, M. S. (2023) |
| Licence | CC BY 4.0 |
| Collected | 1 June – 13 November 2023, via the Reddit API (PRAW) |
| Size | 15,477 posts, 3 columns (`Title`, `Post`, `Label`) |
| SHA256 | `04a8d7c795e380bb8d649a442e55843ea987330f124b16a54b75c1f9fa24cfbb` |

**Labels are subreddit provenance**, not clinical assessment:

- at-risk — `r/SuicideWatch`
- not at-risk — `r/CasualConversation`, `r/BenignExistence`, `r/CongratsLikeImFive`

After cleaning: **14,187 unique posts** (1,234 empty posts dropped, 9 duplicates
removed), 47.7% at-risk. Stratified 80/20 split → 11,349 train / 2,838 test.

### Fetching it

The data is not committed. Download and verify it:

```powershell
New-Item -ItemType Directory -Force -Path data, data\extracted
Invoke-WebRequest -Uri "https://data.mendeley.com/public-files/datasets/z8s6w86tr3/files/2e4d2f1a-7a6c-4397-9d23-377589b4ebee/file_downloaded" -OutFile data\suicide_ideation_reddit_v2.zip
Expand-Archive data\suicide_ideation_reddit_v2.zip -DestinationPath data\extracted -Force

# verify before trusting it
(Get-FileHash -Algorithm SHA256 data\suicide_ideation_reddit_v2.zip).Hash.ToLower()
# expect: 04a8d7c795e380bb8d649a442e55843ea987330f124b16a54b75c1f9fa24cfbb
```

---

## Setup

Python 3.13. Create a virtual environment and install the dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install numpy pandas scipy scikit-learn xgboost vaderSentiment matplotlib openpyxl requests python-pptx pillow
```

Verified against: Python 3.13.15, numpy 2.5.3, pandas 3.0.6, scipy 1.18.1,
scikit-learn 1.9.1, xgboost 3.4.1, vaderSentiment 3.3.2, matplotlib 3.11.2,
python-pptx 1.0.2, Pillow 12.3.0.

---

## Usage

### 1. Run the study

```powershell
.\.venv\Scripts\python.exe experiments.py --data "data\extracted\Suicidal Ideation Detection Reddit Dataset-Version 2.csv" --text-col Post --label-col Label --pos-label "Suicidal" --neg-label "Non-Suicidal" --seed 42
```

Takes ~8 minutes. Auto-detects the text and label columns if you omit the flags;
`--max-rows` caps the sample for a faster laptop run, and `--seed` controls
reproducibility. Everything is written to `./results/`.

### 2. Render print-resolution figures

```powershell
.\.venv\Scripts\python.exe make_poster_figures.py
```

Six figures at 300 dpi sized to their final physical size on A0, with type
scaled for reading at 1–3 m. → `results/poster_figs/`

### 3. Build the poster

```powershell
.\.venv\Scripts\python.exe build_poster.py poster_A0.pptx
```

A0 portrait (84.1 × 118.9 cm), 3 columns, editable. Every number in the captions
and the results table is read from `results/metrics_all.csv` at build time, so
prose cannot drift out of sync with the study output.

Open in PowerPoint, fill the 8 boxes marked `PLACEHOLDER`, then
**File → Export → Create PDF/XPS** (or *Save As → PDF*) with *embed fonts* ticked.

> Close the file in PowerPoint before rebuilding — PowerPoint holds a lock on
> open documents and the save fails with `PermissionError`.

---

## Outputs

`results/` — the study record, tracked in git:

| File | What it holds |
|---|---|
| `metrics_all.csv` | All 15 runs: accuracy, precision, recall, F1, AUC, with 95% CIs on recall and F1 |
| `claim_test_combined_vs_single.csv` | **The file that decides the finding** — paired ΔF1 with CIs |
| `data_at_a_glance.json` | Provenance, row counts, split, seed |
| `proposed_risk_tiers.csv` | Observed at-risk rate per probability band |
| `confusion_matrix_best.txt` | TN/FP/FN/TP plus the false-negative and false-positive rates |
| `feature_importance.csv` | XGBoost gain and standardised LR coefficients per feature |
| `top_terms_CSV_ONLY.csv` | Highest-weight TF-IDF terms. **Internal only — keep off the poster** |

Figure PNGs (`results/*.png`, `results/poster_figs/`) are gitignored; regenerate
them with steps 2–3.

### Risk tiers (proposed, not validated)

| Band | Share of test posts | Observed at-risk rate |
|---|---|---|
| Low (<0.33) | 49% | 5.3% |
| Moderate (0.33–0.67) | 8% | 50.4% |
| High (>0.67) | 43% | 95.6% |

The score is ordinally informative, but the Low band is **not a safety net at
scale**: it holds 49% of posts at 5.3% residual risk, so it would generate more
missed cases (74) than the Moderate band catches (115).

---

## Limitations

1. **Labels are subreddit membership, not clinical assessment.** No clinician
   ground truth, no C-SSRS, no clinician adjudication. We are measuring
   forum-group discriminability; reported performance is an **upper bound** on
   what clinical deployment would achieve.
2. **Not Ugandan data.** English Reddit, Western-heavy platform sample. Uganda
   has different language, help-seeking norms, and far lower Reddit penetration.
   The *method* transfers; the coefficients and thresholds do not. Local
   recalibration would be mandatory, not optional.
3. **The risk tiers are proposed, not validated.** The bands are probability
   cut-points, not a clinical instrument. The observed rates show ordinal
   information only.
4. **There is a strong lexical shortcut.** 57.1% of at-risk posts contain
   explicit suicide vocabulary (`die`, `kill`, `pills`, `overdose`, `rope`) vs
   4.3% of controls — a single-regex baseline already reaches F1 0.706. The top
   TF-IDF terms are the same words. The model genuinely beats that baseline
   (0.706 → 0.917), but the honest framing is "explicit *and* implicit signals
   together", not "subtle implicit markers". Post length also differs
   (847 vs 651 chars) and TF-IDF can partly exploit it.
5. **Posts are treated as independent.** No user-level or temporal modelling,
   so the risk of a user is not estimated, only the content of a single post.
6. **`hate` is in the distress-term list** (`experiments.py`), which is broad and
   not suicide-specific. `distress_term_rate` ranks 3rd by XGBoost gain (0.096),
   so this is worth a panel question.

Subreddit boilerplate was checked and is **not** a confound: the literal string
`suicidewatch` appears in only 0.1% of posts, and mod/reddit meta-markers are
*slightly more* frequent in the controls (0.10 vs 0.04 per post).

---

## Repository map

```
experiments.py               the whole study: load -> clean -> features -> 15 runs -> CIs -> claim test
make_poster_figures.py       re-render the 6 figures at 300 dpi for A0 print
build_poster.py              assemble the A0 portrait .pptx
poster_A0.pptx               the poster (editable; PLACEHOLDER boxes awaiting your text)
data/                        Mendeley dataset (gitignored — see Fetching it)
results/                     study record; CSVs tracked, PNGs gitignored
```

## Notes

- `experiments.py`'s docstring says `run_experiments.py`; the file is
  `experiments.py`. Use the name in the command above.
- The bootstrap reuses one RNG sequentially across metrics and models, so the
  CIs are correlated with each other. Fine for reporting, but they are not
  independent samples.
- Nothing here is committed yet. If you run `git add .`, the 12 MB dataset and
  `.venv/` are already excluded by `.gitignore`.
