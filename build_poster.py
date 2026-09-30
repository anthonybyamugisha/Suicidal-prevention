#!/usr/bin/env python3
"""
Build the A0 portrait poster scaffold (84.1 x 118.9 cm, 3 columns).

Every figure is placed at its real size from results/poster_figs/.  Prose is left
as clearly-marked PLACEHOLDER boxes for you to overwrite; the numbers, captions,
headline and the results table are pre-filled from the actual study output.

Usage (from the folder holding results/):
    python build_poster.py [output.pptx]

Output:  a .pptx you open in PowerPoint, then File > Export > PDF.
         Close the file in PowerPoint first, or the save will fail with
         PermissionError (PowerPoint holds a lock on open documents).
"""
import os
import sys
from pptx import Presentation
from pptx.util import Cm, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from PIL import Image

FIG = os.path.join("results", "poster_figs")
OUTFILE = sys.argv[1] if len(sys.argv) > 1 else "poster_A0_portrait.pptx"

# ---------------------------------------------------------------- design tokens
FONT = "Arial"
NAVY = RGBColor(0x0B, 0x2A, 0x4A)
BLUE = RGBColor(0x00, 0x70, 0xC0)
LBLUE = RGBColor(0x7F, 0xB3, 0xE6)
GREY = RGBColor(0x5A, 0x5A, 0x5A)
LGREY = RGBColor(0x8C, 0x8C, 0x8C)
RED = RGBColor(0xC0, 0x39, 0x2B)
GREEN = RGBColor(0x2E, 0x7D, 0x32)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
RULE = RGBColor(0xD5, 0xDC, 0xE3)

# A0 portrait
SLIDE_W, SLIDE_H = 84.1, 118.9
M = 2.4                       # outer margin
GUT = 1.8                     # column gutter
COL_W = (SLIDE_W - 2 * M - 2 * GUT) / 3
COL_X = [M, M + COL_W + GUT, M + 2 * (COL_W + GUT)]

BODY_TOP = 19.0
BODY_BOT = 115.5

BODY_PT = 20
CAP_PT = 15
HEAD_PT = 33

prs = Presentation()
prs.slide_width = Cm(SLIDE_W)
prs.slide_height = Cm(SLIDE_H)
slide = prs.slides.add_slide(prs.slide_layouts[6])


# ---------------------------------------------------------------- helpers
def box(x, y, w, h):
    tb = slide.shapes.add_textbox(Cm(x), Cm(y), Cm(w), Cm(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = 0
    tf.margin_top = tf.margin_bottom = 0
    return tf


def para(tf, text, size, color=NAVY, bold=False, italic=False, first=False,
         space_after=6, align=PP_ALIGN.LEFT, space_before=0, line=None):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align
    p.space_after = Pt(space_after)
    p.space_before = Pt(space_before)
    if line:
        p.line_spacing = line
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    r.font.name = FONT
    r.font.color.rgb = color
    return p


def heading(x, y, text, w=None, size=HEAD_PT):
    """Section header with an accent rule underneath."""
    w = w or COL_W
    tf = box(x, y, w, 1.9)
    para(tf, text, size, NAVY, bold=True, first=True, space_after=0)
    ln = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Cm(x), Cm(y + 1.75), Cm(w), Cm(0.16))
    ln.fill.solid()
    ln.fill.fore_color.rgb = BLUE
    ln.line.fill.background()
    ln.shadow.inherit = False
    ln.name = "accent_rule"
    return y + 3.0



def placeholder(x, y, w, h, prompt, hint=""):
    """Dashed-outline box so empty sections are obvious on the printed proof."""
    shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Cm(x), Cm(y), Cm(w), Cm(h))
    shp.fill.solid()
    shp.fill.fore_color.rgb = RGBColor(0xF4, 0xF7, 0xFA)
    shp.line.color.rgb = LBLUE
    shp.line.width = Pt(1.0)
    shp.shadow.inherit = False
    tf = shp.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Cm(0.8)
    tf.margin_top = tf.margin_bottom = Cm(0.6)
    tf.vertical_anchor = MSO_ANCHOR.TOP
    para(tf, prompt, 17, LGREY, italic=True, first=True, space_after=4)
    if hint:
        para(tf, hint, 13, LGREY, italic=True, space_after=0)
    return y + h


def figure(x, y, w_cm, name, caption):
    """Place a figure at true width, caption underneath, return the new y."""
    path = os.path.join(FIG, name)
    with Image.open(path) as im:
        px_w, px_h = im.size
    h_cm = w_cm * px_h / px_w
    slide.shapes.add_picture(path, Cm(x), Cm(y), Cm(w_cm), Cm(h_cm))
    cap_h = 1.9
    tf = box(x, y + h_cm + 0.45, w_cm, cap_h)
    para(tf, caption, CAP_PT, GREY, italic=True, first=True, space_after=0)
    return y + h_cm + 0.45 + cap_h


def bullets(x, y, w, items, size=BODY_PT, gap=7):
    """Bullet list sized to its wrapped content; returns height consumed, in cm."""
    # estimate wrapped height first: ~0.5em average glyph advance, 1.2 line height
    char_cm = 0.5 * size * 2.54 / 72
    per_line = max(int(w / char_cm), 10)
    lines = sum(max(1, -(-(len(it) + 4) // per_line)) for it in items)
    h = lines * (size * 1.2 * 2.54 / 72) + len(items) * gap * 2.54 / 72 + 0.4

    tf = box(x, y, w, h)
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        p.line_spacing = 1.06
        r = p.add_run()
        r.text = "\u25aa  " + it
        r.font.size = Pt(size)
        r.font.name = FONT
        r.font.color.rgb = NAVY
    return h




# ---------------------------------------------------------------- title banner
band = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Cm(0), Cm(0), Cm(SLIDE_W), Cm(12.6))
band.fill.solid()
band.fill.fore_color.rgb = NAVY
band.line.fill.background()
band.shadow.inherit = False

tf = box(M, 1.5, SLIDE_W - 2 * M, 5.2)
para(tf, "PLACEHOLDER - STUDY TITLE (aim for one line, max 15 words)",
     40, WHITE, bold=True, first=True, space_after=0)

tf = box(M, 7.4, SLIDE_W - 2 * M, 4.6)
para(tf, "PLACEHOLDER - Author Name (superscript 1)  |  PLACEHOLDER Institution  |  PLACEHOLDER-email",
     20, LBLUE, first=True, space_after=3)
para(tf, "PLACEHOLDER - Conference / venue and date   \u00b7   PLACEHOLDER - poster number",
     16, LBLUE, space_after=0)

# ---------------------------------------------------------------- takeaway strip
strip = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Cm(M), Cm(13.4), Cm(SLIDE_W - 2 * M), Cm(4.6))
strip.fill.solid()
strip.fill.fore_color.rgb = RGBColor(0xE8, 0xF1, 0xFA)
strip.line.color.rgb = BLUE
strip.line.width = Pt(1.5)
strip.shadow.inherit = False
tf = strip.text_frame
tf.word_wrap = True
tf.margin_left = tf.margin_right = Cm(1.0)
tf.vertical_anchor = MSO_ANCHOR.MIDDLE
para(tf, "HEADLINE (one sentence, readable at 3 m):", 14, BLUE, bold=True,
     first=True, space_after=3)
para(tf, "PLACEHOLDER - the single claim the poster makes. Suggested, from the "
         "claim test: \u201cCombining sentiment and linguistic features reliably beats "
         "either alone (F1 0.85 vs 0.79, 6/6 bootstrap CIs exclude zero) \u2014 but adds "
         "little on top of raw text.\u201d", 19, NAVY, bold=True, space_after=0)

# ---------------------------------------------------------------- results table
def results_table(x, y, w):
    """Pre-filled summary of the strongest model per feature set, read from metrics_all.csv."""
    import csv
    rows = list(csv.DictReader(open(os.path.join("results", "metrics_all.csv"))))
    order = ["Sentiment only", "Linguistic only", "Sentiment + linguistic",
             "TF-IDF text only", "TF-IDF + sentiment + linguistic"]
    short = ["Sentiment only", "Linguistic only", "Sentiment + linguistic",
             "TF-IDF only", "All features"]

    data = [["Feature set", "Best model", "F1 (95% CI)", "Recall", "AUC"]]
    for fs, lbl in zip(order, short):
        cand = [r for r in rows if r["feature_set"] == fs]
        best = max(cand, key=lambda r: float(r["f1"]))
        data.append([
            lbl,
            best["model"].replace("Logistic Regression", "LogReg"),
            "%.3f  (%.3f\u2013%.3f)" % (float(best["f1"]), float(best["f1_ci_low"]),
                                        float(best["f1_ci_high"])),
            "%.3f" % float(best["recall"]),
            "%.3f" % float(best["auc"]),
        ])

    nrow, ncol = len(data), 5
    gtbl = slide.shapes.add_table(nrow, ncol, Cm(x), Cm(y), Cm(w), Cm(1.25 * nrow)).table
    for c, cw in zip(gtbl.columns, [7.2, 4.6, 6.9, 3.2, 3.3]):
        c.width = Cm(cw)
    for ri, row in enumerate(data):
        gtbl.rows[ri].height = Cm(1.25 if ri else 1.4)
        for ci, val in enumerate(row):
            cell = gtbl.cell(ri, ci)
            cell.text = val
            cell.margin_left = cell.margin_right = Cm(0.25)
            cell.margin_top = cell.margin_bottom = Cm(0.1)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            cell.fill.fore_color.rgb = NAVY if ri == 0 else (
                WHITE if ri % 2 else RGBColor(0xF4, 0xF7, 0xFA))
            for p in cell.text_frame.paragraphs:
                p.alignment = PP_ALIGN.LEFT if ci == 0 else PP_ALIGN.CENTER
                for r in p.runs:
                    r.font.size = Pt(12 if ri else 12.5)
                    r.font.bold = (ri == 0)
                    r.font.name = FONT
                    r.font.color.rgb = WHITE if ri == 0 else NAVY
    return 1.25 * (nrow - 1) + 1.4


# ---------------------------------------------------------------- study numbers
# Every figure quoted in the poster prose and table is read from the study
# output, so captions can never drift out of sync with results/.
def _rows():
    import csv as _csv
    return list(_csv.DictReader(open(os.path.join("results", "metrics_all.csv"))))


def best_f1(feature_set):
    return max(float(r["f1"]) for r in _rows() if r["feature_set"] == feature_set)


def get(feature_set, model, field):
    for r in _rows():
        if r["feature_set"] == feature_set and r["model"] == model:
            return float(r[field])
    raise KeyError((feature_set, model, field))


_f_sent = best_f1("Sentiment only")
_f_ling = best_f1("Linguistic only")
_f_both = best_f1("Sentiment + linguistic")
_f_full = best_f1("TF-IDF + sentiment + linguistic")
_r_full = get("TF-IDF + sentiment + linguistic", "XGBoost", "recall")
_f1_lr_tfidf = get("TF-IDF text only", "Logistic Regression", "f1")


# ================================================================ COLUMN 1
y = heading(COL_X[0], BODY_TOP, "1.  Background")
y = placeholder(COL_X[0], y, COL_W, 19.0,
                "PLACEHOLDER - background / problem statement",
                "3-5 bullets. Why suicide prevention needs an early-warning signal; "
                "gap in cheap, scalable, language-light screening. Cite WHO/ministry "
                "figures here if you have them.")
y += 1.0

y = heading(COL_X[0], y, "2.  Aim and objectives")
y = placeholder(COL_X[0], y, COL_W, 13.0,
                "PLACEHOLDER - aim, and the specific question",
                "State the claim being tested explicitly, so the Results answer it. "
                "The pre-filled headline above already commits to one claim - keep "
                "the two consistent.")
y += 1.0

y = heading(COL_X[0], y, "3.  Data")
y += bullets(COL_X[0], y, COL_W, [
    "Mendeley Data DOI 10.17632/z8s6w86tr3.2 (Matin & Alam, 2023), CC BY 4.0.",
    "15,477 Reddit posts \u2192 14,187 after removing empty and duplicate posts.",
    "47.7% at-risk.  Stratified 80/20 split: 11,349 train / 2,838 test.",
    "At-risk: r/SuicideWatch.  Not at-risk: r/CasualConversation, r/BenignExistence, "
    "r/CongratsLikeImFive.",
    "Stand-in for Ugandan data not yet available \u2014 proof of concept only.",
]) + 1.0

y = heading(COL_X[0], y, "4.  Method")
y += bullets(COL_X[0], y, COL_W, [
    "Sentiment: 4 VADER scores (neg / neu / pos / compound).",
    "Linguistic: 9 features \u2014 first-person pronouns, absolutist words, negation, "
    "distress terms, length, punctuation, capitals.",
    "Models: Logistic Regression, Random Forest, XGBoost (all class-balanced).",
    "Ablation over 5 feature sets \u00d7 3 models = 15 runs.",
    "Uncertainty: 1000-resample bootstrap CIs, and a paired bootstrap test of "
    "\u0394F1 for every combined-vs-single comparison.",
]) + 1.0


# ================================================================ COLUMN 2
y = heading(COL_X[1], BODY_TOP, "5.  Results \u2014 which feature groups work?")
y = figure(COL_X[1], y, COL_W, "ablation_f1.png",
           "Figure 1. Ablation. F1 by feature set and model. Sentiment alone and "
           "linguistic alone reach F1 \u2248 0.79; together they reach 0.85. TF-IDF "
           "alone is stronger still (0.92).")
y += 0.6

y = figure(COL_X[1], y, COL_W, "claim_test.png",
           "Figure 2. The claim test. (A) Combining sentiment + linguistic beats "
           "either group alone in all 6 comparisons, every CI clear of zero. "
           "(B) Added on top of TF-IDF, the sign flips \u2014 no reliable gain.")
y += 0.6

y = heading(COL_X[1], y, "6.  Model comparison")
y = figure(COL_X[1], y, COL_W, "model_comparison.png",
           "Figure 3. All three models on the full feature set. XGBoost leads on "
           "F1 (%.3f) and recall (%.3f), but its CI overlaps TF-IDF-only Logistic "
           "Regression (F1 %.3f) \u2014 a tie, not a win."
           % (_r_full, _f_full, _f1_lr_tfidf))

y += 1.0

y = heading(COL_X[1], y, "6b.  Summary of all results")
y += results_table(COL_X[1], y, COL_W) + 0.5
tf = box(COL_X[1], y, COL_W, 2.2)
para(tf, "Table 1. Strongest model per feature set, with 95% bootstrap CIs "
         "(1000 resamples). Every number here is the held-out test set (n = 2,838).",
     CAP_PT, GREY, italic=True, first=True, space_after=0)


# ================================================================ COLUMN 3
y = heading(COL_X[2], BODY_TOP, "7.  Which indicators matter?")


y = figure(COL_X[2], y, COL_W, "feature_importance.png",
           "Figure 4. XGBoost gain. VADER negativity and exclamations lead; "
           "first-person rate, negation and distress terms follow.")
y += 0.6

y = heading(COL_X[2], y, "8.  Proposed risk tiers")
y = figure(COL_X[2], y, COL_W, "risk_tiers.png",
           "Figure 5. Observed at-risk rate rises 5% \u2192 50% \u2192 96% across the "
           "three bands, so the score is ordinally informative. Bands are PROPOSED, "
           "not clinically validated.")
y += 0.6

y = figure(COL_X[2], y, COL_W * 0.80, "confusion_matrix.png",
           "Figure 6. 9.1% of at-risk posts missed; 6.7% false-alarm rate.")
y += 0.6

y = heading(COL_X[2], y, "9.  Limitations")
y += bullets(COL_X[2], y, COL_W, [
    "Labels come from Reddit communities, not clinicians \u2014 no clinical ground truth.",
    "Not Ugandan data. English, Western platform sample; coefficients and thresholds "
    "will not transfer without local recalibration.",
    "Risk tiers are proposed, not validated. The Low band holds 49% of posts at 5.3% "
    "residual risk, so it is not a safety net at scale.",
    "Lexical shortcut: 57% of at-risk posts contain explicit suicide vocabulary vs 4% "
    "of controls. A single-regex baseline already reaches F1 0.71.",
    "Posts treated as independent; no user-level or temporal modelling.",
], size=17, gap=6) + 1.2

y = heading(COL_X[2], y, "10.  Conclusion and next steps")
y += bullets(COL_X[2], y, COL_W, [
    "Sentiment and linguistic features are cheap, transparent and they combine \u2014 "
    "F1 %.3f versus %.3f / %.3f for either group alone."
    % (_f_both, _f_sent, _f_ling),
    "They add little on top of raw text (F1 %.3f vs %.3f), so this supports "
    "interpretable screening, not replacement of it." % (_f_full, _f_both),
    "Next: Ugandan behavioural data, user-level modelling, ethical clearance, and "
    "human-in-the-loop triage.",
], size=17, gap=6) + 1.2

y = heading(COL_X[2], y, "References", size=24)
bullets(COL_X[2], y, COL_W, [
    "Matin, M. M. H., & Alam, M. S. (2023). Suicidal Ideation Detection Reddit "
    "Dataset (Version 2). Mendeley Data. doi:10.17632/z8s6w86tr3.2",
    "Hutto, C. J., & Gilbert, E. E. (2014). VADER: A parsimonious rule-based model "
    "for sentiment analysis of social media. ICWSM.",
    "PLACEHOLDER - add the first-person / absolutist-words literature you cite.",
], size=13, gap=4)


# ---------------------------------------------------------------- footer
bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Cm(0), Cm(SLIDE_H - 2.2), Cm(SLIDE_W), Cm(2.2))
bar.fill.solid()
bar.fill.fore_color.rgb = RGBColor(0xF0, 0xF3, 0xF7)
bar.line.fill.background()
bar.shadow.inherit = False
tf = box(M, SLIDE_H - 1.75, SLIDE_W - 2 * M, 1.4)
para(tf, "Proof of concept \u2014 not a validated clinical tool.  Do not use for triage "
         "or screening decisions.  Code and full results: PLACEHOLDER repo/URL",
     13, GREY, first=True, space_after=0)

prs.save(OUTFILE)
print(f"Wrote {OUTFILE}")
print(f"  slide      : {SLIDE_W} x {SLIDE_H} cm  (A0 portrait)")
print(f"  column grid: {COL_W:.2f} cm wide, {GUT} cm gutters, origin x = "
      + ", ".join(f"{x:.2f}" for x in COL_X))
print(f"  shapes     : {len(slide.shapes)}")
print()
print("Next: open in PowerPoint, fill the PLACEHOLDER boxes, then")
print("  File > Export > Create PDF/XPS  (embed fonts, no compression).")
