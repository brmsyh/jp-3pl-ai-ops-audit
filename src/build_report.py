"""
Build the client-facing audit report (PDF) from the analysis outputs.
Run after notebooks 01-03:  python src/build_report.py
"""
from pathlib import Path

import matplotlib
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

ROOT = Path(__file__).resolve().parents[1]
APP, FIG, OUT = ROOT / "data" / "app", ROOT / "reports" / "figures", ROOT / "reports"

# Fonts: DejaVu ships with matplotlib and covers ¥, ≈, ≥
fdir = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
pdfmetrics.registerFont(TTFont("Body", str(fdir / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("Bold", str(fdir / "DejaVuSans-Bold.ttf")))
from reportlab.lib.fonts import addMapping
addMapping("Body", 0, 0, "Body"); addMapping("Body", 1, 0, "Bold")
addMapping("Body", 0, 1, "Body"); addMapping("Body", 1, 1, "Bold")

INK, MUTED, BLUE, LINE, TINT = (colors.HexColor(c) for c in ["#1b1b1a", "#5b5a56", "#2a78d6", "#d9d8d3", "#eef4fc"])
H1 = ParagraphStyle("H1", fontName="Bold", fontSize=19, leading=24, textColor=INK, spaceAfter=4)
H2 = ParagraphStyle("H2", fontName="Bold", fontSize=13, leading=17, textColor=INK, spaceBefore=10, spaceAfter=5)
H3 = ParagraphStyle("H3", fontName="Bold", fontSize=10.5, leading=14, textColor=BLUE, spaceBefore=6, spaceAfter=2)
BODY = ParagraphStyle("B", fontName="Body", fontSize=9.4, leading=13.6, textColor=INK, alignment=TA_LEFT, spaceAfter=5)
SMALL = ParagraphStyle("S", parent=BODY, fontSize=8, leading=11, textColor=MUTED)
CELL = ParagraphStyle("C", parent=BODY, fontSize=8.4, leading=11, spaceAfter=0)
CELLB = ParagraphStyle("CB", parent=CELL, fontName="Bold")
KPI_V = ParagraphStyle("KV", fontName="Bold", fontSize=15, leading=19, textColor=BLUE)
KPI_L = ParagraphStyle("KL", fontName="Body", fontSize=7.8, leading=10, textColor=MUTED)

# ------------------------------------------------------------------ data
k = pd.read_csv(APP / "kpis.csv", index_col=0)["value"]
scores = pd.read_csv(APP / "task_scores.csv")
ini = pd.read_csv(APP / "initiatives.csv")
perc = pd.read_csv(APP / "perception.csv")
tick = pd.read_csv(APP / "tickets_by_category.csv").set_index("category")
docs_t = pd.read_csv(APP / "docs_by_type.csv")
docs_f = pd.read_csv(APP / "docs_by_format.csv").set_index("source_format")
TOP3 = scores["task_type"].head(3).tolist()
t3 = scores.head(3)
meet = scores.set_index("task_type").loc["Internal meetings"]

def ym(x): return f"¥{x / 1e6:,.1f}M"
def pct(x): return f"{x:.0%}"

top3_share = t3["hours"].sum() / k["total_hours"]
net_total, one_total = ini["net_annual_jpy"].sum(), ini["one_off_jpy"].sum()
payback_total = one_total / (net_total / 12)
hours_freed, fte_freed = ini["hours_freed"].sum(), ini["fte_freed"].sum()
doc_err = (docs_t["error_rate"] * docs_t["docs"]).sum() / docs_t["docs"].sum()
pdf_scan = docs_f.loc[["PDF (email)", "Scanned paper"], "share"].sum()
w = tick.loc["WISMO"]
unrec_share = k["unrecovered_jpy"] / k["overbilled_jpy"]

def sens(f):
    net = (ini["baseline_hours"] * ini["automation_pct"] * f * ini["avg_hourly_cost_jpy"]
           + ini["extra_benefit_jpy"] * f - ini["annual_jpy"]).sum()
    return net, one_total / (net / 12)

# ------------------------------------------------------------------ helpers
def table(rows, widths, header=True, zebra=True, bold_last=False):
    data = [[Paragraph(str(c), CELLB if (header and i == 0) or (bold_last and i == len(rows) - 1) else CELL)
             for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
          ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
          ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]
    if header:
        st += [("LINEBELOW", (0, 0), (-1, 0), 1, INK)]
    t.setStyle(TableStyle(st))
    return t

def fig(name, width_mm=170):
    from PIL import Image as PI
    p = FIG / name
    wpx, hpx = PI.open(p).size
    return Image(str(p), width=width_mm * mm, height=width_mm * mm * hpx / wpx)

def kpis(items):
    cells = [[Paragraph(v, KPI_V), Paragraph(l, KPI_L)] for v, l in items]
    t = Table([[c for c in cells]], colWidths=[42.5 * mm] * len(items))
    inner = []
    for v, l in items:
        it = Table([[Paragraph(v, KPI_V)], [Paragraph(l, KPI_L)]], colWidths=[39 * mm])
        it.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 1)]))
        inner.append(it)
    t = Table([inner], colWidths=[42.5 * mm] * len(items))
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), TINT), ("LINEBEFORE", (1, 0), (-1, 0), 2, colors.white),
                           ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8)]))
    return t

def footer(c, doc):
    c.saveState()
    c.setFont("Body", 7.2); c.setFillColor(MUTED)
    c.drawString(20 * mm, 11 * mm, "AI Operations Audit · Top 3 Time Drains · 3PL, Japan (case study, synthetic data)")
    c.drawRightString(190 * mm, 11 * mm, f"{doc.page}")
    c.restoreState()

# ------------------------------------------------------------------ story
s = []
s += [Paragraph("AI Operations Audit: Top 3 Time Drains", H1),
      Paragraph("Mid-sized third-party logistics provider · Kanto region, Japan · ~60 office staff · "
                "data period Nov 2025 – Oct 2026", SMALL),
      Spacer(1, 8)]
s.append(Paragraph("Executive summary", H2))
s.append(Paragraph(
    f"The office team logged <b>{k['total_hours']:,.0f} hours</b> in 12 months, a loaded staff cost of "
    f"<b>{ym(k['total_cost_jpy'])}</b>. Management asked which three operational time drains to fix first with AI "
    f"and what that is worth. We measured time from the task-tracking system, cross-checked it against ticket, "
    f"document and invoice data, and compared it with what staff believe.", BODY))
s.append(kpis([(pct(top3_share), "of all hours go to the top 3 drains"),
               (f"{fte_freed:.1f} FTE", f"capacity freed ({hours_freed:,.0f} h/yr)"),
               (ym(net_total), "net annual benefit after running costs"),
               (f"{payback_total:.1f} mo", f"blended payback on {ym(one_total)} one-off")]))
s.append(Spacer(1, 8))
s.append(Paragraph("The three drains to fix first", H3))
rows = [["#", "Time drain", "Hours / yr", "Share", "Recommended AI lever"]]
levers = {TOP3[0]: "Intelligent document processing (OCR + LLM extraction), human validation",
          TOP3[1]: "Proactive tracking notifications + LLM reply assistant on live TMS data",
          TOP3[2]: "Automated matching against contract rate cards; people handle exceptions"}
for i, r in enumerate(t3.itertuples(), 1):
    rows.append([i, r.task_type, f"{r.hours:,.0f}", pct(r.share), levers[r.task_type]])
s.append(table(rows, [8 * mm, 50 * mm, 20 * mm, 14 * mm, 78 * mm]))
s.append(Spacer(1, 6))
s.append(Paragraph("Key messages", H3))
for b in [
    f"<b>Meetings are the biggest block of time ({pct(meet['share'])}) but not the biggest AI opportunity.</b> "
    f"AI can only trim them. The top 3 drains together take {pct(top3_share)} of hours, nearly twice as much.",
    "<b>Staff perception points the wrong way.</b> People over-weight meetings and Excel reporting, and "
    "under-weight document keying, status inquiries and invoice checking, which are repetitive work spread thinly through the day.",
    f"<b>Each drain has a measurable symptom:</b> {pct(doc_err)} of keyed documents contain an error; "
    f"{pct(w['share'])} of labelled tickets ask \"where is my shipment?\" and {pct(w['reopen_rate'])} of those are reopened; "
    f"{ym(k['unrecovered_jpy'])} of carrier overbilling ({pct(unrec_share)}) was never recovered.",
    f"<b>The business case holds under stress.</b> At half the planned automation, the programme still returns "
    f"{ym(sens(0.5)[0])} a year and pays back in {sens(0.5)[1]:.0f} months.",
    "<b>Start with WISMO</b> (fastest to launch, visible to customers), then invoice matching, then document processing.",
]:
    s.append(Paragraph("•&nbsp;&nbsp;" + b, BODY))
s.append(PageBreak())

# Page 2 – where time goes
s.append(Paragraph("1. Where the time goes", H2))
s.append(Paragraph(
    "Time-tracking entries were cleaned first (duplicate submissions, 100+ spellings of 25 task types, missing and "
    "runaway timers, mixed date formats) so that a typical day sums to 7–8.5 hours. Hours were then costed with "
    "each employee's loaded hourly rate.", BODY))
s.append(fig("01_hours_by_task.png", 165))
s.append(Paragraph("2. Perception vs data", H2))
s.append(Paragraph(
    f"Before seeing the data, {len(pd.read_csv(ROOT / 'data' / 'raw' / 'employee_survey.csv'))} staff named their three "
    "biggest time drains (weighted 3-2-1). Visible, frustrating work is over-weighted; high-volume micro-tasks are under-weighted. "
    "Shipping document entry shows the largest gap.", BODY))
s.append(fig("02_perception_vs_actual.png", 165))
s.append(PageBreak())

# Page 3 – scoring
s.append(Paragraph("3. Which drains AI can actually remove", H2))
s.append(Paragraph(
    "For every task we estimated the share of time AI or automation can realistically remove within 12 months, "
    "based on how repetitive, rule-based and digital the work is. Multiplying by the cost of the hours gives the "
    "<b>AI-addressable cost</b>, which is the ranking used to pick the top 3. The percentages are analyst "
    "assumptions and are listed so they can be challenged.", BODY))
s.append(fig("03_ai_addressable_cost.png", 160))
rows = [["Task", "Hours / yr", "AI share", "Addressable cost / yr", "Lever"]]
for r in scores.head(6).itertuples():
    rows.append([r.task_type, f"{r.hours:,.0f}", pct(r.ai_addressable_pct), ym(r.addressable_cost_jpy), r.ai_lever])
s.append(table(rows, [46 * mm, 18 * mm, 19 * mm, 25 * mm, 62 * mm]))
s.append(Spacer(1, 4))
s.append(Paragraph("Manual tracking updates (#4) share a root cause with WISMO, the lack of an automated tracking feed, "
                   "so they are addressed by the same initiative.", SMALL))
s.append(PageBreak())

# Page 4 – deep dives
s.append(Paragraph("4. Deep dives and recommendations", H2))
s.append(Paragraph("4.1 Shipping document data entry (Operations)", H3))
s.append(Paragraph(
    f"<b>Finding.</b> {k['docs']:,.0f} documents a year are re-typed into the WMS. {pct(doc_err)} contain at least one "
    f"keying error, creating {docs_t['rework_h'].sum():,.0f} hours of rework; error rates rise with document complexity "
    f"(customs declarations {pct(docs_t.set_index('doc_type').loc['Customs declaration', 'error_rate'])}). "
    f"{pct(pdf_scan)} arrive as PDF or scans. <b>Recommendation.</b> Intelligent document processing extracts fields, "
    "a person validates low-confidence fields, and the result is pushed to the WMS. Excel files are imported directly. "
    "Target: ~70% of keying time removed.", BODY))
s.append(Paragraph("4.2 Shipment status inquiries / WISMO (Customer Service)", H3))
s.append(Paragraph(
    f"<b>Finding.</b> {pct(w['share'])} of labelled tickets are status questions. Each takes ~{w['avg_handle_min']:.0f} "
    f"minutes, but volume peaks in December and March, and {pct(w['reopen_rate'])} are reopened because the customer "
    f"chases again (median first response {w['median_first_response_min']:.0f} min). The answer already exists in the TMS. "
    "<b>Recommendation.</b> (1) Proactive tracking emails/SMS at key milestones; (2) an LLM reply assistant that answers "
    "WISMO emails from live tracking data, introduced in suggest-mode first.", BODY))
s.append(fig("04_wismo_patterns.png", 160))
s.append(Paragraph("4.3 Carrier invoice reconciliation (Finance)", H3))
s.append(Paragraph(
    f"<b>Finding.</b> All {k['invoice_lines']:,.0f} carrier invoice lines are checked by hand, yet only ~14% are wrong. "
    f"Overbilling totalled {ym(k['overbilled_jpy'])}, mostly fuel surcharges and wrong weight tiers, and "
    f"{pct(unrec_share)} of it was never recovered. <b>Recommendation.</b> Match every line automatically against the "
    "contract rate card, flag mismatches by reason, and let people work only the exceptions. Earlier, better-evidenced "
    "disputes raise recovery (assumed 62% to 90%).", BODY))
s.append(PageBreak())

# Page 5 – ROI
s.append(Paragraph("5. Business case", H2))
s.append(Paragraph(
    "Value = hours freed × average loaded hourly cost of the staff doing the task, plus improved overbilling recovery "
    "for invoices. Costs are typical estimates for a company of this size (software plus integration) and should be "
    "replaced with vendor quotes.", BODY))
rows = [["Initiative", "Hours freed", "FTE", "Gross benefit", "One-off", "Running / yr", "Net / yr", "Payback"]]
for r in ini.itertuples():
    rows.append([r.initiative, f"{r.hours_freed:,.0f}", f"{r.fte_freed:.1f}", ym(r.gross_benefit_jpy), ym(r.one_off_jpy),
                 ym(r.annual_jpy), ym(r.net_annual_jpy), f"{r.payback_months:.1f} mo"])
rows.append(["Total", f"{hours_freed:,.0f}", f"{fte_freed:.1f}", ym(ini["gross_benefit_jpy"].sum()), ym(one_total),
             ym(ini["annual_jpy"].sum()), ym(net_total), f"{payback_total:.1f} mo"])
s.append(table(rows, [44 * mm, 18 * mm, 11 * mm, 20 * mm, 17 * mm, 20 * mm, 20 * mm, 17 * mm], bold_last=True))
s.append(Spacer(1, 6))
s.append(fig("05_roi.png", 160))
rows = [["Scenario", "Net annual benefit", "Payback"]]
for f in [0.5, 0.75, 1.0]:
    n, p = sens(f)
    rows.append([f"{int(f * 100)}% of planned automation", ym(n), f"{p:.1f} months"])
s.append(Paragraph("Sensitivity", H3))
s.append(table(rows, [60 * mm, 40 * mm, 30 * mm]))
s.append(Spacer(1, 4))
s.append(Paragraph("Freed hours are capacity, not automatic cash savings. The value is realised by absorbing volume "
                   "growth without new hires, reducing overtime in peak months and moving staff to higher-value work "
                   "such as exception handling and customer care.", SMALL))
s.append(PageBreak())

# Page 6 – roadmap & PoC
s.append(Paragraph("6. Roadmap", H2))
rows = [["Phase", "Timing", "What", "Success measure"],
        ["1 · Quick win", "Month 0–3", "Proactive tracking notifications; WISMO reply assistant in suggest-mode; "
         "auto-send for high-confidence emails after a 4-week pilot", "WISMO tickets −40%, reopen rate below 10%"],
        ["2 · Finance", "Month 2–5", "Rate-card matching for the two largest carriers, then all five; dispute workflow",
         "Lines checked by hand −65%; recovery rate ≥ 85%"],
        ["3 · Documents", "Month 4–9", "Document processing for delivery notes and packing lists first, then invoices, "
         "B/L and customs; WMS integration", "Keying time −70%; error rate below 5%"],
        ["Enablers", "Ongoing", "Owner per initiative, monthly time-tracking review, staff training, data-privacy "
         "check for customer emails (APPI)", "Adoption above 80% of target users"]]
s.append(table(rows, [26 * mm, 22 * mm, 78 * mm, 44 * mm]))
s.append(Paragraph("7. Proof of concept: email classifier", H2))
s.append(Paragraph(
    "To test the WISMO lever, we trained a TF-IDF + logistic regression model on the historic inbox. On a hold-out "
    "set it reached 97.4% accuracy (macro-F1 0.97) versus 0.87 macro-F1 for keyword rules. With a conservative "
    "confidence threshold of 0.90 it can auto-handle about 80% of WISMO emails at ~97% precision, while most "
    "mixed-topic emails stay with a person. Precision is capped by the ~3% of historic agent labels that are wrong.", BODY))
s.append(fig("07_threshold.png", 150))
s.append(Paragraph("8. Assumptions and limitations", H2))
for b in ["Time tracking reflects how staff record their work; under-recording of short interruptions is likely, so "
          "high-volume tasks may be understated rather than overstated.",
          "AI-addressable percentages and costs are estimates; the sensitivity table shows the impact of missing them.",
          "The classifier was tested on historic emails only; a live pilot is required before auto-sending replies.",
          "This report is a portfolio case study built on realistic synthetic data; no real company data is used."]:
    s.append(Paragraph("•&nbsp;&nbsp;" + b, BODY))

doc = SimpleDocTemplate(str(OUT / "AI_Operations_Audit_Report.pdf"), pagesize=A4, leftMargin=20 * mm,
                        rightMargin=20 * mm, topMargin=17 * mm, bottomMargin=18 * mm,
                        title="AI Operations Audit: Top 3 Time Drains", author="Yunido B.")
doc.build(s, onFirstPage=footer, onLaterPages=footer)
print("Saved", OUT / "AI_Operations_Audit_Report.pdf")
