"""
Lumina Clippers Marketing Audit Tool — PDF Generator v3
Dashboard-style: bold numbers, visual bars, minimal text, zero fluff.
Sections: Gauge → Brand Visibility → Competitor Visibility → Revenue → CPM → CTA
Packed tight — fewer pages, less whitespace.

Brand: Deep forest green bg, bright lime-green accents, white text.
"""

import os, math
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, KeepTogether, Image,
)
from reportlab.platypus.flowables import Flowable
from reportlab.pdfgen import canvas as pdfgen_canvas


# ───────────────────── Brand colours — Lumina Clippers ───
BG_PAGE     = colors.HexColor("#0a2e1a")   # Deep forest green
BG_CARD     = colors.HexColor("#0d3320")   # Slightly lighter green
BG_CARD_ALT = colors.HexColor("#0b2b17")   # Subtle variant
ACCENT      = colors.HexColor("#4ade80")   # Bright lime green (primary accent)
ACCENT_DIM  = colors.HexColor("#22c55e")   # Darker green accent
TEXT_WHITE   = colors.HexColor("#FFFFFF")   # Pure white
TEXT_MUTED   = colors.HexColor("#b0c4b0")   # Soft green-grey
TEXT_FAINT   = colors.HexColor("#5a7a5a")   # Faint green
RED          = colors.HexColor("#E74C3C")
GREEN_GOOD   = colors.HexColor("#4ade80")   # Same as accent — for positive bars
BAR_BG       = colors.HexColor("#163d26")   # Dark green bar background

# Legacy aliases (used in some flowables)
GOLD = ACCENT
GOLD_DIM = ACCENT_DIM

PAGE_W, PAGE_H = A4
MARGIN    = 18 * mm
CONTENT_W = PAGE_W - 2 * MARGIN


# ── Path to bundled assets ──
_ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
_IMG_VOUCH  = os.path.join(_ASSETS_DIR, "vouch_dashboard.jpg")
_IMG_WALL   = os.path.join(_ASSETS_DIR, "client_wall.jpg")
_IMG_LOGO   = os.path.join(_ASSETS_DIR, "lumina_clippers_logo.png")


# ───────────────────── Page background + footer ──────────
def _on_page(canv: pdfgen_canvas.Canvas, doc):
    canv.saveState()
    canv.setFillColor(BG_PAGE)
    canv.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # Subtle top border accent
    canv.setStrokeColor(ACCENT); canv.setLineWidth(1.5)
    canv.line(0, PAGE_H - 1, PAGE_W, PAGE_H - 1)

    # Footer
    fy = 10 * mm
    canv.setStrokeColor(ACCENT_DIM); canv.setLineWidth(0.3)
    canv.line(MARGIN, fy, PAGE_W - MARGIN, fy)
    canv.setFont("Helvetica", 6.5); canv.setFillColor(TEXT_FAINT)
    canv.drawString(MARGIN, fy - 4, "Lumina Clippers — Visibility Audit")
    canv.drawRightString(PAGE_W - MARGIN, fy - 4, f"Page {canv.getPageNumber()}")
    canv.restoreState()


# ───────────────────── Custom Flowables ──────────────────

class AccentRule(Flowable):
    """Horizontal accent line in lime green."""
    def __init__(self, width, thickness=0.5):
        super().__init__(); self.width = width; self.height = thickness
    def draw(self):
        self.canv.setStrokeColor(ACCENT); self.canv.setLineWidth(self.height)
        self.canv.line(0, 0, self.width, 0)


class GaugeArc(Flowable):
    """Semi-circle gauge: 0-100 score, colour-coded."""
    def __init__(self, score, width=160, height=90):
        super().__init__(); self.score = max(0, min(100, int(score)))
        self.width = width; self.height = height

    def draw(self):
        cx, cy = self.width / 2, 12
        r = 70
        self.canv.setStrokeColor(BAR_BG); self.canv.setLineWidth(14)
        self.canv.arc(cx - r, cy - r, cx + r, cy + r, 0, 180)
        if self.score < 30:   c = RED
        elif self.score < 60: c = colors.HexColor("#facc15")  # Yellow/amber
        else:                 c = ACCENT
        self.canv.setStrokeColor(c); self.canv.setLineWidth(14)
        angle = self.score / 100 * 180
        self.canv.arc(cx - r, cy - r, cx + r, cy + r, 180, -angle)
        self.canv.setFont("Helvetica-Bold", 36); self.canv.setFillColor(TEXT_WHITE)
        self.canv.drawCentredString(cx, cy + 18, f"{self.score}")
        self.canv.setFont("Helvetica", 10); self.canv.setFillColor(TEXT_MUTED)
        self.canv.drawCentredString(cx, cy + 2, "/ 100")


class HBar(Flowable):
    """Horizontal comparison bar — two values, filled proportionally."""
    def __init__(self, val_a, val_b, label_a, label_b, width=None, height=42,
                 color_a=None, color_b=RED):
        super().__init__()
        self.width = width or CONTENT_W
        self.height = height
        self.val_a = max(val_a, 0); self.val_b = max(val_b, 0)
        self.label_a = label_a; self.label_b = label_b
        self.color_a = color_a or ACCENT; self.color_b = color_b

    def draw(self):
        total = self.val_a + self.val_b
        if total == 0: total = 1
        bar_w = self.width - 4
        bar_h = 14
        y_top = self.height - 6
        self.canv.setFont("Helvetica-Bold", 9); self.canv.setFillColor(TEXT_WHITE)
        self.canv.drawString(2, y_top, self.label_a)
        self.canv.setFont("Helvetica-Bold", 9); self.canv.setFillColor(self.color_a)
        self.canv.drawRightString(self.width - 2, y_top, f"{self.val_a:,} views")
        y_bar1 = y_top - 16
        self.canv.setFillColor(BAR_BG)
        self.canv.roundRect(2, y_bar1, bar_w, bar_h, 3, fill=1, stroke=0)
        fill_a = max(4, bar_w * self.val_a / total)
        self.canv.setFillColor(self.color_a)
        self.canv.roundRect(2, y_bar1, fill_a, bar_h, 3, fill=1, stroke=0)
        y_lab2 = y_bar1 - 16
        self.canv.setFont("Helvetica-Bold", 9); self.canv.setFillColor(TEXT_WHITE)
        self.canv.drawString(2, y_lab2, self.label_b)
        self.canv.setFillColor(self.color_b)
        self.canv.drawRightString(self.width - 2, y_lab2, f"{self.val_b:,} views")
        y_bar2 = y_lab2 - 16
        self.canv.setFillColor(BAR_BG)
        self.canv.roundRect(2, y_bar2, bar_w, bar_h, 3, fill=1, stroke=0)
        fill_b = max(4, bar_w * self.val_b / total)
        self.canv.setFillColor(self.color_b)
        self.canv.roundRect(2, y_bar2, fill_b, bar_h, 3, fill=1, stroke=0)


class VBarChart(Flowable):
    """Side-by-side vertical bar chart for two values."""
    def __init__(self, val_a, val_b, label_a, label_b,
                 name_a="You", name_b="Competitor",
                 width=None, height=160, color_a=TEXT_WHITE, color_b=None):
        super().__init__()
        self.width = width or CONTENT_W
        self.height = height
        self.val_a = val_a; self.val_b = val_b
        self.label_a = label_a; self.label_b = label_b
        self.name_a = name_a; self.name_b = name_b
        self.color_a = color_a; self.color_b = color_b or ACCENT

    def draw(self):
        max_v = max(self.val_a, self.val_b, 1)
        bar_area_h = self.height - 55
        bar_w = 70
        gap = 40
        total_bars_w = bar_w * 2 + gap
        start_x = (self.width - total_bars_w) / 2
        base_y = 30

        for i, (v, lbl, name, col) in enumerate([
            (self.val_a, self.label_a, self.name_a, self.color_a),
            (self.val_b, self.label_b, self.name_b, self.color_b),
        ]):
            x = start_x + i * (bar_w + gap)
            h = max(6, bar_area_h * v / max_v)
            self.canv.setFillColor(BAR_BG)
            self.canv.roundRect(x, base_y, bar_w, bar_area_h, 4, fill=1, stroke=0)
            self.canv.setFillColor(col)
            self.canv.roundRect(x, base_y, bar_w, h, 4, fill=1, stroke=0)
            # Value on top of bar
            self.canv.setFont("Helvetica-Bold", 16); self.canv.setFillColor(col)
            self.canv.drawCentredString(x + bar_w/2, base_y + h + 6, str(lbl))
            # Name under bar
            self.canv.setFont("Helvetica-Bold", 9); self.canv.setFillColor(TEXT_MUTED)
            self.canv.drawCentredString(x + bar_w/2, base_y - 14, name)


class CPMBars(Flowable):
    """Two horizontal bars comparing CPM values — one tall, one tiny."""
    def __init__(self, cpm_ads, cpm_clip, industry, width=None, height=100):
        super().__init__()
        self.width = width or CONTENT_W
        self.height = height
        self.cpm_ads = cpm_ads; self.cpm_clip = cpm_clip
        self.industry = industry

    def draw(self):
        bar_w = self.width * 0.65
        x_start = (self.width - bar_w) / 2
        y1 = self.height - 20
        self.canv.setFont("Helvetica-Bold", 10); self.canv.setFillColor(RED)
        self.canv.drawString(x_start, y1 + 2, f"Meta Ads  —  ${self.cpm_ads:.2f} CPM")
        self.canv.setFillColor(RED)
        self.canv.roundRect(x_start, y1 - 18, bar_w, 14, 3, fill=1, stroke=0)
        y2 = y1 - 50
        self.canv.setFont("Helvetica-Bold", 10); self.canv.setFillColor(ACCENT)
        self.canv.drawString(x_start, y2 + 2, f"Clipping  —  ${self.cpm_clip:.2f} CPM")
        clip_w = max(6, bar_w * self.cpm_clip / max(self.cpm_ads, 0.01))
        self.canv.setFillColor(BAR_BG)
        self.canv.roundRect(x_start, y2 - 18, bar_w, 14, 3, fill=1, stroke=0)
        self.canv.setFillColor(ACCENT)
        self.canv.roundRect(x_start, y2 - 18, clip_w, 14, 3, fill=1, stroke=0)
        if self.cpm_clip > 0:
            mult = self.cpm_ads / self.cpm_clip
            self.canv.setFont("Helvetica-Bold", 18); self.canv.setFillColor(ACCENT)
            self.canv.drawCentredString(self.width / 2, y2 - 48, f"{mult:.0f}x cheaper")


# ───────────────────── Styles ────────────────────────────
def _styles():
    base = dict(fontName="Helvetica", textColor=TEXT_WHITE, backColor=None, spaceAfter=2)
    def s(name, **kw): return ParagraphStyle(name, **{**base, **kw})
    return {
        "brand":      s("brand", fontSize=36, leading=42, textColor=ACCENT,
                         alignment=TA_CENTER, fontName="Helvetica-Bold"),
        "brand_sub":  s("brand_sub", fontSize=13, leading=16, textColor=TEXT_MUTED,
                         alignment=TA_CENTER),
        "h1":         s("h1", fontSize=20, leading=24, textColor=ACCENT,
                         fontName="Helvetica-Bold", spaceAfter=2),
        "h2":         s("h2", fontSize=14, leading=18, textColor=ACCENT,
                         fontName="Helvetica-Bold", spaceAfter=2),
        "big_num":    s("big_num", fontSize=44, leading=50, textColor=TEXT_WHITE,
                         alignment=TA_CENTER, fontName="Helvetica-Bold"),
        "big_accent": s("big_accent", fontSize=44, leading=50, textColor=ACCENT,
                         alignment=TA_CENTER, fontName="Helvetica-Bold"),
        "label":      s("label", fontSize=10, leading=13, textColor=TEXT_MUTED,
                         alignment=TA_CENTER),
        "label_left": s("label_left", fontSize=10, leading=13, textColor=TEXT_MUTED),
        "card_num":   s("card_num", fontSize=22, leading=26, textColor=TEXT_WHITE,
                         alignment=TA_CENTER, fontName="Helvetica-Bold"),
        "card_accent":s("card_accent", fontSize=22, leading=26, textColor=ACCENT,
                         alignment=TA_CENTER, fontName="Helvetica-Bold"),
        "card_label": s("card_label", fontSize=9, leading=12, textColor=TEXT_MUTED,
                         alignment=TA_CENTER, fontName="Helvetica-Bold"),
        "scale_txt":  s("scale_txt", fontSize=8, leading=10, textColor=TEXT_FAINT,
                         alignment=TA_CENTER),
        "name":       s("name", fontSize=16, leading=20, textColor=TEXT_WHITE,
                         alignment=TA_CENTER, fontName="Helvetica-Bold"),
        "detail":     s("detail", fontSize=11, leading=14, textColor=TEXT_MUTED,
                         alignment=TA_CENTER),
        "date":       s("date", fontSize=8, leading=11, textColor=TEXT_FAINT,
                         alignment=TA_CENTER),
        "body":       s("body", fontSize=10, leading=14, textColor=TEXT_MUTED),
        "cta_big":    s("cta_big", fontSize=20, leading=26, textColor=ACCENT,
                         alignment=TA_CENTER, fontName="Helvetica-Bold"),
        "cta_email":  s("cta_email", fontSize=11, leading=14, textColor=TEXT_MUTED,
                         alignment=TA_CENTER),
        "bullet":     s("bullet", fontSize=10, leading=14, textColor=TEXT_WHITE),
        # Legacy aliases
        "card_gold":  s("card_gold", fontSize=22, leading=26, textColor=ACCENT,
                         alignment=TA_CENTER, fontName="Helvetica-Bold"),
    }


# ───────────────────── Helpers ───────────────────────────
def _fmt(n):
    try: return f"{int(n):,}"
    except: return str(n) if n else "0"

def _safe(d, *keys, default=""):
    for k in keys:
        if not isinstance(d, dict): return default
        d = d.get(k); 
        if d is None: return default
    return d if d is not None else default

def _platform_cards(platforms, styles, card_style="card_num"):
    """Build a 2x2 grid of platform metric boxes."""
    if not platforms: return []
    cells = []
    for p in platforms[:4]:
        name  = _safe(p, "platform", default="—")
        views = _safe(p, "their_views", default=0)
        inner = Table([
            [Paragraph(name.upper(), styles["card_label"])],
            [Paragraph(_fmt(views), styles[card_style])],
            [Paragraph("views", styles["scale_txt"])],
        ], colWidths=[(CONTENT_W - 20) / 2])
        inner.setStyle(TableStyle([
            ("BACKGROUND",   (0,0),(-1,-1), BG_CARD),
            ("BOX",          (0,0),(-1,-1), 0.5, ACCENT_DIM),
            ("ALIGN",        (0,0),(-1,-1), "CENTER"),
            ("TOPPADDING",   (0,0),(-1,-1), 6),
            ("BOTTOMPADDING",(0,0),(-1,-1), 6),
            ("LEFTPADDING",  (0,0),(-1,-1), 4),
            ("RIGHTPADDING", (0,0),(-1,-1), 4),
        ]))
        cells.append(inner)
    empty_cell = Paragraph("", styles["scale_txt"])
    while len(cells) < 4:
        cells.append(empty_cell)
    half_w = (CONTENT_W - 10) / 2
    grid = Table([[cells[0], cells[1]], [cells[2], cells[3]]],
                 colWidths=[half_w, half_w],
                 hAlign="CENTER")
    grid.setStyle(TableStyle([
        ("LEFTPADDING",  (0,0),(-1,-1), 2),
        ("RIGHTPADDING", (0,0),(-1,-1), 2),
        ("TOPPADDING",   (0,0),(-1,-1), 2),
        ("BOTTOMPADDING",(0,0),(-1,-1), 2),
        ("ALIGN",        (0,0),(-1,-1), "CENTER"),
    ]))
    return [grid]


# ═══════════════════════════════════════════════════════════
# PAGE BUILDERS — compact layout, minimal gaps
# ═══════════════════════════════════════════════════════════

def _page1_score(story, audit, styles):
    """PAGE 1 — Logo + Visibility Score gauge + prospect info."""
    p = audit.get("prospect", {})
    score    = int(_safe(p, "visibility_score", default=0))
    name     = _safe(p, "name", default="Prospect")
    company  = _safe(p, "company", default="")
    industry = _safe(p, "industry", default="")
    today    = datetime.now().strftime("%B %d, %Y")

    story.append(Spacer(1, 8*mm))

    # Logo
    if os.path.exists(_IMG_LOGO):
        logo = Image(_IMG_LOGO, width=180, height=45, kind='proportional')
        logo.hAlign = 'CENTER'
        story.append(logo)
        story.append(Spacer(1, 4*mm))
    else:
        story.append(Paragraph("LUMINA CLIPPERS", styles["brand"]))
        story.append(Spacer(1, 1*mm))

    story.append(Paragraph("Visibility Audit", styles["brand_sub"]))
    story.append(Spacer(1, 6*mm))
    story.append(AccentRule(CONTENT_W))
    story.append(Spacer(1, 8*mm))

    gauge = GaugeArc(score, width=200, height=100)
    gauge.hAlign = "CENTER"
    story.append(gauge)
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph("VISIBILITY SCORE", styles["label"]))
    story.append(Spacer(1, 4*mm))

    scale = Table(
        [[Paragraph("0–30  LOW", styles["scale_txt"]),
          Paragraph("30–60  MODERATE", styles["scale_txt"]),
          Paragraph("60–100  STRONG", styles["scale_txt"])]],
        colWidths=[CONTENT_W/3]*3)
    scale.setStyle(TableStyle([
        ("ALIGN",(0,0),(-1,-1),"CENTER"),
        ("TOPPADDING",(0,0),(-1,-1),0),
        ("BOTTOMPADDING",(0,0),(-1,-1),0),
    ]))
    story.append(scale)

    story.append(Spacer(1, 8*mm))
    story.append(AccentRule(CONTENT_W))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(name, styles["name"]))
    if company or industry:
        parts = [x for x in [company, industry] if x]
        story.append(Paragraph(" · ".join(parts), styles["detail"]))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(today, styles["date"]))
    story.append(PageBreak())


def _page2_brand_visibility(story, audit, styles):
    """Brand Exposure (48h) + platform boxes."""
    vis   = audit.get("visibility_audit", {})
    total = _safe(vis, "their_total_views_48h", default=0)
    plats = _safe(vis, "platform_breakdown", default=[]) or []

    story.append(Paragraph("Brand Exposure", styles["h1"]))
    story.append(AccentRule(CONTENT_W))
    story.append(Spacer(1, 4*mm))

    story.append(Paragraph(_fmt(total), styles["big_num"]))
    story.append(Paragraph("total views on brand mentions (past 48 hours)", styles["label"]))
    story.append(Spacer(1, 5*mm))

    for el in _platform_cards(plats, styles, "card_num"):
        story.append(el)

    # No PageBreak — let content flow naturally


def _page3_competitor(story, audit, styles):
    """Competitor Exposure (48h) + comparison bar."""
    comp  = audit.get("competitor_visibility", {})
    c_total = _safe(comp, "competitor_total_views_48h", default=0)
    c_name  = _safe(comp, "competitor_name", default="Competitor")
    c_plats = _safe(comp, "platform_breakdown", default=[]) or []

    vis   = audit.get("visibility_audit", {})
    your_total = _safe(vis, "their_total_views_48h", default=0)

    story.append(Spacer(1, 6*mm))
    story.append(Paragraph("Competitor Exposure", styles["h1"]))
    story.append(AccentRule(CONTENT_W))
    story.append(Spacer(1, 3*mm))

    bar = HBar(int(your_total), int(c_total),
               "Your Brand", c_name, color_a=ACCENT, color_b=RED)
    bar.hAlign = "CENTER"
    story.append(bar)
    story.append(Spacer(1, 4*mm))

    story.append(Paragraph(_fmt(c_total), styles["big_accent"]))
    story.append(Paragraph(f"{c_name} views (past 48 hours)", styles["label"]))
    story.append(Spacer(1, 4*mm))

    for el in _platform_cards(c_plats, styles, "card_accent"):
        story.append(el)

    story.append(PageBreak())


def _page4_revenue(story, audit, styles):
    """Revenue Comparison bar chart — no view counts shown."""
    rev = audit.get("revenue_comparison", {})
    own_rev_str  = _safe(rev, "own_revenue", default="$0")
    comp_name    = _safe(rev, "competitor_name", default="Competitor")
    comp_rev_str = _safe(rev, "competitor_revenue", default="$0")
    is_estimate  = rev.get("competitor_revenue_is_estimate", False)

    # Fallback: if competitor_revenue is still N/A or empty, show ~$0
    if not comp_rev_str or comp_rev_str.upper() in ("N/A", "NOT AVAILABLE", ""):
        comp_rev_str = "~$0"
        is_estimate = True

    def _parse_dollar(s):
        try:
            s = str(s).replace("$","").replace(",","").replace("/yr","").replace("/year","").replace("~","").strip()
            if "m" in s.lower() or "M" in s:
                s = s.lower().replace("m","").strip()
                return float(s) * 1_000_000
            if "k" in s.lower() or "K" in s:
                s = s.lower().replace("k","").strip()
                return float(s) * 1_000
            return float(s)
        except: return 0

    own_v  = _parse_dollar(own_rev_str)
    comp_v = _parse_dollar(comp_rev_str)

    story.append(Paragraph("Revenue Comparison", styles["h1"]))
    story.append(AccentRule(CONTENT_W))
    story.append(Spacer(1, 5*mm))

    chart = VBarChart(own_v, comp_v,
                      own_rev_str, comp_rev_str,
                      name_a="You", name_b=comp_name,
                      color_a=TEXT_WHITE, color_b=ACCENT,
                      height=150)
    chart.hAlign = "CENTER"
    story.append(chart)
    story.append(Spacer(1, 6*mm))

    # Two revenue boxes — no views references
    half = (CONTENT_W - 8) / 2
    left = Table([
        [Paragraph("YOUR REVENUE", styles["card_label"])],
        [Paragraph(str(own_rev_str), styles["card_num"])],
    ], colWidths=[half])
    left.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1), BG_CARD),
        ("BOX",(0,0),(-1,-1),0.5,ACCENT_DIM),
        ("ALIGN",(0,0),(-1,-1),"CENTER"),
        ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
    ]))
    right = Table([
        [Paragraph(f"{comp_name.upper()} REVENUE{' (Est.)' if is_estimate else ''}", styles["card_label"])],
        [Paragraph(str(comp_rev_str), styles["card_accent"])],
    ], colWidths=[half])
    right.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1), BG_CARD),
        ("BOX",(0,0),(-1,-1),0.5,ACCENT),
        ("ALIGN",(0,0),(-1,-1),"CENTER"),
        ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
    ]))
    row = Table([[left, right]], colWidths=[half+4, half+4])
    row.setStyle(TableStyle([
        ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
        ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),
    ]))
    story.append(row)

    # No PageBreak — let CPM section follow naturally


def _page5_cpm(story, audit, styles):
    """CPM Comparison: Meta Ads vs Clipping."""
    cost   = audit.get("cost_analysis", {})
    cpm_ads  = float(_safe(cost, "meta_cpm", default=14))
    cpm_clip = float(_safe(cost, "clipping_cpm", default=0.70))
    industry = _safe(audit, "prospect", "industry", default="your industry")

    story.append(Spacer(1, 6*mm))
    story.append(Paragraph("Cost Analysis", styles["h1"]))
    story.append(AccentRule(CONTENT_W))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(f"{industry} — Average Meta Ads CPM", styles["label"]))
    story.append(Spacer(1, 5*mm))

    bars = CPMBars(cpm_ads, cpm_clip, industry, height=100)
    bars.hAlign = "CENTER"
    story.append(bars)
    story.append(Spacer(1, 6*mm))

    bp_style = ParagraphStyle("bullet_point", parent=styles["bullet"],
                               bulletFontName="Helvetica-Bold", bulletFontSize=12,
                               bulletColor=ACCENT, leftIndent=18, bulletIndent=0,
                               spaceBefore=3, spaceAfter=3,
                               backColor=BG_CARD)
    b1 = Paragraph("<bullet>\u2022</bullet>Clips live forever \u2014 compounding views at zero marginal cost", bp_style)
    b2 = Paragraph("<bullet>\u2022</bullet>Ads stop the moment budget stops \u2014 zero residual value", bp_style)
    story.append(b1)
    story.append(Spacer(1, 1*mm))
    story.append(b2)

    story.append(PageBreak())


def _page6_cta(story, audit, styles):
    """CTA page: logo + two proof images + contact info."""
    story.append(Spacer(1, 4*mm))

    # Logo
    if os.path.exists(_IMG_LOGO):
        logo = Image(_IMG_LOGO, width=180, height=45, kind='proportional')
        logo.hAlign = 'CENTER'
        story.append(logo)
        story.append(Spacer(1, 2*mm))
    else:
        story.append(Paragraph("LUMINA CLIPPERS", styles["brand"]))
        story.append(Spacer(1, 1*mm))

    story.append(Paragraph("Content Tracking Dashboard", styles["brand_sub"]))
    story.append(Spacer(1, 3*mm))
    story.append(AccentRule(CONTENT_W))
    story.append(Spacer(1, 4*mm))

    img_w = CONTENT_W
    if os.path.exists(_IMG_VOUCH):
        img1 = Image(_IMG_VOUCH, width=img_w, height=img_w * 0.52,
                     kind='proportional')
        img1.hAlign = 'CENTER'
        story.append(img1)
    story.append(Spacer(1, 3*mm))

    if os.path.exists(_IMG_WALL):
        img2 = Image(_IMG_WALL, width=img_w, height=img_w * 0.50,
                     kind='proportional')
        img2.hAlign = 'CENTER'
        story.append(img2)
    story.append(Spacer(1, 4*mm))

    story.append(AccentRule(CONTENT_W))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph("Book Your Free Strategy Call", styles["cta_big"]))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph('<a href="mailto:rhys@luminaclippers.com" color="#b0c4b0">rhys@luminaclippers.com</a>', styles["cta_email"]))
    story.append(Spacer(1, 1*mm))
    story.append(Paragraph("luminaclippers.com", styles["date"]))


# ═══════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════

def generate_pdf(audit: dict, job_id: str, output_dir: str = "outputs") -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(script_dir, output_dir)
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"{job_id}.pdf")

    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=18*mm,
        title="Lumina Clippers Visibility Audit",
        author="Lumina Clippers",
    )
    st = _styles()
    story = []
    _page1_score(story, audit, st)
    _page2_brand_visibility(story, audit, st)
    _page3_competitor(story, audit, st)
    _page4_revenue(story, audit, st)
    _page5_cpm(story, audit, st)
    _page6_cta(story, audit, st)
    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return filepath


# ═══════════════════════════════════════════════════════════
# SMOKE TEST
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    sample = {
        "prospect": {
            "name": "Jordan Mitchell",
            "company": "UrbanEdge Barbershop",
            "industry": "Men's Grooming",
            "visibility_score": 18,
        },
        "visibility_audit": {
            "their_total_views_48h": 1_820,
            "platform_breakdown": [
                {"platform": "Twitter / X", "their_views": 720},
                {"platform": "TikTok",      "their_views": 540},
                {"platform": "Instagram",   "their_views": 385},
                {"platform": "YouTube",     "their_views": 175},
            ],
        },
        "competitor_visibility": {
            "competitor_name": "StyleKing",
            "competitor_total_views_48h": 56_000,
            "platform_breakdown": [
                {"platform": "Twitter / X", "their_views": 22_000},
                {"platform": "TikTok",      "their_views": 18_500},
                {"platform": "Instagram",   "their_views": 9_200},
                {"platform": "YouTube",     "their_views": 6_300},
            ],
        },
        "revenue_comparison": {
            "own_revenue": "$100k",
            "competitor_name": "StyleKing",
            "competitor_revenue": "~$200k",
            "competitor_revenue_is_estimate": True,
            "own_views_48h": 1_820,
            "competitor_views_48h": 56_000,
        },
        "cost_analysis": {
            "meta_cpm": 14.00,
            "clipping_cpm": 0.70,
        },
        "lumina_fit_score": 91,
        "lumina_pitch": (
            "Jordan, UrbanEdge has strong craft but zero visibility. "
            "Lumina would build your content engine — you focus on the chair."
        ),
    }
    out = generate_pdf(sample, job_id="test_v4_green")
    print(f"PDF: {out}")
