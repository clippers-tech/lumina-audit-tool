"""pdf_generator.py — ReportLab branded dark-theme PDF for LinkedIn audit."""

import os
from datetime import datetime, timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, white, Color
from reportlab.lib.units import mm, inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether,
)
from reportlab.graphics.shapes import Drawing, Rect, String, Circle
from reportlab.graphics import renderPDF

# ── Brand colors ──
BG_DARK = HexColor("#0D0D0D")
BG_CARD = HexColor("#1A1A1A")
BG_CARD_ALT = HexColor("#141414")
GOLD = HexColor("#C9A84C")
GOLD_DIM = HexColor("#8A7333")
TEXT_WHITE = HexColor("#F0F0F0")
TEXT_MUTED = HexColor("#999999")
TEXT_FAINT = HexColor("#666666")
SEVERITY_HIGH = HexColor("#E74C3C")
SEVERITY_MEDIUM = HexColor("#E89B2D")
SEVERITY_LOW = HexColor("#27AE60")

PAGE_W, PAGE_H = A4
MARGIN = 20 * mm


def _severity_color(severity: str) -> HexColor:
    return {
        "high": SEVERITY_HIGH,
        "medium": SEVERITY_MEDIUM,
        "low": SEVERITY_LOW,
    }.get(severity.lower(), TEXT_MUTED)


def _severity_label(severity: str) -> str:
    return severity.upper()


def _bg_canvas(canvas, doc):
    """Draw dark background on every page."""
    canvas.saveState()
    canvas.setFillColor(BG_DARK)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # Footer
    canvas.setFillColor(TEXT_FAINT)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(MARGIN, 10 * mm, f"Lumina Clippers — LinkedIn Audit Report")
    canvas.drawRightString(PAGE_W - MARGIN, 10 * mm, f"Page {canvas.getPageNumber()}")

    canvas.restoreState()


def _make_styles():
    """Create custom paragraph styles for the dark PDF."""
    styles = {}

    styles["title"] = ParagraphStyle(
        "title",
        fontName="Helvetica-Bold",
        fontSize=28,
        leading=34,
        textColor=GOLD,
        alignment=TA_LEFT,
    )
    styles["h1"] = ParagraphStyle(
        "h1",
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=26,
        textColor=GOLD,
        alignment=TA_LEFT,
        spaceBefore=10,
        spaceAfter=8,
    )
    styles["h2"] = ParagraphStyle(
        "h2",
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=TEXT_WHITE,
        alignment=TA_LEFT,
        spaceBefore=6,
        spaceAfter=4,
    )
    styles["body"] = ParagraphStyle(
        "body",
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=TEXT_WHITE,
        alignment=TA_LEFT,
    )
    styles["body_muted"] = ParagraphStyle(
        "body_muted",
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=TEXT_MUTED,
        alignment=TA_LEFT,
    )
    styles["body_small"] = ParagraphStyle(
        "body_small",
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=TEXT_MUTED,
    )
    styles["center"] = ParagraphStyle(
        "center",
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=TEXT_WHITE,
        alignment=TA_CENTER,
    )
    styles["center_gold"] = ParagraphStyle(
        "center_gold",
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=GOLD,
        alignment=TA_CENTER,
    )
    styles["score_big"] = ParagraphStyle(
        "score_big",
        fontName="Helvetica-Bold",
        fontSize=64,
        leading=72,
        textColor=GOLD,
        alignment=TA_CENTER,
    )
    styles["lumina_brand"] = ParagraphStyle(
        "lumina_brand",
        fontName="Helvetica-Bold",
        fontSize=42,
        leading=50,
        textColor=GOLD,
        alignment=TA_CENTER,
        spaceAfter=6,
    )
    styles["subtitle"] = ParagraphStyle(
        "subtitle",
        fontName="Helvetica",
        fontSize=12,
        leading=16,
        textColor=TEXT_MUTED,
        alignment=TA_CENTER,
    )
    styles["badge_high"] = ParagraphStyle(
        "badge",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=white,
    )
    return styles


def _gap_table(gaps: list, styles: dict, available_width: float) -> list:
    """Render a list of gap items as styled table rows."""
    elements = []
    for gap in gaps:
        sev = gap.get("severity", "medium")
        sev_color = _severity_color(sev)
        sev_label = _severity_label(sev)

        issue_text = f'<font color="{TEXT_WHITE.hexval()}">{gap.get("issue", "")}</font>'
        evidence_text = f'<font color="{TEXT_MUTED.hexval()}"><b>Evidence:</b> {gap.get("evidence", "")}</font>'
        fix_text = f'<font color="{TEXT_MUTED.hexval()}"><b>Fix:</b> {gap.get("fix", "")}</font>'

        badge_para = Paragraph(
            f'<font color="white">{sev_label}</font>',
            styles["badge_high"],
        )
        issue_para = Paragraph(issue_text, styles["h2"])
        evidence_para = Paragraph(evidence_text, styles["body_small"])
        fix_para = Paragraph(fix_text, styles["body_small"])

        # Table: [severity badge | issue + evidence + fix]
        inner_content = []
        inner_content.append(issue_para)
        inner_content.append(Spacer(1, 3))
        inner_content.append(evidence_para)
        inner_content.append(Spacer(1, 3))
        inner_content.append(fix_para)

        # Build single-row table for the card
        data = [[badge_para, inner_content]]
        col_widths = [55, available_width - 55 - 12]
        t = Table(data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BG_CARD),
            ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#2A2A2A")),
            ("VALIGN", (0, 0), (0, 0), "TOP"),
            ("VALIGN", (1, 0), (1, 0), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (0, 0), 8),
            ("LEFTPADDING", (1, 0), (1, 0), 4),
            ("RIGHTPADDING", (-1, -1), (-1, -1), 8),
            ("BACKGROUND", (0, 0), (0, 0), sev_color),
            ("TEXTCOLOR", (0, 0), (0, 0), white),
            ("ALIGN", (0, 0), (0, 0), "CENTER"),
            ("ROUNDEDCORNERS", [4, 4, 4, 4]),
        ]))
        elements.append(KeepTogether([t, Spacer(1, 6)]))
    return elements


def _score_ring_drawing(score: int, size: float = 120) -> Drawing:
    """Draw a circular score ring using ReportLab graphics."""
    d = Drawing(size, size)
    cx, cy = size / 2, size / 2
    r = size / 2 - 8

    # Background circle
    bg_circle = Circle(cx, cy, r)
    bg_circle.fillColor = BG_CARD_ALT
    bg_circle.strokeColor = HexColor("#2A2A2A")
    bg_circle.strokeWidth = 2
    d.add(bg_circle)

    # Score text
    score_str = String(cx, cy - 10, str(score),
                       fontName="Helvetica-Bold", fontSize=32,
                       fillColor=GOLD, textAnchor="middle")
    d.add(score_str)

    label_str = String(cx, cy - 24, "/100",
                       fontName="Helvetica", fontSize=10,
                       fillColor=TEXT_MUTED, textAnchor="middle")
    d.add(label_str)

    return d


def generate_pdf(audit: dict, job_id: str) -> str:
    """Generate a dark-themed branded PDF audit report.

    Args:
        audit: The structured audit dict from Claude.
        job_id: Used to name the output file.

    Returns:
        Absolute path to the generated PDF.
    """
    output_path = os.path.join("outputs", f"{job_id}.pdf")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN + 10 * mm,
    )

    available_width = PAGE_W - 2 * MARGIN
    styles = _make_styles()
    story = []

    prospect = audit.get("prospect", {})
    name = prospect.get("name", "Unknown")
    headline = prospect.get("headline", "")
    company = prospect.get("company", "")
    score = prospect.get("score", 0)
    score_rationale = prospect.get("score_rationale", "")
    lumina_fit = audit.get("lumina_fit_score", 0)
    lumina_pitch = audit.get("lumina_pitch", "")

    # ──────────────────────────────────────
    # PAGE 1: Cover
    # ──────────────────────────────────────
    story.append(Spacer(1, 40 * mm))
    story.append(Paragraph("LUMINA", styles["lumina_brand"]))
    story.append(Paragraph("CLIPPERS", styles["lumina_brand"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("LinkedIn Audit Report", styles["subtitle"]))
    story.append(Spacer(1, 20 * mm))

    # Score ring
    ring = _score_ring_drawing(score, size=140)
    ring_table = Table([[ring]], colWidths=[available_width])
    ring_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(ring_table)
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Brand Presence Score", styles["center_gold"]))
    story.append(Spacer(1, 12 * mm))

    # Prospect info
    story.append(Paragraph(name, styles["h1"]))
    if headline:
        story.append(Paragraph(headline, styles["body_muted"]))
    if company:
        story.append(Paragraph(company, styles["body_muted"]))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(score_rationale, styles["body"]))
    story.append(Spacer(1, 10 * mm))

    # Date
    now_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    story.append(Paragraph(f"Generated: {now_str}", styles["body_small"]))
    story.append(PageBreak())

    # ──────────────────────────────────────
    # PAGE 2: Lumina Pitch + Quick Wins + Priority Actions
    # ──────────────────────────────────────
    story.append(Paragraph("── WHY LUMINA CLIPPERS ──", styles["h1"]))
    story.append(Spacer(1, 4 * mm))

    # Lumina fit score
    fit_table_data = [[
        Paragraph(f"<font color='{GOLD.hexval()}'><b>Lumina Fit Score: {lumina_fit}/100</b></font>", styles["body"]),
    ]]
    fit_table = Table(fit_table_data, colWidths=[available_width])
    fit_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_CARD),
        ("BOX", (0, 0), (-1, -1), 1, GOLD_DIM),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(fit_table)
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph(lumina_pitch, styles["body"]))
    story.append(Spacer(1, 10 * mm))

    # Quick wins
    story.append(Paragraph("── QUICK WINS ──", styles["h1"]))
    story.append(Spacer(1, 3 * mm))
    quick_wins = audit.get("quick_wins", [])
    for i, win in enumerate(quick_wins, 1):
        win_data = [[Paragraph(f"<font color='{GOLD.hexval()}'><b>{i}.</b></font>", styles["body"]),
                     Paragraph(win, styles["body"])]]
        win_table = Table(win_data, colWidths=[20, available_width - 20])
        win_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BG_CARD_ALT),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (0, 0), 10),
            ("LEFTPADDING", (1, 0), (1, 0), 4),
            ("RIGHTPADDING", (-1, -1), (-1, -1), 10),
            ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#2A2A2A")),
        ]))
        story.append(win_table)
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 8 * mm))

    # Priority actions
    story.append(Paragraph("── PRIORITY ACTIONS ──", styles["h1"]))
    story.append(Spacer(1, 3 * mm))
    priority_actions = audit.get("priority_actions", [])
    action_rows = []
    for i, action in enumerate(priority_actions, 1):
        action_rows.append([
            Paragraph(f"<font color='{GOLD.hexval()}'><b>{i}</b></font>", styles["center_gold"]),
            Paragraph(action, styles["body"]),
        ])
    if action_rows:
        actions_table = Table(action_rows, colWidths=[30, available_width - 30])
        actions_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BG_CARD),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [BG_CARD, BG_CARD_ALT]),
            ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#2A2A2A")),
            ("LINEBELOW", (0, 0), (-1, -2), 0.25, HexColor("#2A2A2A")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (0, -1), 10),
            ("LEFTPADDING", (1, 0), (1, -1), 8),
            ("RIGHTPADDING", (-1, -1), (-1, -1), 10),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(actions_table)

    story.append(PageBreak())

    # ──────────────────────────────────────
    # PAGE 3+: Gap Analysis
    # ──────────────────────────────────────

    # Personal Brand Gaps
    personal_gaps = audit.get("personal_brand_gaps", [])
    if personal_gaps:
        story.append(Paragraph("── PERSONAL BRAND GAPS ──", styles["h1"]))
        story.append(Spacer(1, 4 * mm))
        story.extend(_gap_table(personal_gaps, styles, available_width))
        story.append(Spacer(1, 8 * mm))

    # Company Brand Gaps
    company_gaps = audit.get("company_brand_gaps", [])
    if company_gaps:
        story.append(Paragraph("── COMPANY BRAND GAPS ──", styles["h1"]))
        story.append(Spacer(1, 4 * mm))
        story.extend(_gap_table(company_gaps, styles, available_width))
        story.append(Spacer(1, 8 * mm))

    # Content Strategy Gaps
    content_gaps = audit.get("content_strategy_gaps", [])
    if content_gaps:
        story.append(Paragraph("── CONTENT STRATEGY GAPS ──", styles["h1"]))
        story.append(Spacer(1, 4 * mm))
        story.extend(_gap_table(content_gaps, styles, available_width))

    # Build PDF
    doc.build(story, onFirstPage=_bg_canvas, onLaterPages=_bg_canvas)

    return output_path
