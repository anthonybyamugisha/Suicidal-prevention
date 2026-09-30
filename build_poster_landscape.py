#!/usr/bin/env python3
"""
Build the 140 x 90 cm LANDSCAPE conference poster (.pptx) — professional
red-palette edition, resized typography after the URI / ASME / SIAM poster
standards (title ~80pt, headings ~34-38pt, body ~28-34pt, refs ~20pt).

Layout (cm):
    header       1.2..16.6           maroon four-tone band, 80 pt title
    LEFT column  1.2..29.4           INTRODUCTION | AIMS AND OBJECTIVES | METHOD
                                     (full height 17.8..88.8)
    RESULTS     30.6..138.8 x 17.8..58.8   four exported charts, 2x2, 52x16.5 cm
    BOTTOM row  30.6..138.8 x 60.0..88.8   CONCLUSIONS | RECOMMENDATION | REFERENCES+CONTACT
                                     (tall band that the 34 pt type fills)

The four chart images are used exactly as exported (no modification — the .pptx
only places the files at true size).
"""
import os
import re
import sys
import csv
from pptx import Presentation
from pptx.util import Cm, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

FIG = os.path.join("results", "poster_figs")
RES = "results"
OUTFILE = sys.argv[1] if len(sys.argv) > 1 else "poster_140x90.pptx"

FONT = "Arial"
MAROON = RGBColor(0x5F, 0x0F, 0x1E)     # header
DEEP = RGBColor(0x6E, 0x14, 0x23)        # section strips
CRIMSON = RGBColor(0xB3, 0x26, 0x2E)     # accents, contact strip
SOFT = RGBColor(0xE3, 0xCD, 0xD1)        # hairlines
WARM = RGBColor(0xF2, 0xEC, 0xEB)        # page background
PAPER = RGBColor(0xFF, 0xFF, 0xFF)       # panels
INK = RGBColor(0x2B, 0x23, 0x25)         # body text
MUT = RGBColor(0x74, 0x60, 0x66)         # secondary
OFFWHT = RGBColor(0xF6, 0xEA, 0xEC)      # header text
GOLD = RGBColor(0xC9, 0xA2, 0x27)

# ------------------------------------------------------------------ slide
W, H = 140.0, 90.0
prs = Presentation()
prs.slide_width = Cm(W)
prs.slide_height = Cm(H)
slide = prs.slides.add_slide(prs.slide_layouts[6])

bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
bg.fill.solid()
bg.fill.fore_color.rgb = WARM
bg.line.fill.background()
bg.shadow.inherit = False
bg.name = "bg"


# ------------------------------------------------------------------ helpers
def rect(x, y, w, h, fill=PAPER, line=None, line_w=0.5, shape=MSO_SHAPE.RECTANGLE):
    shp = slide.shapes.add_shape(shape, Cm(x), Cm(y), Cm(w), Cm(h))
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid()
        shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(line_w)
    shp.shadow.inherit = False
    return shp


def tbox(x, y, w, h, wrap=True):
    tb = slide.shapes.add_textbox(Cm(x), Cm(y), Cm(w), Cm(h))
    tf = tb.text_frame
    tf.word_wrap = wrap
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    return tf


def _p(tf):
    return tf.paragraphs[0] if not tf.paragraphs[0].runs else tf.add_paragraph()


def para(tf, text, size, color=INK, bold=False, italic=False,
         space_after=6, space_before=0, align=PP_ALIGN.LEFT, line=1.12):
    p = _p(tf)
    p.alignment = align
    p.space_after = Pt(space_after)
    p.space_before = Pt(space_before)
    p.line_spacing = line
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    r.font.name = FONT
    r.font.color.rgb = color
    return p


def bullets(tf, items, size, color=INK, gap=6, marker="\u25aa"):
    for it in items:
        p = _p(tf)
        p.space_after = Pt(gap)
        p.line_spacing = 1.14
        r0 = p.add_run()
        r0.text = marker + "  "
        r0.font.size = Pt(max(16, size - 10))
        r0.font.name = FONT
        r0.font.color.rgb = CRIMSON
        r1 = p.add_run()
        r1.text = it
        r1.font.size = Pt(size)
        r1.font.name = FONT
        r1.font.color.rgb = color


def numbered(tf, items, size, color=INK, gap=6):
    for n, txt in enumerate(items, 1):
        p = _p(tf)
        p.space_after = Pt(gap)
        p.line_spacing = 1.14
        r = p.add_run()
        r.text = f"{n}.  "
        r.font.size = Pt(size)
        r.font.bold = True
        r.font.name = FONT
        r.font.color.rgb = CRIMSON
        r = p.add_run()
        r.text = txt
        r.font.size = Pt(size)
        r.font.name = FONT
        r.font.color.rgb = color


def strip(x, y, w, h, label, size=34, fill=DEEP):
    rect(x, y, w, h, fill=fill).name = "strip_" + re.sub(r"\W+", "_", label)
    rect(x, y, 0.55, h, fill=GOLD)          # gold tick at the strip start
    tf = tbox(x + 1.5, y, w - 2.5, h)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = label
    r.font.size = Pt(size)
    r.font.bold = True
    r.font.name = FONT
    r.font.color.rgb = PAPER


def panel(x, y, w, h, label, content, strip_h=2.6, strip_size=34):
    rect(x, y, w, h, fill=PAPER, line=SOFT, line_w=0.75).name = "panel_" + label
    strip(x, y, w, strip_h, label, size=strip_size)
    tf = tbox(x + 1.5, y + strip_h + 0.6, w - 3.0, h - strip_h - 1.2)
    content(tf)
    return tf


def load_rows():
    with open(os.path.join(RES, "metrics_all.csv")) as f:
        return list(csv.DictReader(f))


ROWS = load_rows()


def row(feature_set, model):
    for r in ROWS:
        if r["feature_set"] == feature_set and r["model"] == model:
            return r
    raise KeyError((feature_set, model))


# ================================================================== HEADER
tones = ["#470B17", "#53101D", "#5F0F1E", "#6E1A2A"]
for i, tn in enumerate(tones):
    rect(1.2, 1.2 + i * 3.85, W - 2.4, 3.85, fill=RGBColor.from_string(tn[1:]))
rect(1.2, 16.60, W - 2.4, 0.16, fill=GOLD)

logo = rect(2.2, 2.6, 14.6, 11.2, fill=PAPER, line=SOFT, line_w=0.75,
            shape=MSO_SHAPE.ROUNDED_RECTANGLE)
logo.adjustments[0] = 0.10
rect(2.2, 2.6, 14.6, 0.5, fill=CRIMSON)
ltf = tbox(2.8, 3.7, 13.4, 5.4)
para(ltf, "MAKERERE", 17, DEEP, bold=True, space_after=0, align=PP_ALIGN.CENTER)
para(ltf, "UNIVERSITY", 17, DEEP, bold=True, space_after=4, align=PP_ALIGN.CENTER)
rect(5.9, 10.0, 7.2, 0.09, fill=GOLD)
ltf2 = tbox(2.8, 10.5, 13.4, 2.0)
para(ltf2, "Kampala \u00b7 Uganda", 11, MUT, align=PP_ALIGN.CENTER, space_after=0)

TITLE = ("Artificial Intelligence and Data-Driven Identification of Suicide Risk "
         "Signals Among University Students in Uganda")
AUTHOR = "Byamugisha Anthony  \u00b7  Bachelor of Science in Computer Science  \u00b7  YR 3"
INST = "Makerere University, Kampala, Uganda"

ttf = tbox(18.6, 2.6, 120.0, 7.6)
p = ttf.paragraphs[0]
p.alignment = PP_ALIGN.CENTER
p.line_spacing = 1.03
r = p.add_run()
r.text = TITLE
r.font.size = Pt(80)
r.font.bold = True
r.font.name = FONT
r.font.color.rgb = PAPER

rect(55.0, 10.6, 30.0, 0.10, fill=GOLD)

atf = tbox(18.6, 11.0, 120.0, 2.4)
para(atf, AUTHOR, 30, OFFWHT, bold=True, align=PP_ALIGN.CENTER, space_after=0)
itf = tbox(18.6, 13.9, 120.0, 2.2)
para(itf, INST, 26, RGBColor(0xEF, 0xD9, 0xDD), align=PP_ALIGN.CENTER, space_after=0)

# ================================================================== LEFT COLUMN
LX, LW = 1.2, 28.2


def intro_content(tf):
    def stat(num, rest):
        para(tf, num, 42, CRIMSON, bold=True, space_after=2)
        para(tf, rest, 28, INK, space_after=14, line=1.14)
    stat("11.2",
         "Deaths per 100,000 in Africa \u2014 above the 8.0 global average.")
    stat("0.08",
         "Psychiatrists per 100,000 people in Uganda (2016).")
    bullets(tf, [
        "A leading cause of death for ages 15\u201329, yet stigma and scarce "
        "counselling leave many students unidentified.",
        "In Uganda, men die by suicide nearly 4\u00d7 as often as women "
        "(8.8 vs 2.3 per 100,000, 2021).",
        "Students leave written and digital traces of distress that consented, "
        "anonymised AI analysis could surface earlier.",
    ], 28, gap=10)


panel(LX, 17.8, LW, 24.0, "INTRODUCTION", intro_content)


def aims_content(tf):
    para(tf, "Overall aim", 28, CRIMSON, bold=True, space_after=4)
    para(tf, "Build and evaluate an AI framework that flags suicide-risk signals "
             "early among Ugandan university students and routes them to "
             "professional care.", 28, INK, space_after=14, line=1.16)
    para(tf, "Specific objectives", 28, CRIMSON, bold=True, space_after=4)
    numbered(tf, [
        "Detect distress and ideation signals in anonymised text.",
        "Compare Logistic Regression, Random Forest and XGBoost.",
        "Classify risk levels to guide referral for assessment.",
        "Uphold privacy, consent, fairness and cultural sensitivity.",
    ], 28, gap=10)


panel(LX, 43.0, LW, 22.8, "AIMS AND OBJECTIVES", aims_content)


def method_content(tf):
    for head, txt in [
        ("Data",
         "Anonymised text from student support platforms, counselling "
         "interactions and voluntary digital mental-health surveys."),
        ("Features",
         "NLP and sentiment analysis extract language cues; behavioural "
         "indicators add context."),
        ("Models",
         "Supervised learning with Logistic Regression, Random Forest and "
         "XGBoost."),
        ("Safeguards",
         "Informed consent, anonymisation, fairness and cultural sensitivity "
         "built in from the start."),
    ]:
        p = _p(tf)
        p.space_after = 12
        p.line_spacing = 1.16
        r = p.add_run()
        r.text = head + " \u2014 "
        r.font.size = Pt(28)
        r.font.bold = True
        r.font.name = FONT
        r.font.color.rgb = CRIMSON
        r = p.add_run()
        r.text = txt
        r.font.size = Pt(28)
        r.font.name = FONT
        r.font.color.rgb = INK


panel(LX, 67.0, LW, 21.8, "METHOD", method_content)

# ================================================================== RESULTS
RX, RW, RH = 30.6, 108.2, 41.0
panel(RX, 17.8, RW, RH, "RESULTS", lambda tf: None, strip_h=2.6, strip_size=38)

G1, G2, GW, GH = 32.2, 85.2, 52.0, 16.5
figs = ["fig_ablation.png", "fig_model_compare.png",
        "fig_confusion.png", "fig_feature_importance.png"]
pos = [(G1, 21.2), (G2, 21.2), (G1, 38.7), (G2, 38.7)]
for (fx, fy), fname in zip(pos, figs):
    slide.shapes.add_picture(os.path.join(FIG, fname), Cm(fx), Cm(fy), Cm(GW), Cm(GH))

xgb_full = float(row("TF-IDF + sentiment + linguistic", "XGBoost")["f1"])
lr_tfidf = float(row("TF-IDF text only", "Logistic Regression")["f1"])
cl = list(csv.DictReader(open(os.path.join(RES, "claim_test_combined_vs_single.csv"))))
sig = sum(1 for r in cl if r["combined"] == "Sentiment + linguistic"
          and float(r["ci_low"]) > 0)
note = tbox(RX + 1.6, 56.6, RW - 3.2, 1.8)
para(note, "Proof of concept on 14,187 anonymised Reddit posts (public corpus, "
           "Mendeley DOI 10.17632/z8s6w86tr3.2) \u2014 stand-in for Ugandan data; "
           "not a validated clinical tool.", 11, MUT, italic=True, space_after=3,
     line=1.05)
para(note, ("Strongest model: XGBoost, F1 %.3f \u2014 statistically tied with "
            "TF-IDF-only logistic regression (%.3f); combining sentiment + "
            "linguistic features beats either alone (%d/6 paired tests).")
     % (xgb_full, lr_tfidf, sig), 11, MUT, italic=True, space_after=0, line=1.05)

# ================================================================== BOTTOM ROW
BY, BH = 60.0, 28.8


def conclusions_content(tf):
    bullets(tf, [
        "AI analysis of anonymised text can surface early risk signals that "
        "stigma and limited counselling capacity hide.",
        "Combining language and behavioural signals improves identification "
        "(preliminary).",
        "Models support, and never replace, trained counsellors: every flag "
        "leads to human assessment.",
        "Privacy, consent, fairness and cultural sensitivity are conditions "
        "for use, not add-ons.",
    ], 34, gap=13)
    para(tf, "From silence to action.  Early signals.  Timely referral.",
         30, CRIMSON, bold=True, space_after=0, space_before=20,
         align=PP_ALIGN.CENTER)


panel(30.6, BY, 43.2, BH, "CONCLUSIONS", conclusions_content)

RECS = [
    "Pilot in university counselling services with ethical clearance and "
    "informed consent.",
    "Keep a human in the loop: the model flags, a counsellor decides.",
    "Validate on Ugandan English, Luganda and code-switched text for cultural "
    "fit.",
    "Audit fairness across gender, faculty and year of study, and track "
    "missed cases.",
    "Strengthen referral pathways and counsellor capacity alongside national "
    "suicide-prevention policy.",
    "Tail it to Uganda and East African population.",
]


def recommendation_content(tf):
    numbered(tf, RECS, 32, gap=11)


panel(74.9, BY, 39.6, BH, "RECOMMENDATION", recommendation_content)

REFS = [
    "WHO. Suicide (fact sheet). Geneva: World Health Organization.",
    "UN Statistics Division. SDG Global Database, indicator 3.4.2: suicide "
    "mortality rate (2021).",
    "Breiman L. Random forests. Machine Learning. 2001;45:5\u201332.",
    "Chen T, Guestrin C. XGBoost: a scalable tree boosting system. Proc KDD. "
    "2016:785\u2013794.",
    "Coppersmith G, et al. Natural language processing of social media as "
    "screening for suicide risk. Biomed Inform Insights. 2018;10.",
    "https://github.com/anthonybyamugisha/Suicidal-prevention",
]


def refs_content(tf):
    for i, ref in enumerate(REFS, 1):
        p = _p(tf)
        p.space_after = 9
        p.line_spacing = 1.12
        r = p.add_run()
        r.text = f"{i}. "
        r.font.size = Pt(20)
        r.font.bold = True
        r.font.name = FONT
        r.font.color.rgb = CRIMSON
        r = p.add_run()
        r.text = ref
        r.font.size = Pt(20)
        r.font.name = FONT
        r.font.color.rgb = INK


RX3, RW3 = 115.6, 23.2
panel(RX3, BY, RW3, BH, "REFERENCES", refs_content, strip_size=30)
strip(RX3, BY + 21.6, RW3, 2.6, "CONTACT", size=30, fill=CRIMSON)
ctf = tbox(RX3 + 1.2, BY + 24.6, RW3 - 2.4, 3.6)
para(ctf, "Byamugisha Anthony", 26, DEEP, bold=True, space_after=4)
para(ctf, "byamugishanthony@gmail.com", 22, CRIMSON, space_after=4)
para(ctf, "+256 748 161 708", 22, INK, space_after=0)

prs.save(OUTFILE)
print(f"Wrote {OUTFILE}")
print(f"  slide  : {W} x {H} cm")
print(f"  fonts  : title 80, headings 30-38, body 28-34, refs 20")
print(f"  shapes : {len(slide.shapes)}")
print("Next: open in PowerPoint, review, then File > Export > Create PDF/XPS.")