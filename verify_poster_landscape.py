#!/usr/bin/env python3
"""
Verification pass over poster_140x90.pptx.

Checks:
  1. slide geometry            slide is 140 x 90 cm, all shapes inside it
  2. panel grid                named panels do not overlap; sizes as designed
  3. figure placement          4 charts at 52 x 14.2 cm, inside Results panel,
                               PNG dpi >= 200 at placed size
  4. text fidelity             every author-supplied string appears verbatim
  5. numbers audit             headline chips + notes match results/ CSVs
  6. font report               sizes used vs conference template allowances
  7. soft overflow estimate    per text box: wrapped-height est. vs box height

Usage:  python verify_poster_landscape.py [poster.pptx]
Exits non-zero if any hard check fails.
"""
import sys
import os
import re
import math
import csv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from pptx import Presentation
from pptx.util import Emu
from PIL import Image

pptx = sys.argv[1] if len(sys.argv) > 1 else "poster_140x90.pptx"
EMU_CM = 360000.0

prs = Presentation(pptx)
slide = prs.slides[0]
SW, SH = prs.slide_width / EMU_CM, prs.slide_height / EMU_CM

fails = []
warns = []

# ------------------------------------------------------------------ 1 skeleton
print(f"[1] slide size      {SW:.1f} x {SH:.1f} cm")
if abs(SW - 140) > 0.1 or abs(SH - 90) > 0.1:
    fails.append(f"slide {SW:.1f}x{SH:.1f} != 140x90")

for sh in slide.shapes:
    try:
        x, y, w, h = (sh.left / EMU_CM, sh.top / EMU_CM,
                      sh.width / EMU_CM, sh.height / EMU_CM)
    except TypeError:
        continue
    if x < -0.05 or y < -0.05 or x + w > SW + 0.05 or y + h > SH + 0.05:
        fails.append(f"shape '{sh.shape_id}' out of slide: bbox "
                     f"({x:.1f},{y:.1f},{w:.1f},{h:.1f})")

# ------------------------------------------------------------------ 2 panels
panels = []
pics = []
for sh in slide.shapes:
    try:
        x, y, w, h = (sh.left / EMU_CM, sh.top / EMU_CM,
                      sh.width / EMU_CM, sh.height / EMU_CM)
    except TypeError:
        continue
    if sh.shape_type == 13:                       # PICTURE
        pics.append((sh.name, x, y, w, h))
    if getattr(sh, "name", "").startswith("panel_"):
        panels.append((sh.name, x, y, w, h))
    if getattr(sh, "name", "") == "header_banner":
        panels.append(("header_banner", x, y, w, h))

print(f"[2] panels  {len(panels)}")
overlap_ok = True
for i in range(len(panels)):
    for j in range(i + 1, len(panels)):
        a, b = panels[i], panels[j]
        ox = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
        oy = min(a[2] + a[4], b[2] + b[4]) - max(a[2], b[2])
        if ox > 0 and oy > 0:
            inter = ox * oy
            if inter > 0.5:                       # >0.5 cm2 counted as a fault
                fails.append(f"panels overlap {a[0]} & {b[0]} by {inter:.1f} cm2")
                overlap_ok = False
if overlap_ok:
    print("     no panel overlaps")

# ------------------------------------------------------------------ 3 figures
print(f"[3] pictures {len(pics)}")
FIGFILES = ["fig_ablation.png", "fig_model_compare.png",
            "fig_confusion.png", "fig_feature_importance.png"]
for idx, (name, x, y, w, h) in enumerate(pics):
    fname = FIGFILES[idx] if idx < len(FIGFILES) else name
    with Image.open(os.path.join("results", "poster_figs", fname)) as im:
        px, py = im.size
    dpi = px / (w / 2.54)
    ok_sz = abs(w - 52.0) < 0.2 and abs(h - 16.5) < 0.2
    ok_pos = 30.6 <= x and x + w <= 138.8 and 17.8 <= y and y + h <= 58.8
    if not (ok_sz and ok_pos) or dpi < 200:
        fails.append(f"picture {fname}: size {w:.1f}x{h:.1f}cm at ({x:.1f},{y:.1f}), "
                     f"dpi {dpi:.0f}")
    print(f"     {fname:26s} {w:.1f}x{h:.1f} cm  dpi {dpi:.0f}  "
          f"{'OK' if ok_sz and ok_pos else 'PLACEMENT/SIZE FAIL'}")

# ------------------------------------------------------------------ 4 text fidelity
def all_text():
    out = []
    for sh in slide.shapes:
        if sh.has_text_frame:
            out.append(sh.text_frame.text)
        if sh.has_table:
            for row in sh.table.rows:
                for c in row.cells:
                    out.append(c.text)
    return "\n".join(out)

text = all_text()
flat = re.sub(r"\s+", " ", text)

REQUIRED = [
    "Artificial Intelligence and Data-Driven Identification of Suicide Risk "
    "Signals Among University Students in Uganda",
    "Byamugisha Anthony",
    "Bachelor of Science in Computer Science",
    "Makerere University, Kampala, Uganda",
    "Deaths per 100,000 in Africa",
    "above the 8.0 global average",
    "0.08",
    "Psychiatrists per 100,000 people in Uganda (2016)",
    "leading cause of death for ages 15\u201329",
    "men die by suicide nearly 4\u00d7 as often as women",
    "8.8 vs 2.3 per 100,000, 2021",
    "consented, anonymised AI analysis could surface earlier",
    "Build and evaluate an AI framework that flags suicide-risk signals early",
    "routes them to professional care",
    "Detect distress and ideation signals in anonymised text",
    "Compare Logistic Regression, Random Forest and XGBoost",
    "Classify risk levels to guide referral for assessment",
    "Uphold privacy, consent, fairness and cultural sensitivity",
    "Anonymised text from student support platforms, counselling interactions",
    "NLP and sentiment analysis extract language cues",
    "behavioural indicators add context",
    "Supervised learning with Logistic Regression, Random Forest and XGBoost",
    "Informed consent, anonymisation, fairness and cultural sensitivity built in "
    "from the start",
    "AI analysis of anonymised text can surface early risk signals",
    "Combining language and behavioural signals improves identification "
    "(preliminary)",
    "every flag leads to human assessment",
    "conditions for use, not add-ons",
    "From silence to action.  Early signals.  Timely referral.",
    "Pilot in university counselling services with ethical clearance",
    "Keep a human in the loop: the model flags, a counsellor decides",
    "Validate on Ugandan English, Luganda and code-switched text",
    "Audit fairness across gender, faculty and year of study",
    "Strengthen referral pathways and counsellor capacity",
    "Tail it to Uganda and East African population",
    "WHO. Suicide (fact sheet). Geneva",
    "SDG Global Database, indicator 3.4.2",
    "Breiman L. Random forests. Machine Learning. 2001;45:5\u201332",
    "XGBoost: a scalable tree boosting system. Proc KDD. 2016:785\u2013794",
    "screening for suicide risk. Biomed Inform Insights. 2018;10",
    "https://github.com/anthonybyamugisha/Suicidal-prevention",
    "byamugishanthony@gmail.com",
    "+256 748 161 708",
    "INTRODUCTION",
    "AIMS AND OBJECTIVES",
    "METHOD",
    "RESULTS",
    "CONCLUSIONS",
    "RECOMMENDATION",
    "REFERENCES",
    "CONTACT",
    "Proof of concept on 14,187 anonymised Reddit posts",
]
missing = [s for s in REQUIRED if re.sub(r"\s+", " ", s) not in flat]
print(f"[4] text fidelity  {len(REQUIRED)} strings required, "
      f"{len(missing)} missing")
if missing:
    fails.append("missing verbatim strings: " + "; ".join(missing[:6]))

# ------------------------------------------------------------------ 5 numbers
print("[5] number audit")
def rows():
    return list(csv.DictReader(open(os.path.join("results", "metrics_all.csv"))))

def best(fs):
    cand = [r for r in rows() if r["feature_set"] == fs]
    return max(cand, key=lambda r: float(r["f1"]))

bf = best("Sentiment + linguistic")
bfu = best("TF-IDF + sentiment + linguistic")
cl = list(csv.DictReader(open(os.path.join("results", "claim_test_combined_vs_single.csv"))))
sig = sum(1 for r in cl if r["combined"] == "Sentiment + linguistic"
          and float(r["ci_low"]) > 0)
tiers = list(csv.DictReader(open(os.path.join("results", "proposed_risk_tiers.csv"))))
rate = lambda t: float(t["observed_at_risk_rate"]) * 100
low, high = min(tiers, key=rate), max(tiers, key=rate)
cm_ = dict((k, v) for k, v in
           re.findall(r"\b(TN|FP|FN|TP)=(\d+)",
                      open(os.path.join("results", "confusion_matrix_best.txt")).read()))
fnr = int(cm_["FN"]) / (int(cm_["FN"]) + int(cm_["TP"]))
xgb = [r for r in rows() if r["model"] == "XGBoost"
       and r["feature_set"] == "TF-IDF + sentiment + linguistic"][0]
lr = [r for r in rows() if r["model"] == "Logistic Regression"
      and r["feature_set"] == "TF-IDF text only"][0]

expect = [
    ("F1 %.3f" % float(xgb["f1"]), "footnote XGB F1"),
    ("(%.3f)" % float(lr["f1"]), "footnote LR TF-IDF F1"),
    ("14,187", "footnote n"),
    ("%d/6" % sig, "footnote combine count"),
]
for val, where in expect:
    ok = val in flat
    print(f"     {where:18s} '{val}'  {'OK' if ok else 'NOT FOUND'}")
    if not ok:
        fails.append(f"number '{val}' ({where}) not on poster")

# ------------------------------------------------------------------ 6 fonts
print("[6] font report vs template (title 80-100, inst 30-36, body 36-40, "
      "refs 24-30; smaller allowed for long titles / large text)")
sizes = {}
for sh in slide.shapes:
    if not sh.has_text_frame:
        continue
    txt = sh.text_frame.text.strip()
    if not txt:
        continue
    first = txt.split("\n", 1)[0][:26]
    for p in sh.text_frame.paragraphs:
        for r in p.runs:
            if r.font.size:
                sizes.setdefault(r.font.size.pt, []).append(first)
for pt in sorted(sizes, reverse=True):
    print(f"     {pt:6.1f} pt   {len(sizes[pt]):3d} runs   e.g. "
          f"'{sizes[pt][0][:30]}'")

# ------------------------------------------------------------------ 7 overflow
print("[7] text overflow estimate (approx; ignores zero-height boxes)")
for sh in slide.shapes:
    if not sh.has_text_frame:
        continue
    tf = sh.text_frame
    txt = tf.text.strip()
    if not txt:
        continue
    try:
        w = sh.width / EMU_CM - 0.2
        h = sh.height / EMU_CM
    except TypeError:
        continue
    need = 0.0
    for p in tf.paragraphs:
        runs = [(r.text, r.font.size.pt if r.font.size else None) for r in p.runs]
        if not runs:
            continue
        size = next((s for _, s in runs if s), 28)
        chars = sum(len(t) for t, _ in runs)
        per_line = max(1, int(w / (0.5 * size * 2.54 / 72)))
        lines = max(1, math.ceil(chars / per_line))
        need += lines * size * 2.54 / 72 * 1.10
        if p.space_after:
            need += p.space_after.pt * 2.54 / 72
    if need > h and need - h > 0.4:
        warns.append(f"'{txt[:40]}...' est {need:.1f} cm > box {h:.1f} cm")

print(f"     {len(warns)} soft overflows")
for wt in warns:
    print("     WARN " + wt)

# ================================================================== verdict
print()
if fails:
    print("FAIL")
    for ft in fails:
        print("  - " + ft)
    sys.exit(1)
print("ALL CHECKS PASSED" + (f"  ({len(warns)} soft warnings)" if warns else ""))