"""veriscope/pdf_report.py

PDF report generator using ReportLab with:
- Cover page + Overall Grade
- Horizontal bar chart for main scores
- Color-coded tables and status indicators
- Inclusion of AI summary and top failures

This is a clean, professional layout aimed at agency-style deliverables.
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics import renderPDF
from io import BytesIO


GRADE_THRESHOLDS = [(90, "A"), (80, "B"), (70, "C"), (60, "D"), (0, "F")]


def compute_overall_grade(scores: dict) -> (str, float):
    vals = [v for v in scores.values() if isinstance(v, (int, float))]
    if not vals:
        avg = 0.0
    else:
        avg = sum(vals) / len(vals)
    grade = next((g for t, g in GRADE_THRESHOLDS if avg >= t), "F")
    return grade, round(avg, 1)


def _draw_bar_chart(scores: dict, width=400, height=80) -> Drawing:
    drawing = Drawing(width, height)
    categories = ["performance", "seo", "best-practices"]
    max_width = width - 120
    y = height - 20
    for cat in categories:
        val = scores.get(cat) or 0
        bar_w = (val / 100.0) * max_width
        # color ramp
        if val >= 90:
            fill = colors.green
        elif val >= 75:
            fill = colors.yellowgreen
        elif val >= 60:
            fill = colors.orange
        else:
            fill = colors.red
        drawing.add(Rect(100, y - 14, bar_w, 12, fillColor=fill, strokeColor=colors.black))
        drawing.add(String(10, y - 12, cat.replace('-', ' ').title(), fontSize=9))
        drawing.add(String(110 + max_width + 10, y - 12, f"{val}%", fontSize=9))
        y -= 24
    return drawing


def generate_pdf(report: dict) -> bytes:
    """Return PDF bytes for the given report structure (as produced by engine + scraper + ai_summary)."""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = []

    # Cover page
    grade, avg = compute_overall_grade(report.get("scores", {}))
    cover_style = ParagraphStyle(
        "Cover", parent=styles["Title"], fontSize=36, alignment=1, spaceAfter=12
    )
    story.append(Paragraph(report.get("url", ""), styles["Normal"]))
    story.append(Paragraph(f"Overall Grade: <b>{grade}</b>", cover_style))
    story.append(Paragraph(f"Average Score: {avg}%", styles["Heading2"]))
    story.append(Spacer(1, 20))

    # Visual bar chart
    story.append(Paragraph("Summary Scores", styles["Heading3"]))
    drawing = _draw_bar_chart(report.get("scores", {}))
    story.append(drawing)
    story.append(Spacer(1, 12))

    # Core Web Vitals table
    story.append(Paragraph("User Experience (Core Web Vitals)", styles["Heading3"]))
    vitals = report.get("core_web_vitals", {})
    vitals_data = [["Metric", "Value"]]
    for k in ("FCP", "LCP", "CLS"):
        v = vitals.get(k, {})
        vitals_data.append([k, v.get("display") or "—"])
    t = Table(vitals_data, hAlign="LEFT")
    t.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F4F7")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ])
    )
    story.append(t)
    story.append(Spacer(1, 12))

    # On-page SEO table
    story.append(Paragraph("On-Page SEO", styles["Heading3"]))
    seo = report.get("onpage", {})
    seo_table = [["Item", "Status / Value"]]
    title_status = seo.get("title_status") if seo else "missing"
    title_bg = colors.green if title_status == "ok" else colors.red
    seo_table.append(["Title", seo.get("title") or "—"])
    seo_table.append(["Title Status", title_status])
    seo_table.append(["Meta Description", seo.get("meta_description") or "—"])
    seo_table.append(["Meta Description Status", seo.get("meta_description_status") or "—"])
    seo_table.append(["H1", seo.get("h1") or "—"])
    t2 = Table(seo_table, hAlign="LEFT")
    t2.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 1), (1, 1), colors.whitesmoke),
        ])
    )
    story.append(t2)
    story.append(Spacer(1, 12))

    # Top failures
    story.append(Paragraph("Top Failures", styles["Heading3"]))
    failures = report.get("top_failures", [])
    failures_table = [["Issue", "Impact", "Details"]]
    for f in failures:
        impact_pct = f"{round(f.get('impact', 0) * 100, 1)}%"
        failures_table.append([f.get("title"), impact_pct, f.get("displayValue") or f.get("description") or "—"])
    tf = Table(failures_table, hAlign="LEFT", colWidths=[150, 60, 300])
    tf.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F4F7"))]))
    story.append(tf)
    story.append(Spacer(1, 12))

    # AI Summary (3 bullets)
    story.append(Paragraph("Recommended Action Summary", styles["Heading3"]))
    ai_text = report.get("ai_summary", "")
    # ensure bullets
    for line in (ai_text.splitlines() if ai_text else []):
        story.append(Paragraph(line.strip(), styles["Normal"]))

    doc.build(story)
    pdf = buf.getvalue()
    buf.close()
    return pdf


if __name__ == "__main__":
    # quick smoke test
    sample = {
        "url": "https://example.com",
        "scores": {"performance": 72.3, "seo": 80.0, "best-practices": 65.1},
        "core_web_vitals": {"FCP": {"display": "1.2 s"}, "LCP": {"display": "3.8 s"}, "CLS": {"display": "0.18"}},
        "onpage": {"title": "Example", "title_status": "ok", "meta_description": "desc", "meta_description_status": "ok", "h1": "Welcome"},
        "top_failures": [],
        "ai_summary": "- Primary bottleneck...\n- Business impact...\n- First step...",
    }
    b = generate_pdf(sample)
    with open("sample_report.pdf", "wb") as f:
        f.write(b)
    print("Wrote sample_report.pdf")
